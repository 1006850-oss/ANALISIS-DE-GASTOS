Trabajo en el repositorio `analisis-de-gastos`. Lee `PLAN.md` y `docs/bitacora.md` (si no están en tu rama, están en la rama `claude/zen-rubin-srjgvq` o en la rama donde se cerró el Hilo 0). Hoy desarrollamos el **Hilo 1 – Carga, limpieza y validación**. Al terminar, deja el código probado, actualiza la bitácora y haz commit.

## Contexto
Soy ingeniero industrial, trabajo en educación (colegios) y enseño dirección de proyectos. Construyo un análisis de gastos de compras que se repetirá cada semestre sobre una base de más de 100 000 registros (órdenes de compra y facturas del ERP). Adjunto la muestra de 28 filas y, si lo tengo, un extracto real o anonimizado. Respóndeme en lenguaje sencillo y verifica todo sobre los datos antes de afirmarlo.

## Paso 0 – Verifica que el Hilo 0 esté cerrado
Antes de programar, confirma que existen `docs/diccionario_datos.md`, `docs/reglas_negocio.md` y `config/parametros.yaml`. Si faltan o tienen puntos abiertos en `docs/pendientes.md` que afecten la limpieza (por ejemplo, qué estados cuentan como gasto o cómo se define el semestre), DETENTE, dime cuáles faltan y hazme solo esas preguntas.

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
Problemas ya detectados en la muestra (verifícalos tú mismo):
- "Proveedor" trae el RUC pegado al nombre (ej. `20267879398 PORTALAMPARAS S.A.C.`) → separar en `ruc` y `proveedor`.
- "Clase" mezcla tipo de obra y año (`Ampliaciones 2018`, `Obras Nuevas`) y está vacía en 7 filas → separar en `clase_tipo` y `clase_anio`; marcar vacíos.
- "Descripcion" trae el texto basura `_x000D_` (3 filas) y espacios al inicio → limpiar.
- "Periodo Factura" viene como texto en español (`may 2017`, `ago 2015`, `dic 2016`) → convertir a fecha.
- "Procura" está vacía en las 28 filas → confirmar si se conserva.
- "Monto MN" es el monto total de la OC y se repite en cada factura → NUNCA sumarlo por fila.

Columnas que debe agregar el script:
- `id_linea` (identificador único), `semestre` (según la regla del Hilo 0).
- `monto_gasto` = "Monto facturado" en soles (convertido con TC si hubiera otra moneda).
- `es_primera_linea_oc` (1 solo en la primera fila de cada OC), para contar el monto de la OC una sola vez.
- `con_factura_pendiente` según "Estado de OC" (6 filas en la muestra).
- Banderas de calidad por fila (ej. `flag_clase_vacia`, `flag_duplicado`).

## Paso 3 – Rendimiento con más de 100 000 registros
- Si no hay extracto real, crea `tests/generar_sintetico.py` que genere 150 000 filas con la misma estructura de la muestra (con duplicados y errores sembrados a propósito).
- Mide el tiempo de ejecución e informa. Meta: pocos minutos en una laptop normal.
- Lee xlsx y csv. Guarda la tabla limpia en Parquet (para procesar) y un resumen en Excel (para revisar). No generes un Excel con las 100 000 filas salvo que yo lo pida.
- Todas las rutas y umbrales salen de `config/parametros.yaml`, no escritos en el código.

## Paso 4 – Pruebas automáticas (pytest)
1. Muestra normal: suma de `monto_gasto` = S/ 2 454 438.56; suma de "Monto MN" con `es_primera_linea_oc` = gasto de OC sin doble conteo; 23 OC distintas; 14 proveedores.
2. Columna faltante o renombrada → el script se detiene con un mensaje claro.
3. Factura duplicada sembrada → se detecta.
4. Base sintética de 150 000 filas → corre sin errores y el control de totales cuadra.
5. Ejecutar dos veces con la misma entrada da exactamente el mismo resultado.

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
