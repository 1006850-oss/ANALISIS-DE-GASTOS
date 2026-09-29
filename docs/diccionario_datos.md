# Diccionario de datos – Exportación del ERP

Versión 2026-09-25 (Hilo 0). Basado en la muestra de 28 filas (anonimizada/mezclada, según el usuario) y en las respuestas del usuario.

Nivel de detalle: en la muestra parecía **una fila = una factura de una OC**. En la data real parece **una fila = una línea de OC × factura** (pendiente #9).
Formato: xlsx. Extracto real 2015–2017: 103 050 filas (~17 000 por semestre).

**Nombres de columnas en la data real** (se estandarizan con `config/parametros.yaml > mapeo_columnas`):
- "Año" viene con encabezado vacío.
- "Procura" se llama **"Nota"** y tiene texto útil (14 670 valores).
- "COMPRADOR" se llama **"Empleado"**; "SUPERVISOR" se llama **"Supervisor"**.

Perfil completo del extracto real: `docs/perfil_extracto_real.md`.

## Columnas de origen

| # | Columna | Tipo | Oblig. | Significado | Uso | Observaciones en la muestra |
|---|---|---|---|---|---|---|
| 1 | Año | entero | Sí | Año de la fecha de OC | Control | Coincide siempre con "Fecha de OC" |
| 2 | Mes | entero | Sí | Mes de la fecha de OC | Control | Coincide siempre con "Fecha de OC" |
| 3 | Fecha de OC | fecha | Sí | Fecha de emisión de la OC | Fraccionamiento, ciclo OC→factura | Rango jul-2015 a dic-2017 |
| 4 | N° de Orden de Compra | entero | Sí | Número de la OC | Llave de OC | 23 OC distintas |
| 5 | Proveedor | texto | Sí | RUC + razón social en un solo campo | Proveedor | Separar: `20267879398 PORTALAMPARAS S.A.C.` → ruc + nombre |
| 6 | Sede | texto | Sí | Colegio / sede de destino | Gasto por sede | 17 sedes |
| 7 | Moneda | texto | Sí | Moneda de la OC | Conversión | Real: Soles (86 246) y Dolares Americanos (16 804). "Monto facturado" ya viene en soles |
| 8 | Monto MN | decimal | Sí | Monto de la OC en soles (total o por línea: pendiente #9) | Monto de OC para niveles de aprobación | Muestra: se repite. Real: cambia dentro de la OC en 8 039 OC. NO sumar sin resolver #9 |
| 9 | Monto ME | decimal | No | Monto de la OC en moneda extranjera | Conversión | 0 en todas las filas |
| 10 | TC de OC | decimal | No | Tipo de cambio de la OC | Conversión | 1 en todas las filas |
| 11 | Procura → **Nota** | texto | No | Muestra: vacío. Real: nota libre de la OC | Apoyo a la taxonomía | 14 670 valores distintos |
| 12 | Monto facturado | decimal | Sí | Monto de la factura en soles | **Gasto** | Suma muestra = S/ 2 454 438.56 |
| 13 | Monto FA ME | decimal | No | Monto de la factura en moneda extranjera | Conversión | 0 en todas las filas |
| 14 | TC de FA | decimal | No | Tipo de cambio de la factura | Conversión | 1 en todas las filas |
| 15 | N° de Factura | texto | Sí | Serie y número de factura | Duplicados | Formatos mixtos: `FA 0001-000311` y `FA-...` → normalizar |
| 16 | Periodo Factura | texto | Sí | Mes de la factura (`may 2017`) | **Semestre del gasto** | Meses en español abreviado |
| 17 | Estado Factura | texto | Sí | Estado de pago | Informativo | Solo "Pagado por completo" |
| 18 | COMPRADOR | texto | Sí | Comprador que emite la OC | Cruces | 4 compradores (A–D) |
| 19 | SUPERVISOR | texto | Sí | **Aprobador de la OC** | Control interno | 1 solo supervisor (F) |
| 20 | Articulo | texto | Sí | **Categoría de compra** (según el usuario) | Nivel 1 de la taxonomía | 10 valores; mezcla mayúsculas y prefijos ("Ventas :", "VENTAS :") |
| 21 | Descripcion | texto | Sí | Descripción de la OC | Subcategoría / producto (Hilo 2) | `_x000D_` en 3 filas; espacios al inicio |
| 22 | Concepto | texto | No | Sin valor analítico (según el usuario) | Se ignora (revisar: pendiente #11) | Real: 232 valores, 2 342 vacíos |
| 23 | Departamento | texto | Sí | Área solicitante | Filtro | Solo "CONST" |
| 24 | Clase | texto | No | **Glosa de palabras clave** que se coloca en la descripción de la OC | Etiqueta auxiliar | Vacía en 7 filas; trae años (`Ampliaciones 2018`) que no coinciden con el año de la OC |
| 25 | ID Interno OC | entero | Sí | Identificador interno del ERP | Llave técnica | 1 a 1 con N° de OC |
| 26 | Estado de OC | texto | Sí | Estado de la OC. "Factura pendiente" = factura registrada pero no pagada | Ciclo OC→factura | "Totalmente facturado" (22) / "Factura pendiente" (6) |

## Columnas que agregará el Hilo 1

| Columna | Regla |
|---|---|
| `id_linea` | Identificador único de fila |
| `ruc`, `proveedor` | Separados de "Proveedor" |
| `semestre` | `AAAA-S1` / `AAAA-S2` según "Periodo Factura" |
| `monto_gasto` | "Monto facturado" en soles |
| `es_primera_linea_oc` | 1 en la primera fila de cada OC (para contar "Monto MN" una sola vez) |
| `nivel_aprobacion_oc` | Nivel 1–5 según "Monto MN" y `config/parametros.yaml` |
| `con_factura_pendiente` | Según "Estado de OC" |
| `clase_glosa`, `clase_anio` | "Clase" separada en texto y año |
| `articulo_normalizado` | "Articulo" en formato uniforme |
| `flag_*` | Banderas de calidad por fila |
