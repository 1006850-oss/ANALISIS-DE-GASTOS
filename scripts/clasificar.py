"""Hilo 2 – Taxonomía: asigna categoría > subcategoría > producto a cada línea de gasto.

Entrada: tabla_limpia.parquet (Hilo 1) + config/reglas_taxonomia.yaml + (opcional) maestro validado.
Salidas en --salida:
  - tabla_clasificada.parquet        tabla limpia + categoria, subcategoria, producto y su origen
  - resumen_clasificacion.xlsx       gasto por nivel, cobertura por origen, cuadre con el total
  - nuevas_para_validar.xlsx         artículos y combinaciones que no están en el maestro
  - maestro_propuesto.xlsx           maestro armado con las propuestas de esta corrida (--construir-maestro)
  - validacion_taxonomia.xlsx        Excel para que la persona valide (--generar-validacion)

Uso:
  python scripts/clasificar.py --tabla <tabla_limpia.parquet> --salida <carpeta> [--maestro maestro_categorias.xlsx]
         [--construir-maestro] [--generar-validacion]
  python scripts/clasificar.py --aplicar-validacion validacion_taxonomia.xlsx --maestro maestro_categorias.xlsx

El maestro validado manda sobre las reglas. Nada de datos personales ni montos se envía a un LLM desde aquí.
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

RAIZ = Path(__file__).resolve().parents[1]
REGLAS_DEFECTO = RAIZ / "config" / "reglas_taxonomia.yaml"
SIN_CLASIFICAR = "Sin clasificar"
SEP = " | "


# --------------------------------------------------------------------------- utilidades

def cargar_reglas(ruta: Path | str = REGLAS_DEFECTO) -> dict:
    with open(ruta, encoding="utf-8") as f:
        return yaml.safe_load(f)


def normalizar(s: pd.Series) -> pd.Series:
    """MAYÚSCULAS, sin tildes, espacios simples. Conserva signos (":", ".", "-")."""
    def uno(x):
        if x is None or x is pd.NA or (isinstance(x, float) and np.isnan(x)):
            return ""
        x = unicodedata.normalize("NFKD", str(x)).encode("ascii", "ignore").decode().upper()
        return re.sub(r"\s+", " ", x).strip()
    return s.astype(object).map(uno).astype("string")


def llave_descripcion(s: pd.Series) -> pd.Series:
    """Descripción normalizada para la llave del maestro: solo letras y espacios."""
    x = normalizar(s).str.replace(r"[^A-Z ]", " ", regex=True).str.replace(r"\s+", " ", regex=True).str.strip()
    return x


def titulo(s: pd.Series) -> pd.Series:
    return s.str.strip().str.capitalize()


# ------------------------------------------------------------------- niveles 1 y 2

def clasificar_articulos(articulos: pd.Series, reglas: dict) -> pd.DataFrame:
    """Una fila por artículo normalizado con su categoría/subcategoría según las reglas (primera que coincide)."""
    arts = pd.Series(sorted(articulos.dropna().unique()), dtype="string")
    norm = normalizar(arts)
    out = pd.DataFrame({"articulo_normalizado": arts, "categoria": SIN_CLASIFICAR,
                        "subcategoria": SIN_CLASIFICAR, "origen": "sin_regla", "confianza": "baja",
                        "regla": pd.NA})
    libre = pd.Series(True, index=arts.index)
    for i, r in enumerate(reglas["articulos"]):
        m = libre & norm.str.contains(r["patron"], regex=True)
        if m.any():
            out.loc[m, ["categoria", "subcategoria", "confianza"]] = [r["categoria"], r["subcategoria"], r["confianza"]]
            out.loc[m, "origen"] = "regla"
            out.loc[m, "regla"] = f"{i + 1}: {r['patron']}"
            libre &= ~m
    return out


def leer_maestro(ruta: Path | str | None) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    if not ruta or not Path(ruta).exists():
        return None, None
    xl = pd.ExcelFile(ruta)
    art = pd.read_excel(xl, "articulos", dtype=str) if "articulos" in xl.sheet_names else None
    comb = pd.read_excel(xl, "combinaciones", dtype=str) if "combinaciones" in xl.sheet_names else None
    return art, comb


# ------------------------------------------------------------------- nivel 3

def asignar_productos(t: pd.DataFrame, reglas: dict) -> tuple[pd.Series, pd.Series]:
    texto = normalizar(t["descripcion"].fillna("") + " " + t["concepto"].fillna("") + " " + t["nota"].fillna(""))
    producto = pd.Series(pd.NA, index=t.index, dtype="string")
    origen = pd.Series(pd.NA, index=t.index, dtype="string")
    for cat, lista in (reglas.get("productos") or {}).items():
        en_cat = t["categoria"] == cat
        for r in lista:
            m = en_cat & producto.isna() & texto.str.contains(r["patron"], regex=True)
            producto[m] = r["producto"]
            origen[m] = "regla_palabra"
    concepto = titulo(t["concepto"].astype("string"))
    m = producto.isna() & concepto.notna() & (t["categoria"] != "Infraestructura y obras")
    producto[m] = concepto[m]
    origen[m] = "concepto"
    m = producto.isna()
    producto[m] = "Otros – " + t.loc[m, "subcategoria"].astype("string")
    origen[m] = "subcategoria"
    return producto, origen


# ------------------------------------------------------------------- proceso

def clasificar(t: pd.DataFrame, reglas: dict, maestro_art: pd.DataFrame | None = None,
               maestro_comb: pd.DataFrame | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve (tabla clasificada, tabla de artículos usada)."""
    t = t.copy()
    arts = clasificar_articulos(t["articulo_normalizado"], reglas)
    if maestro_art is not None and len(maestro_art):
        m = maestro_art[["articulo_normalizado", "categoria", "subcategoria", "origen", "confianza"]]
        arts = arts.set_index("articulo_normalizado")
        m = m.set_index("articulo_normalizado")
        comunes = arts.index.intersection(m.index)
        arts.loc[comunes, ["categoria", "subcategoria", "origen", "confianza"]] = m.loc[comunes].to_numpy()
        arts.loc[comunes, "regla"] = "maestro"
        arts = arts.reset_index()

    t = t.merge(arts[["articulo_normalizado", "categoria", "subcategoria", "origen", "confianza"]]
                .rename(columns={"origen": "origen_categoria", "confianza": "confianza_categoria"}),
                on="articulo_normalizado", how="left")
    sin_art = t["categoria"].isna()
    t.loc[sin_art, ["categoria", "subcategoria", "origen_categoria", "confianza_categoria"]] = \
        [SIN_CLASIFICAR, SIN_CLASIFICAR, "sin_articulo", "baja"]

    # Construcción: subcategoría = tipo de intervención según "clase_glosa".
    c = reglas["construccion"]
    es_const = normalizar(t["articulo_normalizado"].fillna("")).str.contains("|".join(c["articulos"]), regex=True)
    es_const &= t["subcategoria"] == "(según clase)"
    clase = normalizar(t["clase_glosa"].fillna(""))
    sub = clase.map({k.upper(): v for k, v in c["subcategoria_por_clase"].items()})
    t.loc[es_const, "subcategoria"] = sub[es_const].fillna(c["subcategoria_sin_clase"]).to_numpy()

    t["llave_combinacion"] = t["articulo_normalizado"].fillna("").astype("string") + SEP + \
        llave_descripcion(t["descripcion"])
    t["producto"], t["origen_producto"] = asignar_productos(t, reglas)

    if maestro_comb is not None and len(maestro_comb):
        mc = maestro_comb.dropna(subset=["producto"])
        mc = mc[mc["origen"].isin(["humano", "llm"])].drop_duplicates("llave_combinacion", keep="last")
        mapa = dict(zip(mc["llave_combinacion"], mc["producto"]))
        orig = dict(zip(mc["llave_combinacion"], mc["origen"]))
        m = t["llave_combinacion"].isin(mapa.keys())
        t.loc[m, "producto"] = t.loc[m, "llave_combinacion"].map(mapa)
        t.loc[m, "origen_producto"] = t.loc[m, "llave_combinacion"].map(orig)

    t["excluir_de_kraljic"] = t["categoria"].isin(reglas.get("excluir_de_kraljic", []))
    for col in ["categoria", "subcategoria", "producto", "origen_categoria", "confianza_categoria", "origen_producto"]:
        t[col] = t[col].astype("string")
    return t, arts


