Trabajo en el repositorio `analisis-de-gastos`. Lee `PLAN.md` y `docs/bitacora.md` (si no están en tu rama, están en la rama `claude/zen-rubin-srjgvq`). Hoy desarrollamos el **Hilo 0 – Fundaciones**. Al terminar, deja los archivos revisados, actualiza la bitácora y haz commit.

## Contexto
Soy ingeniero industrial, trabajo en educación (colegios) y enseño dirección de proyectos. Estoy construyendo un análisis de gastos de compras que se repetirá cada semestre sobre una base de más de 100 000 registros (órdenes de compra y facturas exportadas del ERP). Adjunto una muestra de 28 filas y 26 columnas. Respóndeme en lenguaje sencillo y verifica todo sobre los datos antes de afirmarlo.

## Objetivo de este hilo
Dejar definidas y escritas las reglas del proyecto, de modo que los hilos siguientes solo programen. En este hilo NO se programan los análisis.

## Paso 1 – Hazme estas preguntas antes de escribir nada
Pregúntalas en bloques cortos, con una respuesta sugerida en cada una, y espera mis respuestas.

**A. Umbrales y política de compras**
1. ¿Cuáles son los niveles de aprobación de la política de compras (montos y quién aprueba cada nivel)?
2. ¿Los umbrales son en soles, incluyen IGV y cambian por tipo de compra (bienes, servicios, obras)?
3. ¿Qué ventana de días usamos para detectar compras fraccionadas (sugerencia: 30 días)?
4. ¿Qué corte usamos para el Pareto y la clasificación ABC (sugerencia: A = 80 %, B = 95 %)?

**B. Dónde viven los datos**
5. ¿Dónde se guardan la data real, el maestro de categorías y el histórico acumulado: Google Drive, mi computadora u otro lugar?
6. ¿La data real es confidencial? ¿Debe anonimizarse (RUC, nombres) antes de trabajarla con un LLM?

**C. La exportación del ERP**
7. ¿La exportación siempre sale con las mismas 26 columnas de la muestra y con los mismos nombres?
8. ¿En qué formato llega (xlsx, csv) y cuántos registros tiene aproximadamente por semestre?
9. ¿Puedo tener un extracto real o anonimizado de al menos un semestre para el Hilo 1?
10. ¿Cómo se define un semestre (S1 = enero–junio, S2 = julio–diciembre) y se filtra por fecha de OC o por periodo de factura?

**D. Significado de los campos dudosos**
11. ¿Qué significan "Clase", "Artículo", "Concepto" y "Procura" en el ERP?
12. ¿Qué valores puede tomar "Estado Factura" y "Estado de OC", y cuáles cuentan como gasto?
13. ¿La muestra está anonimizada? Lo pregunto porque hay incoherencias, como obra civil con concepto "Alimentos" y una aseguradora facturando obra.

## Paso 2 – Revisa la muestra
Con Python, revisa las 26 columnas: tipo de dato, vacíos, valores distintos y ejemplos. Confirma el control conocido: la suma de "Monto facturado" debe ser S/ 2 454 438.56 y la suma de "Monto MN" S/ 5 864 650.11 (doble conteo).

## Paso 3 – Entregables (en el repositorio)
1. `docs/diccionario_datos.md`: cada columna, significado, tipo, si es obligatoria y problemas detectados.
2. `docs/reglas_negocio.md`: cómo se calcula el gasto sin doble conteo, definición de fraccionamiento, criterios ABC, qué estados cuentan como gasto, definición de semestre y criterios base de Kraljic.
3. `config/parametros.yaml`: umbrales, ventana de días, cortes de Pareto, moneda y ubicación de los archivos. Cada parámetro con un comentario que explique para qué sirve.
4. Estructura de carpetas: `scripts/`, `config/`, `docs/`, `tests/datos/`, `plantillas/`, cada una con un README corto.
5. `docs/pendientes.md`: lo que quede sin respuesta y quién debe responderlo.
6. Actualiza `docs/bitacora.md` con las decisiones tomadas.

## Reglas
- No subas data real al repositorio. Sube la muestra a `tests/datos/` solo si confirmo que está anonimizada.
- Si algo no se puede verificar en los datos, dilo en vez de suponerlo.
- Cierra el hilo con un resumen: qué quedó decidido, qué quedó pendiente y qué necesita el Hilo 1.
