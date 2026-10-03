"""Prepara y revisa un equipo (laptop) para correr el ciclo de análisis de gastos.

  python scripts/preparar_equipo.py --raiz "<carpeta 'analisis de gastos' sincronizada con Google Drive>"
  python scripts/preparar_equipo.py            # solo revisa (usa la ruta ya guardada)

Qué hace:
  1. Revisa la versión de Python y que estén instaladas las librerías de requirements.txt.
  2. Guarda la ruta de la carpeta de datos de ESTE equipo en config/local.yaml (no se versiona: cada equipo
     tiene su propia ruta, por ejemplo "G:/Mi unidad/analisis de gastos" en Windows).
  3. Revisa la carpeta de datos: crea las subcarpetas que falten (entrada, maestro, historico, salida) y avisa si
     falta el maestro de categorías, que es indispensable.
Termina con código 0 si todo está listo y 1 si falta algo (lo explica en la lista).
"""
from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

import yaml

RAIZ_REPO = Path(__file__).resolve().parents[1]
LOCAL = RAIZ_REPO / "config" / "local.yaml"
LIBRERIAS = {"pandas": "pandas", "numpy": "numpy", "openpyxl": "openpyxl", "pyarrow": "pyarrow", "yaml": "pyyaml",
             "matplotlib": "matplotlib"}
OPCIONALES = {"python_calamine": "python-calamine (solo acelera la lectura del xlsx)"}


def revisar(raiz: Path | None, params: dict) -> list[tuple[str, bool, str]]:
    R, C = params["rutas"], params["ciclo"]
    items = [("Python 3.10 o superior", sys.version_info >= (3, 10), f"versión {sys.version.split()[0]}")]
    for mod, pip in LIBRERIAS.items():
        try:
            m = importlib.import_module(mod)
            items.append((f"Librería {pip}", True, getattr(m, "__version__", "")))
        except ImportError:
            items.append((f"Librería {pip}", False, "instalar con: pip install -r requirements.txt"))
    for mod, texto in OPCIONALES.items():
        try:
            importlib.import_module(mod)
            items.append((f"Opcional: {texto}", True, ""))
        except ImportError:
            items.append((f"Opcional: {texto}", True, "no instalada (no es obligatoria)"))
    if raiz is None:
        items.append(("Carpeta de datos configurada", False,
                      "falta: python scripts/preparar_equipo.py --raiz \"<carpeta de Drive>\""))
        return items
    items.append(("Carpeta de datos existe", raiz.exists(), str(raiz)))
    if not raiz.exists():
        return items
    for clave in ["entrada", "maestro", "historico", "salida"]:
        d = raiz / R[clave]
        creada = not d.exists()
        d.mkdir(exist_ok=True)
        items.append((f"Subcarpeta {R[clave]}/", True, "creada ahora" if creada else "existe"))
    maestro = raiz / R["maestro"] / C["maestro_archivo"]
    items.append(("Maestro de categorías", maestro.exists(),
                  str(maestro) if maestro.exists() else f"FALTA {maestro}: cópielo desde el respaldo (es indispensable)"))
    codigos = raiz / R["maestro"] / C["codigos_archivo"]
    items.append(("Tabla de códigos de personas", True,
                  "existe" if codigos.exists() else "aún no existe (se crea en el primer ciclo)"))
    taller = raiz / R["maestro"] / C["kraljic_taller_archivo"]
    items.append(("Taller de Kraljic completado", True,
                  "existe" if taller.exists() else "no existe: el ciclo usará Kraljic provisional si la persona lo decide"))
    hist = raiz / R["historico"]
    ciclos = sorted(p.name for p in hist.glob("*__v*"))
    items.append(("Histórico de ciclos", True, ", ".join(ciclos) if ciclos else "vacío (el primer ciclo no tendrá comparación)"))
    extractos = sorted(p.name for p in (raiz / R["entrada"]).glob("*.xls*"))
    items.append(("Extractos en entrada/", True, ", ".join(extractos) if extractos else "ninguno todavía"))
    return items


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Prepara y revisa este equipo para el ciclo de análisis de gastos.")
    ap.add_argument("--raiz", help="Carpeta 'analisis de gastos' sincronizada con Google Drive (se guarda en config/local.yaml)")
    a = ap.parse_args(argv)
    params = yaml.safe_load((RAIZ_REPO / "config" / "parametros.yaml").read_text(encoding="utf-8"))
    local = yaml.safe_load(LOCAL.read_text(encoding="utf-8")) if LOCAL.exists() else {}
    local = local or {}
    if a.raiz:
        local["raiz_datos"] = str(Path(a.raiz).expanduser())
        LOCAL.write_text("# Configuración de ESTE equipo (no se versiona). La crea scripts/preparar_equipo.py.\n"
                         + yaml.safe_dump(local, allow_unicode=True), encoding="utf-8")
    raiz = Path(local["raiz_datos"]) if local.get("raiz_datos") else None
    items = revisar(raiz, params)
    print("Revisión del equipo para el análisis de gastos\n")
    for nombre, ok, detalle in items:
        print(f"  {'✔' if ok else '✖'} {nombre}: {detalle}")
    faltan = [n for n, ok, _ in items if not ok]
    print("\nListo para correr el ciclo." if not faltan else f"\nFalta resolver: {', '.join(faltan)}.")
    return 0 if not faltan else 1


if __name__ == "__main__":
    sys.exit(main())
