# Bitácora de hilos

## Hilo de planificación – 2026-09-25
- Se definió el orden de los 9 hilos (ver PLAN.md).
- Verificado en la muestra: gasto real S/ 2 454 438.56 (Monto facturado); suma de Monto MN S/ 5 864 650.11 (doble conteo).
- Pendiente para el Hilo 0: umbral de aprobación, ubicación del maestro/histórico, extracción real de prueba.

## Hilo 0 – Fundaciones – 2026-09-25 (cerrado)
Decisiones:
- Niveles de aprobación de OC: 5 niveles (S/ 35 000 / 250 000 / 1 000 000 / 2 000 000), con IGV, iguales para bienes, servicios y obras.
- Fraccionamiento: mismo proveedor, ventana de 60 días.
- ABC: A ≤ 80 %, B ≤ 95 %, C resto.
- Datos en Google Drive (`entrada/`, `maestro/`, `historico/`, `salida/`); la data es confidencial; al LLM solo van descripciones únicas.
- Exportación: xlsx, ~200 000 registros por semestre, 26 columnas fijas.
- Semestre según "Periodo Factura".
- "Articulo" = categoría de compra (nivel 1). "Clase" = glosa de palabras clave. "Procura" y "Concepto" se ignoran.
- Gasto = toda factura registrada, sin importar el estado de pago.
- La muestra está anonimizada/mezclada: sirve para probar cálculos, no la taxonomía. No se sube al repositorio.

Entregables: `docs/diccionario_datos.md`, `docs/reglas_negocio.md`, `config/parametros.yaml`, `docs/pendientes.md`, estructura de carpetas.

Para el Hilo 1: extracto real (xlsx), ruta de Google Drive, pendiente #1 (estado de la OC 35490).
