# Taxonomía de compras

Versión 2026-09-29 (Hilo 2). Reglas en `config/reglas_taxonomia.yaml`; script `scripts/clasificar.py`.

## Niveles

| Nivel | Qué es | Cómo se asigna |
|---|---|---|
| 1. Categoría | 15 grupos de compra | Por **artículo** (regla o maestro validado) |
| 2. Subcategoría | 64 grupos | Por **artículo**; en Construcción, por **tipo de intervención** según "Clase" (Obra nueva, Ampliación, Mejoras y mantenimiento mayor, Obra sin tipo) |
| 3. Producto | Tipo de bien o servicio | Palabras clave en descripción + concepto + nota; si no hay coincidencia, el "Concepto" del ERP; si no hay, "Otros – subcategoría" |

Decisiones aprobadas (2026-09-29): taxonomía propia adaptada a colegios (UNSPSC opcional por categoría, pendiente de asignar y verificar en la fuente oficial); las cuentas contables forman su propia categoría y se excluyen de Kraljic; validación: 88 artículos (95 % del gasto) + muestra de 200 combinaciones (100 por peso de gasto y 100 al azar; criterio ≥ 95 % de aciertos).

## Categorías y subcategorías (gasto 2015–2017, taxonomía validada)

### Infraestructura y obras — 57.3 % del gasto
Obras nuevas, ampliaciones, mejoras mayores, materiales de construcción y permisos.

- Obra nueva: 26.21 %
- Ampliación: 20.79 %
- Obra sin tipo de intervención: 9.15 %
- Mejoras y mantenimiento mayor: 0.74 %
- Licencias, permisos y estudios: 0.20 %
- Materiales de construcción: 0.17 %

### Equipamiento y mobiliario — 7.6 % del gasto
Mobiliario escolar y de oficina, equipamiento general y especializado, vehículos y enseres.

- Equipamiento general: 4.27 %
- Mobiliario: 2.60 %
- Equipamiento especializado: 0.55 %
- Enseres y equipos menores: 0.10 %
- Vehículos: 0.04 %

### Servicios generales de sede — 6.7 % del gasto
Seguridad, limpieza, servicios públicos, mensajería, salud ocupacional, alimentación y eventos.

- Seguridad y vigilancia: 3.45 %
- Limpieza: 2.75 %
- Salud y seguridad en el trabajo: 0.19 %
- Servicios públicos y agua: 0.16 %
- Mensajería, transporte y archivo: 0.08 %
- Eventos y representación: 0.04 %
- Alimentación y atenciones: 0.02 %

### Tecnología — 5.5 % del gasto
Telecomunicaciones, software y licencias, equipos de cómputo y desarrollo de sistemas.

- Telecomunicaciones: 2.78 %
- Software y licencias: 1.75 %
- Desarrollo y soporte de sistemas: 0.79 %
- Equipos de cómputo: 0.21 %

### Inmuebles — 4.7 % del gasto
Alquiler y compra de inmuebles y terrenos, fideicomiso y tasaciones.

- Alquiler de inmuebles: 3.49 %
- Compra de terrenos: 0.81 %
- Fideicomiso y tasaciones: 0.41 %

### Cuentas contables (no gestionables por Compras) — 3.7 % del gasto
Anticipos, diferidos, EPS, gastos financieros, tributos y ajustes. Cuenta en el total; fuera de Kraljic.

- Anticipos, diferidos y provisiones: 2.92 %
- Aportes EPS: 0.43 %
- Tributos, tasas y contribuciones: 0.18 %
- Gastos financieros: 0.10 %
- Otros ajustes contables: 0.07 %

### Marketing y admisión — 3.5 % del gasto
Publicidad en medios, marketing digital, publicidad exterior, call center, activaciones y materiales de admisión.

- Publicidad en medios: 1.07 %
- Marketing digital: 0.79 %
- Materiales de admisión y captación: 0.61 %
- Call center: 0.35 %
- Agencias y diseño: 0.24 %
- Publicidad exterior y módulos: 0.17 %
- Activaciones, eventos y merchandising: 0.10 %
- Otros de marketing: 0.10 %
- Investigación de mercado: 0.04 %

### Mantenimiento — 2.9 % del gasto
Mantenimiento de instalaciones, equipos y mobiliario; mejoras y reposiciones.

- Mantenimiento de instalaciones: 2.02 %
- Mejoras y reposiciones: 0.52 %
- Mantenimiento de equipos y mobiliario: 0.38 %

### Capacitación — 1.5 % del gasto
Capacitación docente, administrativa, cursos y materiales.

- Cursos y materiales de capacitación: 0.97 %
- Capacitación docente: 0.48 %
- Capacitación administrativa: 0.07 %

### Servicios profesionales — 1.3 % del gasto
Asesoría legal, contable, consultoría, auditoría, clasificación de riesgo y acreditación.

