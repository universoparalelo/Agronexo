# AgroNexo — Instrucciones para Claude

## Estado actual del proyecto

**Release activa:** v4.0.0 (en desarrollo) — seguimiento en `docs/release-v4.0.0.md`
**Release anterior:** v3.0.0 — seguimiento en `docs/release-v3.0.0.md`
**Plan de trabajo completo:** `docs/4_Plan_de_trabajo.html` — incluye todos los sprints y releases con checkboxes interactivos para marcar el avance.

### Qué está implementado y funcionando

| Área | Estado | Notas |
|---|---|---|
| Docker Compose (stack completo) | ✅ | db, redis, minio, api, worker, frontend |
| FastAPI + SQLAlchemy async + PostGIS | ✅ | |
| Migraciones Alembic (0001 → 0020) | ✅ | Correr `alembic upgrade head` al arrancar |
| Auth JWT (registro, login, refresh) | ✅ | access 30 min, refresh 7 días |
| CRUD lotes con geometría PostGIS | ✅ | Soft delete, área calculada en PostGIS |
| Upload GeoTIFF → MinIO + Celery | ✅ | `POST /lotes/desde-geotiff` (lote + vuelo en un paso) |
| Worker GIS: NDVI, NDRE, SAVI, ExG | ✅ | Vectoriza zonas, exporta GeoJSON a MinIO |
| Worker actualiza geometry del lote | ✅ | Extrae bounding box del GeoTIFF tras reproyectar |
| CI GitHub Actions (3 jobs) | ✅ | test-api (migraciones + health + test_ingesta.py), test-gis (test_ndvi_pipeline + test_indices_worker + test_ingesta_worker + config Celery), build-frontend |
| Frontend Login + Dashboard | ✅ | Lista de lotes, cards con cultivo y área |
| Modal carga GeoTIFF (drag & drop) | ✅ | Llama a `/lotes/desde-geotiff` |
| Polling de progreso (barra) | ✅ | Cada 2s contra `/vuelos/{id}/estado` |
| Mapa Leaflet con zonas NDVI | ✅ | Coloreado por clase, tooltip con área y NDVI prom. |
| Umbralización dinámica (fijo/otsu/percentil) | ✅ | `workers/gis/clasificacion.py` |
| Vectorización con connectivity=8 y área mínima | ✅ | `workers/gis/zonas.py` (antes `ndvi.py` — renombrado, es genérico para los 4 índices) |
| Z-score por polígono (zonas atípicas) | ✅ | Campo `zscore` y `es_atipica` en GeoJSON |
| Modal límites lote (GeoJSON + Leaflet preview) | ✅ | `frontend/src/components/ModalLimites.jsx` |
| Eliminar diagnóstico (soft delete) + reintentar análisis fallido | ✅ | Botones en tabla "Análisis Recientes"; `DELETE`/`POST .../reintentar` en `app/ingesta/router.py` |
| Botón "Nuevo lote" (formulario + límite dibujado en mapa, sin GeoTIFF) | ✅ | `frontend/src/components/ModalNuevoLote.jsx` → `POST /lotes`. El límite se puede omitir: el primer GeoTIFF lo completa (`workers/gis/tasks.py::_poligono_cobertura_wkt`) |
| Modal "Cargar Ortomosaico" con selector de lote existente | ✅ | `ModalCargaGeoTIFF.jsx` ahora sube vuelos a un lote ya creado vía `POST /lotes/{id}/vuelos`, no crea lote nuevo |
| Multi-índice real (NDVI + NDRE/SAVI/ExG en paralelo) | ✅ | Tabla `analisis_indices`, tarea Celery `analizar_indice`, endpoints `.../vuelos/{id}/indices/*`. Selector de pastillas en "Vista geoespacial" del Dashboard |
| Motor de diagnóstico (RFDR-01) | ✅ | On-demand/sin persistencia — `GET /lotes/{id}/vuelos/{id}/diagnostico`. 20 reglas en `app/diagnostico/reglas.py`. Historial persistido queda para release 4 (ver `docs/release-v1.0.0.md`) |
| Atributos del lote | ✅ | `tipo_suelo` (enum 7 valores NEA). Cultivo, variedad y fechas ya NO son del lote — viven en `cultivos` (migración 0020, ver fila siguiente) |
| Cultivos por lote | ✅ | Tabla `cultivos` (`tipo_cultivo`, `variedad`, `fecha_siembra`, `fecha_cosecha`, soft delete). `GET/POST/PUT/DELETE /lotes/{id}/cultivos`. Todo análisis (`vuelos.cultivo_id`) se hace sobre un cultivo existente del lote o uno nuevo creado en el momento (`cultivo_id` o `cultivo_tipo…` en el upload; `cultivo_id` o `cultivo{…}` en `desde-satelite`). El diagnóstico toma tipo/variedad del cultivo del vuelo; el estadio fenológico es solo del vuelo |
| Tabla productos fitosanitarios en BD | ✅ | 21 productos seed, `GET /api/v1/productos-fitosanitarios` con filtros por `causa` y `tipo`. Migración 0015. El diagnóstico consulta productos desde BD |
| Diagnóstico explicado por zona | ✅ | Texto legible, severidad, vinculado a lote/vuelo. `app/diagnostico/texto.py` |
| Zonificación de manejo (RFDR-02) | ✅ | Agrupa zonas contiguas por causa+severidad en unidades de manejo. `app/diagnostico/zonificacion.py` |
| Mapa con color por severidad | ✅ | Toggle automático al activar tab Diagnóstico + contornos de unidades de manejo |
| Dashboard de resultados (tabla stats + UX) | ✅ | Tabla compacta + cards toggle, KPIs reales, spinner diagnóstico, link zonas→diagnóstico |
| Tests unitarios del motor de diagnóstico | ✅ | 84 tests: engine, forma, texto, zonificación, API. `pytest tests/test_diagnostico_*.py tests/test_texto.py tests/test_zonificacion.py tests/test_forma.py` |
| Reporte ejecutivo PDF | ✅ | `GET /lotes/{id}/vuelos/{id}/reporte/pdf` — motor de diagnóstico → mapa PNG estático (Pillow) → template Jinja2 → WeasyPrint (`app/reportes/`). Sin botón en el dashboard todavía (ver tarjeta Trello "Integración en el dashboard") |
| Exportación Shapefile | ❌ | Pendiente |

