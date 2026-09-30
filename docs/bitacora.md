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

## Hilo 2 – Taxonomía y maestro de categorías – 2026-09-29 (construido; falta validación del usuario)
Decisiones aprobadas por el usuario:
- 15 categorías; subcategoría por artículo (en Construcción, tipo de intervención según "Clase"); producto por palabras clave.
- Cuentas contables en su propia categoría: dentro del gasto total, fuera de Kraljic.
- Taxonomía propia con UNSPSC opcional.
- Validación: 88 artículos (95 % del gasto) + muestra de 200 combinaciones (100 por gasto, 100 al azar), criterio ≥ 95 %.

Hallazgos que cambiaron la propuesta inicial:
- El prefijo "GRUPO : SUBGRUPO" solo cubre 106 artículos y el 3.8 % del gasto: no sirve como jerarquía.
- 88 artículos cubren el 95 % del gasto (16 el 80 %): la validación de niveles 1 y 2 es por artículo.

Resultados (extracto 2015–2017):
- 62 reglas de artículo clasifican los 410 artículos: 0 filas sin clasificar; gasto por categoría = S/ 283 013 851.95 (cuadra).
- Confianza "media" en artículos que suman el 2.1 % del gasto.
- Gasto por categoría: Infraestructura y obras 57.8 % · Equipamiento y mobiliario 7.6 % · Servicios generales 6.7 % · Tecnología 5.5 % · Inmuebles 4.7 % · Cuentas contables 4.1 % · Marketing y admisión 3.5 % · Mantenimiento 2.4 % · Capacitación 1.5 % · Viajes 1.3 % · Material educativo 1.2 % · Suministros 1.2 % · Servicios profesionales 1.1 % · Personal 1.1 % · Seguros 0.3 %.
- Infraestructura por subcategoría: Obra nueva 45.4 % · Ampliación 36.0 % · Sin tipo 15.8 % · Mejoras 2.2 %. Por producto: Obra civil 56.1 % · Acabados 10.9 % · **Adicionales de obra 10.2 %** · Instalaciones 9.5 % · Supervisión 3.3 % · Expediente y diseño 3.1 %.
- Producto: 65.4 % del gasto por palabras clave, 31.7 % por "Concepto", 2.9 % solo subcategoría. 791 productos distintos (a consolidar).
- Corrección en el Hilo 1: se eliminan caracteres de control en los textos (impedían exportar a Excel).

