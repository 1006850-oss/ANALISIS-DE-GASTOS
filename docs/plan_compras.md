# Plan de compras anual (Hilo 6)

Script: `scripts/proyectar.py`. Parámetros: `config/plan_compras.yaml` (aprobados el 2026-09-30).

> **Ejercicio metodológico.** La data termina en 2017; el plan proyecta **2018**. La línea base es un punto de partida
> que se ajusta con el plan de obras y el presupuesto; no es un pronóstico confiable. El mismo script sirve con data reciente.

## Segmentación (78 unidades de compra de Kraljic)
| Segmento | Regla | Unidades | Tratamiento |
|---|---|---|---|
| Por proyecto | Infraestructura y obras + compra de terrenos | 24 | **No se proyecta**: se toma del plan de obras aprobado. Se entregan referencias históricas (hoja `Obras_referencias`). |
| Recurrente | ≥ 30 de 36 meses con gasto y CV mensual ≤ 1.0 | 11 | Gasto por sede × sedes del plan; índice estacional propio. |
| Variable | Resto de compras frecuentes | 38 | Gasto por sede × sedes del plan; índice estacional del grupo. |
| Esporádica | ≤ 12 meses con gasto | 5 | Reserva anual, sin detalle mensual. |

## Método
- **Principal: gasto por sede.** Línea base = gasto del último año ÷ sedes activas ese año × sedes del plan (54, dato del usuario) × (1 + inflación). Inflación = 0 (decisión del usuario: soles nominales).
- Sede activa = sede con gasto en "Servicios generales de sede" ese año: 41 (2015), 44 (2016), 54 (2017).
- **Comparación: tendencia lineal** (último año + variación del último año). Se muestra, pero no se usa como base: con 2 puntos supone que el crecimiento continúa igual.
- **Rango** de la línea base: ± el error absoluto de la validación hacia atrás del segmento.

## Validación hacia atrás (estimar 2017 con 2015–2016)
| Segmento | Gasto por sede (principal) | Tendencia lineal | Repetir 2016 | Error mensual promedio (principal) |
|---|---|---|---|---|
| Recurrente | −10.0 % | +0.8 % | −26.7 % | 26 % |
| Variable | −8.2 % | −0.6 % | −25.2 % | 25 % |
| Esporádica | −78 % | −66 % | −82 % | 83 % |

Lectura: el total anual se estima con un error de ~10 %; el detalle mensual, con ~25 %. Las esporádicas no son predecibles (por eso se tratan como reserva).

## Modalidad de contratación (política interna)
| Modalidad | Soles (con IGV) | Dólares | Plazo (supuesto) |
|---|---|---|---|
| 1 cotización | ≤ 1 000 | ≤ 300 | 1 semana |
| 2 cotizaciones | > 1 000 y ≤ 20 000 | > 300 y ≤ 6 000 | 2 semanas |
| 3 cotizaciones | > 20 000 y ≤ 80 000 | > 6 000 y ≤ 25 000 (*) | 3 semanas |
| Licitación | > 80 000 | > 25 000 | 8 semanas (obras: 10) |

(*) La política dice "6001 < X ≤ 25000"; se asumió que cubre desde > 6 000. **Los plazos son supuestos** del asistente (pendiente #17).

El plan muestra dos modalidades por unidad: la que corresponde a la **OC típica** del último año (mediana) y la que correspondería **si se consolida** el volumen anual en un solo proceso.

## Hallazgo principal: oportunidad de consolidación
47 unidades (S/ 48.1 M de S/ 48.3 M proyectables) se compran hoy en OC pequeñas (6 550 OC en 2017, típicamente con 1 o 2 cotizaciones), pero su volumen anual corresponde a **licitación**. Ejemplos: equipamiento general (641 OC, OC típica S/ 2 450), mobiliario (324 OC), seguridad (110 OC), telecomunicaciones (166 OC). Consolidar donde tenga sentido (no, por ejemplo, alquileres de locales distintos) permite negociar mejor (cuadrante de apalancamiento) y reduce el riesgo de fraccionamiento (Hilo 4).

## Calendario de procesos
- Recurrentes: contrato anual vigente desde enero → iniciar la licitación ~8 semanas antes (noviembre del año anterior).
- Variables: listos antes del mes de mayor gasto histórico.
- Obras: según el plan de obras; referencia: terminar antes del inicio del año escolar (marzo). Meses de mayor ejecución histórica de obra civil: octubre–diciembre.

## Limitaciones
- 3 años de historia; la institución estaba en expansión (41 → 54 sedes), lo que infla cualquier tendencia.
- Obras (≈ 60 % del gasto) depende del plan de obras, no de la historia.
- Cuadrantes de Kraljic provisionales hasta el taller de expertos.
