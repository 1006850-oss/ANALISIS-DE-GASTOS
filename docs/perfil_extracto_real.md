# Perfil del extracto real – "DATA TOTAL SOLO.xlsx"

Revisado el 2026-09-29 con pandas. Solo cifras agregadas: la data no se sube al repositorio.

## Tamaño y periodo
- 1 hoja ("Hoja1"), **103 050 filas**, 26 columnas. Lectura: ~20 s.
- Fecha de OC: 05/01/2015 a 31/12/2017 (3 años). **No es un semestre: es el histórico 2015–2017.**
- Filas por semestre (según "Periodo Factura"): 2015-S1 11 557 · 2015-S2 11 179 · 2016-S1 14 424 · 2016-S2 19 722 · 2017-S1 21 018 · 2017-S2 23 649 · 2018-S1 1 475 · 2014 (7 filas).
- Promedio ≈ 17 000 filas por semestre (no 200 000).
- 23 009 OC, 1 403 proveedores, 85 sedes, 27 departamentos, 414 artículos.

## Columnas: diferencias con la muestra
| Muestra | Extracto real | Observación |
|---|---|---|
| Año | *(encabezado vacío, se lee como `0`)* | Mismo contenido (año de la OC) |
| Procura | **Nota** | Texto libre con 14 670 valores distintos: útil para la taxonomía |
| COMPRADOR | **Empleado** | 55 personas (nombres reales) |
| SUPERVISOR | **Supervisor** | 61 personas (nombres reales) |

Las otras 22 columnas coinciden. El Hilo 1 debe usar un **mapeo de nombres** (`config/parametros.yaml > mapeo_columnas`).

## Montos (hallazgo principal)
| Medida | Valor |
|---|---|
| Suma de "Monto facturado" (por fila) | S/ 283 013 851.95 |
| Suma de "Monto MN" (por fila) | S/ 712 793 100.53 |
| Suma de "Monto MN" contando la primera fila de cada OC | S/ 206 267 721.83 |
| Suma de "Monto facturado" contando cada factura una vez | S/ 210 926 657.17 |

- En la muestra, "Monto MN" era el total de la OC repetido. **En la data real no siempre**: en 8 039 de las 10 238 OC con varias filas, "Monto MN" cambia entre filas (se comporta como monto por línea).
- En el 79 % de las OC, la suma de "Monto facturado" = suma de "Monto MN" de sus filas (margen S/ 1). Mediana del cociente facturado/MN por OC = 1.00.
- Conclusión provisional: **cada fila parece ser una línea (OC × factura)**. "Monto facturado" por fila sigue siendo la mejor medida de gasto, pero el Hilo 1 debe confirmar el nivel de detalle y explicar el 21 % de OC que no cuadra.
- La regla "Monto MN de la primera fila = monto de la OC" **no sirve** para los niveles de aprobación (acierta solo en el 54 % de las OC).

## Moneda
- Soles: 86 246 filas. Dólares americanos: 16 804 filas.
- En las filas en dólares, "Monto facturado" = "Monto FA ME" × "TC de FA" (mediana 1.00): **"Monto facturado" ya viene en soles**.

## Estados
| Estado Factura | Filas |
|---|---|
| Pagado por completo | 102 872 |
| Pendiente | 152 |
| Aprobación pendiente | 7 |
| (vacío) | 19 |

- "Estado de OC": Totalmente facturado 101 233 · Factura pendiente 1 817.
- Las 19 filas sin factura tienen "Monto facturado" = 0 y "Estado de OC" = Factura pendiente (OC sin facturar).
- 1 795 filas "Factura pendiente" dicen "Pagado por completo": la contradicción de la muestra se repite a escala.

## Calidad
- `_x000D_` en 13 965 descripciones. "Descripcion" vacía en 4 652 filas. "Clase" vacía en 32 626. "Departamento" vacío en 374. "Concepto" vacío en 2 342.
- 1 724 filas con proveedor sin RUC de 11 dígitos (proveedores del exterior, ej. universidades de EE. UU.).
- 291 filas idénticas en todas las columnas (posibles duplicados).
- "Concepto" **sí tiene contenido** (232 valores: Mantenimiento, Pasajes, Alimentos…), a diferencia de la muestra.

## Control interno
- **"Empleado" = "Supervisor" en 94 725 filas (21 601 de 23 009 OC, 94 %).** Si "Supervisor" es el aprobador, la misma persona emite y aprueba casi todas las OC. Hay que confirmar el significado antes de concluir.
