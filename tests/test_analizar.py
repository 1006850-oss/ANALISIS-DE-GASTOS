"""Pruebas del Hilo 3 (análisis descriptivo)."""
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

import analizar as an  # noqa: E402
import clasificar as cl  # noqa: E402
import limpiar_validar as lv  # noqa: E402
from generar_sintetico import generar  # noqa: E402

PARAMS = lv.cargar_parametros()
REGLAS = cl.cargar_reglas()
MUESTRA = Path(os.environ.get("ANALISIS_MUESTRA", RAIZ / "data" / "muestra.xlsx"))

TABLAS_CON_GASTO = ["pareto_proveedores", "frecuencia_proveedores", "gasto_categoria", "gasto_subcategoria",
                    "gasto_producto", "tendencia_categoria_anio", "tendencia_categoria_semestre",
                    "comprador_proveedor", "especializacion_comprador", "gasto_sede", "gasto_departamento",
                    "concentracion_categoria", "concentracion_subcategoria"]


@pytest.fixture(scope="module")
def tabla() -> pd.DataFrame:
    df, _ = generar(filas=6000, semilla=21)
    t, _ = cl.clasificar(lv.procesar(df, PARAMS).tabla, REGLAS)
    return t


@pytest.fixture(scope="module")
def resultado(tabla) -> dict:
    return an.analizar(tabla, PARAMS)


# 1. Cuadre: cada tabla suma el gasto total del periodo analizado.
def test_cada_tabla_cuadra_con_el_total(tabla, resultado):
    dentro, _ = an.filtrar_periodo(tabla, PARAMS["analisis"]["periodo_desde"], PARAMS["analisis"]["periodo_hasta"])
    total = dentro["monto_gasto"].sum()
    for k in TABLAS_CON_GASTO:
        assert resultado[k]["gasto"].sum() == pytest.approx(total, abs=0.01), k
    assert not resultado["control"]["resultado"].str.startswith("NO CUADRA").any()
    matriz = resultado["comprador_categoria"].set_index("comprador_codigo")
    assert matriz.to_numpy().sum() == pytest.approx(total, abs=0.01)


def test_fuera_de_ventana_no_se_muestra_pero_se_reporta(tabla, resultado):
    assert set(resultado["tendencia_categoria_semestre"]["semestre"]) <= {
        f"{a}-S{s}" for a in (2015, 2016, 2017) for s in (1, 2)}
    _, fuera = an.filtrar_periodo(tabla, "2015-S1", "2017-S2")
    ctrl = resultado["control"].set_index("control")
    assert ctrl.loc["Gasto fuera de la ventana (no se muestra)", "valor_soles"] == pytest.approx(fuera["monto_gasto"].sum())


# 2. ABC respeta los cortes y cambia si cambian los parámetros.
def test_abc_respeta_y_sigue_los_parametros(tabla, resultado):
    p = resultado["pareto_proveedores"]
    a = p[p["clase_abc"] == "A"]
    assert (a["pct_acumulado"] - a["pct_gasto"]).max() < 80
    assert p.loc[p["clase_abc"] != "A", "pct_acumulado"].min() > 80
    otros = copy.deepcopy(PARAMS)
    otros["pareto_abc"]["corte_a"] = 0.50
    p2 = an.analizar(tabla, otros)["pareto_proveedores"]
    assert (p2["clase_abc"] == "A").sum() < (p["clase_abc"] == "A").sum()


# 3. Muestra de 28 filas.
@pytest.mark.skipif(not MUESTRA.exists(), reason="muestra no disponible")
def test_muestra_cifras():
    t, _ = cl.clasificar(lv.procesar(lv.leer_entrada(MUESTRA), PARAMS).tabla, REGLAS)
    r = an.analizar(t, PARAMS)
    assert len(r["pareto_proveedores"]) == 14
    assert r["frecuencia_proveedores"]["n_lineas"].sum() == 28
    assert round(r["pareto_proveedores"]["gasto"].sum(), 2) == 2_454_438.56


# 4. Filtrar por un semestre = calcular solo con las filas de ese semestre.
def test_filtro_de_semestre_equivale_a_filtrar_filas(tabla):
    a = an.analizar(tabla, PARAMS, "2016-S1", "2016-S1")
    b = an.analizar(tabla[tabla["semestre"] == "2016-S1"], PARAMS, "2016-S1", "2016-S1")
    for k in ["pareto_proveedores", "gasto_categoria", "especializacion_comprador", "gasto_sede"]:
        pd.testing.assert_frame_equal(a[k], b[k])


# 5. Reproducible.
def test_reproducible(tabla, resultado):
    otro = an.analizar(tabla.copy(), PARAMS)
    for k in TABLAS_CON_GASTO:
        pd.testing.assert_frame_equal(resultado[k], otro[k])
    assert resultado["hallazgos"] == otro["hallazgos"]


def test_indicadores_puntuales():
    base = dict(proveedor="X", ruc="1", excluir_de_kraljic=False, semestre="2016-S1", anio_gasto=2016,
                subcategoria="S", producto="P", sede="A", departamento="D", factura_normalizada="F",
                periodo_factura=pd.Timestamp("2016-01-01"), fecha_oc=pd.Timestamp("2016-01-01"))
    filas = [
        dict(base, id_linea=1, oc=1, proveedor_id="P1", comprador_codigo="C1", categoria="K1", monto_gasto=60.0),
        dict(base, id_linea=2, oc=2, proveedor_id="P1", comprador_codigo="C1", categoria="K1", monto_gasto=30.0),
        dict(base, id_linea=3, oc=3, proveedor_id="P2", comprador_codigo="C2", categoria="K1", monto_gasto=10.0),
    ]
    t = pd.DataFrame(filas)
    r = an.analizar(t, PARAMS, "2016-S1", "2016-S1")
    conc = r["concentracion_categoria"].iloc[0]
    assert conc["hhi"] == pytest.approx(0.9 ** 2 * 10000 + 0.1 ** 2 * 10000)
    f = r["frecuencia_proveedores"].set_index("proveedor_id").loc["P1"]
    assert f["ticket_promedio_oc"] == 45 and f["ticket_mediano_oc"] == 45
    cp = r["concentracion_comprador"].set_index("proveedor_id").loc["P1"]
    assert cp["pct_comprador_principal"] == 100 and cp["concentrado"]
    assert r["pareto_proveedores"]["clase_abc"].tolist() == ["A", "B"]
