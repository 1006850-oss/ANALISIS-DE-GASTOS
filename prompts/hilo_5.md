Trabajo en el repositorio `analisis-de-gastos`. Lee `PLAN.md`, `docs/bitacora.md`, `docs/reglas_negocio.md`, `docs/taxonomia.md` y `docs/indicadores.md` (si no están en tu rama, trae la rama principal o la rama donde se cerró el Hilo 3; si no la encuentras, pregúntame cuál es). Hoy desarrollamos el **Hilo 5 – Matriz de Kraljic**. Al terminar, deja el código probado, actualiza la bitácora y haz commit.

## Contexto
Soy ingeniero industrial, trabajo en educación (colegios) y enseño dirección de proyectos. Construyo un análisis de gastos de compras con el histórico 2015–2017 del ERP (103 050 filas, 23 009 OC). Adjunto el extracto real "DATA TOTAL SOLO.xlsx" (también está en la carpeta `entrada/` de Google Drive). Respóndeme en lenguaje sencillo y verifica todo, incluidas las fuentes metodológicas, antes de afirmarlo.

## Paso 0 – Verifica que los Hilos 2 y 3 estén cerrados
Confirma que existen `scripts/clasificar.py`, `scripts/analizar.py`, el maestro de categorías y las tablas del Hilo 3 (gasto por categoría y HHI). Ejecuta el flujo sobre el extracto. Si algo falta, DETENTE y dime qué falta.

## Base metodológica (verifícala)
- Peter Kraljic, "Purchasing Must Become Supply Management", *Harvard Business Review*, septiembre–octubre de 1983.
- Dos ejes: **impacto en el resultado** (importancia financiera de la compra) y **riesgo de suministro** (complejidad del mercado proveedor).
- Cuatro cuadrantes: **estratégico** (alto impacto, alto riesgo), **apalancamiento** (alto impacto, bajo riesgo), **cuello de botella** (bajo impacto, alto riesgo) y **no crítico** (bajo impacto, bajo riesgo).
- Advertencia: si solo se usa el gasto, la matriz refleja volumen y no importancia estratégica. El eje de riesgo necesita criterio experto.

## Lo que ya se sabe de la data (provisional, por "Articulo"; verifícalo con la taxonomía)
- **"CONSTRUCCION" es ~57 % del gasto** (227 proveedores). Si se deja como un solo punto, domina la matriz: hay que analizarla a nivel de subcategoría o producto (tipo de obra, especialidad).
- 16 artículos concentran el 80 % del gasto. De ellos, 8 tienen HHI > 2 500 (mercado muy concentrado): por ejemplo Seguridad, Servicio de limpieza, Internet, Terrenos, Alquileres.
- 143 artículos tienen un solo proveedor, pero suman solo ~3 % del gasto: posibles cuellos de botella.
- Algunos "artículos" parecen cuentas contables y no categorías de compra (ej. "ALQUILERES POR DEVENGAR MN", "GASTOS CONTRATADOS POR ANTICIPADO MN"). Usa la taxonomía del Hilo 2, no el artículo crudo.

## Objetivo de este hilo
Construir `scripts/kraljic.py` y el proceso para ubicar cada categoría, subcategoría y producto en la matriz, con una estrategia por cuadrante.

## Paso 1 – Eje de impacto (sale de la data)
Propónme el indicador y el punto de corte (ej. % del gasto total, gasto absoluto o combinación con N° de sedes que atiende). Muéstrame cómo cambia la matriz con 2 cortes distintos antes de elegir.

## Paso 2 – Eje de riesgo (data + criterio experto)
1. **Aproximaciones desde la data**: N° de proveedores activos, HHI (verifica y cita el umbral de concentración que uses, por ejemplo los de las guías de concentraciones del Departamento de Justicia y la FTC de EE. UU.), % del gasto en el proveedor principal, proveedores con una sola OC.
2. **Criterios expertos (1 a 5)**: N° de proveedores alternativos en el mercado, criticidad para la operación del colegio (¿se detienen las clases si falla?), complejidad técnica o de especificación y tiempo de reemplazo del proveedor.
3. El LLM puede proponer un puntaje inicial por criterio con su justificación, **marcado como propuesta**. Los puntajes finales se validan en un taller con expertos.
4. Proponme las ponderaciones de cada criterio y cómo combinar data + expertos en un solo puntaje de riesgo.

## Paso 3 – Plantilla para el taller de expertos
`plantillas/kraljic_taller.xlsx`: una fila por categoría o subcategoría con el gasto, los indicadores de la data, el puntaje propuesto por criterio y su justificación, columnas para el puntaje del experto y comentarios, e instrucciones de llenado en una hoja aparte. Debe servir para repetir el taller cada año.

## Paso 4 – Matriz y estrategias
1. Matriz 2×2 en 3 niveles (categoría, subcategoría, producto), con el tamaño del punto proporcional al gasto.
2. `docs/estrategias_kraljic.md`: estrategia por cuadrante (ej. alianzas y contratos de largo plazo en estratégicos; licitaciones y consolidación de volumen en apalancamiento; asegurar el suministro y buscar alternativas en cuello de botella; simplificar y automatizar en no críticos), con acciones concretas para colegios y la fuente de cada recomendación.
3. Conexión con la skill `comparativo-proveedores-construccion`: para las categorías estratégicas y de apalancamiento, indica cuándo usarla en la licitación y adjudicación.

## Pruebas (pytest)
1. Cada categoría queda en exactamente un cuadrante.
2. Cambiar el corte de impacto o una ponderación de riesgo mueve las categorías como se espera.
3. Si falta el puntaje experto, el script usa solo la data y marca el resultado como "provisional".
4. El gasto total de la matriz = gasto total del Hilo 3.
5. Ejecutar dos veces da el mismo resultado.

## Entregables
1. `scripts/kraljic.py`, parámetros (cortes y ponderaciones) en `config/parametros.yaml` y pruebas en `tests/`.
2. `plantillas/kraljic_taller.xlsx` y `docs/estrategias_kraljic.md`.
3. En Drive (`salida/`): `kraljic.xlsx` (matriz por nivel, indicadores, puntajes y cuadrante) y gráficos de la matriz.
4. Actualiza `docs/bitacora.md` con decisiones, cortes, ponderaciones y resultados.

## Reglas
- No subas data real ni nombres de personas al repositorio.
- Los montos, índices y cuadrantes salen del script; no hagas cálculos a mano.
- Distingue siempre lo que viene de la data, lo que propone el LLM y lo que validan los expertos.
- Si un criterio no está claro, pregúntame en vez de suponer.
- Cierra el hilo con un resumen: método aprobado, categorías por cuadrante, estrategias principales, qué falta validar en el taller y qué necesitan los Hilos 6 y 7.
