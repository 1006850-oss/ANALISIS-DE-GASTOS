"""Pruebas del Hilo 2 (taxonomía y maestro de categorías)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(RAIZ / "tests"))

import clasificar as cl  # noqa: E402
import limpiar_validar as lv  # noqa: E402
from generar_sintetico import generar  # noqa: E402
from test_limpiar_validar import fila  # noqa: E402

PARAMS = lv.cargar_parametros()
REGLAS = cl.cargar_reglas()
MUESTRA = Path(os.environ.get("ANALISIS_MUESTRA", RAIZ / "data" / "muestra.xlsx"))
EXTRACTO = Path(os.environ.get("ANALISIS_EXTRACTO", RAIZ / "data" / "extracto.xlsx"))


@pytest.fixture(scope="module")
def tabla_sintetica() -> pd.DataFrame:
    df, _ = generar(filas=4000, semilla=11)
    return lv.procesar(df, PARAMS).tabla


def limpia(filas: list[dict]) -> pd.DataFrame:
    return lv.procesar(pd.DataFrame(filas), PARAMS).tabla


# 1. Todas las filas quedan con 3 niveles o marcadas "Sin clasificar" y listadas.
def test_todas_las_filas_tienen_tres_niveles(tabla_sintetica):
    t, _ = cl.clasificar(tabla_sintetica, REGLAS)
    assert t[["categoria", "subcategoria", "producto"]].notna().all().all()
    assert (t["categoria"] != cl.SIN_CLASIFICAR).all()


def test_articulo_desconocido_queda_sin_clasificar_y_listado():
    t = limpia([fila(**{"Articulo": "ZZZ ARTICULO INEXISTENTE"}), fila()])
    tc, _ = cl.clasificar(t, REGLAS)
    assert tc.loc[0, "categoria"] == cl.SIN_CLASIFICAR
    arts, _ = cl.nuevas_para_validar(tc, None, None)
    assert "ZZZ ARTICULO INEXISTENTE" in set(arts["articulo_normalizado"])


# 2. El gasto por categoría suma el total (nada se pierde ni se duplica).
def test_cuadre_del_gasto_por_categoria(tabla_sintetica):
    t, _ = cl.clasificar(tabla_sintetica, REGLAS)
    assert len(t) == len(tabla_sintetica)
    r = cl.resumen(t)
    assert r["Por_categoria"]["gasto"].sum() == pytest.approx(tabla_sintetica["monto_gasto"].sum(), abs=0.01)


# 3. Una descripción nueva aparece en la lista de "nuevas para validar".
def test_descripcion_nueva_aparece_para_validar(tabla_sintetica, tmp_path):
    t, arts = cl.clasificar(tabla_sintetica, REGLAS)
    maestro = tmp_path / "maestro.xlsx"
    cl.escribir_excel(maestro, cl.construir_maestro(t, arts, REGLAS))
    m_art, m_comb = cl.leer_maestro(maestro)
    nueva = tabla_sintetica.iloc[[0]].copy()
    nueva["descripcion"] = "INSTALACION DE PANELES SOLARES EN TECHO"
    t2, _ = cl.clasificar(pd.concat([tabla_sintetica, nueva], ignore_index=True), REGLAS, m_art, m_comb)
    art_n, comb_n = cl.nuevas_para_validar(t2, m_art, m_comb)
    assert len(art_n) == 0
    assert list(comb_n["descripcion_ejemplo"]) == ["INSTALACION DE PANELES SOLARES EN TECHO"]


# 4. Dos ejecuciones dan el mismo resultado.
def test_reproducible(tabla_sintetica):
    a, _ = cl.clasificar(tabla_sintetica, REGLAS)
    b, _ = cl.clasificar(tabla_sintetica.copy(), REGLAS)
    pd.testing.assert_frame_equal(a, b)


# 5. La muestra de 28 filas corre sin errores (no se evalúa la calidad: está mezclada).
@pytest.mark.skipif(not MUESTRA.exists(), reason="muestra no disponible")
def test_muestra_corre():
    t = lv.procesar(lv.leer_entrada(MUESTRA), PARAMS).tabla
    tc, _ = cl.clasificar(t, REGLAS)
    assert len(tc) == 28 and round(tc["monto_gasto"].sum(), 2) == 2_454_438.56


@pytest.mark.skipif(not EXTRACTO.exists(), reason="extracto real no disponible")
def test_extracto_real_cuadra_y_sin_pendientes():
    t = lv.procesar(lv.leer_entrada(EXTRACTO), PARAMS).tabla
    tc, arts = cl.clasificar(t, REGLAS)
    assert (tc["categoria"] == cl.SIN_CLASIFICAR).sum() == 0
    assert round(tc["monto_gasto"].sum(), 2) == 283_013_851.95
    assert set(tc["categoria"]) <= set(REGLAS["categorias"])
    assert len(arts) == 410


# ------------------------------------------------------------------- reglas puntuales

def test_construccion_se_divide_por_clase_y_producto():
    t = limpia([
        fila(**{"Clase": "Obras Nuevas 2018", "Descripcion": "Adicional de obra pabellón"}),
        fila(**{"Clase": "Ampliaciones", "Descripcion": "Supervisión de obra"}),
        fila(**{"Clase": None, "Descripcion": "Construcción obra civil"}),
    ])
    tc, _ = cl.clasificar(t, REGLAS)
    assert tc["subcategoria"].tolist() == ["Obra nueva", "Ampliación", "Obra sin tipo de intervención"]
    assert tc["producto"].tolist() == ["Adicionales de obra", "Supervisión de obra", "Obra civil"]


def test_cuentas_contables_fuera_de_kraljic_y_viajes_antes_que_marketing():
    t = limpia([fila(**{"Articulo": "ALQUILERES POR DEVENGAR MN"}), fila(**{"Articulo": "VENTAS : PASAJES"})])
    tc, _ = cl.clasificar(t, REGLAS)
    assert tc.loc[0, "categoria"] == "Cuentas contables (no gestionables por Compras)" and tc.loc[0, "excluir_de_kraljic"]
    assert tc.loc[1, "categoria"] == "Viajes y movilidad" and not tc.loc[1, "excluir_de_kraljic"]


def test_maestro_validado_manda_sobre_las_reglas_y_aplicar_validacion(tabla_sintetica, tmp_path):
    t, arts = cl.clasificar(tabla_sintetica, REGLAS)
    maestro = tmp_path / "maestro.xlsx"
    cl.escribir_excel(maestro, cl.construir_maestro(t, arts, REGLAS))
    validacion = tmp_path / "validacion.xlsx"
    hojas = cl.generar_validacion(t, arts, REGLAS)
    art = "INTERNET"
    fila_art = hojas["Articulos_95pct"]["Artículo"] == art
    if not fila_art.any():
        fila_art = hojas["Articulos_resto"]["Artículo"] == art
        hoja = "Articulos_resto"
    else:
        hoja = "Articulos_95pct"
    hojas[hoja].loc[fila_art, ["¿Correcto? (SI/NO)", "Categoría corregida"]] = ["NO", "Servicios generales de sede"]
    cl.escribir_excel(validacion, hojas)
    cambios = cl.aplicar_validacion(validacion, maestro)
    assert cambios["articulos_corregidos"] == 1
    m_art, m_comb = cl.leer_maestro(maestro)
    t2, _ = cl.clasificar(tabla_sintetica, REGLAS, m_art, m_comb)
    fila_internet = t2[t2["articulo_normalizado"] == art].iloc[0]
    assert fila_internet["categoria"] == "Servicios generales de sede"
    assert fila_internet["origen_categoria"] == "humano"


def test_muestra_de_validacion_tiene_200_y_es_reproducible(tabla_sintetica):
    t, arts = cl.clasificar(tabla_sintetica, REGLAS)
    a = cl.generar_validacion(t, arts, REGLAS)["Muestra_productos"]
    b = cl.generar_validacion(t, arts, REGLAS)["Muestra_productos"]
    n_comb = t.loc[t["monto_gasto"] > 0, "llave_combinacion"].nunique()
    assert len(a) == min(200, n_comb) and a["Llave"].is_unique
    pd.testing.assert_frame_equal(a.reset_index(drop=True), b.reset_index(drop=True))
