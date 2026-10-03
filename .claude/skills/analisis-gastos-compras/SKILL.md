---
name: analisis-gastos-compras
description: "Ejecuta el análisis de gastos de compras (spend analysis) del semestre con el extracto del ERP: Pareto de proveedores, compras fraccionadas y otras alertas, Kraljic, plan de compras. No para teoría."
---

# Análisis de gastos de compras – ciclo semestral

Esta skill ejecuta el ciclo semestral de análisis de gastos de compras de una red de colegios:
limpieza y validación del extracto del ERP → clasificación → Pareto y análisis descriptivo → alertas de control →
matriz de Kraljic → plan de compras (ciclos S2) → Excel con tablero e informe para el CEO → histórico y comparación
con el ciclo anterior → registro del ciclo en la documentación.

Todo el cálculo lo hacen los scripts. Tu trabajo es: preparar el equipo, pedir los insumos, ejecutar el orquestador,
detenerte en los puntos de parada humanos, explicar el resultado en lenguaje sencillo y dejar el ciclo archivado.

**Rutas**: todas las rutas de esta skill (`scripts/`, `config/`, `docs/`, `plantillas/`, `requirements.txt`) son
relativas a la raíz del repositorio `analisis-de-gastos` (en el paquete ZIP para claude.ai, a la carpeta de la skill,
que tiene la misma estructura). Ejecuta los comandos desde esa raíz. En Windows usa `py` si `python` no existe.

## Reglas (por qué importan)

1. **Los números salen solo de los scripts.** No calcules, no redondees por tu cuenta, no completes cifras
   faltantes. Cita las cifras tal como aparecen en `log_ejecucion.md`, `hallazgos*.md` o `comparacion_resumen.md`.
   El informe al CEO se verifica automáticamente contra sus tablas; una cifra escrita a mano rompe esa garantía.
2. **Las alertas son señales, no conclusiones.** Nunca escribas "fraude" ni "irregularidad"; di "señal para revisar".
3. **Privacidad: no leas ni muestres nombres de personas, RUC ni descripciones de compra.** Solo lee: la salida de
   la consola de los scripts, `log_ejecucion.md`, `3_descriptivo/hallazgos.md`, `4_alertas/hallazgos_control.md`,
   `8_historico/comparacion_resumen.md` y `docs/ciclos.md` (están hechos sin esos datos). No abras con código ni
   muestres: el extracto, `tabla_*.parquet`, `reporte_calidad.xlsx`, `codigos_personas.xlsx`,
   `maestro_categorias.xlsx`, `validar_nuevas.xlsx`, `alertas.xlsx`, `resultados_*.xlsx` ni el Excel de comparación.
   Esos archivos se entregan a la persona, que los revisa ella misma. Compradores y aprobadores van con código (P001…).
4. **La data real nunca va al repositorio.** Vive en la carpeta de Drive. En git solo van código, reglas, documentación
   y `docs/ciclos.md` (cifras agregadas). No hagas `git add` de nada dentro de la carpeta de datos.
5. **Detente en los puntos de parada.** Si el orquestador termina con código 2 o 3, explica qué falta y espera a la
   persona. No uses `--aceptar-propuestas` ni `--kraljic-provisional` sin que la persona lo decida en la conversación
   (excepción: si `docs/pendientes.md` registra que la persona ya aprobó seguir con Kraljic provisional mientras no
   haya taller, úsalo y dilo). Son decisiones humanas y quedan registradas en la bitácora del ciclo.
6. **No programes ejecuciones, no compartas archivos y no hagas `git push`** sin aprobación explícita.

## Paso 0 – Preparar el equipo (la primera vez en cada laptop, y si algo falla)

```bash
pip install -r requirements.txt
python scripts/preparar_equipo.py --raiz "<carpeta 'analisis de gastos' sincronizada con Google Drive>"
```

`preparar_equipo.py` revisa Python y las librerías, guarda la ruta de la carpeta de datos en `config/local.yaml`
(propio de cada equipo, no se versiona), crea las subcarpetas `entrada/ maestro/ historico/ salida/` si faltan y
avisa si falta `maestro/maestro_categorias.xlsx` (indispensable). Si ya hay `config/local.yaml`, basta con
`python scripts/preparar_equipo.py` para revisar. Si la persona no sabe la ruta: en Windows suele ser
`G:/Mi unidad/analisis de gastos`; en Mac, `~/Library/CloudStorage/GoogleDrive-<correo>/Mi unidad/analisis de gastos`.

## Paso 1 – Pedir los insumos

Pregunta solo lo que falte:

1. **Extracto del ERP** (xlsx con las 26 columnas; ver `docs/diccionario_datos.md`). Lo ideal es que esté en
   `<raiz>/entrada/` con el periodo en el nombre (`extracto_2026-S2.xlsx`).
2. **Periodo del ciclo**: `AAAA-S1` (ene–jun) o `AAAA-S2` (jul–dic). La ventana son los 6 semestres que terminan en
   ese periodo.
