# Pendientes

## Abiertos
| # | Pendiente | Quién responde | Afecta a |
|---|---|---|---|
| 15 | Confirmar la precisión del nivel 3 (producto) con una muestra nueva de 200 en el próximo ciclo (estimación independiente actual: 84.5 %). | Usuario (o revisión asistida) | Hilo 8 |
| 17 | Reemplazar los plazos supuestos de cada modalidad (1/2/3 semanas, licitación 8, obras 10) por los reales. | Usuario | Hilo 6 |
| 16 | Taller de expertos de Kraljic: completar `kraljic_taller.xlsx` (prioridad: 23 unidades "Alta" y 8 "Media") y recalcular con `kraljic.py --taller`. | Usuario + expertos | Hilos 6 y 7 |
| 14 | Asignar (opcional) el segmento UNSPSC a cada categoría, verificando los códigos en la fuente oficial. | Hilo 5 o posterior | Comparaciones externas |

## Resueltos (2026-09-25)
| # | Pendiente | Respuesta |
|---|---|---|
| 1 | Significado de "Factura pendiente" | Factura registrada pero no pagada. Cuenta como gasto. |
| 2 | Aprobadores del nivel 5 | Se agrega el CEO. |
| 3 | Montos exactos en el límite | Pertenecen al nivel inferior (límite inclusivo). |
| 5 | Ruta de Google Drive | Carpeta "analisis de gastos", id `1mZsi-I-oM9YzQbtjmVRzPI7iB3LG_pXm`. Acceso verificado. |
| 6 | Rol del supervisor | Es el aprobador de la OC. (Ver pendiente #10.) |
| 13 | Validación de la taxonomía | Hecha el 2026-09-30: niveles 1–2 por el usuario (4 correcciones); nivel 3 con revisión asistida por IA (ver `docs/taxonomia.md`). |
| 9 | Monto total de la OC | Aprobado en el Hilo 1: suma más alta de "Monto MN" por factura. OC con facturado > monto + 5 % se marcan para el Hilo 4. |
| 7 | Subcarpetas en Drive | Creadas el 2026-09-29: `entrada/`, `maestro/`, `historico/`, `salida/` (ids en `config/parametros.yaml`). |
| 8 | Contradicción de estados | Manda "Estado Factura". Las 1 795 filas en conflicto se consideran pagadas. |
| 10 | ¿"Supervisor" aprueba? | Sí, es quien aprueba. "Empleado" = "Supervisor" en el 94 % de las OC es un hallazgo de control (autoaprobación) para el Hilo 4. |
| 11 | ¿Se usa "Concepto"? | Sí, como apoyo a la taxonomía (Hilo 2). |
| 12 | ¿Data posterior a 2017? | No se considera. El proyecto trabaja con 2015–2017. |
| 4 | Extracto real | Entregado el 2026-09-29: "DATA TOTAL SOLO.xlsx", 103 050 filas, 2015–2017. Perfil en `docs/perfil_extracto_real.md`. |
