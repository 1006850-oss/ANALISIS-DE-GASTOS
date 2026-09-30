"""Hilo 8 – Empaqueta la skill `analisis-gastos-compras` desde el repositorio (única fuente de verdad).

Copia a dist/analisis-gastos-compras/:
  SKILL.md (de skill/analisis-gastos-compras/), VERSION.txt, requirements.txt,
  scripts/*.py (los mismos del repositorio), config/*.yaml (configuración base),
  references/*.md (de docs/), assets/kraljic_taller.xlsx (plantilla sin montos)
y genera dist/analisis-gastos-compras.zip con la carpeta de la skill como raíz (formato de claude.ai).

Antes de escribir el ZIP valida: frontmatter (name ≤ 64, minúsculas/números/guiones, sin "anthropic"/"claude";
description ≤ 200 caracteres – límite de claude.ai – y sin < >), cuerpo < 500 líneas, que existan todos los archivos
que cita el SKILL.md, y que el paquete no traiga data (xlsx fuera de assets, parquet, csv) ni RUC.

Uso:  python scripts/empaquetar_skill.py [--salida dist]
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[1]
NOMBRE = "analisis-gastos-compras"
FUENTE = RAIZ / "skill" / NOMBRE
SCRIPTS = ["ejecutar_ciclo.py", "limpiar_validar.py", "clasificar.py", "analizar.py", "alertas.py", "kraljic.py",
           "proyectar.py", "generar_excel.py", "generar_informe.py", "historico.py"]
CONFIG = ["parametros.yaml", "reglas_taxonomia.yaml", "reglas_alertas.yaml", "kraljic.yaml", "plan_compras.yaml",
          "README.md"]
REFERENCIAS = ["manual_ciclo.md", "reglas_negocio.md", "diccionario_datos.md", "taxonomia.md", "indicadores.md",
               "alertas.md", "estrategias_kraljic.md", "plan_compras.md", "informe.md", "tablero.md"]
ASSETS = {"kraljic_taller.xlsx": RAIZ / "plantillas" / "kraljic_taller.xlsx"}
LIMITE_DESCRIPCION = 200     # claude.ai (centro de ayuda); la plataforma admite 1 024
RUC = re.compile(r"(?<![\d.,])(10|15|17|20)\d{9}(?![\d.,])")


def version() -> str:
    try:
        c = subprocess.run(["git", "-C", str(RAIZ), "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                           check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        c = "sin-git"
    return f"{c} · empaquetada {datetime.now():%Y-%m-%d %H:%M}"


def validar_frontmatter(texto: str) -> list[str]:
    m = re.match(r"^---\n(.*?)\n---\n", texto, re.S)
    if not m:
        return ["SKILL.md sin frontmatter YAML"]
    try:
        fm = yaml.safe_load(m.group(1))
    except yaml.YAMLError as e:
        return [f"Frontmatter inválido: {e}"]
    errores = []
    extra = set(fm) - {"name", "description"}
    if extra:
        errores.append(f"Claves no previstas en el frontmatter: {extra}")
    n, d = str(fm.get("name", "")), str(fm.get("description", ""))
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", n) or len(n) > 64:
        errores.append(f"name inválido: {n!r}")
    if "anthropic" in n or "claude" in n:
        errores.append("name contiene una palabra reservada")
    if not d or len(d) > LIMITE_DESCRIPCION or "<" in d or ">" in d:
        errores.append(f"description vacía, con < > o de {len(d)} caracteres (máximo {LIMITE_DESCRIPCION})")
    cuerpo = texto[m.end():]
    if len(cuerpo.splitlines()) >= 500:
        errores.append(f"El cuerpo del SKILL.md tiene {len(cuerpo.splitlines())} líneas (máximo recomendado 500)")
    return errores


def construir(salida: Path) -> tuple[Path, Path]:
    destino = salida / NOMBRE
    if destino.exists():
        shutil.rmtree(destino)
    for sub in ["scripts", "config", "references", "assets"]:
        (destino / sub).mkdir(parents=True)
    shutil.copy2(FUENTE / "SKILL.md", destino / "SKILL.md")
    for s in SCRIPTS:
        shutil.copy2(RAIZ / "scripts" / s, destino / "scripts" / s)
    for c in CONFIG:
        shutil.copy2(RAIZ / "config" / c, destino / "config" / c)
    for r in REFERENCIAS:
        shutil.copy2(RAIZ / "docs" / r, destino / "references" / r)
    for nombre, origen in ASSETS.items():
        shutil.copy2(origen, destino / "assets" / nombre)
    reqs = [l for l in (RAIZ / "requirements.txt").read_text(encoding="utf-8").splitlines() if not l.startswith("pytest")]
    (destino / "requirements.txt").write_text("\n".join(reqs) + "\n", encoding="utf-8")
    (destino / "VERSION.txt").write_text(version() + "\n", encoding="utf-8")
    return destino, salida / f"{NOMBRE}.zip"


def validar_paquete(destino: Path) -> list[str]:
    texto = (destino / "SKILL.md").read_text(encoding="utf-8")
    errores = validar_frontmatter(texto)
    for ref in sorted(set(re.findall(r"`((?:scripts|references|assets|config)/[\w.\-/]+)`", texto))):
        if "*" not in ref and not (destino / ref).exists():
            errores.append(f"El SKILL.md cita {ref}, que no está en el paquete")
    for f in destino.rglob("*"):
        rel = f.relative_to(destino)
        if f.suffix in {".parquet", ".csv"} or (f.suffix in {".xlsx", ".xls"} and rel.parts[0] != "assets"):
            errores.append(f"Archivo de datos no permitido en la skill: {rel}")
        if f.suffix in {".md", ".py", ".yaml", ".txt"}:
            for i, linea in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                if RUC.search(linea):
                    errores.append(f"Posible RUC en {rel}:{i}")
    return errores


def empaquetar(salida: Path) -> Path:
    destino, zip_ruta = construir(salida)
    errores = validar_paquete(destino)
    if errores:
        raise SystemExit("La skill NO se empaquetó:\n  - " + "\n  - ".join(errores))
    if zip_ruta.exists():
        zip_ruta.unlink()
    with zipfile.ZipFile(zip_ruta, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(destino.rglob("*")):
            if f.is_file() and "__pycache__" not in f.parts:
                z.write(f, f.relative_to(salida))
    return zip_ruta


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Empaqueta la skill desde el repositorio.")
    ap.add_argument("--salida", default=str(RAIZ / "dist"))
    a = ap.parse_args(argv)
    z = empaquetar(Path(a.salida))
    with zipfile.ZipFile(z) as zf:
        n = len(zf.namelist())
    print(f"Skill empaquetada: {z} ({n} archivos, {z.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