def nuevas_para_validar(t: pd.DataFrame, maestro_art: pd.DataFrame | None,
                        maestro_comb: pd.DataFrame | None) -> tuple[pd.DataFrame, pd.DataFrame]:
    conocidos_art = set(maestro_art["articulo_normalizado"]) if maestro_art is not None else set()
    conocidas_comb = set(maestro_comb["llave_combinacion"]) if maestro_comb is not None else set()
    g = t.groupby("articulo_normalizado", dropna=False).agg(
        categoria=("categoria", "first"), subcategoria=("subcategoria", "first"),
        gasto=("monto_gasto", "sum"), filas=("id_linea", "size")).reset_index()
    art_nuevos = g[~g["articulo_normalizado"].isin(conocidos_art)].sort_values("gasto", ascending=False)
    c = combinaciones(t)
    comb_nuevas = c[~c["llave_combinacion"].isin(conocidas_comb)].sort_values("gasto", ascending=False)
    return art_nuevos, comb_nuevas


def combinaciones(t: pd.DataFrame) -> pd.DataFrame:
    return t.groupby("llave_combinacion", dropna=False).agg(
        articulo_normalizado=("articulo_normalizado", "first"),
        descripcion_ejemplo=("descripcion", "first"),
        concepto_ejemplo=("concepto", "first"),
        categoria=("categoria", "first"), subcategoria=("subcategoria", "first"),
        producto=("producto", "first"), origen=("origen_producto", "first"),
        gasto=("monto_gasto", "sum"), filas=("id_linea", "size")).reset_index()


