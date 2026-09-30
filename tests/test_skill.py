"""Pruebas del empaquetado de la skill (Hilo 8): la skill sale del repositorio y no queda desactualizada."""
from __future__ import annotations

import filecmp
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import empaquetar_skill as es  # noqa: E402


def test_empaqueta_valida_y_sin_data(tmp_path):
    z = es.empaquetar(tmp_path)
    d = tmp_path / es.NOMBRE
    nombres = zipfile.ZipFile(z).namelist()
    assert all(n.startswith(es.NOMBRE + "/") for n in nombres)           # carpeta de la skill como raíz del ZIP
    assert f"{es.NOMBRE}/SKILL.md" in nombres
    # Los scripts y la configuración son copias exactas del repositorio (no hay lógica duplicada).
    for s in es.SCRIPTS:
        assert filecmp.cmp(RAIZ / "scripts" / s, d / "scripts" / s, shallow=False), s
    for c in es.CONFIG:
        assert filecmp.cmp(RAIZ / "config" / c, d / "config" / c, shallow=False), c
    assert not [n for n in nombres if n.endswith((".parquet", ".csv"))]
    assert es.validar_paquete(d) == []


def test_validador_detecta_errores(tmp_path):
    malo = "---\nname: Claude-Gastos\ndescription: " + "x" * 250 + "\n---\n# t\n"
    errores = es.validar_frontmatter(malo)
    assert any("name" in e for e in errores) and any("description" in e for e in errores)
    assert es.validar_frontmatter("---\nname: a\ndescription: con: dos puntos\n---\n") != []   # YAML inválido


def test_todo_script_del_repo_esta_en_la_skill():
    usados = {p.name for p in (RAIZ / "scripts").glob("*.py")} - {"empaquetar_skill.py"}
    assert usados <= set(es.SCRIPTS), usados - set(es.SCRIPTS)
