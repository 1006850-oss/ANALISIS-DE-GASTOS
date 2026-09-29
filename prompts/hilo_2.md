Trabajo en el repositorio `analisis-de-gastos`. Lee `PLAN.md`, `docs/bitacora.md`, `docs/reglas_negocio.md` y `docs/perfil_extracto_real.md` (si no están en tu rama, trae la rama donde se cerró el Hilo 1; si no la encuentras, pregúntame cuál es). Hoy desarrollamos el **Hilo 2 – Taxonomía y maestro de categorías**. Al terminar, deja el código probado, actualiza la bitácora y haz commit.

## Contexto
Soy ingeniero industrial, trabajo en educación (colegios) y enseño dirección de proyectos. Construyo un análisis de gastos de compras con el histórico 2015–2017 del ERP (103 050 filas, 23 009 OC). Adjunto el extracto real "DATA TOTAL SOLO.xlsx" (también está en la carpeta `entrada/` de Google Drive). Respóndeme en lenguaje sencillo y verifica todo sobre los datos antes de afirmarlo.

## Paso 0 – Verifica que el Hilo 1 esté cerrado
Confirma que existen `scripts/limpiar_validar.py` y sus pruebas, y que la bitácora registra la regla del monto de la OC (pendiente #9). Ejecuta el script sobre el extracto para obtener `tabla_limpia.parquet`. Si falta algo o el script falla, DETENTE y dime qué falta.

## Objetivo de este hilo
Construir la taxonomía de 3 niveles (**categoría > subcategoría > producto**) y el **maestro de categorías**: una tabla que asigna cada combinación de texto a sus 3 niveles, que se construye una vez y luego solo crece cada ciclo.

## Lo que ya se sabe de la data (verifícalo)
- "Articulo" es la categoría de compra del ERP: 410 valores distintos (tras limpiar mayúsculas y espacios). **16 artículos concentran el 80 % del gasto.**
- Muchos artículos traen una estructura "GRUPO : SUBGRUPO" (ej. `VENTAS : CALL CENTER`, `BRANDING : SEM Y PLAN DIGITAL`, `EQUIPAMIENTO SEDE : ÁREAS COMUNES`). Puede servir como jerarquía natural.
- Textos de apoyo: "Descripcion" (23 777 valores distintos limpios; vacía en 4 653 filas), "Concepto" (180 valores), "Nota" (texto libre, ~14 670 valores) y "Clase" (glosa de palabras clave).
- Hay 24 316 combinaciones "Articulo + Descripcion". Por gasto: **1 434 combinaciones cubren el 80 %**, 3 436 el 90 % y 6 068 el 95 %.

## Paso 1 – Propón el diseño antes de clasificar
Propónme, con ejemplos reales (sin nombres de personas ni RUC), y espera mi aprobación:
1. **Qué es cada nivel.** Propuesta de partida para evaluar: categoría = grupo macro (derivado del prefijo "GRUPO :" o de agrupar los 410 artículos en 15–25 categorías), subcategoría = artículo normalizado, producto = tipo de bien o servicio a partir de "Descripcion", "Concepto" y "Nota". Si hay un diseño mejor, compáralo.
2. **Si conviene alinear con un estándar** (por ejemplo UNSPSC a nivel de segmento/familia) o mantener una taxonomía propia adaptada a colegios. Verifica la fuente del estándar antes de proponerlo.
3. **La llave del maestro**: qué campos identifican una fila del maestro (ej. artículo normalizado + descripción normalizada) para que la data nueva se clasifique sola.

## Paso 2 – Clasificación en capas (el LLM al final, no al principio)
1. **Reglas**: mapeos directos y palabras clave (ej. artículo → categoría; "pasaje" → Viajes). Resuelven la mayor parte sin LLM.
2. **LLM solo para lo que las reglas no resuelven**, sobre valores únicos, en lotes, con una lista cerrada de categorías y un nivel de confianza por fila. Nunca enviar nombres de personas, RUC ni montos.
3. **Validación humana priorizada por gasto**: yo valido primero las combinaciones que cubren el 80 % del gasto (~1 434) y las de confianza baja; el resto se acepta con revisión por muestreo. Propón un tamaño de muestra y un criterio de aceptación (ej. ≥ 95 % de aciertos).
Prepara un Excel de validación fácil de revisar: una fila por combinación, columnas con la propuesta, confianza, gasto y una columna "¿Correcto? / Corrección".

## Paso 3 – Script y maestro
- `scripts/clasificar.py`: lee la tabla limpia y el maestro, asigna los 3 niveles, y lista las combinaciones **nuevas** (no están en el maestro) para validar.
- `maestro_categorias.xlsx` en la carpeta `maestro/` de Drive, con: llave, 3 niveles, origen (regla / LLM / humano), confianza, fecha y versión.
- Las reglas y palabras clave en un archivo editable (ej. `config/reglas_taxonomia.yaml`), no escritas en el código.

## Paso 4 – Pruebas (pytest)
1. El 100 % de las filas de la tabla limpia queda con los 3 niveles (o marcada "Sin clasificar" y listada).
2. La suma del gasto por categoría = gasto total del Hilo 1 (ningún monto se pierde ni se duplica).
3. Una descripción nueva inventada aparece en la lista de "nuevas para validar".
4. Ejecutar dos veces da el mismo resultado.
5. Con la muestra de 28 filas, el script corre sin errores (la muestra está mezclada: no evalúes la calidad de la clasificación con ella).

## Entregables
1. `scripts/clasificar.py`, `config/reglas_taxonomia.yaml` y pruebas en `tests/`.
2. `docs/taxonomia.md`: definición de cada nivel, lista de categorías y subcategorías con una línea de descripción cada una, y cómo se mantiene el maestro cada ciclo.
3. En Drive: `maestro/maestro_categorias.xlsx` y `salida/validacion_taxonomia.xlsx`.
4. Resumen de cobertura: % del gasto y % de filas clasificadas por regla, por LLM y validadas por mí.
5. Actualiza `docs/diccionario_datos.md` (columnas `categoria`, `subcategoria`, `producto`) y `docs/bitacora.md`.

## Reglas
- No subas data real al repositorio (el maestro va a Drive; en el repositorio solo reglas y código).
- Los montos y porcentajes salen de scripts, no de cálculos a mano.
- No clasifiques "a ojo" miles de filas en la conversación: usa reglas + LLM por lotes + validación.
- Si una decisión de diseño no está clara, pregúntame en vez de suponer.
- Cierra el hilo con un resumen: diseño aprobado, cobertura lograda, qué quedó por validar y qué necesitan los Hilos 3, 4 y 5.