def resumen(t: pd.DataFrame) -> dict[str, pd.DataFrame]:
    total = float(t["monto_gasto"].sum())

    def por(cols):
        g = t.groupby(cols, dropna=False).agg(gasto=("monto_gasto", "sum"), filas=("id_linea", "size"),
                                               oc=("oc", "nunique"), proveedores=("proveedor_id", "nunique"))
        g["pct_gasto"] = g["gasto"] / total * 100
        return g.reset_index().sort_values("gasto", ascending=False)

    cob = []
    for nivel, col in [("Categoría y subcategoría", "origen_categoria"), ("Producto", "origen_producto")]:
        g = t.groupby(col, dropna=False).agg(gasto=("monto_gasto", "sum"), filas=("id_linea", "size")).reset_index()
        g.insert(0, "nivel", nivel)
        g = g.rename(columns={col: "origen"})
        g["pct_gasto"] = g["gasto"] / total * 100
        g["pct_filas"] = g["filas"] / len(t) * 100
        cob.append(g)
    cuadre = pd.DataFrame([
        ("Gasto total de la tabla limpia", total),
        ("Suma del gasto por categoría", float(por(["categoria"])["gasto"].sum())),
        ("Filas sin clasificar", int((t["categoria"] == SIN_CLASIFICAR).sum())),
    ], columns=["control", "valor"])
    return {"Por_categoria": por(["categoria"]), "Por_subcategoria": por(["categoria", "subcategoria"]),
            "Por_producto": por(["categoria", "subcategoria", "producto"]),
            "Cobertura": pd.concat(cob, ignore_index=True), "Cuadre": cuadre}


# ------------------------------------------------------------------- maestro y validación