### Credenciales de desarrollo

| Servicio | URL | Credenciales |
|---|---|---|
| Frontend | http://localhost:5173 | — |
| API / Swagger | http://localhost:8000/api/docs | — |
| MinIO Console | http://localhost:9001 | Ver `.env` |
| PostgreSQL | localhost:5432 | Ver `.env` |
| **Usuario por defecto** | — | `admin@agronexo.com` / `password123` |

### Decisiones recientes no obvias desde el código

- **Cultivo y estadio ya no viven en `lotes`** (migración 0020). `vuelos.cultivo_id` es nullable solo por compatibilidad con datos viejos (la migración le asigna un cultivo a todos los vuelos existentes); un vuelo sin cultivo devuelve 409 en `/diagnostico`. `lotes.cultivos` (relationship `selectin`, `viewonly`) trae solo los no eliminados, del más reciente al más antiguo — el frontend usa `cultivos[0]` como "cultivo actual" del lote.
- Las zonas vectorizadas se recortan siempre al polígono del lote (`workers/gis/zonas.py::_recortar_a_limite`, se pasa `limite_wgs84` desde `workers/gis/tasks.py::_limite_para_recorte`); si el lote no tiene geometry no se recorta.

- `geometry` en tabla `lotes` es **nullable** (migración 0005) — el worker la rellena con el bounding box del GeoTIFF después de procesar. Un lote recién creado puede tener `geometry = null`.
- El contenedor API necesita `./workers` montado como volumen — sin eso no puede importar `workers.celery_app` y crashea al arrancar.
- `POST /lotes/desde-geotiff` está en el router de ingesta (prefijo `/lotes`), no en el router de lotes. Sigue existiendo pero el frontend ya no lo usa como flujo principal: un "lote" se crea primero (sin GeoTIFF, con límite GeoJSON) vía `ModalNuevoLote.jsx` → `POST /lotes`, y luego cada "vuelo" se sube a un lote ya existente vía `ModalCargaGeoTIFF.jsx` → `POST /lotes/{id}/vuelos`.
- El worker pasa `lote_id` como kwarg a la tarea Celery para poder actualizar la geometry después.
- `rasterio.features.shapes()` rechaza `float64` — el array NDVI siempre se castea a `float32` antes de vectorizar.
- `test_celery_integracion.py` tiene tres tests: dos de configuración (corren en CI dentro del job `test-gis`) y uno de ciclo completo E2E que requiere MinIO + worker levantados — ese solo corre con `docker compose exec worker`.
- `tipo_suelo` en tabla `lotes` es un PostgreSQL enum (`tiposueloenum`) — asyncpg no auto-castea VARCHAR a enum, así que las migraciones crean enums con SQL directo y `DO/EXCEPTION` para idempotencia.
- `productos_fitosanitarios` tiene su propio router (`productos_router`) montado en `/api/v1/productos-fitosanitarios` — no puede ir bajo `/api/v1/lotes/` porque FastAPI interpreta el segmento como `{lote_id}` UUID y falla.
- El servicio de diagnóstico (`app/diagnostico/service.py`) carga productos desde BD en cada request vía `_cargar_catalogo_productos()` — el dict estático en `app/diagnostico/productos.py` sigue existiendo pero ya no se importa.