3. **Taller de Kraljic**: ¿hay un `kraljic_taller.xlsx` completado? Si no, revisa `docs/pendientes.md` (#16).
4. Mira `docs/ciclos.md` para saber qué ciclos ya se corrieron.

## Paso 2 – Ejecutar el ciclo

```bash
python scripts/ejecutar_ciclo.py --entrada "<raiz>/entrada/<extracto.xlsx>" --periodo 2026-S2
```

(`--raiz` no hace falta si el Paso 0 guardó la ruta.) Tarda alrededor de un minuto con ~100 000 filas. Guarda todo en
`<raiz>/salida/<periodo>/` (`1_limpieza` a `8_historico`, `estado.json`, `log_ejecucion.md`). Al volver a ejecutarlo
con el mismo periodo **continúa desde donde quedó**; `--reiniciar` empieza de cero (necesario si cambia el extracto).
Si el extracto llega más allá del periodo pedido (por ejemplo, simular 2017-S1 con data hasta 2017-S2), agrega
`--simular-corte` y dilo en el resumen.

| Código | Significado | Qué haces |
|---|---|---|
| 0 | Ciclo completo | Paso 3 |
| 2 | Una validación BLOQUEA (p. ej., falta o cambió el nombre de una columna) | Explica cuál falla (está en la consola) y qué corregir en la exportación, o si el nombre nuevo debe agregarse a `mapeo_columnas` en `config/parametros.yaml` (con permiso de la persona). Luego `--reiniciar`. |
| 3 | Punto de parada humano | Lee "Punto de parada" en la consola o en `log_ejecucion.md` y sigue la lista de abajo. |
| 1 | Error | Muestra el mensaje y la nota del paso en `log_ejecucion.md`; no arregles la data a mano. |

Puntos de parada (código 3):

- **Descripciones nuevas**: el orquestador escribe `2_clasificacion/validar_nuevas.xlsx` con **solo** lo nuevo
  (todos los artículos nuevos y las combinaciones que suman el 80 % del gasto nuevo son obligatorias). Entrégalo a la
  persona; cuando lo devuelva completo, reanuda con `--validacion <archivo>`. Si la persona prefiere aceptar lo que
  proponen las reglas, reanuda con `--aceptar-propuestas`.
- **Kraljic sin taller**: entrega `5_kraljic/kraljic_taller.xlsx` para el taller y reanuda con `--taller <archivo>`,
  o con `--kraljic-provisional` según la regla 5.
- **No existe el maestro**: pide `maestro_categorias.xlsx` y que lo copie en `<raiz>/maestro/`.

## Paso 3 – Presentar los resultados

1. Lee `log_ejecucion.md` y confirma que todos los cuadres dicen OK. Si alguno no cuadra, dilo primero.
2. Resume en lenguaje sencillo, con las cifras copiadas de `hallazgos.md`, `hallazgos_control.md` y
   `comparacion_resumen.md`: gasto y tendencia, concentración, señales de prioridad alta, cambios frente al ciclo
   anterior y lo pendiente. Si el último año de la tendencia es parcial (ciclos S1), adviértelo: la comparación
   "primer → último año" no es de años completos (pendiente #23).
3. Indica dónde están (ya quedan en Drive): `7_salidas/informe_ejecutivo_<periodo>.xlsx` (BORRADOR para el CEO),
   `7_salidas/resultados_<periodo>.xlsx`, `4_alertas/alertas.xlsx`, `8_historico/comparacion_*.xlsx` y
   `log_ejecucion.md`.

## Paso 4 – Archivar y documentar el ciclo

```bash
python scripts/registrar_ciclo.py --periodo 2026-S2
```

Agrega la fila del ciclo a `docs/ciclos.md` (cifras de las tablas, sin nombres). Luego, si la persona está de acuerdo:
`git add docs/ciclos.md` (y, si cambió algo, `docs/pendientes.md`), `git commit -m "Ciclo 2026-S2"` y
`git tag ciclo-2026-S2`. Pregunta antes de hacer `git push`. Si quedaron decisiones abiertas (validaciones,
taller, observaciones del informe), anótalas en `docs/pendientes.md`. Los resultados se quedan en Drive.

## Referencias (léelas solo cuando las necesites)

- `docs/manual_ciclo.md` – guía del ciclo para personas que no programan (calendario de 4 semanas).
- `docs/reglas_negocio.md` – qué es gasto, total de la OC, niveles de aprobación, moneda.
- `docs/diccionario_datos.md` – las 26 columnas del extracto y sus nombres estándar.
- `docs/taxonomia.md` – categorías, subcategorías y cómo se valida el maestro.
- `docs/indicadores.md` – Pareto ABC, HHI y demás indicadores.
- `docs/alertas.md` – definición y umbrales de cada señal de control.
- `docs/estrategias_kraljic.md` – método de Kraljic, taller y estrategias por cuadrante.
- `docs/plan_compras.md` – segmentación, método y modalidades del plan anual.
- `docs/informe.md` y `docs/tablero.md` – estructura del informe y del tablero.
- `docs/pendientes.md` y `docs/ciclos.md` – decisiones abiertas y ciclos ya corridos.
- `plantillas/kraljic_taller.xlsx` – plantilla del taller de Kraljic (sin montos).

## Scripts

Solo necesitas `scripts/preparar_equipo.py`, `scripts/ejecutar_ciclo.py` y `scripts/registrar_ciclo.py`. Los demás
(`limpiar_validar.py`, `clasificar.py`, `analizar.py`, `alertas.py`, `kraljic.py`, `proyectar.py`,
`generar_excel.py`, `generar_informe.py`, `historico.py`) los usa el orquestador; cada uno tiene `--help`.
Parámetros y umbrales: `config/*.yaml`.
