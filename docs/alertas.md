# Alertas de control (Hilo 4)

Script: `scripts/alertas.py`. Reglas y umbrales: `config/reglas_alertas.yaml` (aprobados por el usuario el 2026-09-29).
Base: `tabla_clasificada.parquet` (todas las OC 2015–2017). **Cada alerta es una señal para revisar, no una conclusión.**

| # | Alerta | Regla | Prioridad |
|---|---|---|---|
| 1 | Compras fraccionadas | OC del **mismo proveedor + misma sede + misma subcategoría** emitidas dentro de 60 días; **cada OC** bajo un límite de aprobación (en soles) y **la suma** por encima. Ventanas que se solapan = un caso. No se evalúan servicios recurrentes (telecomunicaciones, seguridad, limpieza, servicios públicos, alquileres, mensajería, pasajes, viáticos, movilidad, call center, software) ni cuentas contables. El monto de cada OC es el del Hilo 1 (suma más alta por factura). | Alta: todo el caso en ≤ 7 días o varias OC el mismo día · Media: mismo comprador · Baja: resto |
| 2 | Autoaprobación | OC de **nivel ≥ 2** donde comprador = aprobador ("Supervisor"). El nivel 1 se reporta solo como estadística. | Alta: niveles 4–5 · Media: 3 · Baja: 2 |
| 3 | Duplicados | (a) filas idénticas; (b) misma factura (proveedor + N° normalizado) en varias OC; (c) posible factura duplicada: mismo proveedor, monto (≥ S/ 1 000), mes, sede y descripción, con N° de factura distinto (sin servicios recurrentes). | (b) y (c) en la misma OC: Alta · (c): Media · (a): Baja |
| 4 | Ciclo OC → factura | Meses entre fecha de OC y periodo de factura. Factura anterior a la OC; ciclo > 6 meses; OC sin facturar; facturado > monto de OC + 5 %; factura pendiente de pago ("Estado Factura"). | Factura anterior: Alta · ciclo largo, sin facturar, excede OC: Media · pendiente: Baja |
| 5 | Adicionales de obra | Producto "Adicionales de obra" (palabra "adicional" en descripción, concepto o nota, **excepto "aula(s) adicional(es)"**). Alerta por sede si ≥ 20 % del gasto en obras (sedes con ≥ S/ 500 000 en obras) y por proveedor si ≥ 10 % (≥ S/ 100 000). | Alta: el doble del umbral o más · Media: resto |
| 6 | Giro del proveedor | Categorías agrupadas en familias (física, tecnología, servicios de sede, marketing, académica, personal, viajes, profesionales, suministros, seguros). Alerta si el proveedor tiene ≥ S/ 50 000 y **≥ 20 %** en una familia distinta a la principal. | Media: ≥ 30 % · Baja: 20–30 % |
| 7 | Concentración comprador–proveedor | Proveedores clase A donde un comprador maneja ≥ 90 % del gasto (reutiliza el Hilo 3, ventana 2015-S1 a 2017-S2). | Media |

## Salidas
- `alertas.xlsx`: hoja **Resumen** (casos, monto y prioridades por tipo), **Notas**, una hoja por alerta ordenada por prioridad y monto, y **Hallazgos**. Cada hoja de casos trae las columnas vacías **Responsable, Estado, Conclusión** para la investigación.
- `tablas/*.parquet` para el tablero (Hilo 7) y `hallazgos_control.md`.

## Cómo investigar un caso
1. Revisar la evidencia de la fila (OC, fechas, montos, descripciones, comprador y aprobador con código).
2. Pedir los documentos: OC, facturas, conformidad, cotizaciones y el flujo de aprobación en el ERP.
3. Registrar en "Estado" (pendiente / en revisión / cerrado) y en "Conclusión" (justificado / hallazgo / mejora de proceso).
4. Nunca calificar un caso como irregularidad sin la revisión documental.

## Limitaciones
- La exportación trae **un solo aprobador por OC**: la autoaprobación no prueba que falten las otras firmas de la política; solo indica que el campo registrado coincide con el comprador.
- El periodo de factura es mensual: el ciclo se mide en meses, no en días.
- Fraccionamiento usa montos en soles y límites en soles también para OC en dólares.
- Las alertas dependen de la taxonomía (subcategoría, producto): pueden cambiar levemente tras la validación del Hilo 2.
