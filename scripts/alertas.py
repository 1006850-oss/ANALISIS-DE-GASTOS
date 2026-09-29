"""Hilo 4 – Alertas de control interno sobre las compras.

Una alerta es una SEÑAL para revisar, no una conclusión. Cada caso trae su evidencia y columnas
vacías para la investigación ("Responsable", "Estado", "Conclusión").

Entrada: tabla_clasificada.parquet (Hilo 2) + config/parametros.yaml + config/reglas_alertas.yaml.
Salidas en --salida:
  - alertas.xlsx       hoja Resumen + una hoja por tipo de alerta (ordenada por prioridad)
  - tablas/*.parquet   para el tablero del Hilo 7
  - hallazgos_control.md

Uso:
  python scripts/alertas.py --tabla <tabla_clasificada.parquet> --salida <carpeta>
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
from analizar import comprador_proveedor, filtrar_periodo, pareto_proveedores  # noqa: E402
from clasificar import escribir_excel  # noqa: E402

PARAMETROS_DEFECTO = RAIZ / "config" / "parametros.yaml"
REGLAS_DEFECTO = RAIZ / "config" / "reglas_alertas.yaml"
ORDEN_PRIORIDAD = {"Alta": 0, "Media": 1, "Baja": 2}
COLUMNAS_INVESTIGACION = ["Responsable", "Estado", "Conclusión"]


def cargar_yaml(ruta) -> dict:
    with open(ruta, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _ordenar(df: pd.DataFrame, monto: str) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.assign(_p=df["prioridad"].map(ORDEN_PRIORIDAD)).sort_values(["_p", monto], ascending=[True, False])
    return df.drop(columns="_p").reset_index(drop=True)


def _investigacion(df: pd.DataFrame) -> pd.DataFrame:
    for c in COLUMNAS_INVESTIGACION:
        df[c] = ""
    return df


def tabla_oc(t: pd.DataFrame) -> pd.DataFrame:
    """Una fila por OC. La subcategoría/producto de la OC es la de su línea de mayor gasto."""
    principal = (t.sort_values(["oc", "monto_gasto", "id_linea"], ascending=[True, False, True])
                 .drop_duplicates("oc").set_index("oc"))
    g = t.groupby("oc").agg(gasto=("monto_gasto", "sum"), lineas=("id_linea", "size"),
                            facturas=("factura_normalizada", "nunique"))
    cols = ["proveedor_id", "proveedor", "sede", "categoria", "subcategoria", "producto", "descripcion", "fecha_oc",
            "monto_oc", "nivel_aprobacion_oc", "comprador_codigo", "aprobador_codigo", "flag_moneda_extranjera"]
    return principal[cols].join(g).reset_index()


# --------------------------------------------------------------------------- 1. fraccionamiento

def fraccionamiento(oc: pd.DataFrame, params: dict, R: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    F = R["fraccionamiento"]
    limites = [n["hasta_pen"] for n in params["aprobacion_oc"] if n["hasta_pen"] is not None]
    d = oc[~oc["subcategoria"].isin(F["subcategorias_excluidas"]) & ~oc["categoria"].isin(F["categorias_excluidas"])]
    d = d.dropna(subset=["fecha_oc", "monto_oc"])
    casos, detalle = [], []
    ventana = np.timedelta64(F["ventana_dias"], "D")
    for llave, g in d.groupby(F["agrupar_por"], dropna=False):
        if len(g) < F["minimo_oc"]:
            continue
        g = g.sort_values(["fecha_oc", "oc"]).reset_index(drop=True)
        f = g["fecha_oc"].to_numpy()
        m = g["monto_oc"].to_numpy(dtype=float)
        marcadas = []
        for i in range(len(g)):
            j = int(np.searchsorted(f, f[i] + ventana, side="right"))
            if j - i < F["minimo_oc"]:
                continue
            w = m[i:j]
            for lim in limites:
                if (w <= lim).all() and w.sum() > lim:
                    marcadas.append((i, j, lim))
                    break
        actual = None
        unidas = []
        for i, j, lim in marcadas:  # ventanas que se solapan = un solo caso
            if actual and i < actual[1]:
                actual = [actual[0], max(actual[1], j), max(actual[2], lim)]
            else:
                if actual:
                    unidas.append(actual)
                actual = [i, j, lim]
        if actual:
            unidas.append(actual)
        for i, j, lim in unidas:
            s = g.iloc[i:j]
            dias = int((s["fecha_oc"].max() - s["fecha_oc"].min()).days)
            mismo_dia = s["fecha_oc"].nunique() < len(s)
            mismo_comp = s["comprador_codigo"].nunique() == 1
            if dias <= F["prioridad"]["alta_si_dias_max"] or mismo_dia:
                prio = "Alta"
            elif F["prioridad"]["media_si_mismo_comprador"] and mismo_comp:
                prio = "Media"
            else:
                prio = "Baja"
            caso = f"FR-{len(casos) + 1:04d}"
            casos.append({
                "caso": caso, "prioridad": prio, "proveedor_id": llave[0], "proveedor": s["proveedor"].iloc[0],
                "sede": llave[1], "subcategoria": llave[2], "categoria": s["categoria"].iloc[0],
                "n_oc": len(s), "desde": s["fecha_oc"].min().date(), "hasta": s["fecha_oc"].max().date(),
                "dias": dias, "suma_oc": float(s["monto_oc"].sum()), "mayor_oc": float(s["monto_oc"].max()),
                "limite_superado": float(lim), "exceso_sobre_limite": float(s["monto_oc"].sum() - lim),
                "compradores": ", ".join(sorted(s["comprador_codigo"].dropna().unique())),
                "mismo_comprador": mismo_comp, "oc": ", ".join(str(x) for x in s["oc"])})
            detalle.append(s.assign(caso=caso)[["caso", "oc", "fecha_oc", "monto_oc", "descripcion", "producto",
                                                "comprador_codigo", "aprobador_codigo", "nivel_aprobacion_oc"]])
    casos = pd.DataFrame(casos)
    if casos.empty:
        return casos, pd.DataFrame()
    casos = _ordenar(casos, "suma_oc")
    detalle = pd.concat(detalle, ignore_index=True)
    return _investigacion(casos), detalle


# --------------------------------------------------------------------------- 2. autoaprobación

def autoaprobacion(oc: pd.DataFrame, R: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    A = R["autoaprobacion"]
    oc = oc.assign(autoaprobada=oc["comprador_codigo"] == oc["aprobador_codigo"])
    est = oc.groupby("nivel_aprobacion_oc").agg(oc=("oc", "size"), autoaprobadas=("autoaprobada", "sum"),
                                                gasto=("gasto", "sum"),
                                                gasto_autoaprobado=("gasto", lambda s: s[oc.loc[s.index, "autoaprobada"]].sum()))
    est["pct_autoaprobadas"] = est["autoaprobadas"] / est["oc"] * 100
    a = oc[oc["autoaprobada"] & (oc["nivel_aprobacion_oc"] >= A["nivel_minimo"])].copy()
    a["prioridad"] = a["nivel_aprobacion_oc"].astype(int).map(A["prioridad_por_nivel"])
    a = a[["prioridad", "oc", "fecha_oc", "nivel_aprobacion_oc", "monto_oc", "gasto", "comprador_codigo",
           "aprobador_codigo", "proveedor_id", "proveedor", "sede", "categoria", "descripcion"]]
    return _investigacion(_ordenar(a, "monto_oc")), est.reset_index()


# --------------------------------------------------------------------------- 3. duplicados

def duplicados(t: pd.DataFrame, R: dict) -> pd.DataFrame:
    D = R["duplicados"]
    P = D["prioridad"]
    out = []
    ident = t[t["flag_fila_duplicada"]]
    for (oc_n,), g in ident.groupby(["oc"]):
        out.append({"tipo": "Filas idénticas", "prioridad": P["fila_identica"], "proveedor_id": g["proveedor_id"].iloc[0],
                    "proveedor": g["proveedor"].iloc[0], "oc": str(oc_n), "facturas": ", ".join(sorted(g["n_factura"].dropna().unique())),
                    "n_filas": len(g), "monto": float(g["monto_gasto"].sum()), "detalle": g["descripcion"].iloc[0]})
    multi = t[t["flag_factura_en_varias_oc"]]
    for (prov, fac), g in multi.groupby(["proveedor_id", "factura_normalizada"]):
        out.append({"tipo": "Misma factura en varias OC", "prioridad": P["factura_en_varias_oc"], "proveedor_id": prov,
                    "proveedor": g["proveedor"].iloc[0], "oc": ", ".join(str(x) for x in sorted(g["oc"].unique())),
                    "facturas": ", ".join(sorted(g["n_factura"].dropna().unique())), "n_filas": len(g),
                    "monto": float(g["monto_gasto"].sum()), "detalle": g["descripcion"].iloc[0]})
    f = t[t["factura_normalizada"].notna()].groupby(["proveedor_id", "factura_normalizada"]).agg(
        monto=("monto_gasto", "sum"), periodo=("periodo_factura", "first"), sede=("sede", "first"),
        llave=("llave_combinacion", "first"), subcategoria=("subcategoria", "first"), proveedor=("proveedor", "first"),
        n_factura=("n_factura", "first"), oc=("oc", "min"), descripcion=("descripcion", "first")).reset_index()
    f = f[f["monto"] >= D["monto_minimo_factura"]]
    if D["excluir_subcategorias_recurrentes"]:
        f = f[~f["subcategoria"].isin(R["fraccionamiento"]["subcategorias_excluidas"])]
    f["monto_r"] = f["monto"].round(2)
    llave = ["proveedor_id", "monto_r", "periodo", "sede", "llave"]
    f = f[f.groupby(llave, dropna=False)["factura_normalizada"].transform("nunique") > 1]
    for _, g in f.groupby(llave, dropna=False):
        misma_oc = g["oc"].nunique() == 1
        out.append({"tipo": "Posible factura duplicada" + (" (misma OC)" if misma_oc else ""),
                    "prioridad": P["posible_factura_duplicada_misma_oc"] if misma_oc else P["posible_factura_duplicada"],
                    "proveedor_id": g["proveedor_id"].iloc[0], "proveedor": g["proveedor"].iloc[0],
                    "oc": ", ".join(str(x) for x in sorted(g["oc"].unique())), "facturas": ", ".join(sorted(g["n_factura"])),
                    "n_filas": len(g), "monto": float(g["monto"].sum()),
                    "detalle": f"{len(g)} facturas de S/ {g['monto'].iloc[0]:,.2f} en {g['periodo'].iloc[0]:%m/%Y}, "
                               f"sede {g['sede'].iloc[0]}: {g['descripcion'].iloc[0]}"})
    d = pd.DataFrame(out)
    if d.empty:
        return d
    d.insert(0, "caso", [f"DU-{i + 1:04d}" for i in range(len(d))])
    return _investigacion(_ordenar(d, "monto"))


# --------------------------------------------------------------------------- 4. ciclo OC → factura

def ciclo(t: pd.DataFrame, oc: pd.DataFrame, R: dict) -> pd.DataFrame:
    C = R["ciclo"]
    c = t[t["periodo_factura"].notna()].copy()
    c["meses"] = ((c["periodo_factura"].dt.year - c["fecha_oc"].dt.year) * 12
                  + (c["periodo_factura"].dt.month - c["fecha_oc"].dt.month))
    g = c.groupby("oc").agg(meses_min=("meses", "min"), meses_max=("meses", "max"),
                            primera_factura=("periodo_factura", "min"), ultima_factura=("periodo_factura", "max"))
    base = oc.set_index("oc")[["fecha_oc", "proveedor_id", "proveedor", "sede", "categoria", "monto_oc", "gasto",
                               "comprador_codigo", "descripcion"]]
    out = []

    def agregar(ids, tipo, prio, extra=None):
        x = base.loc[list(ids)].reset_index()
        x.insert(0, "tipo", tipo)
        x.insert(1, "prioridad", prio)
        if extra is not None:
            x = x.merge(extra, left_on="oc", right_index=True, how="left")
        out.append(x)

    antes = g[g["meses_min"] < 0]
    agregar(antes.index, "Factura anterior a la OC", C["factura_antes_de_oc"], g)
    largo = g[(g["meses_max"] > C["meses_ciclo_largo"]) & (g["meses_min"] >= 0)]
    agregar(largo.index, f"Ciclo mayor a {C['meses_ciclo_largo']} meses", C["ciclo_largo"], g)
    sin_fac = t.loc[t["flag_sin_factura"], "oc"].unique()
    agregar(sin_fac, "OC sin facturar", C["oc_sin_facturar"])
    exc = t.loc[t["flag_facturado_excede_oc"], "oc"].unique()
    agregar(exc, "Facturado mayor al monto de la OC (+5 %)", C["facturado_excede_oc"])
    pend = t.loc[t["pendiente_de_pago"] & t["factura_normalizada"].notna(), "oc"].unique()
    agregar(pend, "Factura pendiente de pago", C["pendiente_de_pago"])
    d = pd.concat(out, ignore_index=True)
    return _investigacion(_ordenar(d, "gasto")) if len(d) else d


# --------------------------------------------------------------------------- 5. adicionales de obra

def adicionales(t: pd.DataFrame, R: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    A = R["adicionales"]
    inf = t[t["categoria"] == A["categoria"]].assign(es_adicional=lambda x: x["producto"] == A["producto"])

    def tabla(col, umbral, minimo):
        g = inf.groupby(col).agg(gasto_obras=("monto_gasto", "sum"),
                                 gasto_adicionales=("monto_gasto", lambda s: s[inf.loc[s.index, "es_adicional"]].sum()),
                                 n_oc=("oc", "nunique")).reset_index()
        g["gasto_original"] = g["gasto_obras"] - g["gasto_adicionales"]
        g["pct_adicionales"] = g["gasto_adicionales"] / g["gasto_obras"] * 100
        g["pct_sobre_original"] = g["gasto_adicionales"] / g["gasto_original"].replace(0, np.nan) * 100
        g["alerta"] = (g["pct_adicionales"] >= umbral) & (g["gasto_obras"] >= minimo)
        g["prioridad"] = np.where(g["pct_adicionales"] >= 2 * umbral, "Alta", "Media")
        g.loc[~g["alerta"], "prioridad"] = ""
        return g.sort_values(["alerta", "pct_adicionales"], ascending=[False, False]).reset_index(drop=True)

    sedes = tabla("sede", A["umbral_pct_sede"], A["gasto_minimo_sede"])
    provs = tabla("proveedor_id", A["umbral_pct_proveedor"], A["gasto_minimo_proveedor"])
    nombres = inf.groupby("proveedor_id")["proveedor"].first()
    provs.insert(1, "proveedor", provs["proveedor_id"].map(nombres))
    return sedes, provs


# --------------------------------------------------------------------------- 6. giro

def giro(t: pd.DataFrame, R: dict) -> pd.DataFrame:
    G = R["giro"]
    x = t[~t["excluir_de_kraljic"]].assign(familia=lambda d: d["categoria"].map(G["familias"]))
    x = x.groupby(["proveedor_id", "familia"])["monto_gasto"].sum().reset_index()
    x["share"] = x["monto_gasto"] / x.groupby("proveedor_id")["monto_gasto"].transform("sum")
    x = x.sort_values(["proveedor_id", "share"], ascending=[True, False])
    p = x.groupby("proveedor_id").agg(gasto=("monto_gasto", "sum"), n_familias=("familia", "size"),
                                      familia_principal=("familia", "first"), pct_principal=("share", "first"),
                                      segunda_familia=("familia", lambda s: s.iloc[1] if len(s) > 1 else None),
                                      pct_segunda=("share", lambda s: s.iloc[1] if len(s) > 1 else 0.0)).reset_index()
    p = p[(p["gasto"] >= G["gasto_minimo"]) & (p["pct_segunda"] >= G["umbral_segunda_familia"])].copy()
    cats = (t.groupby(["proveedor_id", "categoria"])["monto_gasto"].sum().reset_index()
            .sort_values("monto_gasto", ascending=False).groupby("proveedor_id")["categoria"]
            .agg(lambda s: ", ".join(s.head(4))))
    p["categorias"] = p["proveedor_id"].map(cats)
    p.insert(1, "proveedor", p["proveedor_id"].map(t.groupby("proveedor_id")["proveedor"].first()))
    p["pct_principal"] *= 100
    p["pct_segunda"] *= 100
    p["prioridad"] = np.where(p["pct_segunda"] >= 30, "Media", "Baja") if len(p) else pd.Series(dtype=str)
    return _investigacion(_ordenar(p, "gasto"))


# --------------------------------------------------------------------------- 7. concentración

def concentracion(t: pd.DataFrame, params: dict, R: dict) -> pd.DataFrame:
    A = params["analisis"]
    dentro, _ = filtrar_periodo(t, A["periodo_desde"], A["periodo_hasta"])
    p = pareto_proveedores(dentro, params["pareto_abc"]["corte_a"], params["pareto_abc"]["corte_b"])
    _, conc = comprador_proveedor(dentro, p, A["umbral_concentracion_comprador"])
    c = conc[conc["concentrado"] & (conc["clase_abc"] == R["concentracion_comprador"]["solo_clase"])].copy()
    c.insert(0, "prioridad", R["concentracion_comprador"]["prioridad"])
    return _investigacion(c.reset_index(drop=True))


# --------------------------------------------------------------------------- proceso

def generar_alertas(t: pd.DataFrame, params: dict, R: dict) -> dict:
    oc = tabla_oc(t)
    fr, fr_det = fraccionamiento(oc, params, R)
    au, au_est = autoaprobacion(oc, R)
    du = duplicados(t, R)
    ci = ciclo(t, oc, R)
    ad_sede, ad_prov = adicionales(t, R)
    gi = giro(t, R)
    co = concentracion(t, params, R)
    r = {"fraccionamiento": fr, "fraccionamiento_detalle": fr_det, "autoaprobacion": au,
         "autoaprobacion_por_nivel": au_est, "duplicados": du, "ciclo_oc_factura": ci,
         "adicionales_sede": ad_sede, "adicionales_proveedor": ad_prov, "giro_proveedor": gi,
         "concentracion_comprador": co}
    r["resumen"] = resumen(r)
    r["hallazgos"] = hallazgos(r, t)
    return r


def _conteo(nombre, df, monto, subtipo=None):
    if df is None or df.empty:
        return [{"alerta": nombre, "subtipo": subtipo or "", "casos": 0, "monto_soles": 0.0, "alta": 0, "media": 0, "baja": 0}]
    return [{"alerta": nombre, "subtipo": subtipo or "", "casos": len(df), "monto_soles": float(df[monto].sum()),
             "alta": int((df["prioridad"] == "Alta").sum()), "media": int((df["prioridad"] == "Media").sum()),
             "baja": int((df["prioridad"] == "Baja").sum())}]


def resumen(r: dict) -> pd.DataFrame:
    filas = []
    filas += _conteo("1. Compras fraccionadas", r["fraccionamiento"], "suma_oc")
    filas += _conteo("2. Autoaprobación (nivel ≥ 2)", r["autoaprobacion"], "monto_oc")
    for tipo, g in r["duplicados"].groupby("tipo") if not r["duplicados"].empty else []:
        filas += _conteo("3. Duplicados", g, "monto", tipo)
    for tipo, g in r["ciclo_oc_factura"].groupby("tipo") if len(r["ciclo_oc_factura"]) else []:
        filas += _conteo("4. Ciclo OC → factura", g, "gasto", tipo)
    s = r["adicionales_sede"]
    filas += _conteo("5. Adicionales de obra", s[s["alerta"]], "gasto_adicionales", "Sedes")
    p = r["adicionales_proveedor"]
    filas += _conteo("5. Adicionales de obra", p[p["alerta"]], "gasto_adicionales", "Proveedores")
    filas += _conteo("6. Giro del proveedor", r["giro_proveedor"], "gasto")
    filas += _conteo("7. Concentración comprador–proveedor", r["concentracion_comprador"], "gasto")
    return pd.DataFrame(filas)


def _alta(df: pd.DataFrame) -> int:
    return int((df["prioridad"] == "Alta").sum()) if len(df) and "prioridad" in df else 0


def _suma(df: pd.DataFrame, col: str) -> float:
    return float(df[col].sum()) if len(df) and col in df else 0.0


def _m(x: float) -> str:
    return f"S/ {x / 1e6:,.1f} M"


def hallazgos(r: dict, t: pd.DataFrame) -> list[str]:
    fr, au, est = r["fraccionamiento"], r["autoaprobacion"], r["autoaprobacion_por_nivel"]
    alto = est[est["nivel_aprobacion_oc"] >= 4]
    du, ci = r["duplicados"], r["ciclo_oc_factura"]
    s, p = r["adicionales_sede"], r["adicionales_proveedor"]
    inf = t[t["categoria"] == "Infraestructura y obras"]
    total_ad = s["gasto_adicionales"].sum()
    antes = ci[ci["tipo"] == "Factura anterior a la OC"] if len(ci) else ci
    return [
        f"**Posibles compras fraccionadas:** {len(fr)} casos en {fr['proveedor_id'].nunique() if len(fr) else 0} proveedores "
        f"({_m(_suma(fr, 'suma_oc'))}); {_alta(fr)} de prioridad "
        "alta (OC emitidas en 7 días o menos). [fraccionamiento]",
        f"**Autoaprobación:** {len(au):,} OC de nivel 2 o más fueron aprobadas por el mismo comprador ({_m(_suma(au, 'monto_oc'))}). "
        f"En los niveles 4 y 5 ocurre en {int(alto['autoaprobadas'].sum())} de {int(alto['oc'].sum())} OC. La data trae un solo "
        "aprobador por OC: no permite verificar la cadena completa de firmas. [autoaprobacion]",
        f"**Duplicados:** {len(du)} casos; {_alta(du)} de prioridad alta (misma factura en varias OC "
        "o posible factura duplicada dentro de la misma OC). [duplicados]",
        f"**Facturas anteriores a la OC:** {len(antes)} OC ({_m(_suma(antes, 'gasto'))}) tienen facturas de un mes anterior "
        "a la emisión de la OC: posible regularización de compras ya hechas. [ciclo_oc_factura]",
        f"**Adicionales de obra:** {_m(total_ad)} ({total_ad / max(inf['monto_gasto'].sum(), 1) * 100:.1f} % del gasto en obras). "
        f"{int(s['alerta'].sum())} sedes superan el umbral por sede y {int(p['alerta'].sum())} proveedores el umbral por "
        "proveedor. Indicador de calidad de expedientes y gestión del alcance. [adicionales_sede, adicionales_proveedor]",
        f"**Giro del proveedor:** {len(r['giro_proveedor'])} proveedores facturan una parte relevante en una familia de "
        "compra distinta a la principal. [giro_proveedor]",
        f"**Concentración comprador–proveedor:** {len(r['concentracion_comprador'])} proveedores clase A con un solo "
        f"comprador que maneja el 90 % o más ({_m(_suma(r['concentracion_comprador'], 'gasto'))}). [concentracion_comprador]",
    ]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Alertas de control (Hilo 4).")
    ap.add_argument("--tabla", required=True, help="tabla_clasificada.parquet del Hilo 2")
    ap.add_argument("--salida", required=True)
    ap.add_argument("--parametros", default=str(PARAMETROS_DEFECTO))
    ap.add_argument("--reglas", default=str(REGLAS_DEFECTO))
    a = ap.parse_args(argv)
    params, R = cargar_yaml(a.parametros), cargar_yaml(a.reglas)
    t = pd.read_parquet(a.tabla)
    r = generar_alertas(t, params, R)
    carpeta = Path(a.salida)
    (carpeta / "tablas").mkdir(parents=True, exist_ok=True)
    for k, v in r.items():
        if isinstance(v, pd.DataFrame):
            v.to_parquet(carpeta / "tablas" / f"{k}.parquet", index=False)
    aviso = pd.DataFrame({"nota": [
        "Cada alerta es una SEÑAL para revisar, no una conclusión.",
        "Compradores y aprobadores con código; la equivalencia con nombres está solo en reporte_calidad.xlsx (Drive).",
        f"Reglas: config/reglas_alertas.yaml (versión {R['version']})."]})
    hojas = {"Resumen": r["resumen"], "Notas": aviso, "1_Fraccionamiento": r["fraccionamiento"],
             "1b_Fraccionamiento_OC": r["fraccionamiento_detalle"], "2_Autoaprobacion": r["autoaprobacion"],
             "2b_Autoaprob_por_nivel": r["autoaprobacion_por_nivel"], "3_Duplicados": r["duplicados"],
             "4_Ciclo_OC_factura": r["ciclo_oc_factura"], "5_Adicionales_sede": r["adicionales_sede"],
             "5b_Adicionales_proveedor": r["adicionales_proveedor"], "6_Giro_proveedor": r["giro_proveedor"],
             "7_Concentracion": r["concentracion_comprador"],
             "Hallazgos": pd.DataFrame({"hallazgo": [h.replace("**", "") for h in r["hallazgos"]]})}
    escribir_excel(carpeta / "alertas.xlsx", hojas)
    (carpeta / "hallazgos_control.md").write_text(
        "# Hallazgos de control (señales para revisar, no conclusiones)\n\n"
        + "\n".join(f"{i}. {h}" for i, h in enumerate(r["hallazgos"], 1)) + "\n", encoding="utf-8")
    print(r["resumen"].to_string(index=False))
    print("\n".join(r["hallazgos"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
