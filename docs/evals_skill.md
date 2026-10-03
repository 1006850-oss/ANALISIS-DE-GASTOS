# Evals de la skill `analisis-gastos-compras` (Hilo 8, 2026-09-30)

Definición de los casos: `.claude/skills/analisis-gastos-compras/evals/evals.json`. Frases de activación: `.claude/skills/analisis-gastos-compras/evals/activacion.json`.
Resultados crudos: `.claude/skills/analisis-gastos-compras/evals/resultados/`.

## Resumen

| # | Caso | Cómo se ejecutó | Resultado |
|---|---|---|---|
| 1 | Ciclo normal con el extracto real | Orquestador de la skill **empaquetada**, sin repositorio ni git, con pandas 2.3. Se repitió desde el repositorio (pandas 3.0) en la corrida final | ✔ Las 18 cifras oficiales coinciden (`.claude/skills/analisis-gastos-compras/evals/verificar_ciclo_oficial.py`) y todos los cuadres dan OK |
| 2 | Columna renombrada (`Descripcion` → `Detalle`) | Claude con la skill instalada (`claude -p`, data sintética), frase natural sin nombrar la skill | ✔ Activó la skill; código 2; explicó qué columna falta; propuso corregir la exportación o el mapeo; no cambió nada por su cuenta; no abrió el extracto |
| 3 | Descripciones nuevas (1 artículo, 5 descripciones) | Igual que el 2, en dos conversaciones separadas | ✔ Turno 1: se detuvo (código 3), pidió validar solo las nuevas y no aceptó propuestas por su cuenta. Turno 2: aplicó la validación al maestro (con respaldo), registró "Kraljic provisional" y terminó con todos los cuadres OK |
| 4 | Activación con frases naturales | `run_eval.py` de skill-creator: 10 frases que deben activarla y 10 casi iguales que no | ✔ 20/20 en la versión final (60 de 60 corridas correctas) |

Además, `pytest` cubre los casos 1 a 3 con data sintética (`tests/test_ciclo.py`) y el empaquetado (`tests/test_skill.py`):
69 pruebas, todas pasan.

## Eval 1 – cifras oficiales (ciclo 2017-S2)

| Cifra | Oficial | Obtenida |
|---|---|---|
| Filas / OC | 103 050 / 23 009 | igual |
| Gasto de la tabla limpia | S/ 283 013 851.95 | igual |
| Gasto analizado 2015-S1 a 2017-S2 | S/ 275 378 383.86 | igual |
| Proveedores / clase A / con una sola OC | 1 399 / 81 / 528 | igual |
| Fraccionamiento (alta) / autoaprobación / factura antes de OC | 212 (128) / 1 209 / 95 | igual |
| Duplicados (alta) / señales de prioridad alta | 312 (61) / 312 | igual |
| Kraljic: unidades y cuadrantes | 78 · 3/13/9/53 | igual |
| Consolidación: tipos de compra / OC pequeñas | 47 / 6 550 | igual |

## Eval 4 – iteraciones de la `description`

| Iteración | Description (resumen) | Deben activar | No deben activar | Nota |
|---|---|---|---|---|
| 1 | "Análisis de gastos … Úsala aunque no la nombren." (193 caracteres) | 0/10 | 10/10 | Medición inválida: con 6 corridas en paralelo, Claude veía 6 copias de la skill y elegía otra. Se repitió en serie |
| 2 | igual a la 1 (en serie, 2 corridas por frase) | 10/10 | 9/10 | Falsa activación en "Explícame qué es spend analysis…" (1 de 2 corridas) |
| 3 | "Ejecuta … informe. No para dudas teóricas." | 9/10 | 10/10 | Se perdió "revisa autoaprobaciones y posibles facturas duplicadas…" |
| 4 (final) | "Ejecuta el análisis de gastos de compras (spend analysis) del semestre con el extracto del ERP: Pareto de proveedores, compras fraccionadas y otras alertas, Kraljic, plan de compras. No para teoría." (198 caracteres) | **10/10** | **10/10** | 3 corridas por frase |

Límites de la prueba:

- La activación se midió con Claude Code y un solo modelo.
- En claude.ai el comportamiento puede variar. Conviene probar 2 o 3 frases después de instalar la skill.
- La guía de buenas prácticas recomienda probar con varios modelos.

## Incidente durante las pruebas

En el Eval 3, la instancia de Claude evaluada tenía la herramienta de envío de archivos. Envió al usuario 4 archivos de la **prueba sintética**
(sin data real). Para próximas pruebas: ejecutar `claude -p` con `--disallowedTools SendUserFile`.
