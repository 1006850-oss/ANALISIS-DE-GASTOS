"""Pruebas del Hilo 5 (matriz de Kraljic)."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(RAIZ / "tests"))

import analizar as an  # noqa: E402
import clasificar as cl  # noqa: E402
import kraljic as kr  # noqa: E402
import limpiar_validar as lv  # noqa: E402
from generar_sintetico import generar  # noqa: E402

PARAMS = lv.cargar_parametros()
K = kr.cargar_yaml(kr.KRALJIC_DEFECTO)


@pytest.fixture(scope="module")
def tabla() -> pd.DataFrame:
    df, _ = generar(filas=6000, semilla=31)
    t, _ = cl.clasificar(lv.procesar(df, PARAMS).tabla, cl.cargar_reglas())
    return t


@pytest.fixture(scope="module")
def r(tabla):
    return kr.matriz_kraljic(tabla, PARAMS, K)


# 1. Cada unidad queda en exactamente un cuadrante.
def test_un_cuadrante_por_unidad(r):
    for nivel in ["unidades", "categorias", "productos"]:
        d = r[nivel]
        assert d["cuadrante"].isin(kr.CUADRANTES).all()
        assert d["cuadrante"].notna().all()
    assert r["unidades"]["unidad"].is_unique


# 2. Cambiar el corte de impacto o un peso mueve las unidades como se espera.
def test_parametros_mueven_cuadrantes(tabla, r):
    base = r["unidades"]
    k2 = copy.deepcopy(K)
    k2["impacto"]["corte_pareto"] = 0.95
    alto2 = kr.matriz_kraljic(tabla, PARAMS, k2)["unidades"]["alto_impacto"].sum()
    assert alto2 > base["alto_impacto"].sum()
    k3 = copy.deepcopy(K)
    k3["riesgo"]["corte_alto"] = 1.0  # todo es riesgo alto → solo estratégico o cuello de botella
    q = kr.matriz_kraljic(tabla, PARAMS, k3)["unidades"]["cuadrante"]
    assert set(q) <= {"Estratégico", "Cuello de botella"}


# 3. Sin puntaje experto ni propuesta → solo data y "provisional".
def test_sin_experto_usa_solo_data(tabla):
    k2 = copy.deepcopy(K)
    k2["propuesta_ia"] = {}
    u = kr.matriz_kraljic(tabla, PARAMS, k2)["unidades"]
    assert (u["estado"] == "provisional (solo data)").all()
    assert (u["puntaje_riesgo"] == u["puntaje_datos"]).all()


def test_taller_experto_manda_sobre_propuesta(tabla, r):
    u = r["unidades"]
    unidad = u.iloc[0]["unidad"]
    taller = pd.DataFrame({"Unidad": [unidad], "Experto: alternativas": [5], "Experto: criticidad": [5],
                           "Experto: complejidad": [5], "Experto: reemplazo": [5]})
    u2 = kr.matriz_kraljic(tabla, PARAMS, K, taller)["unidades"].set_index("unidad")
    fila = u2.loc[unidad]
    assert fila["estado"] == "validado por expertos" and fila["puntaje_experto"] == 5
    assert fila["puntaje_riesgo"] == pytest.approx(0.4 * fila["puntaje_datos"] + 0.6 * 5)


# 4. El gasto de la matriz = gasto gestionable del Hilo 3 (sin cuentas contables).
def test_gasto_cuadra_con_hilo_3(tabla, r):
    d3 = an.analizar(tabla, PARAMS)["gasto_categoria"]
    excl = set(cl.cargar_reglas()["excluir_de_kraljic"])
    esperado = d3.loc[~d3["categoria"].isin(excl), "gasto"].sum()
    for nivel in ["unidades", "categorias", "productos"]:
        assert r[nivel]["gasto"].sum() == pytest.approx(esperado, abs=0.01)
    assert r["resumen"]["gasto"].sum() == pytest.approx(esperado, abs=0.01)


# 5. Reproducible.
def test_reproducible(tabla, r):
    otro = kr.matriz_kraljic(tabla.copy(), PARAMS, K)
    for k in ["unidades", "categorias", "productos", "resumen"]:
        pd.testing.assert_frame_equal(r[k], otro[k])


def test_puntaje_de_datos():
    t = pd.DataFrame({
        "unidad": ["U"] * 2, "proveedor_id": ["A", "B"], "monto_gasto": [90.0, 10.0], "sede": ["S1", "S2"]})
    g = kr.indicadores(t, ["unidad"], K).iloc[0]
    # HHI = 8 200 > 1 800 (sí), 2 proveedores ≤ 3 (sí), principal 90 % ≥ 50 % (sí) → 5
    assert g["hhi"] == pytest.approx(8200) and g["puntaje_datos"] == 5
