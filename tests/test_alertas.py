"""Pruebas del Hilo 4 (alertas de control)."""
from __future__ import annotations

import copy
import os
import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(RAIZ / "tests"))

import alertas as al  # noqa: E402
import clasificar as cl  # noqa: E402
import limpiar_validar as lv  # noqa: E402
from generar_sintetico import generar  # noqa: E402
from test_limpiar_validar import fila  # noqa: E402

PARAMS = lv.cargar_parametros()
REGLAS_TAX = cl.cargar_reglas()
R = al.cargar_yaml(al.REGLAS_DEFECTO)
MUESTRA = Path(os.environ.get("ANALISIS_MUESTRA", RAIZ / "data" / "muestra.xlsx"))
DIA = pd.Timestamp("2016-05-02")


def oc(n, dias, monto, **extra):
    """Una OC de una línea y una factura."""
    base = {"N° de Orden de Compra": n, "ID Interno OC": n, "Fecha de OC": DIA + pd.Timedelta(days=dias),
            "Monto MN": monto, "Monto facturado": monto, "N° de Factura": f"FA 0001-{n:06d}",
            "COMPRADOR": "A", "SUPERVISOR": "B", "Sede": "SEDE 1", "Clase": "Ampliaciones",
            "Proveedor": "20100000001 CONTRATISTA UNO S.A.C.", "Descripcion": "Obra civil ampliación"}
    base.update(extra)
    return fila(**base)


def casos_sembrados() -> list[dict]:
    return [
        # Fraccionamiento: 3 OC de S/ 20 000 (nivel 1) en 5 días → suman S/ 60 000 > S/ 35 000.
        oc(101, 0, 20000.0), oc(102, 2, 20000.0), oc(103, 5, 20000.0),
        # Servicio recurrente (Internet): mismo patrón, no debe alertar fraccionamiento.
        oc(201, 0, 20000.0, Articulo="Internet", Proveedor="20100000002 TELECOM S.A.C.", Descripcion="Internet sede"),
        oc(202, 2, 20000.0, Articulo="Internet", Proveedor="20100000002 TELECOM S.A.C.", Descripcion="Internet sede"),
        oc(203, 5, 20000.0, Articulo="Internet", Proveedor="20100000002 TELECOM S.A.C.", Descripcion="Internet sede"),
        # Posible factura duplicada dentro de la misma OC: dos facturas iguales, N° distinto.
        oc(301, 0, 10000.0, Proveedor="20100000003 MUEBLES S.A.C.", Articulo="Muebles y enseres en curso",
           Descripcion="Carpetas", **{"Monto facturado": 5000.0, "N° de Factura": "FA 0001-000900"}),
        oc(301, 0, 10000.0, Proveedor="20100000003 MUEBLES S.A.C.", Articulo="Muebles y enseres en curso",
           Descripcion="Carpetas", **{"Monto facturado": 5000.0, "N° de Factura": "FA 0001-000901"}),
        # Autoaprobación de una OC de nivel 3 (S/ 500 000, comprador = aprobador).
        oc(401, 90, 500000.0, COMPRADOR="C", SUPERVISOR="C", Proveedor="20100000004 GRANDE S.A.C."),
    ]


@pytest.fixture(scope="module")
def sembrado():
    t, _ = cl.clasificar(lv.procesar(pd.DataFrame(casos_sembrados()), PARAMS).tabla, REGLAS_TAX)
    return t, al.generar_alertas(t, PARAMS, R)


# 1. Casos sembrados se detectan.
def test_fraccionamiento_sembrado(sembrado):
    _, r = sembrado
    fr = r["fraccionamiento"]
    assert len(fr) == 1
    caso = fr.iloc[0]
    assert caso["oc"] == "101, 102, 103" and caso["prioridad"] == "Alta" and caso["limite_superado"] == 35000
    assert caso["suma_oc"] == 60000


def test_duplicado_y_autoaprobacion_sembrados(sembrado):
    _, r = sembrado
    du = r["duplicados"]
    fila_du = du[du["tipo"] == "Posible factura duplicada (misma OC)"]
    assert len(fila_du) == 1 and fila_du.iloc[0]["prioridad"] == "Alta" and fila_du.iloc[0]["oc"] == "301"
    au = r["autoaprobacion"]
    assert au["oc"].tolist() == [401]
    assert au.iloc[0]["nivel_aprobacion_oc"] == 3 and au.iloc[0]["prioridad"] == "Media"


# 2. Servicio recurrente no genera fraccionamiento.
def test_servicio_recurrente_no_alerta(sembrado):
    _, r = sembrado
    assert not r["fraccionamiento"]["proveedor_id"].eq("20100000002").any()


# 3. Cambiar los parámetros cambia el resultado.
def test_parametros_cambian_resultado(sembrado):
    t, _ = sembrado
    R2 = copy.deepcopy(R)
    R2["fraccionamiento"]["ventana_dias"] = 1
    assert len(al.generar_alertas(t, PARAMS, R2)["fraccionamiento"]) == 0
    R3 = copy.deepcopy(R)
    R3["autoaprobacion"]["nivel_minimo"] = 4
    assert len(al.generar_alertas(t, PARAMS, R3)["autoaprobacion"]) == 0


# 4. Muestra: el caso del 03/11/2015 (comprador C, 3 OC "Adicional por…" en Chimbote) NO cumple la regla:
#    son 3 proveedores distintos y cada OC ya supera S/ 35 000 (nivel 2); la suma (S/ 176 810) no pasa S/ 250 000.
@pytest.mark.skipif(not MUESTRA.exists(), reason="muestra no disponible")
def test_muestra_caso_chimbote_explicado():
    t, _ = cl.clasificar(lv.procesar(lv.leer_entrada(MUESTRA), PARAMS).tabla, REGLAS_TAX)
    x = t[t["fecha_oc"] == "2015-11-03"].drop_duplicates("oc")
    assert x["proveedor_id"].nunique() == 3
    assert (x["monto_oc"] > 35000).all() and x["monto_oc"].sum() < 250000
    r = al.generar_alertas(t, PARAMS, R)
    assert not r["fraccionamiento"].get("oc", pd.Series(dtype=str)).str.contains("20914").any()


# 5. Reproducible.
def test_reproducible():
    df, _ = generar(filas=4000, semilla=5)
    t, _ = cl.clasificar(lv.procesar(df, PARAMS).tabla, REGLAS_TAX)
    a = al.generar_alertas(t, PARAMS, R)
    b = al.generar_alertas(t.copy(), PARAMS, R)
    for k, v in a.items():
        if isinstance(v, pd.DataFrame):
            pd.testing.assert_frame_equal(v, b[k])
    assert a["hallazgos"] == b["hallazgos"]


def test_adicionales_excluye_aulas_adicionales():
    filas = [oc(1, 0, 100000.0, Descripcion="Adicional de obra por muro"),
             oc(2, 0, 100000.0, Descripcion="Construcción de 8 aulas adicionales")]
    t, _ = cl.clasificar(lv.procesar(pd.DataFrame(filas), PARAMS).tabla, REGLAS_TAX)
    assert t.sort_values("oc")["producto"].tolist() == ["Adicionales de obra", "Obra civil"]
