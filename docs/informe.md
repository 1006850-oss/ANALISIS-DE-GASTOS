# Informe ejecutivo para el CEO (Hilo 7)

Decisiones del usuario (2026-09-30): formato Excel, máximo 5 hojas; lector: CEO; temas: optimización de políticas de
compras, posibles incumplimientos de políticas, compras con comportamiento anómalo y estrategias. Sin logo ni colores
institucionales.

## Estructura (`informe_ejecutivo_<periodo>.xlsx`, lo genera `scripts/generar_informe.py`)
1. **Resumen**: mensaje principal, 3 decisiones propuestas e indicadores clave.
2. **Cumplimiento y anomalías**: tabla de señales (fraccionamiento, autoaprobación, factura antes de OC, facturado > OC,
   duplicados) y los 5 casos de fraccionamiento de mayor monto.
3. **Optimizar políticas**: 7 propuestas (consolidación, proveedores ocasionales, segregación de funciones, control de
   fraccionamiento en el ERP, OC antes de la compra, tope de adicionales, rotación de compradores).
4. **Estrategias y plan**: matriz de Kraljic (provisional) y línea base del plan de compras.
5. **Alcance y límites**: alcance, límites y próximos pasos.

Cada hoja está configurada para imprimirse en una página (horizontal).

## Reglas
- **Cifras**: cada número sale de una tabla de los Hilos 3–6 mediante `calcular_cifras()`. El texto solo usa cifras
  registradas. `informe_trazabilidad.xlsx` lista cada cifra, su valor y su tabla de origen.
- **Verificación**: `verificar_informe()` comprueba que cada cifra aparezca tal cual en el informe. Si falta o fue
  alterada, el script termina con error. Hay una prueba que altera una cifra y verifica que se detecte.
- **Lenguaje**: las alertas son *señales para revisar*, nunca conclusiones ("fraude" o "irregularidad" no se usan).
- **Privacidad**: sin nombres de personas ni RUC (probado).
- **Borrador**: el texto lo redacta la IA; la persona responsable lo revisa antes de enviarlo al CEO.
