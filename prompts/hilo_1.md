Trabajo en el repositorio `analisis-de-gastos`. Lee `PLAN.md` y `docs/bitacora.md` (si no están en tu rama, trae la rama `claude/zen-rubin-srjgvq`, donde se cerró el Hilo 0). Hoy desarrollamos el **Hilo 1 – Carga, limpieza y validación**. Al terminar, deja el código probado, actualiza la bitácora y haz commit.

## Contexto
Soy ingeniero industrial, trabajo en educación (colegios) y enseño dirección de proyectos. Construyo un análisis de gastos de compras que se repetirá cada semestre sobre un histórico de 103 050 registros (2015–2017, ~17 000 por semestre) (órdenes de compra y facturas del ERP). Adjunto la muestra de 28 filas y el extracto real "DATA TOTAL SOLO.xlsx" (13.6 MB; también está en la carpeta de Google Drive indicada en `config/parametros.yaml`). El extracto ya fue perfilado: lee `docs/perfil_extracto_real.md` antes de empezar y verifica sus cifras. Respóndeme en lenguaje sencillo y verifica todo sobre los datos antes de afirmarlo.

## Paso 0 – Verifica que el Hilo 0 esté cerrado
Antes de programar, confirma que existen `docs/diccionario_datos.md`, `docs/reglas_negocio.md` y `config/parametros.yaml`. Si faltan o tienen puntos abiertos en `docs/pendientes.md` que afecten la limpieza (por ejemplo, qué estados cuentan como gasto o cómo se define el semestre), DETENTE, dime cuáles faltan y hazme solo esas preguntas. El único pendiente abierto es el #9 (monto total de la OC) **es lo primero que se resuelve en este hilo**, junto conmigo.

## Paso 0.5 – Resolver el nivel de detalle (pendiente #9)
Ya confirmé que **cada fila es una línea de la OC**. En la muestra, "Monto MN" era el total de la OC repetido en cada factura; en la data real cambia dentro de la OC en 8 039 OC (y se repite en otras 2 199). Analiza la data y proponme, con ejemplos concretos (sin nombres de personas):
1. Cuándo "Monto MN" es monto de línea y cuándo es el total de la OC repetido, y cómo detectarlo.
2. Cómo calcular el gasto sin doble conteo (hipótesis: suma de "Monto facturado" por fila = S/ 283 013 851.95) y por qué el 21 % de las OC no cuadra con "Monto MN".
3. Cómo obtener el monto total de la OC para asignar el nivel de aprobación.
No sigas al Paso 1 hasta que yo confirme la regla.

## Objetivo de este hilo
Construir `scripts/limpiar_validar.py`: recibe la exportación cruda del ERP y entrega una tabla limpia, confiable y lista para todos los análisis. En este hilo NO se hacen análisis (Pareto, fraccionamiento, etc.).

## Paso 1 – Validaciones (antes de limpiar)
Cada validación debe clasificarse como **BLOQUEA** (el proceso se detiene y explica por qué) o **ADVIERTE** (sigue, pero lo reporta). Propón la clasificación y confírmala conmigo:
1. Faltan columnas o cambiaron de nombre respecto al diccionario de datos → BLOQUEA.
2. Tipos de dato inválidos (montos no numéricos, fechas no reconocidas).
3. Filas sin monto facturado, sin comprador, sin proveedor o sin fecha.
4. Facturas duplicadas (mismo RUC + mismo N° de factura).
5. Monedas distintas a soles sin tipo de cambio.
6. Valores nuevos de "Estado Factura" o "Estado de OC" no previstos en las reglas.
7. Proveedores, compradores o sedes nuevos respecto al histórico (si existe).
8. Control de totales: la suma de "Monto facturado" antes y después de limpiar debe ser igual → BLOQUEA si no cuadra.