- Contable, tributaria y auditoría: 0.35 %
- Consultoría y asesoría: 0.31 %
- Legal y notarial: 0.30 %
- Otros servicios de terceros: 0.20 %
- Clasificación de riesgo y centrales: 0.10 %
- Acreditación: 0.02 %

### Viajes y movilidad — 1.3 % del gasto
Pasajes, viáticos, alojamiento, movilidad local y combustible.

- Pasajes: 0.69 %
- Movilidad local y combustible: 0.35 %
- Viáticos y alojamiento: 0.21 %

### Material educativo y programas académicos — 1.2 % del gasto
Programas SEA, material pedagógico y de laboratorio, contenidos y evaluación educativa.

- Programas SEA: 0.55 %
- Material pedagógico y de laboratorio: 0.52 %
- Contenidos y plataformas educativas: 0.12 %
- Evaluación educativa: 0.02 %

### Suministros e impresiones — 1.2 % del gasto
Suministros, útiles, impresiones y fotocopias.

- Suministros y útiles: 0.81 %
- Impresiones y fotocopias: 0.40 %

### Personal: bienestar y gestión humana — 1.1 % del gasto
Agasajos, uniformes y kits, reclutamiento y selección, clima y evaluación.

- Agasajos y bienestar: 0.56 %
- Reclutamiento y selección: 0.26 %
- Beneficios al personal: 0.14 %
- Uniformes y kits: 0.12 %
- Clima, evaluación y comunicación interna: 0.01 %

### Seguros — 0.6 % del gasto
Seguros de alumnos, patrimoniales (multirriesgo, RC) y otros.

- Seguros: 0.55 %

## Validación (2026-09-30)

- **Niveles 1 y 2 – validados por el usuario.** 88 artículos (95.1 % del gasto). Correcciones: las 4 "mejoras" pasan a Mantenimiento › Mejoras y reposiciones; "Otras cuentas por pagar" (cuotas de pólizas) a Seguros; "Inventario activo fijo" (servicio de inventario) a Servicios profesionales; "Gestión de beneficios" a Personal › Beneficios al personal. Las otras 78 propuestas las aprobó en bloque. Los 322 artículos restantes (4.9 % del gasto) quedan por regla.
- **Nivel 3 – revisión asistida por IA** (el usuario la delegó; no es validación humana):
  - Muestra 1 (200 combinaciones): 79.0 % de aciertos con las reglas iniciales. Se agregaron reglas; con ellas, 100 % en esa misma muestra (cifra optimista, porque las reglas se ajustaron con ella).
  - Muestra 2 independiente (200 combinaciones, semilla 2027): **84.5 % de aciertos** (87 % en la mitad por gasto, 82 % en la mitad al azar). Es la mejor estimación del acierto real, medida antes de los ajustes hechos con ella. Luego se corrigieron patrones sistemáticos (por ejemplo "combustible" clasificado como pasaje por contener "bus") y 8 casos puntuales en el maestro.
  - La meta de 95 % no está confirmada: se debe medir con una muestra nueva en el próximo ciclo.
- En el maestro, el origen distingue quién validó: `humano` (usuario), `llm` (revisión asistida) o la regla. **Solo las correcciones reemplazan el producto**; una confirmación no fija el producto para toda la combinación (el producto puede variar por fila según la nota).

## Maestro de categorías (Drive: `maestro/maestro_categorias.xlsx`)

- Hoja **articulos** (410 filas): artículo → categoría, subcategoría, origen (regla / humano), confianza, fecha, versión.
- Hoja **combinaciones** (22 442 filas): llave "artículo | descripción normalizada" → producto, origen (regla_palabra / concepto / subcategoria / humano / llm).
- El maestro **manda sobre las reglas**: lo validado por una persona no se vuelve a proponer.

## Mantenimiento cada ciclo

1. `python scripts/clasificar.py --tabla tabla_limpia.parquet --maestro maestro_categorias.xlsx --salida <carpeta> --generar-validacion`
2. Revisar `nuevas_para_validar.xlsx`: artículos y combinaciones que no están en el maestro (solo esos se validan).
3. Si un artículo nuevo queda "Sin clasificar", agregar una regla en `config/reglas_taxonomia.yaml` o corregirlo en la validación.
4. `python scripts/clasificar.py --aplicar-validacion validacion_taxonomia.xlsx --maestro maestro_categorias.xlsx` carga las correcciones (origen = humano).
5. Guardar el maestro con nueva fecha y versión en Drive.

## Limitaciones conocidas

- Fuera de Construcción, el producto depende todavía del "Concepto" del ERP en el 29 % del gasto; los valores con errores o marcas se limpian con la lista `conceptos` de las reglas.
- Hay unos 250 nombres de producto distintos (tras unificar variantes de escritura del "Concepto").