---

## Qué es este proyecto

AgroNexo es una plataforma de agricultura de precisión que procesa imágenes satelitales y de drones (GeoTIFF multiespectrales) para calcular índices de vegetación (NDVI, GNDVI, SAVI, NDRE, EVI, MSAVI), detectar anomalías espaciales en cultivos y generar diagnósticos agronómicos con recomendaciones de prescripción diferenciada. El foco geográfico es el NEA argentino (Chaco, Formosa, Corrientes), con énfasis en soja, algodón, maíz y sorgo.

---

## Arquitectura del sistema

Monolítica modular con 4 capas. Todo corre en Docker.

```
Frontend (React)
     ↕ REST API + GeoJSON
Backend FastAPI  ←→  Redis  ←→  Worker GIS (Celery)
     ↕                                  ↕
PostgreSQL + PostGIS              MinIO (archivos)
```

**Regla clave:** El Worker GIS es un proceso separado. El procesamiento de GeoTIFF NUNCA ocurre en FastAPI — siempre se encola en Celery. FastAPI solo coordina.

---

## Stack por capa

### Frontend
| Tecnología | Rol |
|---|---|
| React | UI principal |
| React-Leaflet | Mapas, capas GIS, polígonos GeoJSON |
| Vite | Build y dev server |
| CSS plano (Tailwind previsto) | Estilos — no incorporar Tailwind aún |

Comunicación con backend: exclusivamente REST API + GeoJSON.

### Backend (`app/`)
| Tecnología | Rol |
|---|---|
| FastAPI | API REST, routing, coordinación |
| Pydantic / pydantic-settings | Validación y configuración |
| SQLAlchemy + GeoAlchemy2 | ORM + geometrías PostGIS |
| python-jose + bcrypt | JWT + hashing |
| WeasyPrint | Reportes PDF desde HTML/CSS |
| Redis | Broker Celery (db 0) + result_backend de tareas (db 1) — **ambos deben configurarse** para que el polling de estado funcione |
| Celery | Cola de tareas asíncronas |

