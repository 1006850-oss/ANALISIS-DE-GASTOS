# Diccionario de datos – Exportación del ERP

Versión 2026-09-25 (Hilo 0). Basado en la muestra de 28 filas (anonimizada/mezclada, según el usuario) y en las respuestas del usuario.

Nivel de detalle: **una fila = una línea de la OC** con su factura (confirmado por el usuario). Una OC puede tener varias líneas y varias facturas.
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
| 5 | Proveedor | texto | Sí | RUC + razón social en un solo campo | Proveedor | Separar: `20XXXXXXXXX PROVEEDOR EJEMPLO S.A.C.` → ruc + nombre |
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
| 19 | SUPERVISOR (real: "Supervisor") | texto | Sí | **Aprobador de la OC** | Control interno | Real: 61 personas; igual al comprador en el 94 % de las OC |
| 20 | Articulo | texto | Sí | **Categoría de compra** (según el usuario) | Nivel 1 de la taxonomía | 10 valores; mezcla mayúsculas y prefijos ("Ventas :", "VENTAS :") |
| 21 | Descripcion | texto | Sí | Descripción de la OC | Subcategoría / producto (Hilo 2) | `_x000D_` en 3 filas; espacios al inicio |
| 22 | Concepto | texto | No | Tipo de gasto | **Apoyo a la taxonomía** (Hilo 2) | Real: 232 valores, 2 342 vacíos. En la muestra parecía sin valor |
| 23 | Departamento | texto | Sí | Área solicitante | Filtro | Solo "CONST" |
| 24 | Clase | texto | No | **Glosa de palabras clave** que se coloca en la descripción de la OC | Etiqueta auxiliar | Vacía en 7 filas; trae años (`Ampliaciones 2018`) que no coinciden con el año de la OC |
| 25 | ID Interno OC | entero | Sí | Identificador interno del ERP | Llave técnica | 1 a 1 con N° de OC |
| 26 | Estado de OC | texto | Sí | Estado de la OC. "Factura pendiente" = factura registrada pero no pagada | Ciclo OC→factura | "Totalmente facturado" (22) / "Factura pendiente" (6) |

## Columnas de la tabla limpia (`tabla_limpia.parquet`, Hilo 1)

Una fila por fila de la exportación (línea de OC × factura). Nombres en minúscula; los originales se conservan limpios.

| Columna | Tipo | Regla |
|---|---|---|
| `id_linea` | entero | Identificador único (orden de la exportación, desde 1) |
| `anio_oc`, `mes_oc`, `fecha_oc` | entero / fecha | De "Año", "Mes", "Fecha de OC" |
| `oc`, `id_interno_oc` | entero | N° de OC e ID interno |
| `ruc` | texto | 11 dígitos al inicio de "Proveedor"; vacío si es proveedor del exterior |
| `proveedor` | texto | Razón social sin el RUC |
| `proveedor_id` | texto | Llave del proveedor: el RUC, o `EXT:<NOMBRE>` si no tiene RUC |
| `proveedor_original` | texto | "Proveedor" limpio tal como venía |
| `sede`, `departamento`, `moneda` | texto | Limpios |
| `monto_mn_linea`, `monto_me_linea`, `tc_oc` | decimal | "Monto MN", "Monto ME", "TC de OC" (NO sumar por fila) |
| `monto_gasto` | decimal | **Gasto en soles** = "Monto facturado" (ya viene en soles) |
| `monto_fa_me`, `tc_fa` | decimal | "Monto FA ME", "TC de FA" |
| `n_factura`, `factura_normalizada` | texto | N° de factura limpio / sin espacios, guiones ni puntos (para duplicados) |
| `periodo_factura` | fecha | Primer día del mes de "Periodo Factura" |
| `semestre`, `anio_gasto` | texto / entero | `AAAA-S1`/`AAAA-S2` según "Periodo Factura" (si no hay factura, según fecha de OC) |
| `estado_factura`, `estado_oc` | texto | Limpios |
| `pendiente_de_pago` | bool | "Estado Factura" distinto de "Pagado por completo" o sin factura (manda "Estado Factura") |
| `comprador_codigo`, `aprobador_codigo` | texto | Código P001… por persona (la tabla nombre → código solo va en `reporte_calidad.xlsx`, fuera del repositorio) |
| `articulo`, `articulo_normalizado` | texto | Original limpio / mayúsculas y " : " uniforme |
| `descripcion`, `concepto`, `nota` | texto | Sin `_x000D_`, saltos de línea ni espacios dobles |
| `clase`, `clase_glosa`, `clase_anio` | texto / entero | "Clase" y su separación en texto y año final |
| `monto_oc`, `monto_oc_me` | decimal | **Monto total de la OC**: por cada factura se suma "Monto MN" (o "Monto ME") de sus filas y se toma la suma más alta. Repetido en todas las filas de la OC |
| `es_primera_linea_oc` | 0/1 | 1 solo en la primera fila de cada OC (para sumar `monto_oc` una vez) |
| `nivel_aprobacion_oc` | entero 1–5 | Según `monto_oc` y límites en soles; OC en dólares según `monto_oc_me` y límites en dólares |

**Banderas de calidad** (`flag_*`, verdadero/falso): `flag_proveedor_exterior`, `flag_moneda_extranjera`, `flag_sin_factura`, `flag_semestre_por_fecha_oc`, `flag_estado_contradictorio`, `flag_descripcion_vacia`, `flag_clase_vacia`, `flag_facturado_excede_oc` (facturado de la OC > `monto_oc` + 5 %), `flag_fila_duplicada` (idéntica en las 26 columnas; se conserva), `flag_factura_en_varias_oc` (mismo proveedor y factura normalizada en más de una OC).

## Columnas que agrega la clasificación (`tabla_clasificada.parquet`, Hilo 2)

| Columna | Regla |
|---|---|
| `categoria` | Nivel 1 (15 categorías de `config/reglas_taxonomia.yaml`), por artículo |
| `subcategoria` | Nivel 2 (64), por artículo; en Construcción, tipo de intervención según `clase_glosa` |
| `producto` | Nivel 3: palabras clave en descripción + concepto + nota; si no, el concepto; si no, "Otros – subcategoría" |
| `origen_categoria`, `confianza_categoria` | `regla` / `humano` (maestro validado) / `sin_articulo`; confianza alta, media o baja |
| `origen_producto` | `regla_palabra` / `concepto` / `subcategoria` / `humano` / `llm` |
| `llave_combinacion` | "artículo normalizado \| descripción normalizada" (llave del maestro de productos) |
| `excluir_de_kraljic` | Verdadero para "Cuentas contables (no gestionables por Compras)" |
