# Pendientes

## Abiertos
| # | Pendiente | Quién responde | Afecta a |
|---|---|---|---|
| 9 | Nivel de detalle de la fila y monto de la OC: en la data real "Monto MN" cambia dentro de la OC (8 039 OC). ¿Cada fila es una línea de OC × factura? ¿Cómo se obtiene el monto total de la OC para los niveles de aprobación? Ver `docs/perfil_extracto_real.md`. | Usuario + Hilo 1 | Hilos 1 y 4 |
| 10 | "Empleado" = "Supervisor" en el 94 % de las OC. ¿"Supervisor" es realmente quien aprueba, o el campo se llena con el mismo usuario por defecto? | Usuario | Hilo 4 |
| 11 | "Concepto" tiene 232 valores en la data real (Mantenimiento, Pasajes, Alimentos…). ¿Se sigue ignorando o se usa en la taxonomía? | Usuario | Hilo 2 |
| 12 | El extracto cubre 2015–2017 (~17 000 filas por semestre, no 200 000). ¿Hay data más reciente (2018 en adelante)? | Usuario | Hilos 1, 3 y 6 |
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
| 4 | Extracto real | Entregado el 2026-09-29: "DATA TOTAL SOLO.xlsx", 103 050 filas, 2015–2017. Perfil en `docs/perfil_extracto_real.md`. |
