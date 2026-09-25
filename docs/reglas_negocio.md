# Reglas de negocio

Versión 2026-09-25 (Hilo 0). Los valores numéricos viven en `config/parametros.yaml`.

## 1. Gasto
- **Gasto = suma de "Monto facturado"** por fila, en soles.
- "Monto MN" es el monto de la OC y se repite en cada factura. Solo se usa contando **una vez por OC** (`es_primera_linea_oc = 1`).
- Control: en la muestra, gasto = S/ 2 454 438.56; suma ingenua de "Monto MN" = S/ 5 864 650.11 (doble conteo).
- Cuenta como gasto **toda factura registrada**, sin importar su estado de pago. El estado se conserva para el análisis del ciclo OC → factura.

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
| 5 | >2 000 000 | >600 000 | Jefe de Área, Gerente de Área, GAF, Gerencia División Soporte |

En la muestra: 11 OC en nivel 1, 10 en nivel 2, 2 en nivel 3.

## 4. Compras fraccionadas
- Grupo: OC del **mismo proveedor (RUC)** con fecha de OC dentro de **60 días**.
- Alerta cuando **cada OC del grupo está bajo un límite de aprobación y la suma del grupo lo supera** (el grupo habría requerido un nivel superior).
- Mínimo 2 OC por grupo.
- Es una **señal para revisar**, no una conclusión. Cada alerta la investiga una persona.

## 5. Pareto y ABC
- Proveedores ordenados por gasto de mayor a menor; % acumulado.
- A: hasta 80 % del gasto acumulado. B: hasta 95 %. C: el resto.

## 6. Taxonomía
- Nivel 1 (categoría) = **"Articulo"** normalizado (es la categoría de compra del ERP).
- Niveles 2 y 3 (subcategoría, producto): se construyen en el Hilo 2 a partir de "Descripcion" (y "Clase" como apoyo).
- "Concepto" y "Procura" se ignoran.

## 7. Kraljic (criterios base, se detallan en el Hilo 5)
- **Impacto financiero**: gasto y % del gasto total de la categoría (sale de la data).
- **Riesgo de suministro**: puntaje 1–5 de expertos en: N° de proveedores alternativos, criticidad para el colegio, complejidad técnica y tiempo de reemplazo. Aproximaciones desde la data: N° de proveedores por categoría e índice HHI.
- Cuadrantes: estratégico, apalancamiento, cuello de botella, no crítico.

## 8. Confidencialidad
- La data real vive en Google Drive (`entrada/`, `maestro/`, `historico/`, `salida/`), no en este repositorio.
- Los scripts procesan la data en el entorno del usuario. Al LLM solo se le envían descripciones únicas, sin RUC ni montos.
