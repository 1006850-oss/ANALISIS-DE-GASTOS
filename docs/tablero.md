# Tablero en Excel (Hilo 7)

Decisión del usuario (2026-09-30): no hay Power BI; el tablero se hace en Excel, sin colores ni logo institucional.

## Archivo `resultados_<periodo>.xlsx` (lo genera `scripts/generar_excel.py`)

| Hoja | Qué muestra | Fuente |
|---|---|---|
| Portada | Periodo, gasto analizado, versiones de reglas, cómo leer, advertencias | Hilos 2–4 |
| Tablero_Resumen | Indicadores clave + gasto por año y por categoría (gráficos) | Hilo 3 |
| Tablero_Proveedores | Pareto ABC y frecuencia de proveedores | Hilo 3 |
| Tablero_Control | Señales de control por tipo y prioridad | Hilo 4 |
| Tablero_Kraljic | Matriz (imagen) y resumen por cuadrante (provisional) | Hilo 5 |
| Tablero_Plan | Línea base mensual del plan (gráfico) | Hilo 6 |
| Pareto_ABC … Glosario | Tablas de detalle con filtros | Hilos 1–6 |

Los gráficos son nativos de Excel (se actualizan si se editan las tablas). Compradores y aprobadores van con código (P001…).
Los proveedores sí aparecen con RUC y razón social: el archivo es de trabajo interno y se guarda en Drive, no en el repositorio
ni se envía al LLM.

## Modelo en estrella (`tablero/*.parquet`)
Para un Power BI futuro: `hechos_gasto` (1 fila = línea de gasto) + `dim_fecha`, `dim_proveedor`, `dim_comprador`,
`dim_categoria`, `dim_sede`, `dim_departamento`. Las pruebas verifican que no haya claves huérfanas y que la suma de
`monto_gasto` sea igual a la tabla clasificada.

## Cómo actualizar cada semestre
1. Correr los Hilos 1 a 6 con la data nueva (ver `scripts/README.md`).
2. `python scripts/generar_excel.py --descriptivo … --alertas … --kraljic … --plan … --tabla … --calidad … --periodo <periodo> --salida <carpeta>`
3. Subir el archivo a la carpeta de Drive del periodo. No se sube al repositorio.
