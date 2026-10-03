# Reglas de negocio

Versión 2026-09-25 (Hilo 0). Los valores numéricos viven en `config/parametros.yaml`.

## 0. Nivel de detalle
- **Cada fila es una línea de la OC** (confirmado por el usuario, 2026-09-29), combinada con la factura que la cubre.
- Una OC puede tener varias líneas y varias facturas.

## 1. Gasto
- **Gasto = suma de "Monto facturado"** por fila, en soles.
- **"Monto MN" nunca se suma fila por fila.** El ERP lo llena de tres formas (verificado en el extracto real, Hilo 1):
  - A. Monto de la línea, repetido en cada factura que la paga (ej. una línea pagada 20 % + 80 %).
  - B. Varias líneas iguales en una sola factura (se suman).
  - C. Total de la OC repetido en cada factura (como en la muestra).
- **Monto total de la OC** (aprobado el 2026-09-29): para cada factura de la OC se suma "Monto MN" de sus filas y se toma **la suma más alta**. Cuadra con lo facturado en el 85 % de las OC totalmente facturadas (la regla "primera fila" solo en el 56 %).
- Si lo facturado en una OC supera su monto total en más de 5 %, se marca `flag_facturado_excede_oc` (1 166 OC en la data real) para revisión en el Hilo 4.
- Control: en la muestra, gasto = S/ 2 454 438.56; suma ingenua de "Monto MN" = S/ 5 864 650.11 (doble conteo).
- Cuenta como gasto **toda factura registrada**, sin importar su estado de pago. El estado se conserva para el análisis del ciclo OC → factura.
- "Estado de OC" = "Factura pendiente" significa **factura registrada pero no pagada** (confirmado por el usuario). Cuenta como gasto y se marca como pendiente de pago.
- Si "Estado de OC" y "Estado Factura" se contradicen, **manda "Estado Factura"** (decisión del usuario, 2026-09-29). En la data real hay 1 795 filas con "Factura pendiente" en la OC y "Pagado por completo" en la factura: se consideran **pagadas**. El Hilo 1 las cuenta en el reporte de calidad como advertencia informativa.
- Pendiente de pago = "Estado Factura" distinto de "Pagado por completo" ("Pendiente", "Aprobación pendiente") o sin factura.

## 2. Periodo
- Semestre: S1 = enero–junio, S2 = julio–diciembre.
- El gasto se asigna según **"Periodo Factura"**. "Fecha de OC" se usa para fraccionamiento y ciclo OC → factura.

## 3. Niveles de aprobación de OC
Montos con IGV, iguales para bienes, servicios y obras. Se evalúan con el **monto total de la OC** en su moneda (soles o dólares). El límite superior de cada nivel es inclusivo.

| Nivel | Soles | Dólares | Aprueban |
|---|---|---|---|
| 1 | hasta 35 000 | hasta 10 000 | Jefe de Área |
| 2 | >35 000 a 250 000 | >10 000 a 75 000 | Jefe de Área, Gerente de Área |
| 3 | >250 000 a 1 000 000 | >75 000 a 300 000 | + GAF |
| 4 | >1 000 000 a 2 000 000 | >300 000 a 600 000 | + Gerencia División Soporte |
| 5 | >2 000 000 | >600 000 | + CEO |

En la muestra: 11 OC en nivel 1, 10 en nivel 2, 2 en nivel 3.

El límite superior de cada nivel es inclusivo (confirmado: S/ 35 000 exactos = nivel 1).

**Supervisor:** el campo "SUPERVISOR" (en la data real, "Supervisor") es el **aprobador de la OC** (confirmado por el usuario). En la data real, el comprador ("Empleado") y el aprobador son la misma persona en el 94 % de las OC: el Hilo 4 lo reporta como **autoaprobación** (falta de segregación de funciones). La exportación trae un solo aprobador por OC, aunque la política exige varios desde el nivel 2. Por eso la data no permite verificar la cadena completa de aprobación; el Hilo 4 reportará las OC de nivel ≥ 2 y la concentración de aprobaciones por supervisor.

## 4. Compras fraccionadas
- Grupo: OC del **mismo proveedor (RUC)** con fecha de OC dentro de **60 días**.
- Alerta cuando **cada OC del grupo está bajo un límite de aprobación y la suma del grupo lo supera** (el grupo habría requerido un nivel superior).
- Mínimo 2 OC por grupo.
- Es una **señal para revisar**, no una conclusión. Cada alerta la investiga una persona.

## 5. Pareto y ABC
- Proveedores ordenados por gasto de mayor a menor; % acumulado.
- A: hasta 80 % del gasto acumulado. B: hasta 95 %. C: el resto.

## 6. Taxonomía
- Nivel 1 (categoría) = **"Articulo"** normalizado (es la categoría de compra del ERP; 414 valores en la data real).
- Niveles 2 y 3 (subcategoría, producto): se construyen en el Hilo 2 a partir de "Descripcion", con apoyo de **"Concepto"** (232 valores), **"Nota"** y "Clase".
- "Procura" solo existe en la muestra y se ignora.

## 7. Kraljic (criterios base, se detallan en el Hilo 5)
- **Impacto financiero**: gasto y % del gasto total de la categoría (sale de la data).
- **Riesgo de suministro**: puntaje 1–5 de expertos en: N° de proveedores alternativos, criticidad para el colegio, complejidad técnica y tiempo de reemplazo. Aproximaciones desde la data: N° de proveedores por categoría e índice HHI.
- Cuadrantes: estratégico, apalancamiento, cuello de botella, no crítico.

## 8. Alcance temporal
- El proyecto trabaja con el histórico **2015–2017** (103 050 filas). No se considera data posterior.
- Las facturas con periodo 2014 o 2018 que pertenecen a OC de 2015–2017 se conservan.

## 9. Confidencialidad
- La data real vive en la carpeta de Google Drive "analisis de gastos" (id `1mZsi-I-oM9YzQbtjmVRzPI7iB3LG_pXm`), con subcarpetas `entrada/`, `maestro/`, `historico/`, `salida/`. No en este repositorio.
- Los scripts procesan la data en el entorno del usuario. Al LLM solo se le envían descripciones únicas, sin RUC ni montos.
- "Empleado" y "Supervisor" son nombres reales de personas: nunca se envían al LLM y en los reportes del repositorio se usan códigos.
