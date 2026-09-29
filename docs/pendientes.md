# Pendientes

## Abiertos
| # | Pendiente | Quién responde | Afecta a |
|---|---|---|---|
| 9 | Confirmado: cada fila es una línea de la OC. Falta que el Hilo 1 derive con la data la regla del **monto total de la OC** (para los niveles de aprobación) y explique el 21 % de OC donde lo facturado no cuadra con "Monto MN". | Hilo 1 (confirma el usuario) | Hilos 1 y 4 |
| 7 | Crear las subcarpetas `entrada/`, `maestro/`, `historico/`, `salida/` en la carpeta de Drive (hoy está vacía). | Usuario o Claude | Hilo 1 |
| 8 | Contradicción de estados: 1 795 filas con "Estado de OC" = Factura pendiente y "Estado Factura" = Pagado por completo (se confirma en la data real). ¿Cuál de los dos campos manda? | Usuario | Hilos 1 y 4 |

## Resueltos (2026-09-25)
| # | Pendiente | Respuesta |
|---|---|---|
| 1 | Significado de "Factura pendiente" | Factura registrada pero no pagada. Cuenta como gasto. |
| 2 | Aprobadores del nivel 5 | Se agrega el CEO. |
| 3 | Montos exactos en el límite | Pertenecen al nivel inferior (límite inclusivo). |
| 5 | Ruta de Google Drive | Carpeta "analisis de gastos", id `1mZsi-I-oM9YzQbtjmVRzPI7iB3LG_pXm`. Acceso verificado. |
| 6 | Rol del supervisor | Es el aprobador de la OC. (Ver pendiente #10.) |
| 10 | ¿"Supervisor" aprueba? | Sí, es quien aprueba. "Empleado" = "Supervisor" en el 94 % de las OC es un hallazgo de control (autoaprobación) para el Hilo 4. |
| 11 | ¿Se usa "Concepto"? | Sí, como apoyo a la taxonomía (Hilo 2). |
| 12 | ¿Data posterior a 2017? | No se considera. El proyecto trabaja con 2015–2017. |
| 4 | Extracto real | Entregado el 2026-09-29: "DATA TOTAL SOLO.xlsx", 103 050 filas, 2015–2017. Perfil en `docs/perfil_extracto_real.md`. |