def construir_maestro(t: pd.DataFrame, arts: pd.DataFrame, reglas: dict) -> dict[str, pd.DataFrame]:
    hoy = date.today().isoformat()
    a = arts[["articulo_normalizado", "categoria", "subcategoria", "origen", "confianza", "regla"]].copy()
    a["fecha"] = hoy
    a["version"] = reglas["version"]
    c = combinaciones(t)[["llave_combinacion", "articulo_normalizado", "descripcion_ejemplo", "categoria",
                          "subcategoria", "producto", "origen"]].copy()
    c["fecha"] = hoy
    c["version"] = reglas["version"]
    return {"articulos": a, "combinaciones": c}


INSTRUCCIONES = [
    "Validación de la taxonomía de compras",
    "",
    "1. Hoja 'Articulos_95pct': artículos que suman el 95 % del gasto. Revísalos TODOS.",
    "   - Si la propuesta es correcta, escribe SI en '¿Correcto?'.",
    "   - Si no, escribe NO y llena 'Categoría corregida' y/o 'Subcategoría corregida'.",
    "   - Usa solo las categorías de la hoja 'Categorias'.",
    "2. Hoja 'Articulos_resto': revisión opcional (5 % del gasto). Mismo procedimiento.",
    "3. Hoja 'Muestra_productos': 200 combinaciones (100 elegidas por peso de gasto + 100 al azar).",
    "   Marca SI/NO en '¿Correcto?' y, si es NO, escribe el 'Producto corregido'.",
    "   Criterio de aceptación: 95 % o más de SI. Si no se alcanza, se ajustan las reglas de producto.",
    "4. Devuelve el archivo: el script 'clasificar.py --aplicar-validacion' carga tus correcciones al maestro.",
    "",
    "La columna 'Confianza' indica qué propuestas conviene mirar con más cuidado (media).",
    "Construcción se divide por tipo de intervención según la columna 'Clase' del ERP.",
]


def generar_validacion(t: pd.DataFrame, arts: pd.DataFrame, reglas: dict, semilla: int = 2026) -> dict[str, pd.DataFrame]:
    total = float(t["monto_gasto"].sum())
    g = t.groupby("articulo_normalizado").agg(gasto=("monto_gasto", "sum"), filas=("id_linea", "size"),
                                              proveedores=("proveedor_id", "nunique")).reset_index()
    ej = (t.dropna(subset=["descripcion"]).groupby("articulo_normalizado")["descripcion"]
          .agg(lambda s: " / ".join(s.value_counts().index[:3])))
    a = arts.merge(g, on="articulo_normalizado").sort_values("gasto", ascending=False)
    a["pct_gasto"] = a["gasto"] / total * 100
    a["pct_acumulado"] = a["pct_gasto"].cumsum()
    a["ejemplos_descripcion"] = a["articulo_normalizado"].map(ej)
    a["subcategoria"] = np.where(a["subcategoria"] == "(según clase)", "Según Clase (Obra nueva / Ampliación / …)",
                                 a["subcategoria"])
    cols = ["articulo_normalizado", "gasto", "pct_gasto", "pct_acumulado", "filas", "proveedores",
            "ejemplos_descripcion", "categoria", "subcategoria", "confianza"]
    a = a[cols].rename(columns={"articulo_normalizado": "Artículo", "gasto": "Gasto S/", "pct_gasto": "% gasto",
                                "pct_acumulado": "% acumulado", "filas": "Filas", "proveedores": "Proveedores",
                                "ejemplos_descripcion": "Ejemplos de descripción", "categoria": "Categoría propuesta",
                                "subcategoria": "Subcategoría propuesta", "confianza": "Confianza"})
    for c in ["¿Correcto? (SI/NO)", "Categoría corregida", "Subcategoría corregida", "Comentario"]:
        a[c] = ""
    corte = int((a["% acumulado"] < 95).sum()) + 1
    top, resto = a.iloc[:corte], a.iloc[corte:]

    c = combinaciones(t)
    c = c[c["gasto"] > 0].reset_index(drop=True)
    rng = np.random.default_rng(semilla)
    p = (c["gasto"] / c["gasto"].sum()).to_numpy()
    idx_peso = rng.choice(len(c), size=min(100, len(c)), replace=False, p=p)
    restantes = np.setdiff1d(np.arange(len(c)), idx_peso)
    idx_azar = rng.choice(restantes, size=min(100, len(restantes)), replace=False)
    muestra = pd.concat([c.loc[idx_peso].assign(seleccion="por gasto"), c.loc[idx_azar].assign(seleccion="al azar")])
    muestra = muestra[["seleccion", "llave_combinacion", "articulo_normalizado", "descripcion_ejemplo",
                       "concepto_ejemplo", "categoria", "subcategoria", "producto", "origen", "gasto"]]
    muestra = muestra.rename(columns={"seleccion": "Selección", "llave_combinacion": "Llave",
                                      "articulo_normalizado": "Artículo", "descripcion_ejemplo": "Descripción",
                                      "concepto_ejemplo": "Concepto", "categoria": "Categoría",
                                      "subcategoria": "Subcategoría", "producto": "Producto propuesto",
                                      "origen": "Origen del producto", "gasto": "Gasto S/"})
    muestra["¿Correcto? (SI/NO)"] = ""
    muestra["Producto corregido"] = ""

    reglas_prod = [{"Categoría": cat, "Palabras clave (regex)": r["patron"], "Producto": r["producto"]}
                   for cat, lista in (reglas.get("productos") or {}).items() for r in lista]
    return {
        "Instrucciones": pd.DataFrame({"Instrucciones": INSTRUCCIONES}),
        "Articulos_95pct": top, "Articulos_resto": resto, "Muestra_productos": muestra,
        "Categorias": pd.DataFrame({"Categoría": reglas["categorias"]}),
        "Reglas_producto": pd.DataFrame(reglas_prod),
    }


