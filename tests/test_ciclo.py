"""Pruebas del Hilo 8 (orquestador, puntos de parada, histórico y códigos persistentes).

Usan data sintética (nunca la real). Cubren los evals 1 a 3 de la skill con el mismo orquestador que ella ejecuta.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(RAIZ / "tests"))

import clasificar as cl  # noqa: E402
import ejecutar_ciclo as ec  # noqa: E402
import historico as hi  # noqa: E402
import limpiar_validar as lv  # noqa: E402
from generar_sintetico import generar  # noqa: E402

PARAMS = lv.cargar_parametros()
RUC = re.compile(r"(?<!\d)(10|15|17|20)\d{9}(?!\d)")


@pytest.fixture(scope="module")
def base(tmp_path_factory):
    """Raíz tipo Drive con un extracto sintético y su maestro."""
    d = tmp_path_factory.mktemp("drive")
    df, _ = generar(filas=6000, semilla=81)
    entrada = d / "entrada" / "extracto.csv"
    entrada.parent.mkdir()
    df.to_csv(entrada, index=False)
    t = lv.procesar(df, PARAMS).tabla
    reglas = cl.cargar_reglas()
    tc, arts = cl.clasificar(t, reglas)
    (d / "maestro").mkdir()
    cl.escribir_excel(d / "maestro" / "maestro_categorias.xlsx", cl.construir_maestro(tc, arts, reglas))
    return {"raiz": d, "entrada": entrada, "df": df}


def correr(base, periodo, *extra, entrada=None):
    return ec.main(["--entrada", str(entrada or base["entrada"]), "--periodo", periodo, "--raiz", str(base["raiz"]),
                    *extra])


# Eval 1 – ciclo normal: se detiene en Kraljic, reanuda y produce todas las salidas con cuadres.
def test_ciclo_normal_con_parada_y_reanudacion(base, capsys):
    assert correr(base, "2017-S2") == ec.PAUSA
    estado = pd.read_json(base["raiz"] / "salida" / "2017-S2" / "estado.json", typ="series")
    assert estado["pasos"]["5_kraljic"]["estado"] == "PAUSA"
    assert estado["pasos"]["4_alertas"]["estado"] == "ok"
    capsys.readouterr()
    assert correr(base, "2017-S2", "--kraljic-provisional") == ec.OK
    salida = capsys.readouterr().out
    assert "1_limpieza Limpiar y validar (ya hecho)" in salida      # reanuda sin repetir
    d = base["raiz"] / "salida" / "2017-S2"
    for f in ["7_salidas/resultados_2017-S2.xlsx", "7_salidas/informe_ejecutivo_2017-S2.xlsx",
              "7_salidas/tablero/hechos_gasto.parquet", "6_plan/plan_compras.xlsx", "log_ejecucion.md"]:
        assert (d / f).exists(), f
    log = (d / "log_ejecucion.md").read_text(encoding="utf-8")
    assert "sumas de tablas: OK" in log and "todas las cifras coinciden" in log
    assert "--kraljic-provisional" in log                          # la decisión humana queda registrada
    assert not RUC.search(log) and "PERSONA" not in log and not RUC.search(salida)
    tc = pd.read_parquet(d / "2_clasificacion" / "tabla_clasificada.parquet")
    ctrl = pd.read_parquet(d / "3_descriptivo" / "tablas" / "control.parquet")
    assert ctrl["valor_soles"].iloc[0] == pytest.approx(tc["monto_gasto"].sum())
    assert ctrl["valor_soles"].iloc[0] == pytest.approx(ctrl["valor_soles"].iloc[1] + ctrl["valor_soles"].iloc[2])
    assert (base["raiz"] / "historico" / "2017-S2__v1" / "kpis.parquet").exists()


# Eval 2 – columna renombrada o faltante: se detiene (BLOQUEA) y explica qué falta.
def test_columna_faltante_bloquea(base, tmp_path, capsys):
    malo = base["df"].rename(columns={"Descripcion": "Detalle"})
    ruta = tmp_path / "extracto_malo.csv"
    malo.to_csv(ruta, index=False)
    assert correr(base, "2016-S2", "--sin-historico", entrada=ruta) == ec.BLOQUEO
    out = capsys.readouterr().out
    assert "BLOQUEA" in out and "Descripcion" in out
    log = (base["raiz"] / "salida" / "2016-S2" / "log_ejecucion.md").read_text(encoding="utf-8")
    assert "BLOQUEADO" in log and "Punto de parada" in log


# Eval 3 – descripciones nuevas: pide validar solo esas; con la validación completa, continúa.
def test_descripciones_nuevas_se_validan_y_continua(base, tmp_path):
    df = base["df"].copy()
    idx = df.sample(5, random_state=1).index
    df.loc[idx, "Descripcion"] = [f"SERVICIO NUEVO DE PRUEBA {i}" for i in range(5)]
    df.loc[idx[:2], "Articulo"] = "ARTICULO NUEVO DE PRUEBA"
    ruta = tmp_path / "extracto_nuevas.csv"
    df.to_csv(ruta, index=False)
    maestro = base["raiz"] / "maestro" / "maestro_categorias.xlsx"
    filas_antes = {k: len(v) for k, v in zip(["art", "comb"], cl.leer_maestro(maestro))}

    assert correr(base, "2016-S1", "--sin-historico", "--kraljic-provisional", entrada=ruta) == ec.PAUSA
    val = base["raiz"] / "salida" / "2016-S1" / "2_clasificacion" / "validar_nuevas.xlsx"
    art = pd.read_excel(val, "Articulos_nuevos", dtype=str)
    comb = pd.read_excel(val, "Combinaciones_nuevas", dtype=str)
    assert list(art["Artículo"]) == ["ARTICULO NUEVO DE PRUEBA"]              # solo lo nuevo
    assert comb["Descripción"].str.contains("NUEVO DE PRUEBA").all() and len(comb) <= 5

    # Validación incompleta → vuelve a detenerse.
    assert correr(base, "2016-S1", "--sin-historico", "--kraljic-provisional", "--validacion", str(val),
                  entrada=ruta) == ec.PAUSA
    # Validación completa (artículo corregido, un producto corregido) → continúa hasta el final.
    art["¿Correcto? (SI/NO)"], art["Categoría corregida"] = "NO", "Servicios profesionales"
    art["Subcategoría corregida"] = "Consultoría y asesoría"
    comb["¿Correcto? (SI/NO)"] = "SI"
    comb.loc[0, "¿Correcto? (SI/NO)"], comb.loc[0, "Producto corregido"] = "NO", "Producto validado"
    lleno = tmp_path / "validar_nuevas_lleno.xlsx"
    cl.escribir_excel(lleno, {"Articulos_nuevos": art, "Combinaciones_nuevas": comb})
    assert correr(base, "2016-S1", "--sin-historico", "--kraljic-provisional", "--validacion", str(lleno),
                  entrada=ruta) == ec.OK
    a2, c2 = cl.leer_maestro(maestro)
    assert len(a2) == filas_antes["art"] + 1 and len(c2) == filas_antes["comb"] + len(comb)
    fila = a2[a2["articulo_normalizado"] == "ARTICULO NUEVO DE PRUEBA"].iloc[0]
    assert (fila["categoria"], fila["origen"]) == ("Servicios profesionales", "humano")
    tc = pd.read_parquet(base["raiz"] / "salida" / "2016-S1" / "2_clasificacion" / "tabla_clasificada.parquet")
    assert (tc.loc[tc["articulo_normalizado"] == "ARTICULO NUEVO DE PRUEBA", "categoria"] == "Servicios profesionales").all()
    assert (tc["producto"] == "Producto validado").any()
    assert any((base["raiz"] / "maestro" / "respaldos").iterdir())         # respaldo antes de modificar


# Histórico: nunca sobrescribe y compara alertas nuevas vs. recurrentes.
def test_historico_no_sobrescribe_y_compara(base, tmp_path):
    d = base["raiz"] / "salida" / "2017-S2"
    h = tmp_path / "historico"
    v1 = hi.agregar(d, h, "2017-S1")
    v2 = hi.agregar(d, h, "2017-S2")
    v3 = hi.agregar(d, h, "2017-S2")
    assert [v1.name, v2.name, v3.name] == ["2017-S1__v1", "2017-S2__v1", "2017-S2__v2"]
    assert len(pd.read_csv(h / "indice.csv")) == 3
    # Quitar una alerta del ciclo "anterior" → debe aparecer como Nueva en el actual.
    al = pd.read_parquet(v1 / "alertas.parquet")
    al.iloc[1:].to_parquet(v1 / "alertas.parquet", index=False)
    r = hi.comparar(h, "2017-S2")
    det = r["Alertas_detalle"]
    assert (det["estado"] == "Nueva").sum() == 1 and (det["estado"] == "Recurrente").sum() == len(al) - 1
    texto = hi.texto_resumen(r, "2017-S2")
    assert not RUC.search(texto) and "PERSONA" not in texto


# Códigos de persona persistentes entre ciclos.
def test_codigos_persistentes():
    previos = pd.DataFrame({"codigo": ["P001", "P002"], "nombre": ["ZOILA", "ANA"]})
    s, tabla = lv.codificar(pd.Series(["ANA", "BETO", "ZOILA"]), "P", previos)
    assert list(s) == ["P002", "P003", "P001"]
    assert set(tabla["codigo"]) == {"P001", "P002", "P003"}
    s0, _ = lv.codificar(pd.Series(["B", "A"]), "P")
    assert list(s0) == ["P002", "P001"]                                    # sin previos: orden alfabético (igual que antes)


def test_ventana_del_ciclo():
    C = PARAMS["ciclo"]
    assert ec.ventana("2017-S2", C) == ("2015-S1", "2017-S2")
    assert ec.ventana("2017-S1", C) == ("2015-S1", "2017-S1")
    assert ec.ventana("2026-S2", C) == ("2024-S1", "2026-S2")
    assert ec.semestre_menos("2026-S1", 1) == "2025-S2"


# Equipo nuevo: preparar_equipo guarda la ruta, crea subcarpetas y avisa si falta el maestro.
def test_preparar_equipo(tmp_path, monkeypatch, capsys):
    import preparar_equipo as pe
    monkeypatch.setattr(pe, "LOCAL", tmp_path / "local.yaml")
    monkeypatch.setattr(pe, "ciclos_registrados", lambda: [])
    raiz = tmp_path / "drive"
    raiz.mkdir()
    assert pe.main(["--raiz", str(raiz)]) == 1                     # falta el maestro
    assert "FALTA" in capsys.readouterr().out
    assert all((raiz / d).is_dir() for d in ["entrada", "maestro", "historico", "salida"])
    (raiz / "maestro" / "maestro_categorias.xlsx").write_bytes(b"x")
    assert pe.main([]) == 0                                         # usa la ruta guardada
    monkeypatch.setattr(ec, "LOCAL", tmp_path / "local.yaml")
    assert ec.raiz_local() == str(raiz)


# Archivado: registrar_ciclo agrega una fila por ciclo, sin duplicar ni mostrar RUC o nombres.
def test_registrar_ciclo(base, tmp_path, monkeypatch):
    import registrar_ciclo as rc
    monkeypatch.setattr(rc, "REGISTRO", tmp_path / "ciclos.md")
    d = base["raiz"] / "salida" / "2017-S2"
    rc.registrar(d)
    rc.registrar(d)
    texto = (tmp_path / "ciclos.md").read_text(encoding="utf-8")
    filas = [l for l in texto.splitlines() if l.startswith("| 2017-S2 |")]
    assert len(filas) == 1 and "2015-S1 a 2017-S2" in filas[0] and "S/ " in filas[0]
    assert not RUC.search(texto) and "PERSONA" not in texto


def test_preparar_equipo_exige_codigos_e_historico_si_hubo_ciclos(tmp_path, monkeypatch, capsys):
    import preparar_equipo as pe
    monkeypatch.setattr(pe, "LOCAL", tmp_path / "local.yaml")
    monkeypatch.setattr(pe, "ciclos_registrados", lambda: ["2017-S2"])
    raiz = tmp_path / "drive"
    (raiz / "maestro").mkdir(parents=True)
    (raiz / "maestro" / "maestro_categorias.xlsx").write_bytes(b"x")
    assert pe.main(["--raiz", str(raiz)]) == 1
    out = capsys.readouterr().out
    assert "codigos_personas.xlsx" in out and "historico/ está vacío" in out
