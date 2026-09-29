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

### 2026-09-29 – Cierre de pendientes #7 y #8
- #7: subcarpetas `entrada/`, `maestro/`, `historico/`, `salida/` creadas en Drive.
- #8: si los estados se contradicen, manda "Estado Factura".
- #9: se resuelve en el Hilo 1 (acordado).
- Único pendiente abierto: #9.

## Hilo 1 – Carga, limpieza y validación – 2026-09-29 (cerrado)
Se desarrolló en el mismo hilo de planificación (el usuario pegó una versión anterior del prompt; se aplicaron las decisiones vigentes del repositorio).

Decisiones aprobadas por el usuario:
- **Monto total de la OC** (pendiente #9): por cada factura de la OC se suma "Monto MN" de sus filas y se toma la suma más alta. Cubre los 3 patrones del ERP (línea pagada con varias facturas, líneas iguales en una factura, total repetido).
- Nueva bandera `flag_facturado_excede_oc` (facturado > monto de OC + 5 %).
- Clasificación de validaciones: BLOQUEAN 1 (columnas), 2a (montos/fecha/N° de OC ilegibles), 3a (sin proveedor/OC/fecha), 5b (moneda extranjera sin monto en soles) y 8 (control de totales). El resto ADVIERTE; los duplicados se marcan, no se borran.

Cifras oficiales del extracto real (2015–2017):
- 103 050 filas · 23 009 OC · 1 401 proveedores (por RUC; 2 RUC aparecían con dos nombres) · 55 compradores.
- **Gasto (suma de "Monto facturado") = S/ 283 013 851.95.** Control antes/después: diferencia S/ 0.00.
- Monto total de OC (regla aprobada) = S/ 279 870 386.72. Referencia no válida: suma de "Monto MN" por fila = S/ 712 793 100.53.
- OC por nivel de aprobación: 1 = 21 702 · 2 = 1 159 · 3 = 123 · 4 = 12 · 5 = 13 (OC en dólares evaluadas con límites en dólares).
- Advertencias: 19 filas sin factura; 4 653 sin descripción; 291 filas idénticas; 7 filas con factura en más de una OC; 16 804 filas en dólares; 1 795 estados contradictorios; **1 166 OC con facturado > monto de OC + 5 % (S/ 15.9 M)**.
- Gasto por semestre (según "Periodo Factura"): 2015-S1 S/ 20.1 M · 2015-S2 S/ 24.4 M · 2016-S1 S/ 35.2 M · 2016-S2 S/ 58.3 M · 2017-S1 S/ 53.6 M · 2017-S2 S/ 83.7 M · 2018-S1 S/ 7.5 M (facturas de OC de 2017) · 2014 S/ 0.09 M.

Rendimiento (entorno en la nube; una laptop normal debería estar en el mismo orden):
- Extracto real xlsx (103 050 filas): ~10 s en total (lectura 4 s, proceso 3 s).
- Sintético 250 000 filas: csv ~11 s; xlsx ~22 s (lectura 12 s, proceso 6 s).

Pruebas: 14 pruebas con pytest, todas pasan (incluye muestra y extracto real cuando están en `data/`; si no están, esas 2 se saltan).

Para el Hilo 2: usar `tabla_limpia.parquet`; columnas de texto limpias `articulo_normalizado` (410 valores), `descripcion`, `concepto`, `nota`, `clase_glosa`.
