Trabajo en el repositorio `analisis-de-gastos`. Lee `PLAN.md`, `docs/bitacora.md`, `docs/reglas_negocio.md`, `docs/indicadores.md`, `docs/alertas.md`, `docs/estrategias_kraljic.md` y `docs/plan_compras.md` (si no están en tu rama, trae la rama principal o la rama donde se cerró el Hilo 6; si no la encuentras, pregúntame cuál es). Hoy desarrollamos el **Hilo 7 – Salidas: Excel, tablero e informe**. Al terminar, deja el código probado, actualiza la bitácora y haz commit.

## Contexto
Soy ingeniero industrial, trabajo en educación (colegios) y enseño dirección de proyectos. Construyo un análisis de gastos de compras con el histórico 2015–2017 del ERP (103 050 filas, 23 009 OC). Adjunto el extracto real "DATA TOTAL SOLO.xlsx" (también está en la carpeta `entrada/` de Google Drive). Los lectores finales son la dirección y las gerencias: necesitan entender los resultados sin explicación adicional. Respóndeme en lenguaje sencillo y verifica todo antes de afirmarlo.

## Paso 0 – Verifica que los Hilos 3 a 6 estén cerrados
Confirma que existen `scripts/analizar.py`, `scripts/alertas.py`, `scripts/kraljic.py`, `scripts/proyectar.py` y sus tablas de salida. Ejecuta el flujo completo sobre el extracto. Si algo falta o falla, DETENTE y dime qué falta.

## Objetivo de este hilo
Convertir los resultados de los Hilos 3 a 6 en tres salidas que se regeneran solas en cada ciclo: **Excel de resultados**, **modelo de datos para el tablero** e **informe ejecutivo**. En este hilo NO se recalculan indicadores: se leen las tablas que ya producen los scripts.

## Paso 1 – Preguntas antes de diseñar
Hazme estas preguntas y espera mis respuestas:
1. ¿Tengo Power BI Desktop? ¿La institución tiene licencias para publicar y compartir tableros (Power BI Pro o equivalente), o el tablero se comparte como archivo? Si no hay Power BI, ¿uso Excel como tablero?
2. ¿En qué formato quiero el informe ejecutivo (Word, PDF, presentación) y cuántas páginas como máximo?
3. ¿Quiénes lo leerán y qué decisiones deben tomar con él?
4. ¿Hay colores o logotipo institucional que deba usar?

## Paso 2 – Excel de resultados (`scripts/generar_excel.py`)
- Un solo archivo por ciclo, `resultados_AAAA-SN.xlsx`, en `salida/` de Drive.
- Hojas: Portada (periodo, fecha, versión de reglas y del maestro), Resumen ejecutivo (5–8 indicadores clave), Pareto/ABC, Frecuencia, Gasto por categoría, Cruces comprador, Sedes, Alertas (resumen), Kraljic, Plan de compras, Control de calidad (cuadres y advertencias del Hilo 1) y Glosario.
- Formato legible: encabezados fijos, filtros, montos en S/ con separador de miles, porcentajes con un decimal, notas de fuente en cada hoja.
- Compradores y aprobadores con códigos; la tabla de equivalencias queda solo en Drive.

## Paso 3 – Modelo de datos para el tablero
- Diseña un modelo en estrella: una tabla de hechos (líneas de gasto) y dimensiones (fecha, proveedor, categoría, comprador, sede, departamento), más las tablas de alertas, Kraljic y plan.
- Exporta las tablas a una carpeta fija en Drive (`salida/tablero/`) en un formato que Power BI lea directamente (verifica qué conectores tiene Power BI para Parquet, CSV y Excel, y elige el más simple de mantener).
- `docs/tablero.md`: diseño de páginas (Resumen, Proveedores, Categorías, Control, Kraljic, Plan), medidas principales con su fórmula y **pasos para conectar y actualizar** el tablero cada semestre, escritos para alguien que no programa.
- Si no hay Power BI, arma el tablero en Excel (tablas dinámicas y gráficos) con el mismo diseño de páginas.

## Paso 4 – Informe ejecutivo
- Plantilla con secciones fijas: contexto y alcance, gasto total y tendencia, concentración de proveedores, categorías principales, hallazgos de control (como señales, no conclusiones), matriz de Kraljic y estrategias, plan de compras (como línea base), recomendaciones y limitaciones de la data.
- El LLM redacta el borrador **solo con cifras tomadas de las tablas**; cada cifra del texto debe poder rastrearse a una hoja del Excel. Agrega una verificación automática que compare las cifras del informe con las tablas.
- Todo lo que viene del LLM se marca como borrador para revisión humana.

## Paso 5 – Gráficos
Diseña 6–10 gráficos claros y consistentes (Pareto, tendencia, gasto por categoría, mapa de calor comprador × categoría, matriz de Kraljic, alertas por tipo, línea base del plan). Usa la skill de visualización de datos si está disponible. Cada gráfico con título que diga el hallazgo (no solo el tema), fuente y periodo.

## Pruebas (pytest)
1. Cada hoja del Excel se genera y sus totales cuadran con las tablas de origen.
2. Las tablas del modelo tienen las llaves correctas (sin huérfanos entre hechos y dimensiones).
3. La verificación de cifras detecta un número alterado a propósito en el informe.
4. Ningún archivo de salida del repositorio contiene nombres de personas ni RUC.
5. Ejecutar dos veces da el mismo resultado.

## Entregables
1. `scripts/generar_excel.py`, `scripts/generar_informe.py` (o equivalente) y pruebas en `tests/`.
2. `plantillas/` con la plantilla del informe y, si aplica, la del tablero.
3. `docs/tablero.md` y `docs/informe.md` (estructura y cómo se revisa).
4. En Drive (`salida/`): Excel de resultados, tablas del tablero, gráficos y borrador del informe.
5. Actualiza `docs/bitacora.md`.

## Reglas
- No subas data real ni nombres de personas al repositorio.
- No recalcules indicadores: léelos de las tablas de los hilos anteriores.
- Lenguaje prudente en hallazgos de control y en el plan de compras.
- Si una decisión de diseño no está clara, pregúntame en vez de suponer.
- Cierra el hilo con un resumen: salidas construidas, cómo se actualizan, qué revisé yo y qué necesita el Hilo 8 para automatizar todo.
