# Pendientes

## Abiertos
| # | Pendiente | Quién responde | Afecta a |
|---|---|---|---|
| 15 | Confirmar la precisión del nivel 3 (producto) con una muestra nueva de 200 en el próximo ciclo (estimación independiente actual: 84.5 %). | Usuario (o revisión asistida) | Hilo 8 |
| 17 | Reemplazar los plazos supuestos de cada modalidad (1/2/3 semanas, licitación 8, obras 10) por los reales. El usuario está de acuerdo (2026-09-30) en mantener los supuestos hasta tener los plazos reales. | Usuario | Hilo 6 |
| 16 | Taller de expertos de Kraljic: completar `kraljic_taller.xlsx` (prioridad: 23 unidades "Alta" y 8 "Media") y recalcular con `kraljic.py --taller`. El usuario está conforme (2026-09-30) con mantener los cuadrantes provisionales hasta el taller; en el ciclo se usa `--kraljic-provisional`. | Usuario + expertos | Hilos 6 y 7 |
| 21 | Copiar a Drive los resultados de los ciclos simulados (`salida/2017-S1`, `salida/2017-S2`, `historico/`): el conector de Drive solo permitió subir los archivos de texto. | Usuario | Hilo 8 |
| 22 | El historial de git conserva el RUC y la razón social de la muestra que estaban como ejemplo en `docs/diccionario_datos.md` y `prompts/hilo_1.md` (ya reemplazados por un ejemplo ficticio). Decidir si se reescribe el historial. | Usuario | Repositorio |
| 14 | Asignar (opcional) el segmento UNSPSC a cada categoría, verificando los códigos en la fuente oficial. | Hilo 5 o posterior | Comparaciones externas |

## Resueltos (2026-09-30, Hilo 8)
| # | Pendiente | Respuesta |
|---|---|---|
| 18 | Opción de automatización | Aprobada: inicio manual con recordatorio en el calendario (2.ª semana de enero y de julio). No se programa ninguna ejecución. |
| 19 | Dueño del proceso | Jefatura de Compras (confirmado). |
| 20 | Regla de validación de descripciones nuevas | Confirmada: todos los artículos nuevos + combinaciones que suman el 80 % del gasto nuevo (máx. 200). |

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
