Trabajo en el repositorio `analisis-de-gastos`. Lee `PLAN.md`, `docs/bitacora.md`, `docs/reglas_negocio.md`, `docs/taxonomia.md` y `docs/perfil_extracto_real.md` (si no están en tu rama, trae la rama principal o la rama donde se cerró el Hilo 2; si no la encuentras, pregúntame cuál es). Hoy desarrollamos el **Hilo 3 – Análisis descriptivo**. Al terminar, deja el código probado, actualiza la bitácora y haz commit.

## Contexto
Soy ingeniero industrial, trabajo en educación (colegios) y enseño dirección de proyectos. Construyo un análisis de gastos de compras con el histórico 2015–2017 del ERP (103 050 filas, 23 009 OC). Adjunto el extracto real "DATA TOTAL SOLO.xlsx" (también está en la carpeta `entrada/` de Google Drive). Respóndeme en lenguaje sencillo y verifica todo sobre los datos antes de afirmarlo.

## Paso 0 – Verifica que los Hilos 1 y 2 estén cerrados
Confirma que existen `scripts/limpiar_validar.py`, `scripts/clasificar.py`, sus pruebas y el maestro de categorías (en `maestro/` de Drive o adjunto). Ejecuta limpieza + clasificación sobre el extracto y confirma que el gasto total coincide con el que registró el Hilo 1 en la bitácora. Si algo falta o no cuadra, DETENTE y dime qué falta.

## Objetivo de este hilo
Construir `scripts/analizar.py`: calcula todos los análisis descriptivos a partir de la tabla limpia y clasificada, y guarda los resultados en tablas listas para el Excel y el tablero del Hilo 7. En este hilo NO se hacen alertas de control (Hilo 4), Kraljic (Hilo 5) ni proyecciones (Hilo 6).

## Cifras de referencia (provisionales)
Calculadas en el hilo de planificación con "Monto facturado" por fila, antes de cerrar la regla del pendiente #9. Úsalas solo como referencia de orden de magnitud; las cifras oficiales son las que produzca el script con la regla aprobada en el Hilo 1:
- 1 403 proveedores: 80 concentran el 80 % del gasto y 276 el 95 %. El mayor proveedor pesa ~16 %; los 10 mayores ~50 %. 532 proveedores tienen una sola OC.
- 55 compradores: los 5 mayores manejan ~74 % del gasto.
- 85 sedes; "SEDE CENTRAL" es la de mayor gasto. 27 departamentos; CONST concentra la mayor parte.
- Gasto por año de OC: 2015 ≈ S/ 48 M, 2016 ≈ S/ 103 M, 2017 ≈ S/ 132 M.

## Análisis a construir (todos parametrizables por periodo: año o semestre)
1. **Pareto y ABC de proveedores**: ranking por gasto, % y % acumulado, clase A/B/C con los cortes de `config/parametros.yaml`, N° de proveedores por clase. Proveedores del exterior sin RUC: usar el nombre como llave.
2. **Frecuencia por proveedor**: N° de OC, N° de facturas, N° de líneas, ticket promedio y mediano por OC, meses activos, primera y última compra.
3. **Gasto por categoría, subcategoría y producto**: monto, %, N° de OC, N° de proveedores, y tendencia por año y semestre (tasa de variación).
4. **Comprador × proveedor**: matriz de monto y N° de OC; para cada proveedor, % del gasto que maneja su comprador principal; lista de proveedores A donde un solo comprador maneja ≥ 90 %.
5. **Comprador × categoría**: matriz de monto; índice de especialización de cada comprador (ej. % de su gasto en su categoría principal o HHI).
6. **Gasto por sede y por departamento**: ranking, tendencia y categorías principales de cada sede.
7. **Concentración**: índice HHI por categoría (proveedores por categoría). Lo usará el Hilo 5 como aproximación al riesgo.

Antes de programar, propónme el formato de cada salida (qué columnas, qué nivel de detalle) y confírmalo conmigo. Pregúntame también si quiero la tendencia en soles nominales o ajustados por inflación (si es ajustada, verifica la fuente del IPC, por ejemplo el BCRP o el INEI).

## Reglas de cálculo
- El gasto se calcula siempre con la regla aprobada en el Hilo 1 (sin doble conteo).
- Toda tabla debe cuadrar con el gasto total: la suma por proveedor, por categoría, por comprador y por sede = total del periodo.
- Compradores: en las salidas que queden en el repositorio o que se compartan, usar códigos (C01, C02…). La tabla de equivalencias nombre → código se guarda solo en Drive.

## Salidas
- Una tabla por análisis en Parquet (para el Hilo 7) y un `resultados_descriptivos.xlsx` en `salida/` de Drive, con una hoja por análisis y una hoja "Control" con los cuadres de totales.
- 3 a 5 gráficos de verificación (Pareto de proveedores, gasto por categoría, tendencia anual, mapa de calor comprador × categoría). Son para revisar resultados; el diseño final va en el Hilo 7.
- Un resumen en lenguaje sencillo con los 5–8 hallazgos principales, cada uno con su cifra y la tabla de donde sale.

## Pruebas (pytest)
1. Cuadre: cada tabla suma el gasto total del periodo.
2. ABC: los cortes respetan los parámetros; cambiar el parámetro cambia la clasificación.
3. Con la muestra de 28 filas: 14 proveedores, 23 OC, gasto S/ 2 454 438.56 (o el valor que dé la regla del Hilo 1 para la muestra).
4. Filtrar por un semestre da el mismo resultado que calcular con solo las filas de ese semestre.
5. Ejecutar dos veces da el mismo resultado.

## Entregables
1. `scripts/analizar.py` y pruebas en `tests/`.
2. `docs/indicadores.md`: definición y fórmula de cada indicador (Pareto, ABC, ticket, HHI, especialización).
3. En Drive (`salida/`): `resultados_descriptivos.xlsx`, tablas Parquet y gráficos.
4. Actualiza `docs/bitacora.md` con decisiones, cifras oficiales y hallazgos.

## Reglas
- No subas data real ni nombres de personas al repositorio.
- Los números salen del script; no hagas cálculos a mano.
- Si un criterio no está claro, pregúntame en vez de suponer.
- Cierra el hilo con un resumen: análisis construidos, cifras oficiales, hallazgos principales y qué necesitan los Hilos 4, 5 y 7.