Módulos FastAPI: `app/auth/`, `app/lotes/`, `app/ingesta/`, `app/diagnostico/`, `app/reportes/`

### Worker GIS (dentro de workers Celery)
| Tecnología | Rol |
|---|---|
| Rasterio | Lectura raster, extracción de bandas, vectorización |
| NumPy | Cálculos de índices pixel a pixel |
| GDAL | Motor geoespacial base (dependencia de Rasterio) |
| scikit-image | Umbralización Otsu para clasificación |
| GeoPandas | Manipulación vectorial, exportación GeoJSON/SHP |
| Shapely | Geometrías, circularidad, simplificación Douglas-Peucker |

### Datos
| Tecnología | Rol |
|---|---|
| PostgreSQL + PostGIS | BD relacional + geometrías (polígonos de zonas) |
| MinIO | Archivos binarios (GeoTIFF, PDF, SHP) — S3-compatible |

Separación: PostGIS guarda **metadatos y vectores**. MinIO guarda **archivos binarios**.

### Infraestructura
- Docker + Docker Compose (desarrollo y producción)
- Nginx (planificado para producción, R7)

---

## Convenciones de la API REST

- **Base URL:** `/api/v1`
- **Auth:** `Authorization: Bearer <JWT>` en todos los endpoints protegidos
- **IDs:** UUID v4
- **Fechas:** ISO 8601 (`2026-06-12T10:30:00Z`)
- **Formatos:** `application/json` / `multipart/form-data` para uploads
- **access_token:** expira en 30 minutos · **refresh_token:** 7 días
- **Soft delete:** los lotes no se eliminan — se marcan con `deleted_at`
- Los vuelos son sub-recursos de lotes: `/api/v1/lotes/{lote_id}/vuelos/{vuelo_id}`

### Flujo principal
```
POST /auth/login → tokens
POST /lotes → crear lote con GeoJSON
POST /lotes/{id}/vuelos → subir GeoTIFF → encola Celery → 202 Accepted
GET  /lotes/{id}/vuelos/{id}/estado → polling progreso
GET  /lotes/{id}/vuelos/{id}/diagnostico → diagnóstico agronómico por zona
GET  /productos-fitosanitarios → catálogo de productos (?causa=...&tipo=...)
GET  /analisis/{id}/reportes/shapefile → .zip para maquinaria
```

---

## Dominio agronómico — reglas de negocio clave

### Índices de vegetación y cuándo usar cada uno

| Índice | Cuándo usarlo | Bandas (Sentinel-2) |
|---|---|---|
| **SAVI** | Primeras 3 semanas post-siembra (cobertura < 30%) | NIR, RED |
| **NDVI** | Crecimiento vegetativo (25–60 días desde siembra) | B8, B4 |
| **GNDVI** | Cuando NDVI > 0.75 (fase reproductiva, saturación) | B8, B3 |
| **NDRE** | Detección temprana de estrés clorofílico, nitrógeno | B8, B5 |
| **EVI** | Cultivos muy densos donde NDVI satura | B8, B4, B2 |
| **MSAVI** | Inicio de campaña, suelo expuesto | NIR, RED |

**Fórmula NDVI:** `(NIR - RED) / (NIR + RED)` → bandas Sentinel-2: B8 (NIR), B4 (RED)

### Umbrales NDVI para alertas automáticas

```python
# Reglas generales
ndvi < 0.20          → suelo desnudo / sin vegetación
0.20 <= ndvi < 0.70  → cultivo con estrés o en desarrollo
ndvi >= 0.70         → vigor óptimo

# Soja — ciclo fenológico
if dias_desde_siembra < 25:       usar SAVI
if 25 <= dias_desde_siembra < 60: usar NDVI
if ndvi > 0.75:                   usar GNDVI (floración/llenado)
if delta_ndvi < 0 and ndvi → 0.2: estado Senescencia/Cosecha

# Clasificación temporal soja/maíz (sur Córdoba)
pico_ndvi < 2026-02-01  → Siembra Temprana (De Primera)
pico_ndvi > 2026-02-01  → Siembra Tardía (De Segunda)
ndvi_max_estival < 0.70 → alerta "Ciclo Incompleto"
```

