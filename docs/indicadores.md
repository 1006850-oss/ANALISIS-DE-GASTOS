# Indicadores del análisis descriptivo (Hilo 3)

Script: `scripts/analizar.py`. Base: `tabla_clasificada.parquet` (Hilo 2). Montos en **soles nominales** (sin ajuste por inflación).
Ventana: semestres de factura **2015-S1 a 2017-S2** (`config/parametros.yaml > analisis`). Las facturas de 2014 y 2018 no se muestran; la hoja "Control" reporta su monto aparte.

| Indicador | Fórmula | Tabla |
|---|---|---|
| Gasto | Σ `monto_gasto` (= "Monto facturado") | todas |
| % del gasto | gasto del elemento ÷ gasto total del periodo × 100 | todas |
| % acumulado (Pareto) | suma del % del gasto de los proveedores ordenados de mayor a menor | `pareto_proveedores` |
| Clase ABC | A si el acumulado **antes** de sumar al proveedor es < 80 % (el que cruza el 80 % es A); B si es < 95 %; C el resto. Cortes en `pareto_abc` | `pareto_proveedores`, `resumen_abc` |
| N° de OC / facturas / líneas | OC distintas / facturas normalizadas distintas / filas | `frecuencia_proveedores` |
| Ticket promedio por OC | gasto del proveedor ÷ N° de OC | `frecuencia_proveedores` |
| Ticket mediano por OC | mediana del gasto por OC del proveedor | `frecuencia_proveedores` |
| Meses activos | meses distintos con factura (o fecha de OC si no hay factura) | `frecuencia_proveedores` |
| Variación vs. periodo anterior | (gasto del periodo − gasto del periodo anterior) ÷ gasto del periodo anterior × 100; vacío si el anterior es 0 | `tendencia_*` |
| % del comprador principal | gasto del proveedor manejado por su comprador principal ÷ gasto del proveedor × 100 | `concentracion_comprador` |
| Proveedor concentrado | % del comprador principal ≥ 90 % (`umbral_concentracion_comprador`) | `concentracion_comprador` |
| Especialización del comprador | % de su gasto en su categoría principal, y HHI = Σ (participación de cada categoría)² × 10 000 | `especializacion_comprador` |
| HHI de proveedores | Σ (participación de cada proveedor en el gasto de la categoría)² × 10 000; de 0 (muy disperso) a 10 000 (un solo proveedor) | `concentracion_*` |
| % del proveedor principal | gasto del mayor proveedor de la categoría ÷ gasto de la categoría × 100 | `concentracion_*` |

Notas:
- Umbral HHI > 1 800 (`umbral_hhi_alto`): "altamente concentrado" según las Merger Guidelines 2023 del DOJ y la FTC de EE. UU. (antes 2 500, guías de 2010). Verificado en el Hilo 5. Mide la dependencia del gasto propio en pocos proveedores, no la concentración de todo el mercado.
- Compradores con código (P001…). La equivalencia con nombres está solo en `reporte_calidad.xlsx` (Drive).
- Mientras la taxonomía no esté validada (pendiente #13), las cifras por categoría, subcategoría y producto son provisionales; el resto no depende de la taxonomía.
