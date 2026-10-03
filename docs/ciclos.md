# Registro de ciclos de análisis de gastos

Una fila por ciclo ejecutado (la escribe `scripts/registrar_ciclo.py`; no editar a mano). Los resultados completos
están en Google Drive › analisis de gastos › `salida/<periodo>/` y `historico/<periodo>__v<N>/`. Cifras en soles
nominales. Las señales son para revisar, no conclusiones.

| Periodo | Histórico | Inicio | Commit | Ventana | Gasto analizado | Prov. clase A | Señales (alta) | Kraljic | Plan | Maestro | Decisiones humanas |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2017-S1 | 2017-S1__v2 | 2026-09-30 22:01 | 88965c9 | 2015-S1 a 2017-S1 | S/ 191,648,894.55 | 86 (80.1 %) | 2,652 (257) | provisional (propuesta IA) | no (S1) | huella bc565ba6c2fd | SIMULACIÓN: se usan solo las filas con factura (u OC) hasta 2017-S1 (77,926 de 103,050 filas). · Kraljic continúa con la propuesta de IA (provisional), por decisión --kraljic-provisional. |
| 2017-S2 | 2017-S2__v1 | 2026-09-30 04:52 | 97c0842 | 2015-S1 a 2017-S2 | S/ 275,378,383.86 | 81 (80.1 %) | 3,573 (312) | provisional (propuesta IA) | sí | huella bc565ba6c2fd | Kraljic continúa con la propuesta de IA (provisional), por decisión --kraljic-provisional. |