### Patrones espaciales → diagnóstico

| Patrón | Causa probable | Índice afectado |
|---|---|---|
| Circular / radial | Enfermedades fúngicas (Sclerotinia, Rhizoctonia) | NDRE bajo, NDVI bajo |
| Lineal / franjas | Compactación, falla sembradora | NDVI bajo uniforme en franjas |
| Difuso / gradiente | Variabilidad edáfica, déficit hídrico, deficiencia N | NDVI bajo generalizado |
| Aleatorio / disperso | Plagas móviles (orugas, chinches), granizo | NDVI bajo puntual |
| Manchones persistentes | Nematodos, salinidad, suelo (posición fija entre campañas) | NDVI/GNDVI crónicos |
| Siguiendo microtopografía | Anegamiento, Phytophthora (partes bajas del lote) | NDWI alto + NDVI bajo |

**Métricas de forma (Shapely):**
```python
circularidad = (4 * pi * area) / perimetro**2  # ~1 → enfermedad focal
elongacion   = eje_mayor / eje_menor            # alta → compactación/maquinaria
densidad     = num_poligonos / area_total       # alta → plagas/granizo
```

### Particularidades del NEA (Chaco)
- Vertisoles: grietas en época seca generan patrones lineales — usar SAVI en lugar de NDVI cuando la cobertura es < 30%
- Anegamiento temporario frecuente (pendientes < 0.5%) — cruzar NDWI + NDVI + MDE
- Suelos sódico-salinos: NDVI crónico < 0.2 — marcar como limitación edáfica permanente, no fitosanitaria
- Temperaturas altas (> 25°C suelo) → Meloidogyne incognita es el nematodo predominante en algodón

---

## Procesamiento GIS — pipeline

```
GeoTIFF (Sentinel-2 / DJI Mavic 3 Multispectral)
    ↓ Rasterio (windowed reading para archivos > 500 MB)
Extracción de bandas → matrices NumPy
    ↓ NumPy
Cálculo de índice (NDVI, SAVI, GNDVI, etc.)
    ↓ scipy.ndimage.gaussian_filter (sigma=1px, NaN-safe) — `suavizar_indice()`
Suavizado espacial → evita fragmentación "sal y pimienta" al clasificar gradientes continuos
    ↓ scikit-image (Otsu)
Umbralización → máscara de píxeles (las estadísticas reportadas usan el valor SIN suavizar)
    ↓ cast a float32 / uint8 (shapes() rechaza float64 e int8)
    ↓ rasterio.features.shapes()  — para archivos > 500 MB usar rasterio.band(src, n) en lugar de src.read() para evitar cargar el array completo en memoria
Vectorización → polígonos
    ↓ GeoPandas + Shapely
gdf.explode() ANTES de filtrar por área — si no, un buffer(0) que fusiona fragmentos en un MultiPolygon deja pasar ruido cuya área total agregada supera el mínimo
    ↓
Filtrado por área mínima (por fragmento individual), simplificación Douglas-Peucker
    ↓
Exportación: GeoJSON (API) / SHP.zip (maquinaria) / ISO-XML (ISOBUS)
```

**Limitación técnica documentada:** DJI Mavic 3 Multispectral no tiene banda SWIR → NDWI convencional (NIR − SWIR) no es calculable. Usar NDWI de McFeeters (Verde − NIR) / (Verde + NIR) como proxy de agua superficial. NDRE como proxy de estrés hídrico foliar.

**Ojo con el DJI Mavic 3 Multispectral real:** captura solo 4 bandas (Green, Red, RedEdge, NIR) — **no tiene banda Blue**. `workers/gis/band_mapping.py` refleja esto (`GREEN=1, RED=2, RE=3, NIR=4`, sin `BLUE`). Por eso el índice `ExG` (que necesita RGB) no está disponible para `sensor="dji_mavic3"` — es una limitación real del sensor, no un bug.

