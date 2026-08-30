# Release v2.0.0 — Seguimiento

**Estado:** En desarrollo
**Rama principal:** `main`
**Inicio:** Sprint 6

---

## Sprint 6 — Investigación y diseño del motor de diagnóstico

**Período:** previo al desarrollo

### Tareas completadas

| Tarea | Responsable | Estado |
|---|---|---|
| Revisar cómo interpretar NDVI, NDRE, SAVI y ExG para detectar necesidad de fumigación vs. fertilización | Matias Machado | Completada |
| Definir umbrales y patrones espaciales asociados a cada tipo de intervención | — | Completada |
| Documentar criterios por cultivo y estadio fenológico para el NEA | — | Completada |
| Investigar GNDVI, MSAVI y NDWI (McFeeters) como índices candidatos a implementar | — | Completada |
| Evaluar casos de uso de cada uno para el NEA | — | Completada |
| Esquema de datos de productos fitosanitarios | Matias Machado | Completada |

### Tareas pendientes / en progreso

| Tarea | Responsable | Estado |
|---|---|---|
| Investigación fumigación localizada | Zaira Rosin | En progreso |
| Investigación de productos fitosanitarios: relevar productos comerciales usados en NEA | — | Pendiente |
| Clasificar por tipo: herbicida, fungicida, insecticida, defoliante | — | Pendiente |
| Identificar el problema/causa que trata cada producto | — | Pendiente |
| Relevar dosis de referencia por hectárea y unidad | — | Pendiente |
| Definir esquema: nombre, tipo, cultivos aplicables, problema asociado, dosis de referencia y unidad | — | Pendiente |
| Relevar catálogo mínimo viable de productos para NEA | — | Pendiente |

### Problemas encontrados

_(sin problemas reportados en esta fase)_

---

## Sprint 7 — Atributos del lote, nuevos índices y tabla de productos

### Tareas completadas

| Tarea | Responsable | Estado |
|---|---|---|
| Tabla de atributos del lote / guardar info completa | Amilcar Aguirre, Celeste Martin Rodich | Completada |
| — Identificar campos faltantes en el modelo lote | — | Completada |
| — Migración para enriquecer modelo lotes (0014) | — | Completada |
| — Actualizar formulario frontend para capturar variedad, tipo de suelo y fecha de siembra | — | Completada |
| Implementación de nuevos índices | Amilcar Aguirre | Completada |
| — Agregar índice(s) nuevos seleccionados al worker GIS (NDVI, NDRE, SAVI, ExG, GNDVI) | — | Completada |
| — Actualizar band_mapping.py y lógica de selección de índice según sensor y estadio | — | Completada |
| Optimización del cálculo de índices | Matias Machado | Completada |
| — Confirmar windowed reading activo para archivos grandes | — | Completada |
| Tabla de productos fitosanitarios (implementación) | — | Completada |
| — Migración Alembic para tabla productos_fitosanitarios (0015) | — | Completada |
| — Cargar catálogo inicial con seed data (21 productos) | — | Completada |
| — Endpoint de consulta para el motor de reglas (`GET /api/v1/productos-fitosanitarios`) | — | Completada |

### Decisiones de arquitectura

| Decisión | Motivo |
|---|---|
| Reemplazar "condiciones climáticas" por `fecha_siembra` en el modelo Lote | Las condiciones climáticas cambian día a día y no son un atributo fijo del lote. La fecha de siembra es lo que el motor de diagnóstico necesita para calcular días desde siembra y determinar estadio fenológico. |
| `tipo_suelo` como enum con 7 valores NEA-relevantes | Arcilloso, franco, franco arcilloso, franco arenoso, arenoso, vertisol, otro — cubren los tipos de suelo predominantes en Chaco/Formosa/Corrientes. |
| Migrar catálogo de productos de dict Python a tabla en BD | El dict en `productos.py` funcionaba pero no permitía extensión (agregar productos, dosis, filtros). La tabla permite CRUD futuro y filtrado por causa/tipo desde la API. |
| Endpoint de productos en `/api/v1/productos-fitosanitarios` (router separado) | No podía estar bajo `/api/v1/lotes/` porque FastAPI interpretaba "productos-fitosanitarios" como un `{lote_id}` UUID. |

### Problemas encontrados

**Migración 0015 — enum duplicado con asyncpg**
Al correr la migración, `sa.Enum.create(checkfirst=True)` no funcionó correctamente con asyncpg porque SQLAlchemy importa los modelos en `env.py` y registra los enums en metadata antes de ejecutar la migración. Se resolvió usando SQL directo (`DO $$ BEGIN CREATE TYPE ... EXCEPTION WHEN duplicate_object THEN NULL; END $$`) para crear los enums, y `op.execute(CREATE TABLE ...)` para la tabla.

**Migración 0015 — bulk_insert falla con columnas enum en asyncpg**
`op.bulk_insert()` con columnas de tipo `sa.String` envía los valores como VARCHAR, pero PostgreSQL espera el tipo enum nativo. asyncpg no castea automáticamente. Se resolvió usando `op.execute()` con INSERT SQL directo y cast explícito (`::tipoproductoenum`).

---

## Sprint 8 — Motor de reglas y diagnóstico por zona

### Tareas completadas

| Tarea | Responsable | Estado |
|---|---|---|
| Implementar motor de reglas en backend | Matias Machado | Completada |
| — Crear módulo `app/diagnostico/` (engine.py, reglas.py, productos.py, forma.py, estadios.py, service.py) | — | Completada |
| — Lógica que toma zona + índice + contexto del lote y devuelve causa probable + nivel de confianza | — | Completada |
| — Asociar producto fitosanitario sugerido según causa | — | Completada |

### Tareas pendientes

| Tarea | Estado |
|---|---|
| Endpoint que devuelve causa, confianza, acción recomendada y producto sugerido por zona | Pendiente |
| Texto legible para el productor | Pendiente |
| Vincular diagnóstico al vuelo y al lote | Pendiente |

### Problemas encontrados

_(sin problemas reportados)_

---

## Sprint 9 — Severidad y zonificación de manejo

### Tareas pendientes

| Tarea | Estado |
|---|---|
| Calcular afectación relativa de cada zona vs. promedio del lote | Pendiente |
| Clasificar cada zona por nivel de severidad (crítica / deficiente / normal / vigorosa) | Pendiente |
| Agrupar zonas con el mismo problema y severidad similar en una unidad de manejo común | Pendiente |

### Problemas encontrados

_(sprint no iniciado)_

---

## Sprint 10 — Dashboard de resultados, testing y demo

### Tareas pendientes

| Tarea | Estado |
|---|---|
| Mapa de zonas clasificadas con color por severidad | Pendiente |
| Tabla de estadísticas por zona: área, índice promedio, causa, confianza, producto sugerido | Pendiente |
| Pulido de UX y mensajes de estado | Pendiente |
| Pruebas E2E del flujo completo: upload → análisis → diagnóstico | Pendiente |
| Cerrar huecos de cobertura en tests del motor de reglas | Pendiente |
| Preparar demo Hito 2 | Pendiente |
| Testing integral | Pendiente |

### Problemas encontrados

_(sprint no iniciado)_

---

## Otros

| Tarea | Responsable | Estado |
|---|---|---|
| Armar paper | Zaira Rosin | En progreso |
| Preparar ortomosaico con QGIS | Zaira Rosin | Completada |
