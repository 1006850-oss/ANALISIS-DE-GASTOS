"""Eval 1 de la skill – compara un ciclo 2017-S2 del extracto real con las cifras oficiales de docs/bitacora.md.

Las cifras esperadas son las que se validaron en los Hilos 1 a 7 (fuente: docs/bitacora.md). Este archivo no trae data
real: solo totales agregados ya publicados en la bitácora.

Uso: python .claude/skills/analisis-gastos-compras/evals/verificar_ciclo_oficial.py <raiz>/salida/2017-S2
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

OFICIAL = [  # (descripción, valor esperado, tolerancia, hilo)
    ("Filas del extracto", 103_050, 0, "Hilo 1"),
    ("OC distintas", 23_009, 0, "Hilo 1"),
    ("Gasto total de la tabla limpia (S/)", 283_013_851.95, 0.01, "Hilo 1"),
    ("Gasto analizado 2015-S1 a 2017-S2 (S/)", 275_378_383.86, 0.01, "Hilo 3"),
    ("Proveedores en la ventana", 1_399, 0, "Hilo 3/7"),
    ("Proveedores clase A", 81, 0, "Hilo 3"),
    ("Proveedores con una sola OC", 528, 0, "Hilo 3"),
    ("Casos de fraccionamiento", 212, 0, "Hilo 4"),
    ("Fraccionamiento de prioridad alta", 128, 0, "Hilo 4"),
    ("OC autoaprobadas nivel ≥ 2", 1_209, 0, "Hilo 4"),
    ("Facturas anteriores a la OC", 95, 0, "Hilo 4"),
    ("Duplicados (casos)", 312, 0, "Hilo 4"),
    ("Duplicados de prioridad alta", 61, 0, "Hilo 4"),
    ("Señales de prioridad alta (total)", 312, 0, "Hilo 7"),
    ("Unidades de Kraljic", 78, 0, "Hilo 5"),
    ("Unidades Estratégico / Apalancamiento / Cuello / No crítico", "3/13/9/53", None, "Hilo 5"),
    ("Tipos de compra consolidables", 47, 0, "Hilo 6"),
    ("OC pequeñas consolidables", 6_550, 0, "Hilo 6"),
]


def obtenidas(d: Path) -> list:
    t = lambda carpeta, n: pd.read_parquet(d / carpeta / "tablas" / f"{n}.parquet")  # noqa: E731
    limpia = pd.read_parquet(d / "1_limpieza" / "tabla_limpia.parquet", columns=["oc", "monto_gasto"])
    ctrl = t("3_descriptivo", "control").set_index("control")["valor_soles"]
    abc = t("3_descriptivo", "resumen_abc").set_index("clase_abc")
    fr = t("3_descriptivo", "frecuencia_proveedores")
    R = t("4_alertas", "resumen")
    frac = R[R["alerta"].str.startswith("1.")].iloc[0]
    antes = R[R["subtipo"] == "Factura anterior a la OC"].iloc[0]
    dup = R[R["alerta"].str.startswith("3.")]
    kres = t("5_kraljic", "kraljic_resumen").set_index("cuadrante")["unidades"]
    pl = t("6_plan", "plan_plan")
    pp = pl[pl["segmento"] != "Por proyecto"]
    cons = pp[(pp["modalidad_si_se_consolida"] == "Licitación") & (pp["modalidad_por_oc_tipica"] != "Licitación")]
    filas = pd.read_excel(d / "1_limpieza" / "reporte_calidad.xlsx", sheet_name="Por_semestre")["filas"].sum()
    return [
        filas, limpia["oc"].nunique(), limpia["monto_gasto"].sum(),
        [v for k, v in ctrl.items() if k.startswith("Gasto analizado")][0],
        len(t("3_descriptivo", "pareto_proveedores")), abc.loc["A", "proveedores"], int((fr["n_oc"] == 1).sum()),
        frac["casos"], frac["alta"], R[R["alerta"].str.startswith("2.")]["casos"].sum(), antes["casos"],
        dup["casos"].sum(), dup["alta"].sum(), R["alta"].sum(), int(kres.sum()),
        "/".join(str(int(kres.get(q, 0))) for q in ["Estratégico", "Apalancamiento", "Cuello de botella", "No crítico"]),
        len(cons), int(cons["n_oc_ultimo_anio"].sum()),
    ]


def main(argv: list[str]) -> int:
    d = Path(argv[0])
    ok_total = True
    print(f"| Cifra | Oficial | Obtenida | Fuente | ¿Coincide? |\n|---|---|---|---|---|")
    for (nombre, esperado, tol, hilo), valor in zip(OFICIAL, obtenidas(d)):
        ok = valor == esperado if tol is None else abs(float(valor) - float(esperado)) <= tol
        ok_total &= bool(ok)
        fmt = (lambda x: x) if tol is None else (lambda x: f"{float(x):,.2f}" if tol else f"{int(x):,}")
        print(f"| {nombre} | {fmt(esperado)} | {fmt(valor)} | {hilo} | {'✔' if ok else '✖'} |")
    print("\nResultado:", "TODAS COINCIDEN" if ok_total else "HAY DIFERENCIAS")
    return 0 if ok_total else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