---

## Estructura de archivos en MinIO

```
{usuario_id}/{lote_id}/{vuelo_id}/
    ├── original.tif        # ortomosaico subido
    ├── ndvi.tif            # índice calculado
    ├── zonas.geojson       # zonas vectorizadas
    ├── prescripcion.shp.zip
    └── reporte.pdf
```

---

## Requisitos funcionales clave (IDs del ERS)

- **RFMA-04** Detección de anomalías: clasificar por valor del índice Y por forma geométrica del polígono
- **RFDR-01** Motor de reglas: tabla patrón → causa con scoring probabilístico
- **RFDR-02** Zonificación: causas con mismo patrón en zonas contiguas → unidad de manejo única
- **RFDR-03** Severidad: diferencia entre índice de zona afectada vs. promedio del lote
- **RFDR-04** Criterio técnico: el agrónomo puede aceptar, modificar o rechazar el diagnóstico sugerido
- **RFGL-03** Historial de intervenciones: distingue patrones persistentes (edáficos) de episódicos (enfermedades)
- **RFSA-01..04** Exportaciones: PDF (WeasyPrint), SHP.zip, ISO-XML, Orden de Trabajo

---

## Seguimiento de release (`docs/release-vX.X.X.md`)

Cada release tiene su propio archivo de seguimiento en `docs/`. **Una release = un archivo.**

| Release | Archivo | Estado |
|---|---|---|
| v1.0.0 | `docs/release-v1.0.0.md` | Cerrada |
| v2.0.0 | `docs/release-v2.0.0.md` | Cerrada |
| v3.0.0 | `docs/release-v3.0.0.md` | Cerrada |
| v4.0.0 | `docs/release-v4.0.0.md` | En desarrollo |

Al iniciar una release nueva, crear `docs/release-vX.X.X.md` copiando la estructura de la release anterior. El archivo de la release anterior no se modifica una vez cerrada.

**El archivo activo ahora es: `docs/release-v4.0.0.md`**

**Actualizar el archivo AL TERMINAR CADA TAREA — obligatorio, no opcional:**
- Se completa una tarea del sprint → agregar entrada en "Tareas completadas" con fecha, rama/commit, decisiones tomadas y resultado.
- Surge un error relevante → documentarlo dentro de la tarea con el mensaje exacto del error y cómo se resolvió.
- Se toma una decisión de arquitectura no obvia → agregarla a la tabla "Decisiones de arquitectura".
- Aparece un problema abierto sin solución → agregarlo a "Problemas abiertos" y borrarlo cuando se resuelva.
- Se cierra la release → completar la sección "Presentación" y marcar el checklist.

**No documentar:**
- Cambios internos triviales (renombrar variable, ajustar formato).
- Errores de tipeo o de sintaxis resueltos en el mismo momento.
- Decisiones obvias que cualquiera tomaría igual.

**Formato de entrada de tarea completada:**
```
#### Nombre de la tarea
**Fecha:** YYYY-MM-DD
**Rama:** `feat/nombre` (commit `abc1234`)

Descripción breve de qué se hizo y por qué.

**Decisiones tomadas:**
- decisión 1
- decisión 2

**Error encontrado — título descriptivo**
[mensaje de error exacto o descripción]
Cómo se resolvió.
```

---

## Mantenimiento del README.md

El archivo `README.md` es la puerta de entrada para los colaboradores del proyecto. Actualizarlo es obligatorio cuando ocurre cualquiera de estos eventos:

- Se agrega un nuevo servicio al `docker-compose.yml` → actualizar la tabla de servicios y puertos
- Cambia el proceso de instalación o los requisitos previos → actualizar la sección de instalación
- Se crea un módulo nuevo en `app/` o `workers/` → actualizar el árbol de estructura
- Cambia alguna variable de entorno requerida → actualizar `.env.example` Y la tabla del README

