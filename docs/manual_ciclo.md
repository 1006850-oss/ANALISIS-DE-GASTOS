# Manual del ciclo semestral de análisis de gastos

Guía para la persona responsable del ciclo (no necesita programar). Cada semestre se repite lo mismo en 4 semanas.

## Contenido
- Qué se necesita
- Calendario del ciclo (4 semanas)
- Paso a paso
- Puntos de parada: qué hacer
- Qué es automático y qué es humano
- Dueño del proceso, versiones y revisión anual

## Qué se necesita

| Qué | Dónde vive | Quién lo pone |
|---|---|---|
| Extracto del ERP (xlsx, 26 columnas, ~17 000 filas por semestre) | Drive › analisis de gastos › `entrada/` | Responsable de compras (TI lo exporta) |
| Maestro de categorías `maestro_categorias.xlsx` | Drive › `maestro/` | Se actualiza solo con cada validación |
| Tabla de códigos de personas `codigos_personas.xlsx` (nombre ↔ P001…) | Drive › `maestro/` (confidencial) | Se actualiza sola |
| Taller de Kraljic completado (una vez al año) | Drive › `maestro/kraljic_taller_completado.xlsx` | Expertos de compras |
| Histórico de ciclos anteriores | Drive › `historico/` | Se agrega solo; nunca se borra |
| Resultados del ciclo | Drive › `salida/AAAA-SN/` | Los genera el proceso |
| Skill `analisis-gastos-compras` | Claude Code (o claude.ai) | Se instala una vez; se actualiza cuando cambian las reglas |

## Calendario del ciclo (4 semanas)

| Semana | Actividad | Responsable | Resultado |
|---|---|---|---|
| 1 – Extracción | Exportar del ERP las OC y facturas de los últimos 3 años (mismas 26 columnas) y guardarlas en `entrada/` | Compras + TI | Extracto en Drive |
| 2 – Procesamiento y validación | Pedir a Claude "necesito el análisis de gastos del semestre AAAA-SN"; validar las descripciones nuevas si el proceso lo pide; revisar el control de calidad | Responsable del ciclo | Ciclo procesado; maestro actualizado |
| 3 – Taller de Kraljic y plan | (Una vez al año, en el ciclo S2) taller de riesgo con expertos; revisar el plan de compras del año siguiente y el calendario de licitaciones | Compras + expertos | Matriz confirmada; plan revisado |
| 4 – Presentación | Revisar el BORRADOR del informe; presentar al CEO; enviar las señales de prioridad alta a Auditoría Interna | Gerencia de compras | Decisiones y responsables |

Ciclo S1 (datos de enero a junio): semanas de julio. Ciclo S2 (julio a diciembre): semanas de enero; incluye el plan
anual y el taller de Kraljic.

## Paso a paso

1. **Guardar el extracto** en `entrada/` con un nombre que diga el periodo, por ejemplo `extracto_2026-S2.xlsx`.
2. **Abrir Claude** (Claude Code con la carpeta de Drive sincronizada) y escribir, por ejemplo:
   "Necesito el análisis de gastos del semestre 2026-S2; el extracto está en entrada/extracto_2026-S2.xlsx".
3. Claude ejecuta el orquestador. Si se detiene, explica qué falta (ver la sección siguiente). Al terminar, da un
   resumen y la lista de archivos.
4. **Revisar el control de calidad**: abrir `salida/AAAA-SN/log_ejecucion.md`. Todos los cuadres deben decir OK.
5. **Revisar el informe** `7_salidas/informe_ejecutivo_AAAA-SN.xlsx` (5 hojas). Es un BORRADOR: ajustar el texto si
   hace falta, pero **no cambiar cifras** (cada cifra está en `informe_trazabilidad.xlsx` con su tabla de origen).
6. **Tablero**: abrir `7_salidas/resultados_AAAA-SN.xlsx` (hojas `Tablero_…`) y compartirlo desde Drive solo con
   quien corresponda. Las alertas se investigan en `4_alertas/alertas.xlsx` (columnas Responsable, Estado,
   Conclusión).
7. **Comparación con el ciclo anterior**: `8_historico/comparacion_resumen.md` y el Excel de comparación.

## Puntos de parada: qué hacer

| Mensaje | Qué significa | Qué hacer |
|---|---|---|
| "Una validación BLOQUEA" | La exportación cambió (falta o se renombró una columna, no cuadran los totales) | Pedir a TI la exportación con las 26 columnas; si el ERP cambió el nombre de una columna, agregar el nombre nuevo en `mapeo_columnas` de `parametros.yaml`. Volver a pedir el ciclo (empieza de cero). |
| "Hay descripciones nuevas" | Compras que no están en el maestro | Abrir `2_clasificacion/validar_nuevas.xlsx`, marcar SI/NO en las filas obligatorias (y corregir cuando sea NO), guardar y decir a Claude "ya validé". |
| "Kraljic sin confirmar" | Falta el taller de expertos | En el ciclo S2: hacer el taller con `5_kraljic/kraljic_taller.xlsx` y entregarlo. En S1 (o si el taller no se puede hacer): decidir seguir con la propuesta provisional. |
| "No existe el maestro" | Falta `maestro_categorias.xlsx` en `maestro/` | Copiarlo desde el respaldo o el ciclo anterior. |

Cada decisión (aceptar propuestas, seguir con Kraljic provisional) queda escrita en `log_ejecucion.md`.

## Qué es automático y qué es humano

| Automático (scripts) | Humano |
|---|---|
| Limpieza, validaciones y control de totales | Exportar del ERP y corregir exportaciones con fallas |
| Clasificación con el maestro y las reglas | Validar las descripciones nuevas |
| Pareto, frecuencias, concentración, tendencias | Interpretar y decidir |
| Señales de control (fraccionamiento, autoaprobación, duplicados, ciclo OC→factura, adicionales, giro, concentración) | Investigar cada señal con los documentos y registrar la conclusión |
| Matriz de Kraljic con los puntajes disponibles | Taller de riesgo con expertos (anual) |
| Plan de compras (línea base) en S2 | Ajustar con el plan de obras y el presupuesto |
| Excel, tablero, informe (con verificación de cifras) e histórico | Revisar el borrador y presentarlo al CEO |

## Dueño del proceso, versiones y revisión anual

- **Dueño del proceso**: Jefatura de Compras (confirmado por el usuario el 2026-09-30). Responde por la ejecución del ciclo, las
  validaciones y la custodia de `maestro/` (incluye la tabla de códigos de personas, que es confidencial).
- **Versiones**:
  - Código y reglas: en el repositorio. Al cerrar cada ciclo se crea la etiqueta de git `ciclo-AAAA-SN` sobre el
    commit usado (el commit queda escrito en `log_ejecucion.md` y en `historico/indice.csv`).
  - Maestro de categorías: cada cambio deja un respaldo con fecha en `maestro/respaldos/`; la huella del maestro
    usado queda en el log del ciclo.
  - Histórico: cada ejecución se guarda como `AAAA-SN__vN`; nunca se sobrescribe.
  - Skill: cada paquete lleva `VERSION.txt` con el commit del que salió. Se vuelve a empaquetar e instalar cuando
    cambian los scripts o las reglas.
- **Revisión anual (enero, junto con la política de compras)**: niveles de aprobación, modalidades y plazos de
  contratación, umbrales de alertas (`reglas_alertas.yaml`), taxonomía, parámetros de Kraljic y el taller de riesgo.
  Todo cambio se registra en `docs/bitacora.md` con su fecha.
