Trabajo en el repositorio `analisis-de-gastos`. Lee `PLAN.md`, `docs/bitacora.md` y todos los archivos de `docs/` (si no están en tu rama, trae la rama principal o la rama donde se cerró el Hilo 7; si no la encuentras, pregúntame cuál es). Hoy desarrollamos el **Hilo 8 – Integración y automatización**. Al terminar, deja el código probado, actualiza la bitácora y haz commit.

## Contexto
Soy ingeniero industrial, trabajo en educación (colegios) y enseño dirección de proyectos. Construí, bloque por bloque (Hilos 0 a 7), un análisis de gastos de compras sobre el histórico 2015–2017 del ERP (103 050 filas, 23 009 OC). Adjunto el extracto real "DATA TOTAL SOLO.xlsx" (también está en la carpeta `entrada/` de Google Drive). Ahora quiero que todo el proceso se ejecute **con un solo pedido** cada ciclo, de forma repetible y auditable. Respóndeme en lenguaje sencillo y verifica todo, incluida la documentación oficial de skills, antes de afirmarlo.

## Paso 0 – Verifica que los Hilos 1 a 7 estén cerrados
Confirma que existen y pasan sus pruebas: `limpiar_validar.py`, `clasificar.py`, `analizar.py`, `alertas.py`, `kraljic.py`, `proyectar.py`, `generar_excel.py` y el generador del informe. Ejecuta `pytest` completo. Si algo falta o falla, DETENTE y dime qué falta.

## Objetivo de este hilo
1. Un **orquestador** que ejecuta todo el flujo en orden.
2. Un **histórico acumulado** que compara ciclos.
3. Una **skill** `analisis-gastos-compras` que guía a Claude en cada ciclo semestral.
4. Una propuesta de **automatización** (programación) solo si tiene sentido.

## Paso 1 – Orquestador (`scripts/ejecutar_ciclo.py`)
- Un comando: `python scripts/ejecutar_ciclo.py --entrada <archivo> --periodo 2026-S2`.
- Orden: limpiar y validar → clasificar (listar combinaciones nuevas) → analizar → alertas → Kraljic → proyectar → Excel, tablero e informe.
- **Puntos de parada humanos**: si hay validaciones que BLOQUEAN, combinaciones nuevas sin validar, o puntajes de Kraljic sin confirmar, el orquestador se detiene, guarda el estado y explica qué falta. Al reanudar, continúa desde ese punto.
- Bitácora de ejecución por ciclo (`salida/AAAA-SN/log_ejecucion.md`): fecha, versión del código (commit), versión de parámetros y del maestro, tiempos, advertencias y cuadres.
- Todo lee rutas y umbrales de `config/parametros.yaml`.

## Paso 2 – Histórico acumulado
- Cada ciclo **agrega** sus resultados a `historico/` en Drive, sin sobrescribir (llave: periodo + versión).
- Comparación con el ciclo anterior: cambios en el Pareto (proveedores que suben o bajan de clase), categorías que crecen o caen, alertas nuevas vs. recurrentes, proveedores nuevos.
- Simula dos ciclos con el extracto (por ejemplo 2017-S1 y 2017-S2) para probar la comparación.

## Paso 3 – Skill `analisis-gastos-compras`
Usa la skill `skill-creator` si está disponible y verifica en la documentación oficial de Anthropic los requisitos vigentes (formato del `SKILL.md`, límites de `name` y `description`, estructura de carpetas, cómo se instala en claude.ai).
- **El repositorio es la única fuente de verdad**: crea `scripts/empaquetar_skill.py`, que copia los scripts, la configuración base y las referencias del repositorio a la carpeta de la skill y genera el ZIP. Así la skill nunca queda desactualizada respecto del código.
- Estructura propuesta: `SKILL.md` (flujo y reglas clave, menos de ~500 líneas), `scripts/`, `references/` (reglas de negocio, diccionario de datos, indicadores, alertas, estrategias de Kraljic, taxonomía) y `assets/` (plantillas).
- La `description` debe activarse con frases como "análisis de gastos", "spend analysis", "Pareto de proveedores", "compras fraccionadas", "Kraljic", "plan de compras", aunque no se nombre la skill.
- **Lo que cambia cada ciclo NO va dentro de la skill**: maestro de categorías, histórico, parámetros y data viven en Drive. La skill indica qué pedir al usuario al inicio.
- Reglas en el `SKILL.md`: números solo de scripts; alertas como señales; nunca enviar nombres de personas ni RUC al LLM; detenerse ante validaciones que bloquean.
- Verifica y documenta **dónde se ejecuta la skill** y sus límites: en claude.ai (subida de archivos, librerías disponibles en el entorno de ejecución de código, acceso a Drive y tamaño de archivos: un xlsx de ~14 MB puede no pasar por el conector de Drive) frente a Claude Code con la carpeta de Drive sincronizada. Recomiéndame la opción más confiable para mi caso.

## Paso 4 – Pruebas de la skill (evals)
Al menos 4 casos, ejecutados de punta a punta:
1. **Ciclo normal** con el extracto: produce todas las salidas y los cuadres coinciden con las cifras oficiales de la bitácora.
2. **Columna renombrada o faltante**: se detiene y explica.
3. **Descripciones nuevas**: pide validar solo esas y luego continúa.
4. **Frase natural** ("necesito el análisis de gastos del semestre") activa la skill sin nombrarla.
Registra los resultados y ajusta instrucciones o `description` hasta que pasen.

## Paso 5 – Automatización (opcional, evalúala conmigo)
- Compara: (a) iniciar la skill a mano cada semestre con un recordatorio en el calendario; (b) programar la ejecución (programador de tareas de Windows, Power Automate o una rutina programada en la nube).
- Considera frecuencia semestral, confidencialidad de la data, dónde vive el archivo del ERP y quién revisa los puntos de parada humanos.
- Recomiéndame una opción con sus pasos; no la configures sin mi aprobación.

## Paso 6 – Documentación y gobernanza
- `docs/manual_ciclo.md`: guía paso a paso de un ciclo semestral para alguien que no programa (qué subir, qué validar, qué revisar, cómo publicar el tablero), con el calendario sugerido (semana 1 extracción, semana 2 procesamiento y validación, semana 3 taller de Kraljic y plan, semana 4 presentación).
- Dueño del proceso, versionado (etiqueta de git por ciclo, versión del maestro) y revisión anual de reglas junto con la política de compras.
- Actualiza `PLAN.md` marcando todos los hilos como cerrados.

## Entregables
1. `scripts/ejecutar_ciclo.py`, `scripts/empaquetar_skill.py` y pruebas en `tests/`.
2. Carpeta `skill/analisis-gastos-compras/` y el ZIP listo para instalar.
3. `docs/manual_ciclo.md`, `docs/skill.md` (cómo se instala, actualiza y dónde se ejecuta) y resultados de los evals.
4. En Drive: `historico/` con los ciclos simulados y `salida/AAAA-SN/` con un ciclo completo.
5. Actualiza `docs/bitacora.md` y `PLAN.md`.

## Reglas
- No subas data real ni nombres de personas al repositorio ni a la skill.
- No dupliques lógica: la skill usa los mismos scripts del repositorio.
- Los números salen de los scripts; no hagas cálculos a mano.
- No configures ninguna ejecución programada ni compartas archivos sin mi aprobación.
- Si una decisión no está clara, pregúntame en vez de suponer.
- Cierra el hilo con un resumen: cómo se ejecuta un ciclo, qué es automático y qué es humano, resultados de los evals, cómo instalar la skill y la recomendación de automatización.
