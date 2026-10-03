"""Hilo 1 – Carga, limpieza y validación de la exportación del ERP.

Recibe la exportación cruda (xlsx o csv) y entrega:
  - tabla_limpia.parquet: una fila por línea de OC con columnas limpias y derivadas.
  - reporte_calidad.xlsx: validaciones, control de totales, banderas y equivalencia de códigos.

Uso:
  python scripts/limpiar_validar.py --entrada <archivo> --periodo 2017-S2 [--salida <carpeta>]

Todas las reglas y umbrales se leen de config/parametros.yaml.
Código de salida: 0 = OK (con o sin advertencias), 2 = una validación BLOQUEA.
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

RAIZ = Path(__file__).resolve().parents[1]
PARAMETROS_DEFECTO = RAIZ / "config" / "parametros.yaml"

BLOQUEA = "BLOQUEA"
ADVIERTE = "ADVIERTE"


class ValidacionBloqueante(Exception):
    """Una validación de nivel BLOQUEA falló: el proceso no debe continuar."""


@dataclass
class Resultado:
    tabla: pd.DataFrame | None
    validaciones: pd.DataFrame
    control: pd.DataFrame
    codigos: pd.DataFrame
    tiempos: dict = field(default_factory=dict)

    @property
    def bloqueado(self) -> bool:
        v = self.validaciones
        return bool(((v["nivel"] == BLOQUEA) & (v["estado"] == "FALLA")).any())


# --------------------------------------------------------------------------- carga

def cargar_parametros(ruta: Path | str = PARAMETROS_DEFECTO) -> dict:
    with open(ruta, encoding="utf-8") as f:
        return yaml.safe_load(f)


def leer_entrada(ruta: Path | str) -> pd.DataFrame:
    """Lee xlsx (primera hoja) o csv. Usa el motor calamine si está instalado (más rápido)."""
    ruta = Path(ruta)
    if ruta.suffix.lower() == ".csv":
        return pd.read_csv(ruta, low_memory=False)
    try:
        return pd.read_excel(ruta, sheet_name=0, engine="calamine")
    except (ImportError, ValueError):
        return pd.read_excel(ruta, sheet_name=0, engine="openpyxl")


def estandarizar_columnas(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    mapeo = {str(k): v for k, v in params["mapeo_columnas"].items()}
    nuevos = [mapeo.get(str(c).strip(), str(c).strip()) for c in df.columns]
    df = df.copy()
    df.columns = nuevos
    return df


# ------------------------------------------------------------------ utilidades

def limpiar_texto(s: pd.Series, basura: list[str]) -> pd.Series:
    s = s.astype("string")
    for b in basura:
        s = s.str.replace(b, " ", regex=False)
    s = s.str.replace(r"[\x00-\x1f\x7f]+", " ", regex=True)  # saltos de línea y caracteres de control
    s = s.str.replace(r"\s+", " ", regex=True).str.strip()
    return s.mask(s == "", pd.NA)


def normalizar_articulo(s: pd.Series) -> pd.Series:
    s = s.str.upper().str.replace(r"\s*:\s*", " : ", regex=True).str.replace(r"\s+", " ", regex=True)
    return s.str.strip()


def normalizar_factura(s: pd.Series) -> pd.Series:
    return s.str.upper().str.replace(r"[\s\-_.]", "", regex=True)


def periodo_a_fecha(s: pd.Series, meses: dict) -> pd.Series:
    partes = s.str.lower().str.extract(r"^\s*([a-záéíóú]{3})[a-záéíóú]*\.?\s+(\d{4})\s*$")
    mes = partes[0].map(meses).astype("Int64").astype("string").str.zfill(2)
    texto = partes[1].astype("string") + "-" + mes + "-01"
    return pd.to_datetime(texto, format="%Y-%m-%d", errors="coerce")


def semestre_de(fecha: pd.Series, params: dict) -> pd.Series:
    s1 = set(params["periodo"]["s1_meses"])
    sufijo = np.where(fecha.dt.month.isin(s1), "S1", "S2")
    out = fecha.dt.year.astype("Int64").astype("string") + "-" + pd.Series(sufijo, index=fecha.index)
    return out.where(fecha.notna(), pd.NA)


def codificar(s: pd.Series, prefijo: str, previos: pd.DataFrame | None = None) -> tuple[pd.Series, pd.DataFrame]:
    """Asigna códigos a nombres de personas (orden alfabético).

    Con `previos` (tabla codigo–nombre de ciclos anteriores) los códigos existentes se conservan y las personas
    nuevas reciben el número siguiente: así un mismo comprador tiene el mismo código en todos los ciclos."""
    valores = sorted(s.dropna().unique())
    mapa = {}
    if previos is not None and len(previos):
        mapa = dict(zip(previos["nombre"].astype(str), previos["codigo"].astype(str)))
    nums = [int(c[len(prefijo):]) for c in mapa.values() if str(c).startswith(prefijo) and c[len(prefijo):].isdigit()]
    nuevos = [v for v in valores if v not in mapa]
    ancho = max(3, len(str(len(mapa) + len(nuevos))), *(len(c) - len(prefijo) for c in mapa.values()))
    siguiente = max(nums, default=0) + 1
    for i, v in enumerate(nuevos):
        mapa[v] = f"{prefijo}{siguiente + i:0{ancho}d}"
    tabla = pd.DataFrame({"codigo": list(mapa.values()), "nombre": list(mapa.keys())})
    return s.map(mapa).astype("string"), tabla


def nivel_aprobacion(monto: pd.Series, niveles: list[dict], campo: str) -> pd.Series:
    limites = [n[campo] for n in niveles if n[campo] is not None]
    idx = np.searchsorted(np.asarray(limites, dtype=float), monto.to_numpy(dtype=float), side="left")
    nivel = pd.Series(idx + 1, index=monto.index, dtype="Int64")
    return nivel.where(monto.notna(), pd.NA)


# ------------------------------------------------------------------ validación

def _v(lista, num, nombre, nivel, n_casos, detalle, aplica=True):
    estado = "FALLA" if (aplica and n_casos > 0) else "OK"
    lista.append(
        {"n": num, "validacion": nombre, "nivel": nivel, "estado": estado,
         "casos": int(n_casos), "detalle": detalle}
    )


def validar_estructura(df: pd.DataFrame, params: dict) -> list[dict]:
    req = params["limpieza"]["columnas_requeridas"]
    faltan = [c for c in req if c not in df.columns]
    sobran = [c for c in df.columns if c not in req]
    v: list[dict] = []
    detalle = "Faltan: " + ", ".join(faltan) if faltan else "Las 26 columnas están presentes."
    if sobran:
        detalle += " | Columnas no previstas (se ignoran): " + ", ".join(map(str, sobran))
    _v(v, "1", "Columnas requeridas presentes (tras mapeo de nombres)", BLOQUEA, len(faltan), detalle)
    return v


def validar_contenido(df: pd.DataFrame, t: pd.DataFrame, params: dict, historico: pd.DataFrame | None) -> list[dict]:
    """df = datos crudos estandarizados; t = tabla ya transformada (mismas filas)."""
    L = params["limpieza"]
    v: list[dict] = []

    montos_invalidos = 0
    for c in ["Monto facturado", "Monto MN"]:
        crudo = df[c]
        num = pd.to_numeric(crudo, errors="coerce")
        montos_invalidos += int((num.isna() & crudo.notna()).sum())
    fechas_invalidas = int(t["fecha_oc"].isna().sum())
    oc_invalidas = int(t["oc"].isna().sum())
    _v(v, "2a", "Montos numéricos, fecha de OC y N° de OC legibles", BLOQUEA,
       montos_invalidos + fechas_invalidas + oc_invalidas,
       f"Montos no numéricos: {montos_invalidos}; fechas de OC ilegibles: {fechas_invalidas}; "
       f"N° de OC ilegibles: {oc_invalidas}.")

    con_texto = df["Periodo Factura"].notna()
    periodo_malo = int((con_texto & t["periodo_factura"].isna()).sum())
    _v(v, "2b", "Periodo Factura legible", ADVIERTE, periodo_malo,
       f"Filas con 'Periodo Factura' no reconocido: {periodo_malo}.")

    sin_prov = int(t["proveedor"].isna().sum())
    _v(v, "3a", "Filas con proveedor, N° de OC y fecha de OC", BLOQUEA, sin_prov + oc_invalidas + fechas_invalidas,
       f"Sin proveedor: {sin_prov}; sin N° de OC: {oc_invalidas}; sin fecha de OC: {fechas_invalidas}.")

    sin_fac = int(t["flag_sin_factura"].sum())
    sin_desc = int(t["flag_descripcion_vacia"].sum())
    sin_comp = int(t["comprador_codigo"].isna().sum())
    monto_nulo = int(t["monto_gasto"].isna().sum())
    _v(v, "3b", "Filas sin factura, sin descripción, sin comprador o sin monto", ADVIERTE,
       sin_fac + sin_desc + sin_comp + monto_nulo,
       f"Sin factura (OC sin facturar): {sin_fac}; sin descripción: {sin_desc}; "
       f"sin comprador: {sin_comp}; monto facturado vacío: {monto_nulo}.")

    dup = int(t["flag_fila_duplicada"].sum())
    fac_multi = int(t["flag_factura_en_varias_oc"].sum())
    _v(v, "4", "Duplicados (filas idénticas; misma factura en OC distintas)", ADVIERTE, dup + fac_multi,
       f"Filas idénticas en todas las columnas: {dup} (se conservan, no se borran); "
       f"filas cuya factura (RUC + N° normalizado) aparece en más de una OC: {fac_multi}.")

    extranjera = int(t["flag_moneda_extranjera"].sum())
    ext_sin_monto = int((t["flag_moneda_extranjera"] & t["monto_gasto"].isna()).sum())
    _v(v, "5", "Moneda extranjera", ADVIERTE, extranjera,
       f"Filas en moneda distinta a soles: {extranjera} ('Monto facturado' ya viene en soles). "
       f"De ellas, sin monto en soles: {ext_sin_monto}.")
    _v(v, "5b", "Moneda extranjera sin monto en soles", BLOQUEA, ext_sin_monto,
       "Filas en moneda extranjera sin 'Monto facturado': no se pueden convertir.")

    est_oc = set(t["estado_oc"].dropna().unique()) - set(L["estados_oc_conocidos"])
    est_fa = set(t["estado_factura"].dropna().unique()) - set(L["estados_factura_conocidos"])
    n_nuevos = int(t["estado_oc"].isin(est_oc).sum() + t["estado_factura"].isin(est_fa).sum())
    _v(v, "6", "Estados de OC y de factura previstos", ADVIERTE, n_nuevos,
       f"Estados de OC nuevos: {sorted(est_oc) or 'ninguno'}; estados de factura nuevos: {sorted(est_fa) or 'ninguno'}. "
       "Toda factura registrada cuenta como gasto.")

    if historico is None:
        _v(v, "7", "Proveedores, compradores o sedes nuevos vs. histórico", ADVIERTE, 0,
           "Sin histórico todavía: no se compara (informativo).", aplica=False)
    else:
        nuevos = {}
        for col in ["proveedor_id", "comprador_codigo", "sede"]:
            if col in historico.columns:
                nuevos[col] = len(set(t[col].dropna()) - set(historico[col].dropna()))
        _v(v, "7", "Proveedores, compradores o sedes nuevos vs. histórico", ADVIERTE, sum(nuevos.values()),
           "; ".join(f"{k}: {n}" for k, n in nuevos.items()))

    contradictorio = int(t["flag_estado_contradictorio"].sum())
    _v(v, "6b", "Estado de OC contradice Estado Factura (manda Estado Factura)", ADVIERTE, contradictorio,
       f"Filas con 'Factura pendiente' en la OC y 'Pagado por completo' en la factura: {contradictorio}. "
       "Se consideran pagadas.")

    excede_oc = t.loc[t["flag_facturado_excede_oc"], "oc"].nunique()
    excede_monto = float(t.loc[t["flag_facturado_excede_oc"], "monto_gasto"].sum())
    tol = params["validacion"]["tolerancia_facturado_excede_oc"]
    _v(v, "9", f"Facturado mayor al monto de la OC en más de {tol:.0%}", ADVIERTE, excede_oc,
       f"OC que exceden: {excede_oc}; gasto facturado en esas OC: S/ {excede_monto:,.2f}. Revisar en el Hilo 4.")
    return v


# ------------------------------------------------------------------ transformación

def transformar(df: pd.DataFrame, params: dict, codigos_previos: pd.DataFrame | None = None
                ) -> tuple[pd.DataFrame, pd.DataFrame]:
    L = params["limpieza"]
    G = params["gasto"]
    basura = L["textos_basura"]
    n = len(df)
    t = pd.DataFrame(index=df.index)
    t["id_linea"] = np.arange(1, n + 1, dtype="int64")

    t["anio_oc"] = pd.to_numeric(df["Año"], errors="coerce").astype("Int64")
    t["mes_oc"] = pd.to_numeric(df["Mes"], errors="coerce").astype("Int64")
    t["fecha_oc"] = pd.to_datetime(df["Fecha de OC"], errors="coerce")
    t["oc"] = pd.to_numeric(df["N° de Orden de Compra"], errors="coerce").astype("Int64")
    t["id_interno_oc"] = pd.to_numeric(df["ID Interno OC"], errors="coerce").astype("Int64")

    prov = limpiar_texto(df["Proveedor"], basura)
    partes = prov.str.extract(r"^(\d{11})\s+(.*)$")
    t["ruc"] = partes[0].astype("string")
    t["proveedor"] = partes[1].astype("string").fillna(prov)
    t["flag_proveedor_exterior"] = t["ruc"].isna() & prov.notna()
    t["proveedor_id"] = t["ruc"].fillna("EXT:" + t["proveedor"].str.upper())
    t["proveedor_original"] = prov

    t["sede"] = limpiar_texto(df["Sede"], basura)
    t["departamento"] = limpiar_texto(df["Departamento"], basura)
    t["moneda"] = limpiar_texto(df["Moneda"], basura)
    t["flag_moneda_extranjera"] = t["moneda"].notna() & (t["moneda"] != params["moneda"]["valor_moneda_base"])

    t["monto_mn_linea"] = pd.to_numeric(df[G["campo_monto_oc"]], errors="coerce")
    t["monto_me_linea"] = pd.to_numeric(df[G["campo_monto_oc_me"]], errors="coerce")
    t["tc_oc"] = pd.to_numeric(df["TC de OC"], errors="coerce")
    t["monto_gasto"] = pd.to_numeric(df[G["campo_monto_gasto"]], errors="coerce")
    t["monto_fa_me"] = pd.to_numeric(df["Monto FA ME"], errors="coerce")
    t["tc_fa"] = pd.to_numeric(df["TC de FA"], errors="coerce")

    fac = limpiar_texto(df["N° de Factura"], basura)
    t["n_factura"] = fac
    t["factura_normalizada"] = normalizar_factura(fac)
    t["flag_sin_factura"] = fac.isna()

    t["periodo_factura"] = periodo_a_fecha(limpiar_texto(df["Periodo Factura"], basura), L["meses_es"])
    t["flag_semestre_por_fecha_oc"] = t["periodo_factura"].isna()
    fecha_gasto = t["periodo_factura"].fillna(t["fecha_oc"].dt.to_period("M").dt.to_timestamp())
    t["semestre"] = semestre_de(fecha_gasto, params)
    t["anio_gasto"] = fecha_gasto.dt.year.astype("Int64")

    t["estado_factura"] = limpiar_texto(df["Estado Factura"], basura)
    t["estado_oc"] = limpiar_texto(df["Estado de OC"], basura)
    pagados = set(G["estados_pagados"])
    t["pendiente_de_pago"] = ~t["estado_factura"].isin(pagados).fillna(False).astype(bool)
    t["flag_estado_contradictorio"] = (
        (t["estado_oc"] == L["estado_oc_pendiente"]).fillna(False)
        & t["estado_factura"].isin(pagados).fillna(False)
    ).astype(bool)

    comprador = limpiar_texto(df["COMPRADOR"], basura)
    aprobador = limpiar_texto(df["SUPERVISOR"], basura)
    personas = pd.concat([comprador, aprobador]).dropna()
    _, tabla_codigos = codificar(personas, "P", codigos_previos)
    mapa = dict(zip(tabla_codigos["nombre"], tabla_codigos["codigo"]))
    t["comprador_codigo"] = comprador.map(mapa).astype("string")
    t["aprobador_codigo"] = aprobador.map(mapa).astype("string")

    art = limpiar_texto(df["Articulo"], basura)
    t["articulo"] = art
    t["articulo_normalizado"] = normalizar_articulo(art)
    t["descripcion"] = limpiar_texto(df["Descripcion"], basura)
    t["flag_descripcion_vacia"] = t["descripcion"].isna()
    t["concepto"] = limpiar_texto(df["Concepto"], basura)
    t["nota"] = limpiar_texto(df["Nota"], basura)

    clase = limpiar_texto(df["Clase"], basura)
    t["clase"] = clase
    anio = clase.str.extract(r"((?:19|20)\d{2})\s*$")[0]
    t["clase_anio"] = pd.to_numeric(anio, errors="coerce").astype("Int64")
    t["clase_glosa"] = clase.str.replace(r"\s*(?:19|20)\d{2}\s*$", "", regex=True).str.strip()
    t["flag_clase_vacia"] = clase.isna()

    # ---- monto total de la OC (regla aprobada en el Hilo 1):
    # por cada factura de la OC se suma "Monto MN" de sus filas; se toma la suma más alta.
    llave_fac = t["factura_normalizada"].fillna("__SIN_FACTURA__")
    for col_linea, col_oc in [("monto_mn_linea", "monto_oc"), ("monto_me_linea", "monto_oc_me")]:
        por_factura = t.groupby([t["oc"], llave_fac], dropna=False)[col_linea].sum()
        total = por_factura.groupby(level=0, dropna=False).max()
        t[col_oc] = t["oc"].map(total)
    orden = t.sort_values(["oc", "id_linea"], kind="stable")
    t["es_primera_linea_oc"] = (~orden["oc"].duplicated()).reindex(t.index).astype("int8")

    niveles = params["aprobacion_oc"]
    nivel_pen = nivel_aprobacion(t["monto_oc"], niveles, "hasta_pen")
    nivel_usd = nivel_aprobacion(t["monto_oc_me"], niveles, "hasta_usd")
    t["nivel_aprobacion_oc"] = nivel_pen.where(~t["flag_moneda_extranjera"], nivel_usd)

    tol = params["validacion"]["tolerancia_facturado_excede_oc"]
    facturado_oc = t.groupby("oc")["monto_gasto"].transform("sum")
    t["flag_facturado_excede_oc"] = (facturado_oc > t["monto_oc"] * (1 + tol)).fillna(False).astype(bool)

    t["flag_fila_duplicada"] = df.duplicated(keep=False).to_numpy()
    con_fac = t["factura_normalizada"].notna()
    n_oc_por_fac = t[con_fac].groupby(["proveedor_id", "factura_normalizada"])["oc"].transform("nunique")
    t["flag_factura_en_varias_oc"] = False
    t.loc[con_fac, "flag_factura_en_varias_oc"] = (n_oc_por_fac > 1).to_numpy()

    return t.reset_index(drop=True), tabla_codigos


def control_totales(df: pd.DataFrame, t: pd.DataFrame, params: dict) -> pd.DataFrame:
    G = params["gasto"]
    antes = float(pd.to_numeric(df[G["campo_monto_gasto"]], errors="coerce").sum())
    despues = float(t["monto_gasto"].sum())
    oc_total = float(t.loc[t["es_primera_linea_oc"] == 1, "monto_oc"].sum())
    oc_antes = int(pd.to_numeric(df["N° de Orden de Compra"], errors="coerce").nunique())
    prov_antes = int(df["Proveedor"].nunique())
    prov_despues = int(t["proveedor_id"].nunique())
    filas = [
        ("Filas leídas", len(df), len(t), len(df) - len(t), "Deben ser iguales."),
        ("Suma 'Monto facturado' (gasto)", round(antes, 2), round(despues, 2), round(antes - despues, 2),
         "Deben ser iguales (validación 8)."),
        ("OC distintas", oc_antes, int(t["oc"].nunique()), oc_antes - int(t["oc"].nunique()), "Deben ser iguales."),
        ("Proveedores distintos", prov_antes, prov_despues, prov_antes - prov_despues,
         "Después se cuenta por RUC: un mismo RUC escrito con nombres distintos se une."),
        ("Monto total de OC (regla: suma más alta por factura)", None, round(oc_total, 2), None,
         "Se usa para el nivel de aprobación."),
        ("Referencia: suma de 'Monto MN' fila por fila (NO usar)",
         round(float(pd.to_numeric(df[G["campo_monto_oc"]], errors="coerce").sum()), 2), None, None,
         "Duplica montos: solo como referencia."),
    ]
    return pd.DataFrame(filas, columns=["control", "antes", "despues", "diferencia", "nota"])


# ------------------------------------------------------------------ proceso

def procesar(df_crudo: pd.DataFrame, params: dict, historico: pd.DataFrame | None = None,
             codigos_previos: pd.DataFrame | None = None) -> Resultado:
    tiempos = {}
    t0 = time.perf_counter()
    df = estandarizar_columnas(df_crudo, params)
    val = validar_estructura(df, params)
    if val[0]["estado"] == "FALLA":
        return Resultado(None, pd.DataFrame(val), pd.DataFrame(), pd.DataFrame(), tiempos)

    df = df[params["limpieza"]["columnas_requeridas"]]
    t, codigos = transformar(df, params, codigos_previos)
    tiempos["transformar_s"] = round(time.perf_counter() - t0, 2)

    ctrl = control_totales(df, t, params)
    val += validar_contenido(df, t, params, historico)
    dif = abs(ctrl.loc[1, "diferencia"])
    filas_dif = ctrl.loc[0, "diferencia"]
    tol = params["validacion"]["tolerancia_control_totales"]
    _v(val, "8", "Control de totales antes/después de limpiar", BLOQUEA,
       int(dif > tol or filas_dif != 0),
       f"Diferencia de gasto: S/ {dif:,.2f}; diferencia de filas: {filas_dif}.")
    orden = {k: i for i, k in enumerate(["1", "2a", "2b", "3a", "3b", "4", "5", "5b", "6", "6b", "7", "8", "9"])}
    vdf = pd.DataFrame(val)
    vdf = vdf.sort_values("n", key=lambda s: s.map(orden)).reset_index(drop=True)
    tiempos["total_s"] = round(time.perf_counter() - t0, 2)
    return Resultado(t, vdf, ctrl, codigos, tiempos)


BANDERAS_REPORTE = [
    "flag_fila_duplicada", "flag_factura_en_varias_oc", "flag_facturado_excede_oc",
    "flag_sin_factura", "flag_estado_contradictorio",
]
COLUMNAS_REPORTE = [
    "id_linea", "oc", "fecha_oc", "proveedor_id", "proveedor", "comprador_codigo", "aprobador_codigo",
    "articulo_normalizado", "descripcion", "n_factura", "periodo_factura", "monto_mn_linea",
    "monto_gasto", "monto_oc", "nivel_aprobacion_oc", "estado_oc", "estado_factura",
]


def resumen_banderas(t: pd.DataFrame) -> pd.DataFrame:
    flags = [c for c in t.columns if c.startswith("flag_")]
    filas = []
    for f in flags:
        m = t[f].astype(bool)
        filas.append({"bandera": f, "filas": int(m.sum()), "oc": int(t.loc[m, "oc"].nunique()),
                      "gasto_soles": round(float(t.loc[m, "monto_gasto"].sum()), 2)})
    return pd.DataFrame(filas)


def guardar(res: Resultado, carpeta: Path, params: dict, entrada: str, periodo: str) -> dict:
    carpeta.mkdir(parents=True, exist_ok=True)
    rutas = {"reporte": carpeta / "reporte_calidad.xlsx"}
    with pd.ExcelWriter(rutas["reporte"], engine="openpyxl") as xw:
        info = pd.DataFrame(
            [("Archivo de entrada", Path(entrada).name), ("Periodo del ciclo", periodo),
             ("Resultado", "BLOQUEADO" if res.bloqueado else "OK"),
             ("Tiempo de proceso (s)", res.tiempos.get("total_s"))],
            columns=["dato", "valor"])
        info.to_excel(xw, sheet_name="Resumen", index=False)
        res.validaciones.to_excel(xw, sheet_name="Resumen", index=False, startrow=len(info) + 2)
        if not res.control.empty:
            res.control.to_excel(xw, sheet_name="Control_totales", index=False)
        if res.tabla is not None:
            t = res.tabla
            resumen_banderas(t).to_excel(xw, sheet_name="Banderas", index=False)
            m = t[BANDERAS_REPORTE].any(axis=1)
            detalle = t.loc[m, COLUMNAS_REPORTE + BANDERAS_REPORTE]
            detalle.head(params["validacion"]["max_filas_reporte"]).to_excel(
                xw, sheet_name="Filas_con_banderas", index=False)
            por_sem = t.groupby("semestre", dropna=False).agg(
                filas=("id_linea", "size"), gasto_soles=("monto_gasto", "sum"), oc=("oc", "nunique")).reset_index()
            por_sem.to_excel(xw, sheet_name="Por_semestre", index=False)
            res.codigos.to_excel(xw, sheet_name="Codigos_personas", index=False)
    if res.tabla is not None and not res.bloqueado:
        rutas["tabla"] = carpeta / "tabla_limpia.parquet"
        res.tabla.to_parquet(rutas["tabla"], index=False)
    return rutas


def carpeta_salida_defecto(params: dict, periodo: str) -> Path:
    raiz = Path(params["rutas"]["raiz_datos"])
    base = raiz / params["rutas"]["salida"] if raiz.exists() else RAIZ / "salida"
    return base / periodo


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Limpieza y validación de la exportación del ERP.")
    ap.add_argument("--entrada", required=True, help="Archivo xlsx o csv exportado del ERP")
    ap.add_argument("--periodo", required=True, help="Etiqueta del ciclo, ej. 2017-S2")
    ap.add_argument("--salida", help="Carpeta de salida (por defecto: <raiz_datos>/salida/<periodo>)")
    ap.add_argument("--parametros", default=str(PARAMETROS_DEFECTO))
    ap.add_argument("--historico", help="Parquet de un ciclo anterior para detectar valores nuevos (opcional)")
    ap.add_argument("--codigos", help="codigos_personas.xlsx de ciclos anteriores (mantiene los mismos códigos)")
    a = ap.parse_args(argv)

    params = cargar_parametros(a.parametros)
    t0 = time.perf_counter()
    crudo = leer_entrada(a.entrada)
    t_lectura = round(time.perf_counter() - t0, 2)
    hist = pd.read_parquet(a.historico) if a.historico else None
    previos = pd.read_excel(a.codigos, dtype=str) if a.codigos and Path(a.codigos).exists() else None
    res = procesar(crudo, params, hist, previos)
    res.tiempos["lectura_s"] = t_lectura
    carpeta = Path(a.salida) if a.salida else carpeta_salida_defecto(params, a.periodo)
    rutas = guardar(res, carpeta, params, a.entrada, a.periodo)

    print(f"Filas leídas: {len(crudo):,} | lectura {t_lectura}s | proceso {res.tiempos.get('total_s')}s")
    for _, r in res.validaciones.iterrows():
        marca = "✔" if r["estado"] == "OK" else ("✖" if r["nivel"] == BLOQUEA else "!")
        print(f"  {marca} [{r['nivel']}] {r['n']} {r['validacion']}: {r['detalle']}")
    print("Salidas:", ", ".join(str(p) for p in rutas.values()))
    if res.bloqueado:
        print("PROCESO DETENIDO: una validación BLOQUEA. Revise reporte_calidad.xlsx.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
