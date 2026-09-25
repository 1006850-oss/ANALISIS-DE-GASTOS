# Plan de trabajo – Análisis de gastos de compras

Objetivo: construir, bloque por bloque, un proceso de análisis de gastos que se repita
cada semestre sobre la base real (más de 100 000 registros), y al final orquestarlo
con una skill.

Cada bloque se desarrolla en un hilo (conversación) aparte. Este repositorio es la
memoria compartida entre hilos: cada hilo lee lo que dejaron los anteriores y deja
aquí su entrega.

## Datos verificados en la muestra

- 28 filas, 26 columnas.
- Suma de `Monto MN` = S/ 5 864 650.11 (incorrecta: repite el monto de la OC en cada factura).
- Suma de `Monto facturado` = S/ 2 454 438.56 (gasto real). Sirve como prueba de control.

## Reglas para todos los hilos

1. Los números salen siempre de un script, nunca de un cálculo hecho por el LLM.
2. El LLM solo trabaja sobre valores únicos (por ejemplo, descripciones distintas),
   nunca sobre las 100 000 filas.
3. La data real no se sube a este repositorio (ver `.gitignore`). Aquí solo van código,
   reglas, parámetros, el maestro de categorías y datos de prueba anonimizados.
4. Cada hilo termina con: código probado, un resumen en `docs/bitacora.md` y un commit.

## Orden de los hilos

| Hilo | Bloque | Depende de | Entrega principal |
|---|---|---|---|
| 0 | Fundaciones: decisiones, estructura, reglas | – | Diccionario de datos, reglas de negocio, parámetros, estructura de carpetas |
| 1 | Carga, limpieza y validación | 0 | `limpiar_validar.py` + tabla limpia + reporte de calidad |
| 2 | Taxonomía y maestro de categorías | 1 | `clasificar.py` + `maestro_categorias.xlsx` validado |
| 3 | Análisis descriptivo (Pareto, frecuencias, montos, cruces) | 1, 2 | `analizar.py` |
| 4 | Control y alertas (fraccionamiento, duplicados, ciclo OC→factura, adicionales, giro) | 1 | `alertas.py` |
| 5 | Matriz de Kraljic | 2, 3 | `kraljic.py` + plantilla de puntaje de riesgo |
| 6 | Plan de compras anual | 2, 3 | `proyectar.py` |
| 7 | Salidas: Excel, tablero e informe | 3 a 6 | `generar_excel.py`, modelo para Power BI, plantilla de informe |
| 8 | Integración y automatización (skill) | 0 a 7 | Skill `analisis-gastos-compras` + prueba de un ciclo completo |

Los hilos 2 y 4 pueden trabajarse en paralelo después del hilo 1.

## Prompts

El prompt completo de cada hilo se guarda en `prompts/hilo_N.md`. Todos empiezan con la línea de arranque:

## Línea de arranque

> Trabajo en el repositorio `analisis-de-gastos`. Lee `PLAN.md` y `docs/bitacora.md`.
> Hoy desarrollamos el **Hilo N – [bloque]**. Al terminar, deja el código probado,
> actualiza la bitácora y haz commit.
