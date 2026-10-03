"""Hilo 3 – Análisis descriptivo del gasto.

Entrada: tabla_clasificada.parquet (Hilo 2) + config/parametros.yaml.
Salidas en --salida:
  - tablas/*.parquet                 una tabla por análisis (para el tablero del Hilo 7)
  - resultados_descriptivos.xlsx     una hoja por análisis + hoja "Control" (cuadres)
  - graficos/*.png                   gráficos de verificación
  - hallazgos.md                     hallazgos principales con su cifra y tabla de origen

Uso:
  python scripts/analizar.py --tabla <tabla_clasificada.parquet> --salida <carpeta> [--desde 2015-S1 --hasta 2017-S2]

Montos en soles nominales. Compradores siempre con código (P001…).
"""
from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

RAIZ = Path(__file__).resolve().parents[1]
PARAMETROS_DEFECTO = RAIZ / "config" / "parametros.yaml"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from clasificar import escribir_excel  # noqa: E402


def cargar_parametros(ruta: Path | str = PARAMETROS_DEFECTO) -> dict:
    with open(ruta, encoding="utf-8") as f:
        return yaml.safe_load(f)


# --------------------------------------------------------------------------- periodo

def filtrar_periodo(t: pd.DataFrame, desde: str, hasta: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve (filas dentro de la ventana de semestres, filas fuera)."""
    dentro = t["semestre"].between(desde, hasta).fillna(False).astype(bool)
    return t[dentro].copy(), t[~dentro].copy()


def _nombre_frecuente(s: pd.Series):
    return s.mode().iloc[0] if s.notna().any() else pd.NA


# --------------------------------------------------------------------------- 1. Pareto / ABC

def pareto_proveedores(t: pd.DataFrame, corte_a: float, corte_b: float) -> pd.DataFrame:
    total = t["monto_gasto"].sum()
    g = t.groupby("proveedor_id").agg(
        proveedor=("proveedor", _nombre_frecuente), ruc=("ruc", "first"),
        gasto=("monto_gasto", "sum"), n_oc=("oc", "nunique")).reset_index()
    cat = (t.groupby(["proveedor_id", "categoria"])["monto_gasto"].sum().reset_index()
           .sort_values(["proveedor_id", "monto_gasto"], ascending=[True, False])
           .drop_duplicates("proveedor_id").set_index("proveedor_id")["categoria"])
    g["categoria_principal"] = g["proveedor_id"].map(cat)
    g = g.sort_values(["gasto", "proveedor_id"], ascending=[False, True]).reset_index(drop=True)
    g.insert(0, "ranking", np.arange(1, len(g) + 1))
    g["pct_gasto"] = g["gasto"] / total * 100
    g["pct_acumulado"] = g["pct_gasto"].cumsum()
    previo = (g["pct_acumulado"] - g["pct_gasto"]) / 100
    # Un proveedor es A si antes de sumarlo el acumulado aún no llegaba al corte (el que cruza el 80 % es A).
    g["clase_abc"] = np.select([previo < corte_a, previo < corte_b], ["A", "B"], "C")
    return g


def resumen_abc(p: pd.DataFrame) -> pd.DataFrame:
    r = p.groupby("clase_abc").agg(proveedores=("proveedor_id", "size"), gasto=("gasto", "sum"),
                                   n_oc=("n_oc", "sum")).reset_index()
    r["pct_proveedores"] = r["proveedores"] / r["proveedores"].sum() * 100
    r["pct_gasto"] = r["gasto"] / r["gasto"].sum() * 100
    return r


# --------------------------------------------------------------------------- 2. frecuencia

def frecuencia_proveedores(t: pd.DataFrame) -> pd.DataFrame:
    por_oc = t.groupby(["proveedor_id", "oc"])["monto_gasto"].sum().reset_index()
    mes = t["periodo_factura"].fillna(t["fecha_oc"]).dt.to_period("M")
    f = t.assign(_mes=mes).groupby("proveedor_id").agg(
        proveedor=("proveedor", _nombre_frecuente), gasto=("monto_gasto", "sum"),
        n_oc=("oc", "nunique"), n_facturas=("factura_normalizada", "nunique"), n_lineas=("id_linea", "size"),
        meses_activos=("_mes", "nunique"), primera_compra=("fecha_oc", "min"), ultima_compra=("fecha_oc", "max"))
    f["ticket_promedio_oc"] = f["gasto"] / f["n_oc"]
    f["ticket_mediano_oc"] = por_oc.groupby("proveedor_id")["monto_gasto"].median()
    return f.reset_index().sort_values("gasto", ascending=False).reset_index(drop=True)


# --------------------------------------------------------------------------- 3. por nivel y periodo

NIVELES = {"categoria": ["categoria"], "subcategoria": ["categoria", "subcategoria"],
           "producto": ["categoria", "subcategoria", "producto"]}


def gasto_por_nivel(t: pd.DataFrame, nivel: str, periodo: str) -> pd.DataFrame:
    """periodo: 'anio_gasto' o 'semestre'. Variación = cambio % vs. el periodo anterior de la misma llave."""
    cols = NIVELES[nivel]
    g = t.groupby(cols + [periodo]).agg(gasto=("monto_gasto", "sum"), n_oc=("oc", "nunique"),
                                        n_proveedores=("proveedor_id", "nunique")).reset_index()
    tot = t.groupby(periodo)["monto_gasto"].sum()
    g["pct_del_periodo"] = g["gasto"] / g[periodo].map(tot) * 100
    periodos = sorted(t[periodo].dropna().unique())
    completo = pd.MultiIndex.from_product([g[cols].drop_duplicates().apply(tuple, axis=1).tolist(), periodos])
    base = g.set_index(cols + [periodo])["gasto"]
    llaves = [tuple(k) + (p,) for k, p in completo]
    serie = base.reindex(llaves).fillna(0.0)
    anterior = serie.groupby(level=list(range(len(cols)))).shift(1)
    var = ((serie - anterior) / anterior.replace(0, np.nan) * 100)
    g["variacion_pct_vs_anterior"] = g.set_index(cols + [periodo]).index.map(var.to_dict())
    return g.sort_values(cols + [periodo]).reset_index(drop=True)


def gasto_por_nivel_total(t: pd.DataFrame, nivel: str) -> pd.DataFrame:
    cols = NIVELES[nivel]
    g = t.groupby(cols).agg(gasto=("monto_gasto", "sum"), n_oc=("oc", "nunique"),
                            n_proveedores=("proveedor_id", "nunique")).reset_index()
    g["pct_gasto"] = g["gasto"] / t["monto_gasto"].sum() * 100
    anual = t.pivot_table(index=cols, columns="anio_gasto", values="monto_gasto", aggfunc="sum", fill_value=0)
    anual.columns = [f"gasto_{c}" for c in anual.columns]
    return g.merge(anual.reset_index(), on=cols).sort_values("gasto", ascending=False).reset_index(drop=True)


# --------------------------------------------------------------------------- 4 y 5. compradores

def comprador_proveedor(t: pd.DataFrame, pareto: pd.DataFrame, umbral: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    cp = t.groupby(["comprador_codigo", "proveedor_id"]).agg(
        gasto=("monto_gasto", "sum"), n_oc=("oc", "nunique")).reset_index()
    tot = cp.groupby("proveedor_id")["gasto"].transform("sum")
    cp["pct_del_proveedor"] = cp["gasto"] / tot * 100
    cp = cp.sort_values(["proveedor_id", "gasto"], ascending=[True, False])
    principal = cp.drop_duplicates("proveedor_id").rename(
        columns={"comprador_codigo": "comprador_principal", "pct_del_proveedor": "pct_comprador_principal"})
    info = pareto.set_index("proveedor_id")[["proveedor", "gasto", "clase_abc", "n_oc"]]
    conc = principal[["proveedor_id", "comprador_principal", "pct_comprador_principal"]].join(info, on="proveedor_id")
    conc["n_compradores"] = conc["proveedor_id"].map(cp.groupby("proveedor_id").size())
    conc["concentrado"] = conc["pct_comprador_principal"] >= umbral * 100
    conc = conc.sort_values("gasto", ascending=False).reset_index(drop=True)
    return cp.reset_index(drop=True), conc


def comprador_categoria(t: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    m = t.pivot_table(index="comprador_codigo", columns="categoria", values="monto_gasto", aggfunc="sum", fill_value=0)
    tot = m.sum(axis=1)
    shares = m.div(tot, axis=0)
    esp = pd.DataFrame({
        "gasto": tot, "categoria_principal": m.idxmax(axis=1),
        "pct_categoria_principal": shares.max(axis=1) * 100,
        "n_categorias": (m > 0).sum(axis=1),
        "hhi_especializacion": (shares ** 2).sum(axis=1) * 10000,
    }).sort_values("gasto", ascending=False)
    m = m.loc[esp.index]
    return m.reset_index(), esp.reset_index()


# --------------------------------------------------------------------------- 6. sedes y departamentos

def por_unidad(t: pd.DataFrame, col: str, top: int) -> pd.DataFrame:
    g = t.groupby(col, dropna=False).agg(gasto=("monto_gasto", "sum"), n_oc=("oc", "nunique"),
                                         n_proveedores=("proveedor_id", "nunique")).reset_index()
    g["pct_gasto"] = g["gasto"] / t["monto_gasto"].sum() * 100
    anual = t.pivot_table(index=col, columns="anio_gasto", values="monto_gasto", aggfunc="sum", fill_value=0)
    anual.columns = [f"gasto_{c}" for c in anual.columns]
    g = g.merge(anual.reset_index(), on=col, how="left")
    cats = (t.groupby([col, "categoria"], dropna=False)["monto_gasto"].sum().reset_index()
            .sort_values([col, "monto_gasto"], ascending=[True, False]))
    top_cat = cats.groupby(col, dropna=False).head(top).groupby(col, dropna=False)["categoria"].agg(", ".join)
    g["categorias_principales"] = g[col].map(top_cat)
    g[col] = g[col].fillna("(sin dato)")
    return g.sort_values("gasto", ascending=False).reset_index(drop=True)


# --------------------------------------------------------------------------- 7. concentración

def concentracion(t: pd.DataFrame, nivel: str) -> pd.DataFrame:
    cols = NIVELES[nivel]
    x = t.groupby(cols + ["proveedor_id"])["monto_gasto"].sum().reset_index()
    tot = x.groupby(cols)["monto_gasto"].transform("sum")
    x["share"] = x["monto_gasto"] / tot
    g = x.groupby(cols).agg(gasto=("monto_gasto", "sum"), n_proveedores=("proveedor_id", "nunique"),
                            hhi=("share", lambda s: float((s ** 2).sum() * 10000)),
                            pct_proveedor_principal=("share", lambda s: float(s.max() * 100))).reset_index()
    excl = t.groupby(cols)["excluir_de_kraljic"].first().reset_index()
    return g.merge(excl, on=cols).sort_values("gasto", ascending=False).reset_index(drop=True)


# --------------------------------------------------------------------------- proceso

def analizar(t_completa: pd.DataFrame, params: dict, desde: str | None = None, hasta: str | None = None) -> dict:
    A = params["analisis"]
    desde = desde or A["periodo_desde"]
    hasta = hasta or A["periodo_hasta"]
    t, fuera = filtrar_periodo(t_completa, desde, hasta)
    abc = params["pareto_abc"]
    pareto = pareto_proveedores(t, abc["corte_a"], abc["corte_b"])
    cp, conc = comprador_proveedor(t, pareto, A["umbral_concentracion_comprador"])
    cc_matriz, cc_esp = comprador_categoria(t)
    r = {
        "pareto_proveedores": pareto,
        "resumen_abc": resumen_abc(pareto),
        "frecuencia_proveedores": frecuencia_proveedores(t),
        "gasto_categoria": gasto_por_nivel_total(t, "categoria"),
        "gasto_subcategoria": gasto_por_nivel_total(t, "subcategoria"),
        "gasto_producto": gasto_por_nivel_total(t, "producto"),
        "tendencia_categoria_anio": gasto_por_nivel(t, "categoria", "anio_gasto"),
        "tendencia_categoria_semestre": gasto_por_nivel(t, "categoria", "semestre"),
        "tendencia_subcategoria_anio": gasto_por_nivel(t, "subcategoria", "anio_gasto"),
        "comprador_proveedor": cp,
        "concentracion_comprador": conc,
        "comprador_categoria": cc_matriz,
        "especializacion_comprador": cc_esp,
        "gasto_sede": por_unidad(t, "sede", A["top_categorias_por_sede"]),
        "gasto_departamento": por_unidad(t, "departamento", A["top_categorias_por_sede"]),
        "concentracion_categoria": concentracion(t, "categoria"),
        "concentracion_subcategoria": concentracion(t, "subcategoria"),
    }
    r["control"] = control(t_completa, t, fuera, r, desde, hasta)
    r["hallazgos"] = hallazgos(t, r, A["umbral_hhi_alto"])
    return r


def control(t_completa, t, fuera, r, desde, hasta) -> pd.DataFrame:
    total = float(t["monto_gasto"].sum())
    filas = [
        ("Gasto de la tabla clasificada (todas las filas)", float(t_completa["monto_gasto"].sum()), ""),
        (f"Gasto analizado ({desde} a {hasta})", total, "Base de todas las tablas"),
        ("Gasto fuera de la ventana (no se muestra)", float(fuera["monto_gasto"].sum()),
         "Semestres: " + ", ".join(sorted(fuera["semestre"].dropna().unique())) if len(fuera) else "Ninguno"),
    ]
    sumas = {
        "pareto_proveedores": r["pareto_proveedores"]["gasto"].sum(),
        "frecuencia_proveedores": r["frecuencia_proveedores"]["gasto"].sum(),
        "gasto_categoria": r["gasto_categoria"]["gasto"].sum(),
        "gasto_subcategoria": r["gasto_subcategoria"]["gasto"].sum(),
        "gasto_producto": r["gasto_producto"]["gasto"].sum(),
        "tendencia_categoria_anio": r["tendencia_categoria_anio"]["gasto"].sum(),
        "tendencia_categoria_semestre": r["tendencia_categoria_semestre"]["gasto"].sum(),
        "comprador_proveedor": r["comprador_proveedor"]["gasto"].sum(),
        "especializacion_comprador": r["especializacion_comprador"]["gasto"].sum(),
        "gasto_sede": r["gasto_sede"]["gasto"].sum(),
        "gasto_departamento": r["gasto_departamento"]["gasto"].sum(),
        "concentracion_categoria": r["concentracion_categoria"]["gasto"].sum(),
    }
    for k, v in sumas.items():
        dif = round(float(v) - total, 2)
        filas.append((f"Suma de '{k}'", float(v), "OK" if abs(dif) <= 0.01 else f"NO CUADRA (dif. {dif})"))
    return pd.DataFrame(filas, columns=["control", "valor_soles", "resultado"])


def _s(x: float) -> str:
    return f"S/ {x / 1e6:,.1f} M"


def hallazgos(t: pd.DataFrame, r: dict, umbral_hhi: float = 2500) -> list[str]:
    p, abc = r["pareto_proveedores"], r["resumen_abc"].set_index("clase_abc")
    total = t["monto_gasto"].sum()
    top10 = p.head(10)["gasto"].sum() / total * 100
    una_oc = int((r["frecuencia_proveedores"]["n_oc"] == 1).sum())
    cat = r["gasto_categoria"]
    anio = t.groupby("anio_gasto")["monto_gasto"].sum()
    esp = r["especializacion_comprador"]
    top5c = esp.head(5)["gasto"].sum() / total * 100
    conc = r["concentracion_comprador"]
    conc_a = conc[(conc["clase_abc"] == "A") & conc["concentrado"]]
    sede = r["gasto_sede"]
    cc = r["concentracion_subcategoria"]
    cc = cc[~cc["excluir_de_kraljic"]]
    alta = cc[cc["hhi"] > umbral_hhi]
    return [
        f"**Concentración de proveedores:** {int(abc.loc['A', 'proveedores'])} de {len(p):,} proveedores "
        f"({abc.loc['A', 'pct_proveedores']:.1f} %) concentran el {abc.loc['A', 'pct_gasto']:.1f} % del gasto (clase A); "
        f"los 10 mayores, el {top10:.1f} %. [pareto_proveedores, resumen_abc]",
        f"**Proveedores ocasionales:** {una_oc} proveedores ({una_oc / len(p) * 100:.0f} %) tienen una sola OC. "
        "[frecuencia_proveedores]",
        f"**Categorías:** {cat.iloc[0]['categoria']} concentra el {cat.iloc[0]['pct_gasto']:.1f} % del gasto"
        + (("; le siguen " + " y ".join(f"{r.categoria} ({r.pct_gasto:.1f} %)" for r in cat.iloc[1:3].itertuples()))
           if len(cat) > 1 else "") + ". [gasto_categoria]",
        "**Tendencia (soles nominales, por año de factura):** "
        + " → ".join(f"{int(a)}: {_s(v)}" for a, v in anio.items())
        + (f" (×{anio.iloc[-1] / anio.iloc[0]:.1f} entre el primer y el último año)." if len(anio) > 1 else ".")
        + " [tendencia_categoria_anio]",
        f"**Compradores:** los 5 compradores con más gasto manejan el {top5c:.1f} % del total, de {len(esp)} compradores. "
        "[especializacion_comprador]",
        f"**Concentración comprador–proveedor:** en {len(conc_a)} proveedores clase A, un solo comprador maneja el 90 % "
        f"o más del gasto ({_s(conc_a['gasto'].sum())}). Señal para revisar rotación y control, no una conclusión. "
        "[concentracion_comprador]",
        f"**Sedes:** la sede con más gasto es {sede.iloc[0]['sede']} ({sede.iloc[0]['pct_gasto']:.1f} %); las 5 primeras "
        f"suman el {sede.head(5)['pct_gasto'].sum():.1f} %, de {len(sede)} sedes. [gasto_sede]",
        f"**Mercados concentrados:** {len(alta)} de {len(cc)} subcategorías gestionables tienen HHI > {umbral_hhi:,.0f} "
        f"y suman el {alta['gasto'].sum() / total * 100:.1f} % del gasto (mayores: "
        f"{', '.join(alta['subcategoria'].head(5))}). Insumo para el riesgo de Kraljic (Hilo 5). [concentracion_subcategoria]",
    ]


# --------------------------------------------------------------------------- gráficos

AZUL, NARANJA = "#2a78d6", "#eb6834"
TEXTO, TEXTO2, FONDO = "#0b0b0b", "#52514e", "#fcfcfb"
SECUENCIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]


def graficos(r: dict, carpeta: Path, desde: str, hasta: str) -> list[Path]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap

    carpeta.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 9, "axes.edgecolor": TEXTO2, "axes.labelcolor": TEXTO2,
                         "xtick.color": TEXTO2, "ytick.color": TEXTO2, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.axisbelow": True, "figure.facecolor": FONDO, "axes.facecolor": FONDO})
    fuente = f"Fuente: ERP, facturas {desde} a {hasta}. Soles nominales."
    rutas = []

    # 1. Pareto: % del gasto por proveedor (barras) y % acumulado (línea), un solo eje en %.
    n_a = int((r["pareto_proveedores"]["clase_abc"] == "A").sum())
    p = r["pareto_proveedores"].head(n_a)
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.bar(p["ranking"], p["pct_gasto"], color=AZUL, width=0.8, label="% del gasto del proveedor")
    ax.plot(p["ranking"], p["pct_acumulado"], color=NARANJA, lw=2, label="% acumulado")
    ax.axhline(80, color=TEXTO2, lw=0.8, ls=":")
    ax.set_title(f"{n_a} proveedores concentran el 80 % del gasto", loc="left", color=TEXTO, fontsize=11)
    ax.set_xlabel(f"Proveedores clase A ordenados por gasto ({n_a})")
    ax.set_ylabel("% del gasto")
    ax.set_ylim(0, 100)
    ax.grid(axis="y", color="#e6e5e1", lw=0.6)
    ax.legend(frameon=False, loc="center right")
    fig.text(0.01, 0.01, fuente, color=TEXTO2, fontsize=7)
    rutas.append(_guardar(fig, carpeta / "1_pareto_proveedores.png"))

    # 2. Gasto por categoría (barras horizontales, una serie).
    c = r["gasto_categoria"].sort_values("gasto")
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(c["categoria"], c["gasto"] / 1e6, color=AZUL, height=0.7)
    for y, (v, pct) in enumerate(zip(c["gasto"] / 1e6, c["pct_gasto"])):
        ax.text(v, y, f"  {pct:.1f} %", va="center", color=TEXTO2, fontsize=8)
    top = r["gasto_categoria"].iloc[0]
    ax.set_title(f"{top['categoria']} concentra el {top['pct_gasto']:.0f} % del gasto", loc="left", color=TEXTO, fontsize=11)
    ax.set_xlabel("Gasto (millones de soles)")
    ax.grid(axis="x", color="#e6e5e1", lw=0.6)
    fig.text(0.01, 0.01, fuente, color=TEXTO2, fontsize=7)
    rutas.append(_guardar(fig, carpeta / "2_gasto_por_categoria.png"))

    # 3. Tendencia por semestre (una serie).
    s = r["tendencia_categoria_semestre"].groupby("semestre")["gasto"].sum() / 1e6
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(s.index, s.values, color=AZUL, width=0.6)
    for x, v in enumerate(s.values):
        ax.text(x, v, f"{v:,.1f}", ha="center", va="bottom", color=TEXTO2, fontsize=8)
    ax.set_title(f"El gasto semestral pasó de S/ {s.iloc[0]:,.0f} M a S/ {s.iloc[-1]:,.0f} M",
                 loc="left", color=TEXTO, fontsize=11)
    ax.set_ylabel("Gasto (millones de soles)")
    ax.grid(axis="y", color="#e6e5e1", lw=0.6)
    fig.text(0.01, 0.01, fuente, color=TEXTO2, fontsize=7)
    rutas.append(_guardar(fig, carpeta / "3_tendencia_semestral.png"))

    # 4. Mapa de calor comprador × categoría (15 compradores con más gasto), % del gasto de cada comprador.
    m = r["comprador_categoria"].set_index("comprador_codigo").head(15)
    m = m.div(m.sum(axis=1), axis=0) * 100
    m = m[m.sum().sort_values(ascending=False).index]
    fig, ax = plt.subplots(figsize=(13, 6))
    cmap = LinearSegmentedColormap.from_list("azul", SECUENCIAL)
    im = ax.imshow(m.values, aspect="auto", cmap=cmap, vmin=0, vmax=100)
    ax.set_xticks(range(len(m.columns)), [textwrap.fill(x, 18) for x in m.columns], rotation=40, ha="right", fontsize=7)
    ax.set_yticks(range(len(m.index)), m.index, fontsize=7)
    for i in range(m.shape[0]):
        for j in range(m.shape[1]):
            if m.values[i, j] >= 20:
                ax.text(j, i, f"{m.values[i, j]:.0f}", ha="center", va="center", fontsize=7,
                        color="white" if m.values[i, j] >= 55 else TEXTO)
    fig.colorbar(im, ax=ax, label="% del gasto del comprador")
    ax.set_title("La mayoría de compradores concentra su gasto en pocas categorías", loc="left", color=TEXTO, fontsize=11)
    ax.spines[:].set_visible(False)
    fig.text(0.01, 0.01, fuente + " 15 compradores con más gasto.", color=TEXTO2, fontsize=7)
    rutas.append(_guardar(fig, carpeta / "4_comprador_por_categoria.png"))
    return rutas


def _guardar(fig, ruta: Path) -> Path:
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(ruta, dpi=150)
    import matplotlib.pyplot as plt
    plt.close(fig)
    return ruta


# --------------------------------------------------------------------------- CLI

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Análisis descriptivo del gasto (Hilo 3).")
    ap.add_argument("--tabla", required=True, help="tabla_clasificada.parquet del Hilo 2")
    ap.add_argument("--salida", required=True)
    ap.add_argument("--desde", help="Semestre inicial, ej. 2015-S1 (por defecto: parametros.yaml)")
    ap.add_argument("--hasta", help="Semestre final, ej. 2017-S2")
    ap.add_argument("--parametros", default=str(PARAMETROS_DEFECTO))
    ap.add_argument("--sin-graficos", action="store_true")
    a = ap.parse_args(argv)

    params = cargar_parametros(a.parametros)
    t = pd.read_parquet(a.tabla)
    r = analizar(t, params, a.desde, a.hasta)
    desde = a.desde or params["analisis"]["periodo_desde"]
    hasta = a.hasta or params["analisis"]["periodo_hasta"]
    carpeta = Path(a.salida)
    (carpeta / "tablas").mkdir(parents=True, exist_ok=True)
    hojas = {k: v for k, v in r.items() if isinstance(v, pd.DataFrame)}
    for k, v in hojas.items():
        v.to_parquet(carpeta / "tablas" / f"{k}.parquet", index=False)
    hojas = {"Control": hojas.pop("control"), **hojas}
    hojas["Hallazgos"] = pd.DataFrame({"hallazgo": [h.replace("**", "") for h in r["hallazgos"]]})
    escribir_excel(carpeta / "resultados_descriptivos.xlsx", hojas)
    (carpeta / "hallazgos.md").write_text(
        f"# Hallazgos descriptivos ({desde} a {hasta}, soles nominales)\n\n"
        + "\n".join(f"{i}. {h}" for i, h in enumerate(r["hallazgos"], 1)) + "\n", encoding="utf-8")
    if not a.sin_graficos:
        graficos(r, carpeta / "graficos", desde, hasta)

    ctrl = r["control"]
    print(ctrl.to_string(index=False))
    malos = ctrl["resultado"].str.startswith("NO CUADRA").sum()
    print("\n".join(r["hallazgos"]))
    return 1 if malos else 0


if __name__ == "__main__":
    sys.exit(main())
