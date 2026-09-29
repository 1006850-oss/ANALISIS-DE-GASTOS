Trabajo en el repositorio `analisis-de-gastos`. Lee `PLAN.md`, `docs/bitacora.md`, `docs/reglas_negocio.md` y `docs/perfil_extracto_real.md` (si no están en tu rama, trae la rama principal o la rama donde se cerró el Hilo 1; si no la encuentras, pregúntame cuál es). Hoy desarrollamos el **Hilo 4 – Control y alertas**. Al terminar, deja el código probado, actualiza la bitácora y haz commit.

## Contexto
Soy ingeniero industrial, trabajo en educación (colegios) y enseño dirección de proyectos. Construyo un análisis de gastos de compras con el histórico 2015–2017 del ERP (103 050 filas, 23 009 OC). Adjunto el extracto real "DATA TOTAL SOLO.xlsx" (también está en la carpeta `entrada/` de Google Drive). Respóndeme en lenguaje sencillo y verifica todo sobre los datos antes de afirmarlo.

## Paso 0 – Verifica que el Hilo 1 esté cerrado
Confirma que existen `scripts/limpiar_validar.py` y sus pruebas, y que la bitácora registra la regla del **monto total de la OC** (pendiente #9): este hilo depende de ella para asignar niveles de aprobación. Ejecuta el script sobre el extracto. Si la regla no está o el script falla, DETENTE y dime qué falta. (Este hilo no necesita el Hilo 2; si la taxonomía ya existe, úsala para enriquecer las alertas.)

## Objetivo de este hilo
Construir `scripts/alertas.py`: genera alertas de control interno sobre las compras. **Una alerta es una señal para revisar, no una conclusión.** Cada alerta debe traer la evidencia necesaria para que una persona la investigue.

## Cifras de referencia (provisionales)
Calculadas en el hilo de planificación con el monto de OC = suma de "Monto facturado" de sus filas, antes de cerrar el pendiente #9. Solo son orden de magnitud:
- OC por nivel de aprobación: nivel 1 ≈ 21 718 · nivel 2 ≈ 1 135 · nivel 3 ≈ 131 · nivel 4 ≈ 13 · nivel 5 ≈ 12.
- "Empleado" = "Supervisor" (autoaprobación) en ~94 % de las OC; **en los niveles 4 y 5, en el 100 %**.
- Fraccionamiento, regla simple (mismo proveedor, 60 días, cada OC bajo el límite y la suma encima): ~7 550 ventanas en ~203 proveedores, la mayoría en el límite de S/ 35 000. **Son demasiadas para revisar**: hay que agrupar y priorizar (ver alerta 1).
- Descripciones o notas con "ADICIONAL": 1 598 filas, ~6 % del gasto total y ~9 % del gasto de CONST.

## Alertas a construir
1. **Compras fraccionadas.** Regla base de `config/parametros.yaml` (mismo proveedor, 60 días, niveles de aprobación). Para que sea útil:
   - Unir ventanas que se solapan en **un solo caso** por proveedor y periodo.
   - Proponerme criterios para **excluir falsos positivos**, por ejemplo servicios recurrentes mensuales (telefonía, internet, limpieza, vigilancia) o contratos marco, y para **subir la prioridad** cuando las OC tienen descripción similar, misma sede o mismo comprador.
   - Puntaje de prioridad (ej. monto que excede el límite × N° de OC × similitud) y ranking.
2. **Autoaprobación y segregación de funciones.** OC donde comprador = aprobador, por nivel de aprobación, comprador, monto y año. Destacar las de nivel ≥ 2 (la política exige más de un aprobador). Recordar en el reporte que la data trae un solo aprobador por OC, por lo que no se puede verificar la cadena completa.
3. **Duplicados.** Filas idénticas (291 en el perfil), misma factura (proveedor + N° normalizado) en OC distintas, y mismo proveedor + mismo monto + fechas cercanas.
4. **Ciclo OC → factura.** Meses entre "Fecha de OC" y "Periodo Factura" (el periodo es mensual, así que el ciclo se mide en meses); OC sin facturar; facturas pendientes de pago según "Estado Factura".
5. **Adicionales de obra.** % del gasto en adicionales por proveedor, sede, obra ("Clase") y año, frente al monto original. Proponme la regla de detección (palabras clave en "Descripcion", "Nota" y "Clase") y valídala con ejemplos.
6. **Coherencia del giro del proveedor.** Proveedores que facturan en categorías muy distintas entre sí (ej. una aseguradora o agencia de viajes con obra civil). Usa la taxonomía si existe; si no, "Articulo".
7. **Concentración comprador–proveedor.** Proveedores clase A donde un solo comprador maneja ≥ 90 % del gasto (referencia: ~18). Si el Hilo 3 ya lo calcula, reutilízalo.

Antes de programar, preséntame para cada alerta la regla exacta, un ejemplo real (sin nombres de personas) y cuántos casos saldrían. Ajustemos los umbrales juntos para que el número de alertas sea revisable.

## Salidas
- `alertas.xlsx` en `salida/` de Drive: una hoja resumen (N° de casos y monto por tipo de alerta y prioridad) y una hoja por tipo de alerta, ordenada por prioridad, con la evidencia (OC, fechas, montos, descripciones) y columnas vacías para la investigación: "Responsable", "Estado", "Conclusión".
- Tablas Parquet para el tablero del Hilo 7.
- Un resumen en lenguaje sencillo de los hallazgos de control, cada uno con su cifra y la advertencia de que son señales, no conclusiones.

## Pruebas (pytest)
1. Casos sembrados: un fraccionamiento, un duplicado y una autoaprobación de nivel 3 inventados → los tres se detectan.
2. Un servicio mensual recurrente sembrado → no genera alerta de fraccionamiento (o sale con prioridad baja, según la regla aprobada).
3. Cambiar la ventana de días o un límite en `parametros.yaml` cambia el resultado.
4. Con la muestra de 28 filas: detectar el caso del comprador C del 03/11/2015 (3 OC "Adicional por…" a la misma sede) si cumple la regla aprobada; si no la cumple, explicar por qué.
5. Ejecutar dos veces da el mismo resultado.

## Entregables
1. `scripts/alertas.py`, reglas y umbrales en `config/parametros.yaml` (o `config/reglas_alertas.yaml`) y pruebas en `tests/`.
2. `docs/alertas.md`: definición de cada alerta, regla, umbrales, limitaciones y cómo se investiga cada caso.
3. En Drive (`salida/`): `alertas.xlsx` y tablas Parquet.
4. Actualiza `docs/bitacora.md` con decisiones, cifras oficiales y hallazgos.

## Reglas
- No subas data real ni nombres de personas al repositorio; en los reportes, usa códigos de comprador y aprobador.
- Redacta los hallazgos con lenguaje prudente: "señal", "a revisar"; nunca "fraude" ni "irregularidad" como conclusión.
- Los números salen del script; no hagas cálculos a mano.
- Si una regla no está clara, pregúntame en vez de suponer.
- Cierra el hilo con un resumen: alertas construidas, N° de casos por tipo, hallazgos principales y qué necesita el Hilo 7.
