# Pendientes

## Abiertos
| # | Pendiente | Quién responde | Afecta a |
|---|---|---|---|
| 13 | Validar la taxonomía: 88 artículos (95 % del gasto) y la muestra de 200 productos en `validacion_taxonomia.xlsx`; luego cargarla con `clasificar.py --aplicar-validacion`. | Usuario | Hilos 3 y 5 |
| 14 | Asignar (opcional) el segmento UNSPSC a cada categoría, verificando los códigos en la fuente oficial. | Hilo 5 o posterior | Comparaciones externas |

## Resueltos (2026-09-25)
| # | Pendiente | Respuesta |
|---|---|---|
| 1 | Significado de "Factura pendiente" | Factura registrada pero no pagada. Cuenta como gasto. |
| 2 | Aprobadores del nivel 5 | Se agrega el CEO. |
| 3 | Montos exactos en el límite | Pertenecen al nivel inferior (límite inclusivo). |
| 5 | Ruta de Google Drive | Carpeta "analisis de gastos", id `1mZsi-I-oM9YzQbtjmVRzPI7iB3LG_pXm`. Acceso verificado. |
| 6 | Rol del supervisor | Es el aprobador de la OC. (Ver pendiente #10.) |
| 9 | Monto total de la OC | Aprobado en el Hilo 1: suma más alta de "Monto MN" por factura. OC con facturado > monto + 5 % se marcan para el Hilo 4. |
| 7 | Subcarpetas en Drive | Creadas el 2026-09-29: `entrada/`, `maestro/`, `historico/`, `salida/` (ids en `config/parametros.yaml`). |
| 8 | Contradicción de estados | Manda "Estado Factura". Las 1 795 filas en conflicto se consideran pagadas. |
| 10 | ¿"Supervisor" aprueba? | Sí, es quien aprueba. "Empleado" = "Supervisor" en el 94 % de las OC es un hallazgo de control (autoaprobación) para el Hilo 4. |
| 11 | ¿Se usa "Concepto"? | Sí, como apoyo a la taxonomía (Hilo 2). |
| 12 | ¿Data posterior a 2017? | No se considera. El proyecto trabaja con 2015–2017. |
| 4 | Extracto real | Entregado el 2026-09-29: "DATA TOTAL SOLO.xlsx", 103 050 filas, 2015–2017. Perfil en `docs/perfil_extracto_real.md`. |