El README ya no incluye "Comandos frecuentes" ni "Problemas comunes" (se sacaron por decisión explícita para mantenerlo como puerta de entrada profesional, sin contenido de wiki interna). No volver a agregar esas secciones salvo pedido explícito.

No actualizar el README en cambios internos de implementación (refactors, renombrar funciones, ajustar lógica de negocio).

---

## Estrategia de ramas (trunk-based development)

`main` es siempre la rama estable y deployable. Nadie pushea directo a `main` — todo entra por Pull Request. Las ramas son de vida corta: máximo 2-3 días antes de mergear.

### Nomenclatura de ramas

| Prefijo | Cuándo usarlo | Ejemplo |
|---|---|---|
| `feat/` | Nueva funcionalidad del sprint | `feat/auth-jwt` |
| `fix/` | Bug no urgente detectado en desarrollo | `fix/ndvi-division-cero` |
| `hotfix/` | Bug en producción que rompe algo — prioridad máxima | `hotfix/upload-geotiff-crash` |
| `chore/` | Mantenimiento sin lógica: deps, renombrar, configs | `chore/actualizar-rasterio` |
| `release/` | Preparación de release para despliegue | `release/v1.0.0` |

### Flujo según situación

**Feature nueva (caso normal)**
```bash
git checkout main && git pull
git checkout -b feat/nombre-corto
# ... trabajar, commitear frecuente ...
git push origin feat/nombre-corto
# Abrir Pull Request → revisión → merge a main → borrar rama
```

**Bug no urgente**
```bash
git checkout -b fix/descripcion-breve
# corregir, test, commit
# PR a main igual que feat/
```

**Hotfix en producción**
```bash
# Cortar desde el tag que está en producción, no desde main
git checkout v1.0.0
git checkout -b hotfix/descripcion
# corregir mínimo necesario
# PR a main  →  merge
# PR a release/v1.0 también si aplica  →  merge
git tag v1.0.1
```

**Release (cuando llega el momento de desplegar)**
```bash
git checkout main && git pull
git checkout -b release/v1.0.0
# ajustes finales: versión, changelog, smoke test
# PR a main  →  merge
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
# deploy siempre desde el tag, nunca desde main directamente
```

### Reglas de Pull Request

- Todo merge a `main` va por PR — sin excepciones, incluso trabajando solo.
- El PR debe describir qué cambia y cómo probarlo (comando o endpoint).
- Al menos una revisión de un compañero antes de mergear en equipo.
- Resolver conflictos en la rama feature, nunca en main.
- Borrar la rama después del merge.

### Commits

Usar prefijos convencionales para que el historial sea legible:

```
feat:   nueva funcionalidad
fix:    corrección de bug
chore:  mantenimiento, deps, configs
docs:   documentación
test:   tests
refactor: reestructura sin cambiar comportamiento
```

### Protección de main (configurar en GitHub)

En Settings → Branches → Add rule sobre `main`:
- ✅ Require pull request before merging
- ✅ Require at least 1 approval
- ✅ Dismiss stale reviews when new commits are pushed
- ✅ Do not allow bypassing the above settings

---

## Verificación de cambios remotos

Antes de iniciar cualquier tarea, ejecutar:

```bash
git fetch origin
git log --oneline origin/main ^main
```

Si hay commits en el remoto que no están en local, informarlos al usuario y preguntar si quiere traerlos antes de continuar (`git pull`). No asumir que el local está al día.

## Commit y push al terminar

Al completar cualquier tarea, recordar explícitamente al usuario que haga commit y push si todavía no se hizo. Incluir el comando exacto listo para copiar. El trabajo no está compartido hasta que esté en el remoto.

---

## Reglas de desarrollo

