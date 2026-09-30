---
name: analisis-gastos-compras
description: "Ejecuta el análisis de gastos de compras (spend analysis) del semestre con el extracto del ERP: Pareto de proveedores, compras fraccionadas y otras alertas, Kraljic, plan de compras. No para teoría."
---

# Análisis de gastos de compras – ciclo semestral

Esta skill ejecuta, con un solo comando, el ciclo semestral de análisis de gastos de compras de una red de colegios:
limpieza y validación del extracto del ERP → clasificación en la taxonomía → Pareto y análisis descriptivo →
alertas de control → matriz de Kraljic → plan de compras (ciclos S2) → Excel con tablero e informe para el CEO →
histórico y comparación con el ciclo anterior.

Todo el cálculo lo hacen los scripts de `scripts/`. Tu trabajo es: pedir los insumos, ejecutar el orquestador,
detenerte en los puntos de parada humanos, explicar el resultado en lenguaje sencillo y entregar los archivos.

## Reglas (por qué importan)

1. **Los números salen solo de los scripts.** No calcules, no redondees por tu cuenta, no completes cifras
   faltantes. Cita las cifras tal como aparecen en `log_ejecucion.md`, `hallazgos*.md` o `comparacion_resumen.md`.
   El informe al CEO se verifica automáticamente contra sus tablas; una cifra escrita a mano rompe esa garantía.
2. **Las alertas son señales, no conclusiones.** Nunca escribas "fraude" ni "irregularidad"; di "señal para revisar".
3. **Privacidad: no leas ni muestres nombres de personas, RUC ni descripciones de compra.** Solo lee estos archivos:
   la salida de la consola del orquestador, `log_ejecucion.md`, `3_descriptivo/hallazgos.md`,
   `4_alertas/hallazgos_control.md` y `8_historico/comparacion_resumen.md` (están hechos sin esos datos). No abras
   con código ni muestres el contenido de: el extracto, `tabla_*.parquet`, `reporte_calidad.xlsx`,
   `codigos_personas.xlsx`, `maestro_categorias.xlsx`, `validar_nuevas.xlsx`, `alertas.xlsx`, `resultados_*.xlsx`
   ni el Excel de comparación. Esos archivos se entregan a la persona, que los revisa ella misma.
   Compradores y aprobadores aparecen como códigos (P001…).
4. **Detente en los puntos de parada.** Si el orquestador termina con código 2 o 3, explica qué falta y espera a la
   persona. No uses `--aceptar-propuestas` ni `--kraljic-provisional` sin que la persona lo decida explícitamente
   en la conversación: son decisiones humanas y quedan registradas en la bitácora.
5. **No programes ejecuciones ni compartas archivos** sin aprobación explícita.

## Paso 1 – Pedir los insumos

Pregunta solo lo que falte:

1. **Extracto del ERP** (xlsx con las 26 columnas; ver `references/diccionario_datos.md`).
2. **Periodo del ciclo**: `AAAA-S1` (ene–jun) o `AAAA-S2` (jul–dic). La ventana de análisis son los 6 semestres
   que terminan en ese periodo.
3. **Carpeta raíz de datos** (la carpeta "analisis de gastos" de Google Drive, sincronizada con Drive para
   escritorio). Debe tener `maestro/maestro_categorias.xlsx`; `maestro/codigos_personas.xlsx` y `historico/`
   se crean o actualizan solos. Si no hay carpeta sincronizada (claude.ai), crea una carpeta de trabajo, pide a la
   persona que suba el maestro, el archivo de códigos y la carpeta `historico/` del ciclo anterior (como ZIP), y
   descomprímelos allí.
4. **Taller de Kraljic**: ¿hay un `kraljic_taller.xlsx` completado por los expertos? Si no, el ciclo se detendrá en
   Kraljic y la persona decidirá.
5. Si la carpeta raíz tiene su propio `parametros.yaml`, úsalo con `--parametros` (manda sobre el de la skill).

## Paso 2 – Preparar el entorno (una vez por sesión)

```bash
pip install -r requirements.txt   # pandas, numpy, openpyxl, pyarrow, pyyaml, matplotlib, python-calamine
```

Si no hay red para instalar, revisa con `python -c "import pandas, openpyxl, pyarrow, yaml, matplotlib"`;
`python-calamine` es opcional (solo acelera la lectura).

## Paso 3 – Ejecutar el ciclo

```bash
python scripts/ejecutar_ciclo.py --entrada <extracto.xlsx> --periodo 2026-S2 --raiz <carpeta raíz>
```

