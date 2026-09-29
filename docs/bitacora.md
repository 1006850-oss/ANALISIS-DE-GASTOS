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

### Hilo 0 – respuestas a pendientes (2026-09-25)
- "Factura pendiente" = factura registrada pero no pagada (cuenta como gasto).
- Nivel 5 incluye al CEO.
- Límite superior de cada nivel es inclusivo.
- Carpeta de Drive: "analisis de gastos" (`1mZsi-I-oM9YzQbtjmVRzPI7iB3LG_pXm`), acceso verificado; está vacía.
- "SUPERVISOR" = aprobador de la OC. La data trae un solo aprobador por OC: no se puede verificar la cadena completa de aprobación.
- Pendiente: extracto real.

### 2026-09-29 – Extracto real
- El usuario subió "DATA TOTAL SOLO.xlsx" (13.6 MB) a la carpeta de Drive del proyecto. Acceso verificado (metadatos); contenido aún no revisado.
- El conector de Drive devuelve el archivo completo dentro de la conversación, lo que no es viable con 13.6 MB: el Hilo 1 debe recibirlo como adjunto.

### 2026-09-29 – Perfil del extracto real (hilo de planificación)
- Revisado "DATA TOTAL SOLO.xlsx": 103 050 filas, 2015–2017, 23 009 OC, 1 403 proveedores. Detalle en `docs/perfil_extracto_real.md`.
- 4 columnas cambian de nombre respecto a la muestra → se agregó `mapeo_columnas` en parámetros.
- "Monto MN" no siempre es el total de la OC: la regla de la muestra no aplica tal cual (pendiente #9).
- Gasto por "Monto facturado" por fila: S/ 283 013 851.95 (control provisional para el Hilo 1).
- Hay OC en dólares; "Monto facturado" ya viene en soles.
- "Empleado" = "Supervisor" en el 94 % de las OC (pendiente #10).
- Nuevos pendientes: #9 a #12.

### 2026-09-29 – Respuestas a pendientes #9 a #12
- #9: cada fila es una línea de la OC. El Hilo 1 deriva la regla del monto total de la OC.
- #10: "Supervisor" es quien aprueba → autoaprobación en el 94 % de las OC (hallazgo para el Hilo 4).
- #11: "Concepto" se usa como apoyo a la taxonomía.
- #12: no hay data posterior a 2017; el proyecto trabaja con 2015–2017.