def aplicar_validacion(ruta_validacion: Path | str, ruta_maestro: Path | str) -> dict[str, int]:
    """Carga las correcciones de la persona al maestro (origen = humano)."""
    art, comb = leer_maestro(ruta_maestro)
    if art is None:
        raise FileNotFoundError(f"No existe el maestro: {ruta_maestro}")
    xl = pd.ExcelFile(ruta_validacion)
    cambios = {"articulos_confirmados": 0, "articulos_corregidos": 0, "productos_confirmados": 0,
               "productos_corregidos": 0}
    art = art.set_index("articulo_normalizado")
    for hoja in ["Articulos_95pct", "Articulos_resto"]:
        if hoja not in xl.sheet_names:
            continue
        v = pd.read_excel(xl, hoja, dtype=str).fillna("")
        for _, r in v.iterrows():
            ok = r["¿Correcto? (SI/NO)"].strip().upper()
            a = r["Artículo"]
            if a not in art.index or ok not in {"SI", "SÍ", "NO"}:
                continue
            if ok == "NO":
                if r["Categoría corregida"].strip():
                    art.loc[a, "categoria"] = r["Categoría corregida"].strip()
                if r["Subcategoría corregida"].strip():
                    art.loc[a, "subcategoria"] = r["Subcategoría corregida"].strip()
                cambios["articulos_corregidos"] += 1
            else:
                cambios["articulos_confirmados"] += 1
            art.loc[a, ["origen", "confianza", "fecha"]] = ["humano", "alta", date.today().isoformat()]
    comb = comb.set_index("llave_combinacion")
    if "Muestra_productos" in xl.sheet_names:
        v = pd.read_excel(xl, "Muestra_productos", dtype=str).fillna("")
        for _, r in v.iterrows():
            ok = r["¿Correcto? (SI/NO)"].strip().upper()
            k = r["Llave"]
            if k not in comb.index or ok not in {"SI", "SÍ", "NO"}:
                continue
            if ok == "NO" and r["Producto corregido"].strip():
                comb.loc[k, "producto"] = r["Producto corregido"].strip()
                cambios["productos_corregidos"] += 1
            else:
                cambios["productos_confirmados"] += 1
            comb.loc[k, ["origen", "fecha"]] = ["humano", date.today().isoformat()]
    escribir_excel(ruta_maestro, {"articulos": art.reset_index(), "combinaciones": comb.reset_index()})
    return cambios