## Paso 2 – Limpieza y transformación
Aplica primero `mapeo_columnas` de `config/parametros.yaml` (encabezado vacío → "Año", "Nota", "Empleado" → "COMPRADOR", "Supervisor" → "SUPERVISOR"). Problemas ya detectados (verifícalos tú mismo; cifras de la data real en `docs/perfil_extracto_real.md`):
- "Proveedor" trae el RUC pegado al nombre (ej. `20267879398 PORTALAMPARAS S.A.C.`) → separar en `ruc` y `proveedor`.
- "Clase" es una glosa de palabras clave; mezcla texto y año (`Ampliaciones 2018`, `Obras Nuevas`) y está vacía en 7 filas → separar en `clase_glosa` y `clase_anio`; marcar vacíos.
- "Articulo" es la categoría de compra; mezcla mayúsculas y prefijos (`Ventas : Alojamiento`, `VENTAS : Materiales...`) → crear `articulo_normalizado` sin perder el original.
- "N° de Factura" tiene formatos mixtos (`FA 0001-000311`, `FA-...`) → normalizar antes de buscar duplicados.
- "Descripcion" trae el texto basura `_x000D_` (13 965 filas en la data real) y espacios al inicio → limpiar. Está vacía en 4 652 filas.
- 1 724 filas con proveedores del exterior sin RUC de 11 dígitos → `ruc` vacío y `flag_proveedor_exterior`.
- 291 filas idénticas en todas las columnas → marcar `flag_fila_duplicada` (no borrar sin mi confirmación).
- 19 filas sin factura (monto 0) → OC sin facturar.
- "Empleado" y "Supervisor" traen nombres reales de personas → nunca enviarlos al LLM; en los reportes del repositorio usar códigos.
- "Periodo Factura" viene como texto en español (`may 2017`, `ago 2015`, `dic 2016`) → convertir a fecha.
- "Nota" (texto libre) y "Concepto" se conservan limpios: son apoyo para la taxonomía del Hilo 2.
- El alcance es 2015–2017: las facturas con periodo 2014 o 2018 de OC de ese rango se conservan.
- "Monto MN" es el monto total de la OC y se repite en cada factura → NUNCA sumarlo por fila.

Columnas que debe agregar el script:
- `id_linea` (identificador único), `semestre` (`AAAA-S1`/`AAAA-S2` según "Periodo Factura").
- `monto_gasto` = "Monto facturado" en soles (convertido con TC si hubiera otra moneda).
- `es_primera_linea_oc` (1 solo en la primera fila de cada OC), para contar el monto de la OC una sola vez.
- `pendiente_de_pago` según **"Estado Factura"** (manda sobre "Estado de OC"): 1 si es distinto de "Pagado por completo" o no hay factura. Toda factura registrada cuenta como gasto. Reportar como advertencia informativa las filas donde "Estado de OC" = Factura pendiente y "Estado Factura" = Pagado por completo (1 795 en la data real).
- `nivel_aprobacion_oc` (1 a 5) según el monto total de la OC (regla del Paso 0.5) y los niveles de `config/parametros.yaml`.
- Banderas de calidad por fila (ej. `flag_clase_vacia`, `flag_duplicado`).

## Paso 3 – Rendimiento
- Prueba con el extracto real (103 050 filas; se lee en ~20 s).
- Crea `tests/generar_sintetico.py` que genere 250 000 filas con la estructura real (con duplicados y errores sembrados a propósito), para probar crecimiento futuro y para pruebas sin data real.
- Mide el tiempo de ejecución e informa. Meta: pocos minutos en una laptop normal.
- Lee xlsx y csv. Guarda la tabla limpia en Parquet (para procesar) y un resumen en Excel (para revisar). No generes un Excel con todas las filas salvo que yo lo pida.
- Todas las rutas y umbrales salen de `config/parametros.yaml`, no escritos en el código.

## Paso 4 – Pruebas automáticas (pytest)
1. Muestra normal: suma de `monto_gasto` = S/ 2 454 438.56; suma de "Monto MN" con `es_primera_linea_oc` = gasto de OC sin doble conteo; 23 OC distintas; 14 proveedores.
2. Columna faltante o renombrada → el script se detiene con un mensaje claro.
3. Factura duplicada sembrada → se detecta.
4. Base sintética de 250 000 filas → corre sin errores y el control de totales cuadra.
5. Ejecutar dos veces con la misma entrada da exactamente el mismo resultado.
6. Extracto real (se salta si el archivo no está disponible): 103 050 filas leídas, 23 009 OC, control de totales según la regla confirmada en el Paso 0.5.

## Entregables
1. `scripts/limpiar_validar.py`, con un comando simple de uso, por ejemplo `python scripts/limpiar_validar.py --entrada <archivo> --periodo 2026-S2`.
2. `tests/` con las pruebas y el generador sintético.
3. Salidas en la carpeta de salida (fuera del repositorio): `tabla_limpia.parquet` y `reporte_calidad.xlsx` (resumen de validaciones, filas con banderas, control de totales).
4. `requirements.txt` con las librerías usadas.
5. Actualiza `docs/diccionario_datos.md` con las columnas nuevas y `docs/bitacora.md` con las decisiones.

## Reglas
- No subas data real al repositorio.
- Los números salen del script; no hagas cálculos a mano.
- Si una regla de negocio no está clara, pregúntame en vez de suponer.
- Cierra el hilo con un resumen: qué valida y limpia el script, tiempos medidos, resultado de las pruebas, pendientes y qué necesita el Hilo 2 (taxonomía).