Pruebas: 25 pruebas pytest (14 del Hilo 1 + 11 del Hilo 2), todas pasan.
Pendiente: validación del usuario (pendiente #13). Para los Hilos 3 y 5: usar `tabla_clasificada.parquet`; Kraljic debe excluir `excluir_de_kraljic`.

## Hilo 3 – Análisis descriptivo – 2026-09-29 (cerrado; cifras por categoría provisionales hasta validar la taxonomía)
Decisiones aprobadas por el usuario:
- Formato de las 7 salidas aprobado.
- Periodo por factura; **no se muestran 2014 ni 2018**: ventana 2015-S1 a 2017-S2. La hoja "Control" reporta lo que queda fuera (S/ 7 635 468.09).
- Tendencia en **soles nominales**.

Cifras oficiales (2015-S1 a 2017-S2; gasto analizado S/ 275 378 383.86):
- 1 399 proveedores: A = 81 (5.8 %, 80.1 % del gasto) · B = 198 (15.0 %) · C = 1 120 (5.0 %). Los 10 mayores: 49.9 %.
- 528 proveedores (38 %) con una sola OC.
- Gasto por año de factura: 2015 S/ 44.5 M · 2016 S/ 93.5 M · 2017 S/ 137.3 M (×3.1). Por semestre: 20.1 · 24.4 · 35.2 · 58.3 · 53.6 · 83.7 M.
- Categorías: Infraestructura y obras 57.4 % · Equipamiento y mobiliario 7.5 % · Servicios generales 6.9 %.
- 55 compradores; los 5 mayores manejan el 73.4 %.
- 19 proveedores clase A con un solo comprador que maneja ≥ 90 % de su gasto (S/ 35.9 M): señal para el Hilo 4.
- 85 sedes: SEDE CENTRAL 10.7 %; las 5 primeras 24.3 %.
- 22 de 59 subcategorías gestionables con HHI > 2 500 (16.1 % del gasto): insumo para Kraljic. Umbral provisional, a verificar en el Hilo 5.

Pruebas: 32 pytest (14 Hilo 1 + 11 Hilo 2 + 7 Hilo 3), todas pasan.
Para los Hilos 4, 5 y 7: tablas en `tablas/*.parquet`; Kraljic usa `concentracion_subcategoria` y excluye `excluir_de_kraljic`.

## Hilo 4 – Control y alertas – 2026-09-29 (cerrado)
Decisiones aprobadas por el usuario ("todo según la propuesta"):
- Fraccionamiento: mismo proveedor + misma sede + misma subcategoría, 60 días, sin servicios recurrentes ni cuentas contables. La regla simple daba 7 550 ventanas.
- Autoaprobación desde el nivel 2; duplicados en 3 tipos; factura anterior a la OC = prioridad alta; ciclo > 6 meses = media.
- Adicionales: umbral 20 % por sede y 10 % por proveedor. **Detección ajustada:** "adicional" excepto "aula(s) adicional(es)" (cambia el producto en la taxonomía; Hilos 2 y 3 regenerados).
- Giro: familias de categorías, umbral 20 %.

Resultados (OC 2015–2017):
- Fraccionamiento: 210 casos, 77 proveedores, S/ 21.6 M; 127 de prioridad alta. Límite superado: S/ 35 000 (190), S/ 250 000 (15), S/ 1 000 000 (5).
- Autoaprobación nivel ≥ 2: 1 209 OC, S/ 186.0 M; niveles 4–5: 25 de 25 OC.
- Duplicados: 312 casos (61 alta): 120 OC con filas idénticas, 1 factura en 2 OC, 60 posibles facturas duplicadas en la misma OC, 131 en OC distintas.
- Ciclo: 95 OC con factura anterior a la OC (S/ 1.6 M); 438 OC con ciclo > 6 meses; 10 OC sin facturar; 1 166 OC con facturado > monto + 5 %; 59 OC con facturas pendientes de pago.
- Adicionales de obra: S/ 15.2 M (9.3 % del gasto en obras); 6 sedes ≥ 20 % (Surco 5 – Atenea 61.7 %) y 11 proveedores ≥ 10 %.
- Giro: 38 proveedores. Concentración comprador–proveedor: 19 proveedores A (S/ 35.9 M).
- Muestra: el caso del 03/11/2015 (Chimbote) no cumple la regla: 3 proveedores distintos y cada OC ya es de nivel 2.

Pruebas: 39 pytest (7 nuevas del Hilo 4), todas pasan.
Para el Hilo 7: tablas en `tablas/*.parquet` y `alertas.xlsx`.

## Validación de la taxonomía – 2026-09-30 (Hilo 2 cerrado)
- Parte 1 (usuario): mejoras → Mantenimiento; "Otras cuentas por pagar" → Seguros (son cuotas de pólizas); "Inventario activo fijo" → Servicios profesionales (servicio de inventario); "Gestión de beneficios" → Personal › Beneficios al personal; INDECI, "Otros servicios" y "Asesoría terceros" se confirman. Las otras 78 propuestas, aprobadas en bloque.
- Parte 2 (delegada a revisión asistida por IA): muestra 1 = 79.0 % → reglas nuevas; muestra 2 independiente = 84.5 %; se corrigieron patrones sistemáticos y 8 casos en el maestro. 95 % pendiente de confirmar en el próximo ciclo (pendiente #15).
- Mejoras al código: nombres limpios para el "Concepto" (`conceptos` en las reglas), reglas de producto para todas las categorías (`productos_todas`), origen `llm` en el maestro y **solo las correcciones reemplazan el producto** (se detectó y corrigió un defecto que inflaba los adicionales a S/ 28.4 M; prueba de regresión agregada).
- Cifras con la taxonomía validada: Infraestructura y obras 56.9 % del gasto analizado; Mantenimiento 2.9 %; Seguros 0.55 %; Cuentas contables 3.7 %. Adicionales de obra S/ 15.1 M (9.3 % de obras), 6 sedes y 9 proveedores sobre el umbral. Fraccionamiento: 212 casos (128 alta).
- Pruebas: 40 pytest, todas pasan. Hilos 3 y 4 regenerados.

## Hilo 5 – Matriz de Kraljic – 2026-09-30 (cerrado; riesgo provisional hasta el taller)
Decisiones aprobadas por el usuario:
- Unidad: subcategorías gestionables (sin cuentas contables); Obras abierta por tipo de trabajo → 78 unidades, S/ 265.8 M.
- Impacto: unidades que suman el 80 % del gasto (16 unidades).
- Riesgo: 40 % data (HHI > 1 800, ≤ 3 proveedores, principal ≥ 50 %) + 60 % expertos (alternativas 30 %, criticidad 30 %, complejidad 20 %, reemplazo 20 %); alto si ≥ 3.0.
- Umbral HHI 1 800 (Merger Guidelines 2023 DOJ/FTC; verificado). Hilos 3 y 4 actualizados (antes 2 500).

Fuentes verificadas: Kraljic (1983), HBR 61(5):109–117; Merger Guidelines 2023. El PDF original del artículo no fue accesible (red bloqueada); los objetivos por cuadrante se tomaron de fuentes secundarias (citadas en `docs/estrategias_kraljic.md`).

Resultado provisional (propuesta de IA en las 78 unidades, marcada como tal):
- Estratégico 3 unidades (12.3 %): adicionales de obra, seguridad y vigilancia, telecomunicaciones.
- Apalancamiento 13 (68.1 %): obra civil (2.97, cerca del corte), acabados, instalaciones, equipamiento, alquileres, limpieza, mobiliario…
- Cuello de botella 9 (3.1 %): terrenos, seguros, licencias y permisos, fideicomiso, servicios públicos, acreditación…
- No crítico 53 (16.5 %).
- 10 unidades a menos de 0.25 del corte → prioridad en el taller.
- Hilo 3 con HHI 1 800: 32 de 61 subcategorías gestionables concentradas (45.2 % del gasto); con 2 500 eran 22 (16.5 %).

Pruebas: 47 pytest (7 nuevas), todas pasan.
Pendiente #16: taller de expertos. Para los Hilos 6 y 7: `tablas/kraljic_unidades.parquet` (cuadrante por unidad).
