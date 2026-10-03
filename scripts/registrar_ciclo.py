"""Registra un ciclo terminado en docs/ciclos.md (registro versionado de ciclos; sin nombres ni RUC).

  python scripts/registrar_ciclo.py --periodo 2026-S2 [--raiz <carpeta de Drive>]

Lee <raiz>/salida/<periodo>/estado.json y las tablas del ciclo, y agrega (o actualiza) la fila de ese ciclo:
fecha, commit, ventana, cifras clave, estado de Kraljic, versión del histórico, maestro y decisiones humanas.
Las cifras salen de las tablas del ciclo, nunca se escriben a mano. Después, haga commit y la etiqueta
`ciclo-<periodo>` (ver docs/manual_ciclo.md).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd
import yaml

RAIZ_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ejecutar_ciclo import raiz_local  # noqa: E402

REGISTRO = RAIZ_REPO / "docs" / "ciclos.md"
ENCABEZADO = """# Registro de ciclos de análisis de gastos

Una fila por ciclo ejecutado (la escribe `scripts/registrar_ciclo.py`; no editar a mano). Los resultados completos
están en Google Drive › analisis de gastos › `salida/<periodo>/` y `historico/<periodo>__v<N>/`. Cifras en soles
nominales. Las señales son para revisar, no conclusiones.

| Periodo | Histórico | Fecha | Commit | Ventana | Gasto analizado | Prov. clase A | Señales (alta) | Kraljic | Plan | Maestro | Decisiones humanas |
|---|---|---|---|---|---|---|---|---|---|---|---|
"""


def fila_ciclo(d: Path) -> dict:
    e = json.loads((d / "estado.json").read_text(encoding="utf-8"))
    pasos = e["pasos"]
    incompletos = [p for p, x in pasos.items() if x["estado"] not in ("ok", "omitido")]
    if incompletos or len(pasos) < 8:
        raise SystemExit(f"El ciclo {e['periodo']} no está completo (pasos pendientes: {incompletos}). Termínelo antes de registrarlo.")
    t = lambda c, n: pd.read_parquet(d / c / "tablas" / f"{n}.parquet")  # noqa: E731
    ctrl = t("3_descriptivo", "control").set_index("control")["valor_soles"]
    clave = [k for k in ctrl.index if k.startswith("Gasto analizado")][0]
    ventana = re.search(r"\((.*)\)", clave).group(1)
    abc = t("3_descriptivo", "resumen_abc").set_index("clase_abc")
    R = t("4_alertas", "resumen")
    estados = sorted(t("5_kraljic", "kraljic_unidades")["estado"].astype(str).unique())
    hist = re.search(r"\d{4}-S[12]__v\d+", pasos["8_historico"].get("nota", ""))
    decisiones = [re.sub(r"^\S+ \S+ – ", "", x) for x in e["decisiones"]]
    return {
        "periodo": e["periodo"], "historico": hist.group(0) if hist else "—",
        "fecha": e["creado"][:10], "commit": e["versiones"]["codigo"], "ventana": ventana,
        "gasto": f"S/ {ctrl[clave]:,.2f}", "clase_a": f"{int(abc.loc['A', 'proveedores'])} ({abc.loc['A', 'pct_gasto']:.1f} %)",
        "senales": f"{int(R['casos'].sum()):,} ({int(R['alta'].sum()):,})", "kraljic": "; ".join(estados),
        "plan": "sí" if pasos["6_plan"]["estado"] == "ok" else "no (S1)",
        "maestro": "huella " + (re.search(r"huella (\w+)", e["versiones"]["maestro"]) or [None, "?"])[1],
        "decisiones": " · ".join(decisiones) if decisiones else "—",
    }


def registrar(d: Path) -> Path:
    f = fila_ciclo(d)
    linea = "| " + " | ".join(str(v).replace("|", "/") for v in f.values()) + " |"
    texto = REGISTRO.read_text(encoding="utf-8") if REGISTRO.exists() else ENCABEZADO
    lineas = [l for l in texto.splitlines() if not l.startswith(f"| {f['periodo']} | {f['historico']} |")]
    lineas.append(linea)
    REGISTRO.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return REGISTRO


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Registra un ciclo terminado en docs/ciclos.md.")
    ap.add_argument("--periodo", required=True)
    ap.add_argument("--raiz", help="Carpeta de datos (por defecto: config/local.yaml)")
    a = ap.parse_args(argv)
    params = yaml.safe_load((RAIZ_REPO / "config" / "parametros.yaml").read_text(encoding="utf-8"))
    raiz = Path(a.raiz or raiz_local() or params["rutas"]["raiz_datos"])
    d = raiz / params["rutas"]["salida"] / a.periodo
    if not (d / "estado.json").exists():
        print(f"No existe el ciclo {a.periodo} en {d}", file=sys.stderr)
        return 1
    print("Ciclo registrado en", registrar(d))
    print(f"Siguiente paso: git add docs/ciclos.md && git commit -m \"Ciclo {a.periodo}\" && git tag ciclo-{a.periodo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
