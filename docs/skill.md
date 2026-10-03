# Skill `analisis-gastos-compras`: instalación, actualización y dónde se ejecuta

## Contenido
- Qué es y de dónde sale
- Requisitos oficiales verificados
- Dónde ejecutarla: Claude Code vs. claude.ai
- Instalación en una laptop (desde cero)
- Actualización
- Automatización: opciones y recomendación

## Qué es y de dónde sale

La skill guía a Claude en el ciclo semestral: pide los insumos, ejecuta `scripts/ejecutar_ciclo.py`, se detiene en los
puntos de parada humanos y resume los resultados sin leer nombres de personas ni RUC.

**El repositorio es la única fuente de verdad.** La skill vive en `.claude/skills/analisis-gastos-compras/SKILL.md`
y usa directamente los scripts (`scripts/`), la configuración (`config/`) y las referencias (`docs/`) del repositorio:
no hay copias del código. Claude Code la carga sola al abrir el repositorio (skill de proyecto, compartida por git;
ver [Skills en Claude Code](https://code.claude.com/docs/en/skills)). Una prueba (`tests/test_skill.py`) verifica
que todas las rutas que cita el `SKILL.md` existan en el repositorio.

Solo para claude.ai (opcional) se arma un ZIP con la misma estructura de carpetas:

```bash
python scripts/empaquetar_skill.py          # → dist/analisis-gastos-compras.zip (dist/ no se versiona)
```

Lo que cambia en cada ciclo **no va en la skill**: el maestro de categorías, la tabla de códigos de personas, el taller
de Kraljic, el histórico, los resultados y el extracto viven en la carpeta de Drive "analisis de gastos".

## Requisitos oficiales verificados (2026-09-30)

| Requisito | Valor | Fuente |
|---|---|---|
| Campos obligatorios del `SKILL.md` | `name` y `description` (YAML al inicio) | [Agent Skills – overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) |
| `name` | máx. 64 caracteres; solo minúsculas, números y guiones; sin "anthropic" ni "claude" | misma fuente |
| `description` | máx. **1 024** caracteres según la plataforma; máx. **200** según el centro de ayuda de claude.ai; sin etiquetas XML; en tercera persona; debe decir qué hace y cuándo usarla | [overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview), [Creating custom Skills](https://support.claude.com/en/articles/12512198-creating-custom-skills), [best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) |
| Cuerpo del `SKILL.md` | menos de 500 líneas; referencias a un solo nivel de profundidad | [best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) |
| ZIP para claude.ai | la carpeta de la skill debe ser la raíz del ZIP | [Creating custom Skills](https://support.claude.com/en/articles/12512198-creating-custom-skills) |
| Instalación en claude.ai | Customize › Skills › Add; planes Pro, Max, Team y Enterprise con ejecución de código activada; cada usuario la sube por separado | mismas fuentes |
| Instalación en Claude Code | carpeta en `~/.claude/skills/` (personal) o `.claude/skills/` (proyecto) | [overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) |
| Red y paquetes | claude.ai: red completa, parcial o nula según la configuración (por defecto, solo gestores de paquetes); Claude Code: la red del equipo | [overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview), [Create and edit files](https://support.claude.com/en/articles/12111783-create-and-edit-files-with-claude) |
| Tamaño de archivos en claude.ai | chat: 500 MB por archivo ([Upload files](https://support.claude.com/en/articles/8241126-upload-files-to-claude)); el artículo de creación de archivos indica 30 MB por archivo para subidas y descargas | fuentes citadas (se contradicen; el extracto de 13.6 MB cumple ambas) |

Hay dos discrepancias entre las fuentes oficiales: el límite de la `description` y el tamaño de archivo. Se tomó el
valor más estricto. La `description` tiene 198 caracteres y el empaquetador exige 200 o menos.

## Dónde ejecutarla

| Criterio | Claude Code con Drive para escritorio (recomendado) | claude.ai (web) |
|---|---|---|
| Archivos de entrada | Se leen directo de la carpeta sincronizada de Drive | Hay que subir en cada ciclo el extracto, el maestro, los códigos y el histórico (ZIP) |
| Resultados | Quedan directamente en `salida/` e `historico/` de Drive | Hay que descargarlos y subirlos a Drive a mano (riesgo de perder el histórico) |
| Confidencialidad | Los scripts corren en la computadora; al modelo solo llegan conteos y montos agregados | El archivo completo (con nombres de personas) se sube al entorno de ejecución de claude.ai; la skill igual evita leerlos |
| Librerías | Python del equipo (`pip install -r requirements.txt`, una vez) | pandas, openpyxl, etc. del entorno; si la red está desactivada no se pueden instalar las que falten |
| Conector de Drive | No se necesita | En esta sesión, el conector de Drive solo permitió subir archivos pasando todo su contenido dentro de la instrucción. Sirve para textos cortos, no para el xlsx de 13.6 MB. No encontré un límite oficial; no se recomienda depender de él para el extracto |
| Puntos de parada | Se reanuda el mismo comando; el estado queda en Drive | Funciona, pero el estado se pierde al cerrar la conversación si no se descarga |

**Recomendación: Claude Code (aplicación de escritorio o terminal) en la computadora del responsable, con la carpeta
"analisis de gastos" sincronizada mediante Google Drive para escritorio.** Es la opción más confiable para este caso:

- el extracto es grande y confidencial;
- hay un histórico que no debe perderse;
- el ciclo se detiene para validaciones humanas y luego se reanuda.

claude.ai queda como alternativa para una revisión puntual.

Prueba hecha: la skill empaquetada se ejecutó sola (sin el repositorio ni git) con pandas 2.3. Dio las mismas cifras
oficiales que con pandas 3.0 (ver `docs/evals_skill.md`).

## Instalación en una laptop (desde cero)

**Claude Code (recomendado)**

1. Instalar: Python 3.10 o superior, Git, Claude Code y Google Drive para escritorio (sincronizando la carpeta
   "analisis de gastos").
2. Clonar el repositorio: `git clone https://github.com/1006850-oss/ANALISIS-DE-GASTOS.git` y entrar a la carpeta.
3. `pip install -r requirements.txt`
4. `python scripts/preparar_equipo.py --raiz "<ruta de la carpeta de Drive>"` (en Windows suele ser
   `G:/Mi unidad/analisis de gastos`). Guarda la ruta en `config/local.yaml` (no se versiona) y revisa que esté el
   maestro de categorías.
5. Abrir Claude Code **en la carpeta del repositorio** y pedir, por ejemplo: "necesito el análisis de gastos del
   semestre 2026-S2". La skill se activa sola; `.claude/settings.json` ya autoriza correr los scripts del ciclo y las
   pruebas sin pedir permiso cada vez.

**claude.ai (alternativa)**: `python scripts/empaquetar_skill.py` y subir `dist/analisis-gastos-compras.zip` en
Customize › Skills › Add (requiere ejecución de código activada).

## Actualización

1. Cambiar el código o las reglas **en el repositorio**, correr `python -m pytest`, actualizar `docs/bitacora.md` y
   hacer commit. En otra laptop basta `git pull`: la skill se actualiza sola.
2. Solo si se usa claude.ai: volver a empaquetar y subir el ZIP.
3. En el log de cada ciclo, "Código (commit)" muestra la versión usada; `docs/ciclos.md` registra cada ciclo.

## Automatización: opciones y decisión (Paso 5)

| Opción | Cómo sería | A favor | En contra |
|---|---|---|---|
| (a) Inicio manual con recordatorio en el calendario | Dos eventos al año (2.ª semana de enero y de julio) con el enlace a `docs/manual_ciclo.md`; la persona exporta el extracto y pide el análisis a Claude | Simple; la data no sale de la computadora ni de Drive; la persona ya está presente para las validaciones y el taller | Depende de que alguien lo inicie |
| (b1) Programador de tareas de Windows | Ejecuta `ejecutar_ciclo.py` en una fecha fija sobre el último archivo de `entrada/` | Corre solo | El extracto del ERP se exporta a mano, así que no hay archivo nuevo que procesar; igual se detiene en las validaciones; la computadora debe estar encendida |
| (b2) Power Automate | Un flujo detecta el archivo nuevo en `entrada/` y avisa, o lanza el proceso | Útil para avisar | Ejecutar Python necesita Power Automate Desktop o un servidor. Agrega licencias y mantenimiento para 2 corridas al año |
| (b3) Rutina programada en la nube (Claude) | Una sesión en la nube corre el ciclo en una fecha fija | Sin computadora encendida | La data confidencial tendría que subirse a la nube; el conector de Drive no es práctico para el xlsx de 13.6 MB; igual se detiene para validar |

**Decisión (aprobada por el usuario el 2026-09-30): (a) inicio manual con recordatorio en el calendario.**

- Con una frecuencia semestral, la automatización ahorra muy poco: el proceso completo tarda alrededor de un minuto.
- La exportación del ERP es manual.
- Todo ciclo tiene puntos de decisión humana.
- La confidencialidad favorece no mover la data.

Pasos (los hace el usuario; no se configuró ninguna ejecución programada):

1. Crear dos eventos recurrentes anuales en tu calendario (2.ª semana de enero y 2.ª semana de julio) llamados
   "Ciclo de análisis de gastos", con la lista de las 4 semanas del manual.
2. Pedir a TI que deje guardada la consulta de exportación del ERP con las 26 columnas.
3. Revisar esta decisión si el ERP permite exportar automáticamente a Drive. En ese caso, (b2) solo como aviso de
   "archivo nuevo".
