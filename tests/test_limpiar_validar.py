"""Pruebas del Hilo 1 (limpieza y validación).

La muestra y el extracto real NO están en el repositorio (son confidenciales). Las pruebas que
los usan se saltan si no se encuentran. Rutas por defecto (carpeta ignorada por git):
  data/muestra.xlsx   o variable de entorno ANALISIS_MUESTRA
  data/extracto.xlsx  o variable de entorno ANALISIS_EXTRACTO
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(RAIZ / "tests"))

import limpiar_validar as lv  # noqa: E402
from generar_sintetico import generar  # noqa: E402

PARAMS = lv.cargar_parametros()
MUESTRA = Path(os.environ.get("ANALISIS_MUESTRA", RAIZ / "data" / "muestra.xlsx"))
EXTRACTO = Path(os.environ.get("ANALISIS_EXTRACTO", RAIZ / "data" / "extracto.xlsx"))


def fila(**cambios) -> dict:
    """Una fila mínima válida con los nombres de columna de la muestra."""
    base = {
        "Año": 2017, "Mes": 5, "Fecha de OC": pd.Timestamp("2017-05-10"), "N° de Orden de Compra": 1,
        "Proveedor": "20100000001 PROVEEDOR UNO S.A.C.", "Sede": "SEDE 1", "Moneda": "Soles",
        "Monto MN": 100.0, "Monto ME": 0.0, "TC de OC": 1.0, "Procura": None, "Monto facturado": 100.0,
        "Monto FA ME": 0.0, "TC de FA": 1.0, "N° de Factura": "FA 0001-000001", "Periodo Factura": "may 2017",
        "Estado Factura": "Pagado por completo", "COMPRADOR": "A", "SUPERVISOR": "A", "Articulo": "Construccion",
        "Descripcion": "OBRA", "Concepto": "Obra", "Departamento": "CONST", "Clase": "Ampliaciones 2018",
        "ID Interno OC": 1, "Estado de OC": "Totalmente facturado",
    }
    base.update(cambios)
    return base


def procesar_filas(filas: list[dict]) -> lv.Resultado:
    return lv.procesar(pd.DataFrame(filas), PARAMS)


def falla(res: lv.Resultado, n: str) -> bool:
    v = res.validaciones.set_index("n")
    return v.loc[n, "estado"] == "FALLA"


# ------------------------------------------------------------- 1. muestra normal

@pytest.mark.skipif(not MUESTRA.exists(), reason="muestra no disponible (confidencial, fuera del repositorio)")
def test_muestra_cifras_de_control():
    res = lv.procesar(lv.leer_entrada(MUESTRA), PARAMS)
    t = res.tabla
    assert not res.bloqueado
    assert round(t["monto_gasto"].sum(), 2) == 2_454_438.56
    # "Monto MN" contado una vez por OC = gasto sin doble conteo (en la muestra cada OC está facturada al 100 %).
    assert round(t.loc[t["es_primera_linea_oc"] == 1, "monto_oc"].sum(), 2) == 2_454_438.56
    assert t["oc"].nunique() == 23
    assert t["proveedor_id"].nunique() == 14
    assert t["flag_clase_vacia"].sum() == 7
    assert t["flag_estado_contradictorio"].sum() == 6
    assert not t["descripcion"].str.contains("x000D", na=False).any()
    assert t.loc[t["oc"] == 35490, "monto_oc"].iloc[0] == pytest.approx(682_042.31)


# ------------------------------------------------------------- 2. columnas faltantes o renombradas

def test_columna_faltante_bloquea():
    df = pd.DataFrame([fila()]).drop(columns=["Monto facturado"])
    res = lv.procesar(df, PARAMS)
    assert res.bloqueado and res.tabla is None
    assert "Monto facturado" in res.validaciones.iloc[0]["detalle"]


def test_columna_renombrada_bloquea_y_cli_devuelve_2(tmp_path, capsys):
    df = pd.DataFrame([fila()]).rename(columns={"Proveedor": "Proveedor OC"})
    entrada = tmp_path / "export.csv"
    df.to_csv(entrada, index=False)
    codigo = lv.main(["--entrada", str(entrada), "--periodo", "prueba", "--salida", str(tmp_path / "out")])
    assert codigo == 2
    assert "PROCESO DETENIDO" in capsys.readouterr().err
    assert (tmp_path / "out" / "reporte_calidad.xlsx").exists()
    assert not (tmp_path / "out" / "tabla_limpia.parquet").exists()


def test_nombres_reales_se_mapean():
    df = pd.DataFrame([fila()]).rename(columns={"Año": "Unnamed: 0", "Procura": "Nota",
                                               "COMPRADOR": "Empleado", "SUPERVISOR": "Supervisor"})
    assert not lv.procesar(df, PARAMS).bloqueado


# ------------------------------------------------------------- 3. duplicados sembrados

def test_duplicados_sembrados_se_detectan():
    df, siembras = generar(filas=3000, semilla=7)
    res = lv.procesar(df, PARAMS)
    t = res.tabla
    assert t["flag_fila_duplicada"].sum() == siembras["filas_duplicadas"]
    marcadas = set(t.loc[t["flag_factura_en_varias_oc"], "oc"].astype(int))
    assert marcadas == set(siembras["factura_en_dos_oc"]["oc"])
    assert falla(res, "4") and not res.bloqueado


# ------------------------------------------------------------- 4. base sintética grande

def test_sintetico_250k_corre_y_cuadra():
    df, _ = generar(filas=250_000, semilla=42)
    res = lv.procesar(df, PARAMS)
    assert not res.bloqueado
    assert len(res.tabla) == 250_000
    assert res.tabla["monto_gasto"].sum() == pytest.approx(pd.to_numeric(df["Monto facturado"]).sum(), abs=0.01)
    assert res.tiempos["total_s"] < 120


# ------------------------------------------------------------- 5. reproducibilidad

def test_dos_ejecuciones_dan_lo_mismo():
    df, _ = generar(filas=5000, semilla=3)
    a = lv.procesar(df, PARAMS)
    b = lv.procesar(df.copy(), PARAMS)
    pd.testing.assert_frame_equal(a.tabla, b.tabla)
    pd.testing.assert_frame_equal(a.validaciones, b.validaciones)


# ------------------------------------------------------------- 6. extracto real

@pytest.mark.skipif(not EXTRACTO.exists(), reason="extracto real no disponible (confidencial, fuera del repositorio)")
def test_extracto_real_cifras_de_control():
    res = lv.procesar(lv.leer_entrada(EXTRACTO), PARAMS)
    t = res.tabla
    assert not res.bloqueado
    assert len(t) == 103_050
    assert t["oc"].nunique() == 23_009
    assert round(t["monto_gasto"].sum(), 2) == 283_013_851.95
    assert round(t.loc[t["es_primera_linea_oc"] == 1, "monto_oc"].sum(), 2) == 279_870_386.72
    assert t["flag_fila_duplicada"].sum() == 291
    assert t["flag_estado_contradictorio"].sum() == 1795


# ------------------------------------------------------------- reglas puntuales

def test_regla_monto_oc_en_los_tres_casos():
    filas = [
        # Caso A: una línea de 1 000 pagada con dos facturas (20 % y 80 %).
        fila(**{"N° de Orden de Compra": 1, "Monto MN": 1000.0, "Monto facturado": 200.0, "N° de Factura": "FA 1-1"}),
        fila(**{"N° de Orden de Compra": 1, "Monto MN": 1000.0, "Monto facturado": 800.0, "N° de Factura": "FA 1-2"}),
        # Caso B: tres líneas iguales de 50 en una sola factura.
        *[fila(**{"N° de Orden de Compra": 2, "Monto MN": 50.0, "Monto facturado": 50.0, "N° de Factura": "FA 2-1"})
          for _ in range(3)],
        # Caso C: total de 900 repetido en tres facturas de 300.
        *[fila(**{"N° de Orden de Compra": 3, "Monto MN": 900.0, "Monto facturado": 300.0, "N° de Factura": f"FA 3-{i}"})
          for i in range(3)],
    ]
    t = procesar_filas(filas).tabla
    montos = t.groupby("oc")["monto_oc"].first().to_dict()
    assert montos == {1: 1000.0, 2: 150.0, 3: 900.0}
    assert not t["flag_facturado_excede_oc"].any()
    assert t["es_primera_linea_oc"].sum() == 3


def test_limites_de_aprobacion_son_inclusivos():
    filas = [fila(**{"N° de Orden de Compra": i, "Monto MN": m, "Monto facturado": m, "N° de Factura": f"FA {i}"})
             for i, m in enumerate([35_000.0, 35_000.01, 250_000.0, 2_000_000.01], start=1)]
    t = procesar_filas(filas).tabla
    assert t["nivel_aprobacion_oc"].tolist() == [1, 2, 2, 5]


def test_oc_en_dolares_usa_limites_en_dolares():
    f = fila(**{"Moneda": "Dolares Americanos", "Monto MN": 40_000.0, "Monto ME": 12_000.0, "TC de OC": 3.33,
                "Monto facturado": 40_000.0})
    t = procesar_filas([f]).tabla
    assert t["nivel_aprobacion_oc"].iloc[0] == 2  # 12 000 USD > 10 000 USD


def test_limpieza_de_textos_y_fechas():
    f = fila(**{"Proveedor": "EXTERIOR UNIVERSITY INC", "Descripcion": " AMPLIACION_x000D_ OBRA ",
                "Articulo": "Ventas :Alojamiento", "Periodo Factura": "set 2016", "Clase": None,
                "Estado Factura": "Pendiente", "N° de Factura": None})
    t = procesar_filas([f]).tabla.iloc[0]
    assert pd.isna(t["ruc"]) and t["flag_proveedor_exterior"]
    assert t["proveedor_id"] == "EXT:EXTERIOR UNIVERSITY INC"
    assert t["descripcion"] == "AMPLIACION OBRA"
    assert t["articulo_normalizado"] == "VENTAS : ALOJAMIENTO"
    assert t["periodo_factura"] == pd.Timestamp("2016-09-01") and t["semestre"] == "2016-S2"
    assert t["flag_clase_vacia"] and t["pendiente_de_pago"] and t["flag_sin_factura"]


def test_ruc_y_clase_se_separan():
    t = procesar_filas([fila()]).tabla.iloc[0]
    assert t["ruc"] == "20100000001" and t["proveedor"] == "PROVEEDOR UNO S.A.C."
    assert t["clase_glosa"] == "Ampliaciones" and t["clase_anio"] == 2018


def test_facturado_que_excede_la_oc_se_marca():
    filas = [fila(**{"Monto MN": 1000.0, "Monto facturado": 700.0, "N° de Factura": f"FA {i}"}) for i in range(2)]
    t = procesar_filas(filas).tabla
    assert t["flag_facturado_excede_oc"].all()
    assert not procesar_filas(filas).bloqueado
