# Análisis de gastos de compras – instrucciones para Claude

Proceso semestral de análisis de gastos de compras de una red de colegios (extracto del ERP: órdenes de compra y
facturas). El usuario es ingeniero industrial, trabaja en educación y enseña dirección de proyectos: responde en
español sencillo, de manera objetiva, y verifica las fuentes antes de afirmar algo.

## Para correr un ciclo
Usa la skill del proyecto `.claude/skills/analisis-gastos-compras/` (se activa con pedidos como "necesito el análisis
de gastos del semestre 2026-S2"). En un equipo nuevo, el primer paso es `python scripts/preparar_equipo.py --raiz
"<carpeta de Drive>"`. Guía para personas: `docs/manual_ciclo.md`. Ciclos ya corridos: `docs/ciclos.md`.

## Reglas que no se negocian
- **La data real no entra al repositorio** (extracto, maestro, códigos de personas, resultados). Vive en Google Drive ›
  "analisis de gastos" (`entrada/`, `maestro/`, `historico/`, `salida/`). `.gitignore` bloquea xlsx/csv/parquet.
- **Nunca leer ni mostrar nombres de personas, RUC ni descripciones** de compra: compradores y aprobadores van con
  código (P001…); la tabla nombre → código está solo en Drive (`maestro/codigos_personas.xlsx`).
- **Los números salen de los scripts**, nunca de cálculos a mano.
- **Las alertas son señales para revisar**, no conclusiones (no usar "fraude" ni "irregularidad").
- Detenerse en los puntos de parada humanos; no programar ejecuciones, no compartir archivos y no hacer `git push`
  sin aprobación.
- Commits: terminar el mensaje con la atribución que indique la sesión; no incluir identificadores de modelos.

## Documentación y archivado
- Al terminar un ciclo: `python scripts/registrar_ciclo.py --periodo <AAAA-SN>` → commit de `docs/ciclos.md` y
  etiqueta `ciclo-<AAAA-SN>`. Decisiones abiertas en `docs/pendientes.md`.
- Cambios de código o reglas: actualizar `docs/bitacora.md` (qué y por qué), correr `python -m pytest` y hacer
  commit. La skill se lee directo del repositorio; el ZIP para claude.ai se arma con `scripts/empaquetar_skill.py`.
- Mapa: `PLAN.md` (hilos 0–8), `scripts/README.md` (uso de cada script), `config/` (parámetros y reglas),
  `docs/` (reglas de negocio, taxonomía, indicadores, alertas, Kraljic, plan, informe, tablero, skill, evals).
