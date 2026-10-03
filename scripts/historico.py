"""Hilo 8 – Histórico acumulado y comparación entre ciclos.

Cada ciclo AGREGA una carpeta al histórico, sin sobrescribir nunca otra (llave: periodo + versión):
  historico/<periodo>__v<N>/   kpis, pareto, categorias, subcategorias, alertas (con llave estable), kraljic
  historico/indice.csv         una fila por ciclo guardado (fecha, commit, versiones de reglas y maestro, gasto)

La comparación con el ciclo anterior produce comparacion_<actual>_vs_<anterior>.xlsx y un resumen en texto
(SIN nombres ni RUC, apto para leerse en el chat):
  - proveedores que suben o bajan de clase ABC, que entran o salen de la ventana
  - categorías y subcategorías que crecen o caen (gasto del último semestre de cada ciclo)
  - alertas nuevas vs. recurrentes (misma llave en ambos ciclos)

Uso:
  python scripts/historico.py agregar --ciclo <salida/AAAA-SN> --historico <carpeta> --periodo 2017-S2 [--meta meta.json]
  python scripts/historico.py comparar --historico <carpeta> --actual 2017-S2 [--anterior 2017-S1] --salida <carpeta>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clasificar import escribir_excel  # noqa: E402
from generar_excel import cargar_tablas  # noqa: E402

# Llave estable de cada alerta (la numeración FR-0001… cambia entre corridas; estas columnas no).
LLAVES_ALERTAS = {
    "fraccionamiento": ("1. Compras fraccionadas", ["proveedor_id", "sede", "subcategoria", "desde"], "suma_oc"),
    "autoaprobacion": ("2. Autoaprobación", ["oc"], "gasto"),
    "duplicados": ("3. Duplicados", ["tipo", "oc", "facturas"], "monto"),
    "ciclo_oc_factura": ("4. Ciclo OC → factura", ["tipo", "oc"], "gasto"),
    "giro_proveedor": ("6. Giro del proveedor", ["proveedor_id"], "gasto"),
    "concentracion_comprador": ("7. Concentración comprador–proveedor", ["proveedor_id", "comprador_principal"], "gasto"),
}
PERIODO = re.compile(r"^\d{4}-S[12]$")


def _carpetas(historico: Path) -> pd.DataFrame:
    filas = []
    for d in sorted(historico.glob("*__v*")):
        p, v = d.name.split("__v")
        filas.append({"periodo": p, "version": int(v), "carpeta": d})
    return pd.DataFrame(filas, columns=["periodo", "version", "carpeta"])


def alertas_con_llave(T: dict[str, pd.DataFrame]) -> pd.DataFrame:
    partes = []
    for tabla, (nombre, cols, monto) in LLAVES_ALERTAS.items():
        df = T.get(f"alert.{tabla}")
        if df is None or df.empty:
            continue
        x = df.copy()
        llave = x[cols[0]].astype(str)
        for c in cols[1:]:
            llave = llave + "|" + x[c].astype(str)
        subtipo = x["tipo"].astype(str) if "tipo" in x else ""
        partes.append(pd.DataFrame({"alerta": nombre, "subtipo": subtipo, "llave": tabla + ":" + llave,
                                    "prioridad": x.get("prioridad", ""), "monto": x[monto].astype(float)}))
    for tabla, col in [("adicionales_sede", "sede"), ("adicionales_proveedor", "proveedor_id")]:
        df = T.get(f"alert.{tabla}")
        if df is None or df.empty:
            continue
        x = df[df["alerta"].astype(bool)]
        partes.append(pd.DataFrame({"alerta": "5. Adicionales de obra", "subtipo": tabla.split("_")[1],
                                    "llave": tabla + ":" + x[col].astype(str), "prioridad": x["prioridad"],
                                    "monto": x["gasto_adicionales"].astype(float)}))
    cols = ["alerta", "subtipo", "llave", "prioridad", "monto"]
    return pd.concat(partes, ignore_index=True)[cols] if partes else pd.DataFrame(columns=cols)


def agregar(ciclo: Path, historico: Path, periodo: str, meta: dict | None = None) -> Path:
    """Guarda el ciclo en historico/<periodo>__v<N> (N = siguiente versión libre). Nunca sobrescribe."""
    if not PERIODO.match(periodo):
        raise ValueError(f"Periodo inválido: {periodo} (formato AAAA-S1 o AAAA-S2)")
    historico.mkdir(parents=True, exist_ok=True)
    previas = _carpetas(historico)
    version = int(previas.loc[previas["periodo"] == periodo, "version"].max()) + 1 if \
        (previas["periodo"] == periodo).any() else 1
    destino = historico / f"{periodo}__v{version}"
    destino.mkdir(parents=False, exist_ok=False)   # falla si ya existe: nunca sobrescribe

    T = cargar_tablas({"desc": ciclo / "3_descriptivo", "alert": ciclo / "4_alertas", "kraljic": ciclo / "5_kraljic"})
    ctrl = T["desc.control"].set_index("control")["valor_soles"]
    gasto = float([v for k, v in ctrl.items() if k.startswith("Gasto analizado")][0])
    abc = T["desc.resumen_abc"].set_index("clase_abc")
    R = T["alert.resumen"]
    tc = pd.read_parquet(ciclo / "2_clasificacion" / "tabla_clasificada.parquet", columns=["semestre", "monto_gasto"])
    t_sem = tc.loc[tc["semestre"] == periodo, "monto_gasto"].sum()
    kpis = pd.DataFrame([
        ("gasto_analizado", gasto), ("gasto_semestre", float(t_sem)), ("proveedores", len(T["desc.pareto_proveedores"])),
        ("proveedores_clase_a", float(abc.loc["A", "proveedores"])), ("pct_gasto_clase_a", float(abc.loc["A", "pct_gasto"])),
        ("alertas_casos", float(R["casos"].sum())), ("alertas_alta", float(R["alta"].sum())),
    ], columns=["indicador", "valor"])
    kpis.to_parquet(destino / "kpis.parquet", index=False)
    T["desc.pareto_proveedores"][["proveedor_id", "proveedor", "gasto", "n_oc", "clase_abc"]].to_parquet(
        destino / "pareto.parquet", index=False)
    # Categorías y subcategorías: gasto del ÚLTIMO semestre del ciclo (las ventanas de dos ciclos se superponen;
    # el semestre sí es comparable entre ciclos).
    t = pd.read_parquet(ciclo / "2_clasificacion" / "tabla_clasificada.parquet",
                        columns=["semestre", "categoria", "subcategoria", "monto_gasto"])
    t = t[t["semestre"] == periodo]
    for nombre, cols in [("categorias", ["categoria"]), ("subcategorias", ["categoria", "subcategoria"])]:
        g = t.groupby(cols, dropna=False)["monto_gasto"].sum().rename("gasto").reset_index()
        g["pct_gasto"] = g["gasto"] / g["gasto"].sum() * 100 if len(g) else 0.0
        g.to_parquet(destino / f"{nombre}.parquet", index=False)
    alertas_con_llave(T).to_parquet(destino / "alertas.parquet", index=False)
    if "kraljic.kraljic_unidades" in T:
        T["kraljic.kraljic_unidades"][["unidad", "cuadrante", "estado", "gasto"]].to_parquet(
            destino / "kraljic.parquet", index=False)

    fila = {"periodo": periodo, "version": version, "guardado": datetime.now().isoformat(timespec="seconds"),
            "gasto_analizado": round(gasto, 2), **(meta or {})}
    (destino / "meta.json").write_text(json.dumps(fila, ensure_ascii=False, indent=2), encoding="utf-8")
    indice = historico / "indice.csv"
    previo = pd.read_csv(indice, dtype=str) if indice.exists() else pd.DataFrame()
    pd.concat([previo, pd.DataFrame([fila]).astype(str)], ignore_index=True).to_csv(indice, index=False)
    return destino


def ultima_version(historico: Path, periodo: str) -> Path:
    c = _carpetas(historico)
    c = c[c["periodo"] == periodo]
    if c.empty:
        raise FileNotFoundError(f"No hay ciclo {periodo} en el histórico {historico}")
    return c.sort_values("version").iloc[-1]["carpeta"]


def periodo_anterior(historico: Path, actual: str) -> str | None:
    previos = sorted(p for p in _carpetas(historico)["periodo"].unique() if p < actual)
    return previos[-1] if previos else None


def _variacion(a: pd.DataFrame, b: pd.DataFrame, llave: list[str]) -> pd.DataFrame:
    x = a.merge(b, on=llave, how="outer", suffixes=("_actual", "_anterior")).fillna(
        {"gasto_actual": 0.0, "gasto_anterior": 0.0})
    x["variacion"] = x["gasto_actual"] - x["gasto_anterior"]
    x["variacion_pct"] = (x["variacion"] / x["gasto_anterior"].where(x["gasto_anterior"] != 0) * 100).round(1)
    return x.sort_values("variacion", ascending=False)


def comparar(historico: Path, actual: str, anterior: str | None = None) -> dict[str, pd.DataFrame]:
    anterior = anterior or periodo_anterior(historico, actual)
    if anterior is None:
        raise ValueError(f"No hay un ciclo anterior a {actual} en el histórico")
    A, B = ultima_version(historico, actual), ultima_version(historico, anterior)
    leer = lambda d, n: pd.read_parquet(d / f"{n}.parquet")  # noqa: E731

    pa, pb = leer(A, "pareto"), leer(B, "pareto")
    p = pa.merge(pb[["proveedor_id", "gasto", "clase_abc"]], on="proveedor_id", how="outer",
                 suffixes=("_actual", "_anterior"))
    p["proveedor"] = p["proveedor"].fillna(p["proveedor_id"].map(dict(zip(pb["proveedor_id"], pb["proveedor"]))))
    p[["clase_abc_actual", "clase_abc_anterior"]] = p[["clase_abc_actual", "clase_abc_anterior"]].fillna("—")
    orden = {"A": 0, "B": 1, "C": 2, "—": 3}
    delta = p["clase_abc_actual"].map(orden) - p["clase_abc_anterior"].map(orden)
    p["cambio"] = "Igual"
    p.loc[delta < 0, "cambio"] = "Sube de clase"
    p.loc[delta > 0, "cambio"] = "Baja de clase"
    p.loc[p["clase_abc_anterior"] == "—", "cambio"] = "Proveedor nuevo en la ventana"
    p.loc[p["clase_abc_actual"] == "—", "cambio"] = "Sale de la ventana"
    p = p[["cambio", "proveedor_id", "proveedor", "clase_abc_anterior", "clase_abc_actual", "gasto_anterior",
           "gasto_actual"]].fillna({"gasto_anterior": 0.0, "gasto_actual": 0.0})

    cat = _variacion(leer(A, "categorias")[["categoria", "gasto"]], leer(B, "categorias")[["categoria", "gasto"]],
                     ["categoria"])
    sub = _variacion(leer(A, "subcategorias")[["categoria", "subcategoria", "gasto"]],
                     leer(B, "subcategorias")[["categoria", "subcategoria", "gasto"]], ["categoria", "subcategoria"])

    aa, ab = leer(A, "alertas"), leer(B, "alertas")
    aa["estado"] = aa["llave"].isin(ab["llave"]).map({True: "Recurrente", False: "Nueva"})
    cerradas = ab[~ab["llave"].isin(aa["llave"])].assign(estado="Ya no aparece")
    alertas = pd.concat([aa, cerradas], ignore_index=True)
    res_alertas = alertas.pivot_table(index="alerta", columns="estado", values="llave", aggfunc="count",
                                      fill_value=0).reset_index()

    ka, kb = leer(A, "kpis").set_index("indicador")["valor"], leer(B, "kpis").set_index("indicador")["valor"]
    kpis = pd.DataFrame({"indicador": ka.index, "anterior": kb.reindex(ka.index).to_numpy(), "actual": ka.to_numpy()})
    kpis["variacion"] = kpis["actual"] - kpis["anterior"]

    cambios = p["cambio"].value_counts().rename_axis("cambio").reset_index(name="proveedores")
    resumen = pd.DataFrame({"dato": ["Ciclo actual", "Ciclo anterior"], "valor": [A.name, B.name]})
    return {"Resumen": resumen, "Indicadores": kpis, "Cambios_Pareto": cambios,
            "Pareto_detalle": p[p["cambio"] != "Igual"], "Categorias": cat, "Subcategorias": sub,
            "Alertas_resumen": res_alertas, "Alertas_detalle": alertas, "_anterior": anterior}


def _m(x: float) -> str:
    return f"S/ {x / 1e6:,.1f} M"


def texto_resumen(r: dict, actual: str) -> str:
    """Resumen SIN nombres ni RUC (solo conteos, montos y categorías)."""
    k = r["Indicadores"].set_index("indicador")
    c = r["Cambios_Pareto"].set_index("cambio")["proveedores"]
    cat = r["Categorias"]
    sube = cat.head(3)
    baja = cat.sort_values("variacion").head(3)
    al = r["Alertas_resumen"].set_index("alerta")
    lineas = [f"# Comparación {actual} vs. {r['_anterior']}", "",
              f"- Gasto del semestre: {_m(k.loc['gasto_semestre', 'anterior'])} ({r['_anterior']}) → "
              f"{_m(k.loc['gasto_semestre', 'actual'])} ({actual}).",
              f"- Gasto de la ventana analizada: {_m(k.loc['gasto_analizado', 'anterior'])} → "
              f"{_m(k.loc['gasto_analizado', 'actual'])} (las ventanas se superponen).",
              f"- Proveedores clase A: {k.loc['proveedores_clase_a', 'anterior']:.0f} → {k.loc['proveedores_clase_a', 'actual']:.0f}.",
              "- Cambios en el Pareto (proveedores): " + ", ".join(f"{i.lower()}: {n}" for i, n in c.items() if i != "Igual") + ".",
              "- Categorías que más crecen (gasto del semestre): " + ("; ".join(
                  f"{r_.categoria} (+{_m(r_.variacion)})" for r_ in sube.itertuples() if r_.variacion > 0) or "ninguna") + ".",
              "- Categorías que más caen (gasto del semestre): " + ("; ".join(
                  f"{r_.categoria} ({_m(r_.variacion)})" for r_ in baja.itertuples() if r_.variacion < 0) or "ninguna") + ".",
              "- Alertas (nuevas / recurrentes / ya no aparecen):"]
    for a, f in al.iterrows():
        lineas.append(f"  - {a}: {int(f.get('Nueva', 0))} / {int(f.get('Recurrente', 0))} / {int(f.get('Ya no aparece', 0))}")
    lineas += ["", "Las alertas son señales para revisar, no conclusiones. Detalle (con proveedores) en el Excel de comparación."]
    return "\n".join(lineas)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Histórico acumulado de ciclos (Hilo 8).")
    sp = ap.add_subparsers(dest="accion", required=True)
    g = sp.add_parser("agregar")
    g.add_argument("--ciclo", required=True)
    g.add_argument("--historico", required=True)
    g.add_argument("--periodo", required=True)
    g.add_argument("--meta", help="JSON con commit y versiones (lo escribe ejecutar_ciclo.py)")
    c = sp.add_parser("comparar")
    c.add_argument("--historico", required=True)
    c.add_argument("--actual", required=True)
    c.add_argument("--anterior")
    c.add_argument("--salida", required=True)
    a = ap.parse_args(argv)
    if a.accion == "agregar":
        meta = json.loads(Path(a.meta).read_text(encoding="utf-8")) if a.meta else None
        print("Guardado en el histórico:", agregar(Path(a.ciclo), Path(a.historico), a.periodo, meta))
        return 0
    r = comparar(Path(a.historico), a.actual, a.anterior)
    salida = Path(a.salida)
    salida.mkdir(parents=True, exist_ok=True)
    escribir_excel(salida / f"comparacion_{a.actual}_vs_{r['_anterior']}.xlsx", {k: v for k, v in r.items() if k[0] != "_"})
    txt = texto_resumen(r, a.actual)
    (salida / "comparacion_resumen.md").write_text(txt, encoding="utf-8")
    print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
