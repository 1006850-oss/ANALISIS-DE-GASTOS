"""Hilo 5 – Matriz de Kraljic.

Ubica cada categoría, unidad de compra (subcategoría gestionable; Obras por tipo de trabajo) y producto en uno
de los cuatro cuadrantes: estratégico, apalancamiento, cuello de botella y no crítico.

- Eje de impacto (data): alto si la unidad está dentro del 80 % del gasto (Pareto).
- Eje de riesgo: 40 % data (HHI > 1 800, ≤ 3 proveedores, proveedor principal ≥ 50 %) + 60 % criterio experto
  (4 criterios de 1 a 5). Si no hay puntaje experto se usa la propuesta de IA y el resultado queda "provisional";
  si tampoco hay propuesta, solo la data ("provisional – solo data").

Entrada: tabla_clasificada.parquet + config/parametros.yaml + config/kraljic.yaml (+ taller completado, opcional).
Salidas en --salida: kraljic.xlsx, kraljic_taller.xlsx (para el taller), tablas/*.parquet, graficos/*.png.

Uso:
  python scripts/kraljic.py --tabla <tabla_clasificada.parquet> --salida <carpeta> [--taller kraljic_taller.xlsx]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from analizar import filtrar_periodo  # noqa: E402
from clasificar import escribir_excel  # noqa: E402

PARAMETROS_DEFECTO = RAIZ / "config" / "parametros.yaml"
KRALJIC_DEFECTO = RAIZ / "config" / "kraljic.yaml"
CUADRANTES = ["Estratégico", "Apalancamiento", "Cuello de botella", "No crítico"]
CRITERIOS = ["alternativas", "criticidad", "complejidad", "reemplazo"]


def cargar_yaml(ruta) -> dict:
    with open(ruta, encoding="utf-8") as f:
        return yaml.safe_load(f)


def cuadrante(alto_impacto: pd.Series, alto_riesgo: pd.Series) -> pd.Series:
    return pd.Series(np.select([alto_impacto & alto_riesgo, alto_impacto & ~alto_riesgo, ~alto_impacto & alto_riesgo],
                               CUADRANTES[:3], CUADRANTES[3]), index=alto_impacto.index)


def preparar(t: pd.DataFrame, params: dict, K: dict) -> pd.DataFrame:
    A = params["analisis"]
    t, _ = filtrar_periodo(t, A["periodo_desde"], A["periodo_hasta"])
    t = t[~t["excluir_de_kraljic"]].copy()
    U = K["unidad"]
    obras = t["categoria"] == U["categoria_por_producto"]
    t["unidad"] = np.where(obras, U["prefijo"] + t["producto"].astype(str), t["subcategoria"].astype(str))
    return t


def indicadores(t: pd.DataFrame, cols: list[str], K: dict) -> pd.DataFrame:
    """Gasto, proveedores, HHI, participación del principal, impacto (Pareto) y puntaje de datos por nivel."""
    x = t.groupby(cols + ["proveedor_id"])["monto_gasto"].sum().reset_index()
    x["share"] = x["monto_gasto"] / x.groupby(cols)["monto_gasto"].transform("sum")
    g = x.groupby(cols).agg(gasto=("monto_gasto", "sum"), n_proveedores=("proveedor_id", "nunique"),
                            hhi=("share", lambda s: float((s ** 2).sum() * 10000)),
                            pct_principal=("share", lambda s: float(s.max() * 100))).reset_index()
    g["n_sedes"] = g.set_index(cols).index.map(t.groupby(cols)["sede"].nunique())
    g = g.sort_values(["gasto"] + cols, ascending=[False] + [True] * len(cols)).reset_index(drop=True)
    g["pct_gasto"] = g["gasto"] / g["gasto"].sum() * 100
    g["pct_acumulado"] = g["pct_gasto"].cumsum()
    g["alto_impacto"] = (g["pct_acumulado"] - g["pct_gasto"]) < K["impacto"]["corte_pareto"] * 100
    D = K["riesgo"]["datos"]
    ind = pd.DataFrame({"ind_hhi": g["hhi"] > D["hhi_alto"],
                        "ind_pocos_proveedores": g["n_proveedores"] <= D["max_proveedores"],
                        "ind_dependencia": g["pct_principal"] >= D["participacion_principal"] * 100})
    g = pd.concat([g, ind], axis=1)
    g["puntaje_datos"] = ind.astype(int).mul(4).add(1).mean(axis=1)
    return g


def puntajes_expertos(unidades: pd.Series, K: dict, taller: pd.DataFrame | None) -> pd.DataFrame:
    """Puntaje de riesgo experto por unidad (1–5) y su fuente: experto > propuesta IA > sin puntaje."""
    pesos = {c: K["riesgo"]["criterios_expertos"][c]["peso"] for c in CRITERIOS}
    prop = K.get("propuesta_ia") or {}
    filas = []
    exp = taller.set_index("Unidad") if taller is not None and len(taller) else None
    for u in unidades:
        fuente, vals = None, None
        if exp is not None and u in exp.index:
            v = [pd.to_numeric(exp.loc[u, f"Experto: {c}"], errors="coerce") for c in CRITERIOS]
            if all(pd.notna(v)):
                fuente, vals = "experto", v
        if vals is None and u in prop:
            fuente, vals = "propuesta IA", [prop[u][c] for c in CRITERIOS]
        fila = {"unidad": u, "fuente_riesgo_experto": fuente or "sin puntaje"}
        for c, v in zip(CRITERIOS, vals or [np.nan] * 4):
            fila[f"riesgo_{c}"] = v
        fila["puntaje_experto"] = float(sum(pesos[c] * v for c, v in zip(CRITERIOS, vals))) if vals else np.nan
        fila["justificacion_ia"] = prop.get(u, {}).get("justificacion", "")
        filas.append(fila)
    return pd.DataFrame(filas)


def combinar(g: pd.DataFrame, K: dict) -> pd.DataFrame:
    R = K["riesgo"]
    tiene = g["puntaje_experto"].notna()
    g["puntaje_riesgo"] = np.where(tiene, R["peso_datos"] * g["puntaje_datos"] + R["peso_expertos"] * g["puntaje_experto"],
                                   g["puntaje_datos"])
    g["alto_riesgo"] = g["puntaje_riesgo"] >= R["corte_alto"]
    # Sensibilidad: unidades cerca del corte de riesgo (pueden cambiar de cuadrante con el taller)
    g["cerca_del_corte"] = (g["puntaje_riesgo"] - R["corte_alto"]).abs() < R.get("margen_sensibilidad", 0.25)
    g["cuadrante"] = cuadrante(g["alto_impacto"], g["alto_riesgo"])
    g["estado"] = np.select([g["fuente_riesgo_experto"] == "experto", g["fuente_riesgo_experto"] == "propuesta IA"],
                            ["validado por expertos", "provisional (propuesta IA)"], "provisional (solo data)")
    return g


def matriz_kraljic(t_completa: pd.DataFrame, params: dict, K: dict, taller: pd.DataFrame | None = None) -> dict:
    t = preparar(t_completa, params, K)
    # Nivel unidad (el que se lleva al taller)
    u = indicadores(t, ["unidad"], K)
    u.insert(1, "categoria", u["unidad"].map(t.groupby("unidad")["categoria"].first()))
    u = u.merge(puntajes_expertos(u["unidad"], K, taller), on="unidad", how="left")
    u = combinar(u, K)
    # Nivel categoría: riesgo experto = promedio ponderado por gasto del puntaje experto de sus unidades
    c = indicadores(t, ["categoria"], K)
    w = u.dropna(subset=["puntaje_experto"]).assign(p=lambda d: d["puntaje_experto"] * d["gasto"])
    agg = w.groupby("categoria").agg(p=("p", "sum"), g=("gasto", "sum"))
    c["puntaje_experto"] = c["categoria"].map(agg["p"] / agg["g"])
    fuentes = u.groupby("categoria")["fuente_riesgo_experto"].agg(
        lambda s: "experto" if (s == "experto").all() else ("propuesta IA" if s.isin(["experto", "propuesta IA"]).all() else "sin puntaje"))
    c["fuente_riesgo_experto"] = c["categoria"].map(fuentes)
    c = combinar(c, K)
    # Nivel producto: data propia + puntaje experto de su unidad
    p = indicadores(t, ["unidad", "producto"], K)
    p.insert(0, "categoria", p["unidad"].map(t.groupby("unidad")["categoria"].first()))
    p = p.merge(u[["unidad", "puntaje_experto", "fuente_riesgo_experto"]], on="unidad", how="left")
    p = combinar(p, K)
    resumen = (u.groupby("cuadrante").agg(unidades=("unidad", "size"), gasto=("gasto", "sum"))
               .reindex(CUADRANTES).fillna(0).reset_index())
    resumen["pct_gasto"] = resumen["gasto"] / u["gasto"].sum() * 100
    return {"unidades": u, "categorias": c, "productos": p, "resumen": resumen,
            "gasto_gestionable": float(u["gasto"].sum())}


# --------------------------------------------------------------------------- taller

INSTRUCCIONES_TALLER = [
    "Taller de riesgo de suministro – Matriz de Kraljic",
    "",
    "Objetivo: calificar el RIESGO DE SUMINISTRO de cada unidad de compra, de 1 (bajo) a 5 (alto).",
    "El IMPACTO ya está calculado con la data (unidades que suman el 80 % del gasto = alto impacto).",
    "",
    "Criterios (peso en el puntaje experto):",
    "  alternativas (30 %): 1 = muchos proveedores alternativos · 5 = casi ninguno.",
    "  criticidad (30 %): 1 = si falla, casi no afecta · 5 = se detienen las clases o la sede.",
    "  complejidad (20 %): 1 = bien estándar · 5 = especificación técnica compleja.",
    "  reemplazo (20 %): 1 = se cambia de proveedor en días · 5 = toma meses o es inviable.",
    "",
    "Cómo llenar:",
    "  1. Lea la propuesta de IA y su justificación (columnas 'IA: …'). Es solo un punto de partida.",
    "  2. Escriba su puntaje en las columnas 'Experto: …' (números del 1 al 5). Deje vacío si no sabe.",
    "  3. Priorice las filas con 'Prioridad taller' = Alta (alto impacto) y Media (cuellos de botella con más gasto).",
    "  4. Devuelva el archivo: python scripts/kraljic.py --taller kraljic_taller.xlsx recalcula la matriz.",
    "",
    "Puntaje de riesgo final = 40 % data (HHI > 1 800, ≤ 3 proveedores, principal ≥ 50 %) + 60 % expertos.",
    "Riesgo alto si el puntaje final es 3.0 o más. Repetir el taller una vez al año.",
]


def plantilla_taller(u: pd.DataFrame, con_montos: bool = True) -> dict[str, pd.DataFrame]:
    d = u.copy()
    d["Prioridad taller"] = np.where(d["alto_impacto"] | d["cerca_del_corte"], "Alta",
                                     np.where(d["cuadrante"] == "Cuello de botella", "Media", "Baja"))
    cols = {"unidad": "Unidad", "categoria": "Categoría", "pct_gasto": "% gasto", "alto_impacto": "Alto impacto",
            "n_proveedores": "N° proveedores", "hhi": "HHI", "pct_principal": "% proveedor principal",
            "puntaje_datos": "Puntaje datos (1-5)", "puntaje_riesgo": "Riesgo actual (1-5)",
            "cuadrante": "Cuadrante actual"}
    if con_montos:
        cols = {**{"unidad": "Unidad", "categoria": "Categoría", "gasto": "Gasto S/"}, **cols}
    x = d[list(cols) + ["Prioridad taller"]].rename(columns=cols)
    prop = d.set_index("unidad")
    for c in CRITERIOS:
        x[f"IA: {c}"] = x["Unidad"].map(prop[f"riesgo_{c}"]) if (prop["fuente_riesgo_experto"] != "experto").any() else np.nan
    x["IA: justificación"] = x["Unidad"].map(prop["justificacion_ia"])
    for c in CRITERIOS:
        x[f"Experto: {c}"] = ""
    x["Experto: comentario"] = ""
    orden = {"Alta": 0, "Media": 1, "Baja": 2}
    x = x.assign(_o=x["Prioridad taller"].map(orden)).sort_values(["_o", "% gasto"], ascending=[True, False]).drop(columns="_o")
    return {"Instrucciones": pd.DataFrame({"Instrucciones": INSTRUCCIONES_TALLER}), "Unidades": x}


# --------------------------------------------------------------------------- gráficos

COLORES = {"Estratégico": "#2a78d6", "Apalancamiento": "#eb6834", "Cuello de botella": "#1baf7a", "No crítico": "#eda100"}


def grafico(df: pd.DataFrame, etiqueta: str, titulo: str, ruta: Path, K: dict, n_etiquetas: int = 10) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                         "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
    from matplotlib.lines import Line2D
    from matplotlib.ticker import FuncFormatter
    piso = 0.01  # unidades con menos de 0.01 % del gasto se dibujan en el piso del eje
    y = df["pct_gasto"].clip(lower=piso)
    fig, ax = plt.subplots(figsize=(10, 6.5))
    tam = 30 + 1500 * df["gasto"] / df["gasto"].max()
    for q in CUADRANTES:
        m = df["cuadrante"] == q
        ax.scatter(df.loc[m, "puntaje_riesgo"], y[m], s=tam[m], color=COLORES[q], alpha=0.8,
                   edgecolor="#fcfcfb", linewidth=1.5)
    corte_imp = df.loc[df["alto_impacto"], "pct_gasto"].min()
    ax.axhline(corte_imp, color="#52514e", lw=0.8, ls=":")
    ax.axvline(K["riesgo"]["corte_alto"], color="#52514e", lw=0.8, ls=":")
    etiquetas = df.nlargest(n_etiquetas, "gasto")
    for k, (_, r) in enumerate(etiquetas.iterrows()):
        ax.annotate(str(r[etiqueta])[:30], (r["puntaje_riesgo"], r["pct_gasto"]), fontsize=7, color="#0b0b0b",
                    xytext=(8, 10 if k % 2 == 0 else -12), textcoords="offset points",
                    arrowprops={"arrowstyle": "-", "color": "#a3a29c", "lw": 0.6})
    ax.set_yscale("log")
    ax.set_ylim(piso * 0.8, df["pct_gasto"].max() * 2)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g} %"))
    ax.set_xlim(0.8, 5.2)
    ax.set_xlabel("Riesgo de suministro (1 = bajo, 5 = alto)", color="#52514e")
    ax.set_ylabel("Impacto: % del gasto gestionable (escala logarítmica)", color="#52514e")
    ax.set_title(titulo, loc="left", color="#0b0b0b", fontsize=11)
    for x_, y_, txt in [(1.0, df["pct_gasto"].max() * 1.4, "Apalancamiento"), (4.3, df["pct_gasto"].max() * 1.4, "Estratégico"),
                        (1.0, piso * 1.1, "No crítico"), (4.3, piso * 1.1, "Cuello de botella")]:
        ax.text(x_, y_, txt, fontsize=8, color="#52514e", style="italic")
    manijas = [Line2D([0], [0], marker="o", ls="", markersize=8, markerfacecolor=COLORES[q], markeredgecolor="none",
                      label=f"{q} ({int((df['cuadrante'] == q).sum())})") for q in CUADRANTES]
    ax.legend(handles=manijas, frameon=False, loc="upper right", bbox_to_anchor=(1, 0.92), fontsize=8)
    ax.grid(color="#e6e5e1", lw=0.5)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.01, "Fuente: ERP 2015-S1 a 2017-S2. Riesgo = 40 % data + 60 % criterio experto "
             "(provisional mientras no se haga el taller). Tamaño del punto = gasto.", fontsize=7, color="#52514e")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(ruta, dpi=150)
    plt.close(fig)
    return ruta


# --------------------------------------------------------------------------- CLI

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Matriz de Kraljic (Hilo 5).")
    ap.add_argument("--tabla", required=True)
    ap.add_argument("--salida", required=True)
    ap.add_argument("--taller", help="kraljic_taller.xlsx completado por los expertos (opcional)")
    ap.add_argument("--parametros", default=str(PARAMETROS_DEFECTO))
    ap.add_argument("--kraljic", default=str(KRALJIC_DEFECTO))
    ap.add_argument("--plantilla-repo", help="Ruta para guardar la plantilla del taller SIN montos (para el repositorio)")
    a = ap.parse_args(argv)
    params, K = cargar_yaml(a.parametros), cargar_yaml(a.kraljic)
    taller = pd.read_excel(a.taller, sheet_name="Unidades") if a.taller else None
    r = matriz_kraljic(pd.read_parquet(a.tabla), params, K, taller)
    carpeta = Path(a.salida)
    (carpeta / "tablas").mkdir(parents=True, exist_ok=True)
    (carpeta / "graficos").mkdir(parents=True, exist_ok=True)
    for k in ["unidades", "categorias", "productos", "resumen"]:
        r[k].to_parquet(carpeta / "tablas" / f"kraljic_{k}.parquet", index=False)
    estrategias = pd.read_csv(RAIZ / "docs" / "estrategias_kraljic.csv") if (RAIZ / "docs" / "estrategias_kraljic.csv").exists() else None
    hojas = {"Resumen": r["resumen"], "Unidades": r["unidades"], "Categorias": r["categorias"], "Productos": r["productos"]}
    if estrategias is not None:
        hojas["Estrategias"] = estrategias
    escribir_excel(carpeta / "kraljic.xlsx", hojas)
    escribir_excel(carpeta / "kraljic_taller.xlsx", plantilla_taller(r["unidades"]))
    if a.plantilla_repo:
        escribir_excel(a.plantilla_repo, plantilla_taller(r["unidades"], con_montos=False))
    grafico(r["unidades"], "unidad", "Matriz de Kraljic por unidad de compra", carpeta / "graficos" / "kraljic_unidades.png", K)
    grafico(r["categorias"], "categoria", "Matriz de Kraljic por categoría", carpeta / "graficos" / "kraljic_categorias.png", K, 14)
    print(r["resumen"].round(1).to_string(index=False))
    print(r["unidades"]["estado"].value_counts().to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