def escribir_excel(ruta: Path | str, hojas: dict[str, pd.DataFrame]) -> None:
    control = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
    with pd.ExcelWriter(ruta, engine="openpyxl") as xw:
        for nombre, df in hojas.items():
            df = df.apply(lambda s: s.map(lambda v: control.sub(" ", v) if isinstance(v, str) else v)
                          if s.dtype == object or str(s.dtype) in ("string", "str") else s)
            df.to_excel(xw, sheet_name=nombre[:31], index=False)
            ws = xw.sheets[nombre[:31]]
            ws.freeze_panes = "A2"
            for col in ws.columns:
                ancho = min(60, max(10, max(len(str(c.value or "")) for c in col[:200]) + 2))
                ws.column_dimensions[col[0].column_letter].width = ancho


# ------------------------------------------------------------------- CLI

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Clasificación de la tabla limpia en la taxonomía de compras.")
    ap.add_argument("--tabla", help="tabla_limpia.parquet del Hilo 1")
    ap.add_argument("--salida", help="Carpeta de salida")
    ap.add_argument("--maestro", help="maestro_categorias.xlsx validado (opcional)")
    ap.add_argument("--reglas", default=str(REGLAS_DEFECTO))
    ap.add_argument("--construir-maestro", action="store_true", help="Escribe maestro_propuesto.xlsx")
    ap.add_argument("--generar-validacion", action="store_true", help="Escribe validacion_taxonomia.xlsx")
    ap.add_argument("--aplicar-validacion", help="Excel de validación devuelto por la persona")
    a = ap.parse_args(argv)

    if a.aplicar_validacion:
        cambios = aplicar_validacion(a.aplicar_validacion, a.maestro)
        print("Maestro actualizado:", cambios)
        return 0
    if not (a.tabla and a.salida):
        ap.error("--tabla y --salida son obligatorios")

    reglas = cargar_reglas(a.reglas)
    maestro_art, maestro_comb = leer_maestro(a.maestro)
    t = pd.read_parquet(a.tabla)
    tc, arts = clasificar(t, reglas, maestro_art, maestro_comb)
    carpeta = Path(a.salida)
    carpeta.mkdir(parents=True, exist_ok=True)
    tc.to_parquet(carpeta / "tabla_clasificada.parquet", index=False)
    res = resumen(tc)
    escribir_excel(carpeta / "resumen_clasificacion.xlsx", res)
    art_n, comb_n = nuevas_para_validar(tc, maestro_art, maestro_comb)
    escribir_excel(carpeta / "nuevas_para_validar.xlsx", {"articulos_nuevos": art_n, "combinaciones_nuevas": comb_n})
    if a.construir_maestro:
        escribir_excel(carpeta / "maestro_propuesto.xlsx", construir_maestro(tc, arts, reglas))
    if a.generar_validacion:
        escribir_excel(carpeta / "validacion_taxonomia.xlsx", generar_validacion(tc, arts, reglas))

    cuadre = res["Cuadre"].set_index("control")["valor"]
    print(f"Filas clasificadas: {len(tc):,} | sin clasificar: {int(cuadre['Filas sin clasificar'])}")
    print(f"Gasto total S/ {cuadre['Gasto total de la tabla limpia']:,.2f} | "
          f"suma por categoría S/ {cuadre['Suma del gasto por categoría']:,.2f}")
    print(f"Artículos nuevos vs. maestro: {len(art_n)} | combinaciones nuevas: {len(comb_n)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
