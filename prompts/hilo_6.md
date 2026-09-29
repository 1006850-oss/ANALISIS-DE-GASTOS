Trabajo en el repositorio `analisis-de-gastos`. Lee `PLAN.md`, `docs/bitacora.md`, `docs/reglas_negocio.md`, `docs/taxonomia.md`, `docs/indicadores.md` y `docs/estrategias_kraljic.md` (si no están en tu rama, trae la rama principal o la rama donde se cerró el Hilo 5; si no la encuentras, pregúntame cuál es). Hoy desarrollamos el **Hilo 6 – Plan de compras anual**. Al terminar, deja el código probado, actualiza la bitácora y haz commit.

## Contexto
Soy ingeniero industrial, trabajo en educación (colegios) y enseño dirección de proyectos. Construyo un análisis de gastos de compras con el histórico 2015–2017 del ERP (103 050 filas, 23 009 OC). Adjunto el extracto real "DATA TOTAL SOLO.xlsx" (también está en la carpeta `entrada/` de Google Drive). Respóndeme en lenguaje sencillo y verifica todo, incluidas las fuentes de inflación, antes de afirmarlo.

## Alcance: ejercicio metodológico
La data termina en 2017 y no hay data posterior. Por eso este plan es un **ejercicio para diseñar y probar el método**: proyecta el año siguiente al histórico (2018) y se valida con la lógica del negocio, no con decisiones de compra actuales. El mismo script debe servir tal cual cuando llegue data reciente. Déjalo explícito en todas las salidas.

## Paso 0 – Verifica que los Hilos 2, 3 y 5 estén cerrados
Confirma que existen la tabla limpia y clasificada, las tablas del Hilo 3 y la matriz de Kraljic del Hilo 5. Ejecuta el flujo sobre el extracto. Si algo falta, DETENTE y dime qué falta.

## Lo que ya se sabe de la data (provisional, por "Articulo" y fecha de OC; verifícalo)
- 36 meses de historia (2015–2017). El gasto mensual varía mucho (coeficiente de variación ≈ 0.58).
- Gasto creciente: 2015 ≈ S/ 48 M, 2016 ≈ S/ 103 M, 2017 ≈ S/ 132 M.
- Estacionalidad (% del gasto por mes): pico en junio (~14 %) y un segundo semestre más alto (agosto a noviembre ~9–10 % cada mes); abril es el mes más bajo (~4 %).
- 15 artículos se compran en al menos 30 de los 36 meses y suman ~68 % del gasto, **pero incluyen "CONSTRUCCION"** (~57 % del gasto, muy irregular: CV ≈ 0.83), que depende de los proyectos aprobados y no de una demanda que se repite.
- 269 artículos aparecen en 6 meses o menos y suman ~5 % del gasto.

## Objetivo de este hilo
Construir `scripts/proyectar.py`: genera la **línea base** del plan de compras por mes y categoría, que luego las personas ajustan con el plan de obras y el presupuesto.

## Paso 1 – Segmentar antes de proyectar
Propónme cómo separar las categorías en grupos con métodos distintos y espera mi aprobación:
1. **Recurrentes y estables** (servicios, suministros, alquileres): promedio o tendencia con estacionalidad mensual.
2. **Por proyecto** (construcción, equipamiento de sedes nuevas): **no se proyectan con el histórico**. Se toman del plan de obras aprobado; el histórico solo da referencias (costo típico por tipo de obra, % de adicionales del Hilo 4, meses de mayor ejecución).
3. **Esporádicas**: un monto de reserva anual, sin detalle mensual.
Define el criterio de cada grupo (ej. meses activos, coeficiente de variación) y aplícalo sobre la taxonomía, no sobre el artículo crudo.

## Paso 2 – Métodos de la línea base
- Con solo 3 años, usa métodos simples y explicables (promedio móvil, tendencia lineal, índices estacionales). No uses modelos complejos que no se puedan justificar con 36 datos.
- Prueba cada método con **validación hacia atrás**: proyectar 2017 con 2015–2016 y medir el error (ej. MAPE) por grupo. Elige el método con menor error y explica el resultado.
- Ajuste por inflación: pregúntame si lo quiero. Si sí, usa la inflación de Lima Metropolitana publicada por el BCRP o el INEI, cita la fuente y déjala como parámetro.

## Paso 3 – Plan de compras
Para cada categoría y mes: monto de línea base, método usado, rango (mínimo–máximo), cuadrante de Kraljic y **modalidad de contratación sugerida**. Pregúntame cuáles son las modalidades de la política interna (ej. compra directa, cotización, concurso o licitación) y sus umbrales antes de asignarlas. Usa los niveles de aprobación de `config/parametros.yaml` para indicar quién aprobaría cada compra.
Agrega columnas vacías para el ajuste humano: "Monto ajustado", "Fuente del ajuste (plan de obras / presupuesto / otro)" y "Comentario".

## Paso 4 – Calendario de procesos
Con la estrategia de Kraljic y la modalidad, propón **cuándo iniciar cada proceso** (ej. licitar servicios estratégicos antes del inicio del año escolar en marzo) y cuánto dura cada modalidad. Pregúntame los plazos reales antes de asumirlos.

## Pruebas (pytest)
1. La suma de la línea base por mes = total anual por categoría (sin pérdidas ni duplicados).
2. Las categorías "por proyecto" no reciben proyección automática del histórico.
3. La validación hacia atrás reproduce el error reportado.
4. Cambiar la inflación en `parametros.yaml` cambia la línea base en la proporción esperada.
5. Ejecutar dos veces da el mismo resultado.

## Entregables
1. `scripts/proyectar.py`, parámetros (método por grupo, inflación, modalidades y plazos) en `config/parametros.yaml` y pruebas en `tests/`.
2. `docs/plan_compras.md`: método, segmentación, error de validación, supuestos y limitaciones (incluido que la data termina en 2017).
3. En Drive (`salida/`): `plan_compras.xlsx` con la línea base mensual por categoría, el calendario de procesos y las columnas de ajuste.
4. Actualiza `docs/bitacora.md` con decisiones, métodos y errores obtenidos.

## Reglas
- No subas data real ni nombres de personas al repositorio.
- Los montos salen del script; no hagas cálculos a mano.
- No presentes la línea base como un pronóstico confiable: es un punto de partida que ajustan las personas.
- Si un criterio no está claro, pregúntame en vez de suponer.
- Cierra el hilo con un resumen: segmentación aprobada, método por grupo, error de validación, supuestos y qué necesita el Hilo 7.
