"""Pruebas del Hilo 6 (plan de compras)."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(RAIZ / "tests"))

import clasificar as cl  # noqa: E402
import kraljic as kr  # noqa: E402
import limpiar_validar as lv  # noqa: E402
import proyectar as pr  # noqa: E402
from generar_sintetico import generar  # noqa: E402

PARAMS = lv.cargar_parametros()
K = kr.cargar_yaml(kr.KRALJIC_DEFECTO)
P = kr.cargar_yaml(pr.PLAN_DEFECTO)


@pytest.fixture(scope="module")
def tabla() -> pd.DataFrame:
    df, _ = generar(filas=8000, semilla=41)
    t, _ = cl.clasificar(lv.procesar(df, PARAMS).tabla, cl.cargar_reglas())
    return t


@pytest.fixture(scope="module")
def r(tabla):
    return pr.plan_compras(tabla, kr.matriz_kraljic(tabla, PARAMS, K)["unidades"], PARAMS, K, P)


# 1. La suma mensual = total anual por unidad.
def test_suma_mensual_igual_a_anual(r):
    anual = r["plan"].set_index("unidad")["linea_base"]
    mensual = r["mensual"].groupby("unidad")["linea_base"].sum()
    for u, v in mensual.items():
        assert v == pytest.approx(anual[u], rel=1e-9)
    assert (r["mensual"].groupby("unidad").size() == 12).all()


# 2. Las unidades "por proyecto" no reciben proyección automática.
def test_por_proyecto_sin_proyeccion(r):
    p = r["plan"]
    proy = p[p["segmento"] == "Por proyecto"]
    assert len(proy) > 0
    assert proy["linea_base"].isna().all()
    assert not r["mensual"]["unidad"].isin(proy["unidad"]).any()
    assert proy["categoria"].eq("Infraestructura y obras").all() or proy["unidad"].isin(P["segmentacion"]["unidades_proyecto"]).any()


# 3. La validación hacia atrás reproduce el error reportado.
def test_validacion_atras_reproduce_error(tabla, r):
    t = kr.preparar(tabla, PARAMS, K)
    m = pr.base_mensual(t, P)
    seg = pr.segmentar(m, t.groupby("unidad")["categoria"].first(), P)
    sedes = pr.sedes_activas(t, P)
    a = pr.anual(m)
    u = seg.index[seg["segmento"] == "Recurrente"]
    if len(u) == 0:
        pytest.skip("sin unidades recurrentes en la base sintética")
    est = a.loc[u, 2016].sum() / sedes[2016] * sedes[2017]
    real = a.loc[u, 2017].sum()
    fila = r["validacion"].query("segmento == 'Recurrente' and metodo.str.startswith('Gasto por sede')", engine="python").iloc[0]
    assert fila["error_anual_pct"] == pytest.approx((est - real) / real * 100)


# 4. La inflación y las sedes del plan escalan la línea base en la proporción esperada.
def test_inflacion_y_sedes_escalan(tabla, r):
    ku = kr.matriz_kraljic(tabla, PARAMS, K)["unidades"]
    P2 = copy.deepcopy(P)
    P2["inflacion_anual"] = 0.05
    P2["sedes"]["plan"] = P["sedes"]["plan"] * 2
    r2 = pr.plan_compras(tabla, ku, PARAMS, K, P2)
    a = r["plan"].set_index("unidad")["linea_base"].dropna()
    b = r2["plan"].set_index("unidad")["linea_base"].dropna()
    assert np.allclose(b[a.index], a * 1.05 * 2)


# 5. Reproducible.
def test_reproducible(tabla, r):
    ku = kr.matriz_kraljic(tabla, PARAMS, K)["unidades"]
    r2 = pr.plan_compras(tabla.copy(), ku, PARAMS, K, P)
    for k in ["plan", "mensual", "validacion", "calendario"]:
        pd.testing.assert_frame_equal(r[k], r2[k])


def test_modalidades_segun_politica():
    mods = P["modalidades"]
    assert pr.modalidad(1000, mods)[0] == "1 cotización"
    assert pr.modalidad(1000.01, mods)[0] == "2 cotizaciones"
    assert pr.modalidad(80000, mods)[0] == "3 cotizaciones"
    assert pr.modalidad(80000.01, mods) == ("Licitación", 8)


def test_calendario_recurrentes_inician_antes_de_enero(r):
    c = r["calendario"]
    rec = c[c["segmento"] == "Recurrente"]
    assert (rec["inicio_proceso"] < pd.Timestamp(P["anio_plan"], 1, 1)).all()