Tarda alrededor de un minuto con ~100 000 filas. Guarda todo en `<raiz>/salida/<periodo>/` (carpetas `1_limpieza`
a `8_historico`, `estado.json` y `log_ejecucion.md`). Al volver a ejecutarlo con el mismo periodo **continúa desde
donde quedó**. `--reiniciar` empieza de cero (necesario si cambia el extracto).

Códigos de salida y qué hacer:

| Código | Significado | Qué haces |
|---|---|---|
| 0 | Ciclo completo | Paso 4 |
| 2 | Una validación BLOQUEA (p. ej., falta o cambió el nombre de una columna) | Explica cuál validación falla (está en la consola) y qué corregir en la exportación, o si el nombre nuevo de la columna debe agregarse a `mapeo_columnas` en `parametros.yaml`. Luego `--reiniciar`. |
| 3 | Punto de parada humano | Lee "Punto de parada" en la consola o en `log_ejecucion.md` y sigue la tabla de abajo. |
| 1 | Error | Muestra el mensaje y la nota del paso en `log_ejecucion.md`; no intentes arreglar la data a mano. |

Puntos de parada (código 3):

- **Descripciones nuevas** (paso 2): hay artículos o combinaciones que no están en el maestro. El orquestador
  escribe `2_clasificacion/validar_nuevas.xlsx` con **solo** lo nuevo (todos los artículos nuevos y las
  combinaciones que suman el 80 % del gasto nuevo son obligatorias). Entrégaselo a la persona; cuando lo
  devuelva completo, reanuda con `--validacion <archivo>`. Si la persona prefiere aceptar lo que proponen las
  reglas, reanuda con `--aceptar-propuestas`.
- **Kraljic sin taller** (paso 5): entrega `5_kraljic/kraljic_taller.xlsx` para el taller de expertos y reanuda con
  `--taller <archivo completado>`; o, si la persona lo decide, con `--kraljic-provisional` (los cuadrantes quedan
  marcados como propuesta de IA).
- **No existe el maestro**: pide `maestro_categorias.xlsx` (vive en Drive, no en la skill).

## Paso 4 – Presentar los resultados

1. Lee `log_ejecucion.md` y confirma que todos los cuadres dicen OK (gasto limpio = clasificado = analizado + fuera
   de la ventana; sumas de tablas OK; cifras del informe verificadas). Si alguno no cuadra, dilo primero.
2. Resume en lenguaje sencillo, con las cifras copiadas de `hallazgos.md`, `hallazgos_control.md` y
   `comparacion_resumen.md`: gasto y su tendencia, concentración (Pareto), señales de prioridad alta, cambios frente
   al ciclo anterior y lo que queda pendiente (validaciones, taller de Kraljic).
3. Entrega (o indica la ruta de) estos archivos:
   `7_salidas/informe_ejecutivo_<periodo>.xlsx` (5 hojas para el CEO, BORRADOR para revisión),
   `7_salidas/resultados_<periodo>.xlsx` (tablero y detalle), `4_alertas/alertas.xlsx` (casos para investigar),
   `8_historico/comparacion_*.xlsx` y `log_ejecucion.md`.
4. Recuerda que los resultados viven en Drive y no se suben a ningún repositorio. En claude.ai, pide a la persona
   que descargue `salida/<periodo>/`, `historico/` y `maestro/` y los guarde en su Drive.

## Referencias (léelas solo cuando las necesites)

- `references/manual_ciclo.md` – guía del ciclo semestral para personas que no programan (calendario de 4 semanas).
- `references/reglas_negocio.md` – qué es gasto, total de la OC, niveles de aprobación, moneda.
- `references/diccionario_datos.md` – las 26 columnas del extracto y sus nombres estándar.
- `references/taxonomia.md` – categorías, subcategorías y cómo se valida el maestro.
- `references/indicadores.md` – Pareto ABC, HHI y demás indicadores.
- `references/alertas.md` – definición y umbrales de cada señal de control.
- `references/estrategias_kraljic.md` – método de Kraljic, taller y estrategias por cuadrante.
- `references/plan_compras.md` – segmentación, método y modalidades del plan anual.
- `references/informe.md` y `references/tablero.md` – estructura del informe y del tablero en Excel.
- `assets/kraljic_taller.xlsx` – plantilla del taller de Kraljic (sin montos).

## Scripts

`scripts/ejecutar_ciclo.py` es el único que necesitas llamar. Los demás (`limpiar_validar.py`, `clasificar.py`,
`analizar.py`, `alertas.py`, `kraljic.py`, `proyectar.py`, `generar_excel.py`, `generar_informe.py`,
`historico.py`) los usa el orquestador; cada uno tiene `--help` si la persona pide rehacer un solo paso.
Parámetros y umbrales: `config/*.yaml` (versión en `VERSION.txt`).
