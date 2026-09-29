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
