# scripts

Código Python del proceso. Cada hilo agrega su script (ver `PLAN.md`).

## Hilo 1 – `limpiar_validar.py`

```bash
pip install -r requirements.txt
python scripts/limpiar_validar.py --entrada "DATA TOTAL SOLO.xlsx" --periodo 2017-S2 --salida <carpeta>
```

- Lee xlsx o csv. Sin `--salida`, escribe en `<raiz_datos>/salida/<periodo>` (si `raiz_datos` de `config/parametros.yaml` existe) o en `salida/<periodo>` dentro del repositorio (carpeta ignorada por git).
- Salidas: `tabla_limpia.parquet` y `reporte_calidad.xlsx`.
- Código de salida 2 = una validación BLOQUEA (no se genera la tabla limpia; revisar el reporte).

Pruebas: `python -m pytest -q tests` (para incluir la muestra y el extracto real, copiarlos como `data/muestra.xlsx` y `data/extracto.xlsx`; `data/` no se sube al repositorio).

## Hilo 2 – `clasificar.py`

```bash
python scripts/clasificar.py --tabla <tabla_limpia.parquet> --salida <carpeta> \
       [--maestro maestro_categorias.xlsx] [--construir-maestro] [--generar-validacion]
python scripts/clasificar.py --aplicar-validacion validacion_taxonomia.xlsx --maestro maestro_categorias.xlsx
```

Salidas: `tabla_clasificada.parquet`, `resumen_clasificacion.xlsx`, `nuevas_para_validar.xlsx` y, según opciones,
`maestro_propuesto.xlsx` y `validacion_taxonomia.xlsx`. Reglas editables en `config/reglas_taxonomia.yaml`.

## Hilo 3 – `analizar.py`

```bash
python scripts/analizar.py --tabla <tabla_clasificada.parquet> --salida <carpeta> [--desde 2015-S1 --hasta 2017-S2]
```

Salidas: `tablas/*.parquet` (una por análisis), `resultados_descriptivos.xlsx` (hoja "Control" + una hoja por análisis),
`graficos/*.png` y `hallazgos.md`. Devuelve código 1 si alguna tabla no cuadra con el total.

## Hilo 4 – `alertas.py`

```bash
python scripts/alertas.py --tabla <tabla_clasificada.parquet> --salida <carpeta>
```

Salidas: `alertas.xlsx` (Resumen + una hoja por alerta con columnas para la investigación), `tablas/*.parquet`,
`hallazgos_control.md`. Reglas y umbrales en `config/reglas_alertas.yaml`.

## Hilo 5 – `kraljic.py`

```bash
python scripts/kraljic.py --tabla <tabla_clasificada.parquet> --salida <carpeta> [--taller kraljic_taller.xlsx] \
       [--plantilla-repo plantillas/kraljic_taller.xlsx]
```

Salidas: `kraljic.xlsx` (Resumen, Unidades, Categorías, Productos, Estrategias), `kraljic_taller.xlsx` (para los expertos),
`tablas/kraljic_*.parquet` y `graficos/kraljic_*.png`. Parámetros y propuesta de IA en `config/kraljic.yaml`.

## Hilo 6 – `proyectar.py`

```bash
python scripts/proyectar.py --tabla <tabla_clasificada.parquet> --kraljic <tablas/kraljic_unidades.parquet> --salida <carpeta>
```

Salida: `plan_compras.xlsx` (Notas, Plan_anual, Plan_mensual, Calendario_procesos, Obras_referencias, Validacion_atras,
Segmentos, Sedes_activas) y `tablas/plan_*.parquet`. Parámetros en `config/plan_compras.yaml`.