### Código
- Python para backend y worker GIS. JavaScript/React para frontend.
- No mezclar lógica de procesamiento GIS dentro de los endpoints FastAPI. Siempre Celery.
- Los cálculos de índices operan sobre arrays NumPy completos — nunca iterar pixel a pixel.
- Manejar `nodata` y división por cero explícitamente en las operaciones de índices.
- GeoTIFF grandes (> 500 MB): usar windowed reading de Rasterio (`src.block_windows()`). En el paso de vectorización usar `rasterio.band(src, n)` en lugar de `src.read()` para no cargar el array completo en memoria.
- Antes de llamar a `rasterio.features.shapes()`, castear el array a `float32`, `uint8`, `uint16`, `int16` o `int32` — la función rechaza `float64` e `int8` y lanza `TypeError` silencioso.
- Geometrías: validar con Shapely antes de persistir en PostGIS.

### API
- No romper contratos de response existentes — agregar campos, nunca eliminar sin versionar.
- Uploads de archivos → siempre `multipart/form-data`, validar tipo MIME y extensión en FastAPI antes de enviar a MinIO.
- Polling de estado de análisis: el endpoint de estado devuelve porcentaje y mensaje de progreso — no bloquear.

### Seguridad
- Contraseñas: solo bcrypt, nunca texto plano ni MD5/SHA1.
- JWT: verificar firma criptográfica en cada request protegido vía dependencia FastAPI.
- MinIO: generar URLs firmadas de acceso temporario — el frontend nunca accede directamente con credenciales permanentes.
- Nunca exponer trazas de error internas al cliente; loguear internamente.

### Base de datos
- Migraciones con Alembic — no modificar tablas manualmente en producción.
- Columnas de geometría: siempre `GEOMETRY(Polygon, 4326)` con índice GiST.
- Soft delete: `deleted_at` timestamp — nunca `DELETE` físico en tablas de lotes, vuelos o análisis.

### Comentarios y documentación
- No escribir comentarios que expliquen qué hace el código (los nombres lo dicen).
- Solo comentar el POR QUÉ cuando hay una restricción no obvia (ej. limitación del sensor, quirk de PostGIS).

---

## Diagnóstico — mensajes al usuario

El sistema debe comunicar tres niveles de certeza:
1. **"Diagnóstico probable con alta confianza"** — patrón + índice + contexto consistentes con una sola causa
2. **"Diagnóstico ambiguo — se requiere verificación en campo"** — dos o más causas con igual verosimilitud
3. **"Patrón no clasificable — factor edáfico permanente probable"** — patrón persistente entre campañas, sin respuesta a tratamiento

---

## Comandos frecuentes

```bash
# Levantar el stack completo
docker compose up

# Solo backend + bd (sin workers)
docker compose up api db redis

# Correr migraciones
docker compose exec api alembic upgrade head

# Acceder a la base de datos
docker compose exec db psql -U agronexo

# Ver logs del worker GIS
docker compose logs -f worker

# Frontend dev
cd frontend && npm run dev
```

---

## Glosario mínimo

- **Lote:** unidad básica de trabajo — campo agrícola con polígono georreferenciado
- **Vuelo:** conjunto de imágenes capturadas en una fecha (ortomosaico GeoTIFF)
- **Análisis:** procesamiento de un vuelo → genera índices, zonas, diagnóstico
- **Estadio fenológico:** fase del ciclo de la planta (V1..Vn vegetativo, R1..R8 reproductivo)
- **NEA:** Nordeste Argentino — región de enfoque (Chaco, Formosa, Corrientes, Misiones)
- **CRS:** sistema de referencia de coordenadas (EPSG:4326 = WGS84 en grados, EPSG:32721 = UTM zona 21 Sur en metros)
- **nodata:** valor especial en raster que indica píxel sin información válida (nubes, sombras)
- **Buffer de aplicación:** zona de margen geométrico agregada al polígono de maleza para equipos de fumigación (3–7 m estándar en Argentina)
