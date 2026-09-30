# Release v1.0.0 — AgroNexo

**Estado:** Cerrada  
**Fecha de inicio:** 2026-06-24  
**Fecha de cierre estimada:** 2026-07-07 (demo)  
**Responsables:** Matías Machado (Scrum Master), Celeste Martin Rodich, Denise Macarena Pujalte, Zaira Rosin, Amilcar Aguirre  
**Contexto:** Primera release del proyecto. Presentación académica incluida.

---

## Objetivo de la release

Construir el pipeline completo de agricultura de precisión, desde la ingesta de un ortomosaico GeoTIFF hasta la visualización de zonas clasificadas por índice de vegetación en un mapa Leaflet interactivo. Al cierre, el usuario se autentica, gestiona sus lotes con límites geográficos, sube un GeoTIFF multiespectral y, tras el procesamiento asíncrono en el worker, ve el mapa de zonas y un dashboard con estadísticas por zona.

---

## Equipo

| Nombre | Rol | Área principal |
|---|---|---|
| Matías Machado | Scrum Master · Desarrollo | frontend / API |
| Celeste Martin Rodich | Desarrollo | backend / GIS / infra (DevOps) |
| Zaira Rosin | Desarrollo | GIS / análisis espacial |
| Denise Macarena Pujalte | QA | testing / documentación |
| Amilcar Aguirre | Desarrollo | frontend / UI |

---

## Tareas completadas

### Infraestructura base

#### Estructura de carpetas y Docker Compose
**Fecha:** 2026-06-24  
**Rama:** `main` (commit `e4c9ce9`)

Se definió la arquitectura de 4 capas (Frontend, Backend FastAPI, Worker GIS, Datos) y se levantó el stack completo con Docker Compose: PostgreSQL+PostGIS, Redis, MinIO, API y Worker.

**Decisiones tomadas:**
- Worker GIS en contenedor separado del API — el procesamiento de GeoTIFF nunca bloquea la API.
- MinIO como almacenamiento de objetos S3-compatible para archivos binarios (GeoTIFF, PDF, SHP).
- Redis cumple doble rol: broker de Celery (db 0) y caché de estado de análisis (db 1).

**Error encontrado — Worker crasheaba al levantar**
```
ModuleNotFoundError: No module named 'app'
```
El `Dockerfile.worker` no copiaba el módulo `app/` que contiene la configuración compartida (`app/core/config.py`). Se resolvió agregando `COPY app/ ./app/` al Dockerfile y montando `./app:/app/app` como volumen en el Compose.

**Error encontrado — Conflicto de numpy en imagen GDAL**
```
ERROR: Cannot uninstall numpy 1.26.4, RECORD file not found.
Hint: The package was installed by debian.
```
La imagen base `osgeo/gdal` tiene numpy instalado vía apt. pip no puede sobreescribirlo. Se resolvió eliminando numpy de `requirements.worker.txt` (la imagen base lo provee) y agregando el flag `--ignore-installed` al comando pip del Dockerfile.

**Error encontrado — pydantic-settings faltante en worker**
```
ModuleNotFoundError: No module named 'pydantic_settings'
```
El worker importa `app.core.config` que depende de pydantic-settings, pero ese paquete no estaba en `requirements.worker.txt`. Se agregó `pydantic==2.10.4` y `pydantic-settings==2.7.0` a los requirements del worker.

---

#### FastAPI + Alembic + Migración inicial
**Fecha:** 2026-06-24  
**Rama:** `main` (commit `9007623`)

Se configuró FastAPI con CORS, se conectó SQLAlchemy async a PostgreSQL y se configuró Alembic para migraciones.

**Decisiones tomadas:**
- `alembic.ini` en la raíz del proyecto (no dentro de `migrations/`) para que Alembic lo detecte automáticamente al correr desde el contenedor.
- La URL de base de datos se sobreescribe en `migrations/env.py` desde pydantic-settings — no se hardcodea en `alembic.ini`.
- Endpoint `/api/v1/health/db` que verifica la conexión y devuelve la versión de PostGIS instalada.

**Migración 0001:** habilitó extensiones `postgis`, `postgis_topology` y `uuid-ossp`.

**Error encontrado — alembic.ini en ubicación incorrecta**  
El archivo estaba dentro de `migrations/` en lugar de la raíz. Alembic no lo encontraba al correr `alembic upgrade head` desde `/app`. Se movió a la raíz y se actualizó el Dockerfile para copiarlo.

---

#### Pipeline NDVI — Worker GIS
**Fecha:** 2026-06-24  
**Rama:** `main` (commit `4dba3e6`)

Se implementó el pipeline completo de procesamiento de índice NDVI dentro del Worker GIS:
lectura de bandas → cálculo → clasificación en 4 zonas → vectorización → exportación GeoJSON.

**Decisiones tomadas:**
- GeoTIFF sintético como fixture de prueba (4 cuadrantes con NDVI controlado) en lugar de datos reales descargados — permite verificar el pipeline sin depender de conectividad externa ni archivos grandes en el repositorio.
- Área mínima de polígono: 1000 m² (0.1 ha) — polígonos menores se descartan como ruido.
- Simplificación Douglas-Peucker con tolerancia 0.000005 grados — reduce vértices sin perder la forma de la zona.
- Cálculo de área en hectáreas reproyectando a EPSG:32721 (UTM zona 21 Sur, unidades en metros).

**Umbrales de clasificación implementados:**

| Clase | Rango NDVI | Código |
|---|---|---|
| crítica | < 0.20 | 1 |
| deficiente | 0.20 – 0.40 | 2 |
| normal | 0.40 – 0.70 | 3 |
| vigorosa | ≥ 0.70 | 4 |

**Error encontrado — GeoTIFF sintético con valores NDVI incorrectos**  
Los valores de reflectancia asignados a NIR y RED estaban invertidos en dos cuadrantes, produciendo NDVIs negativos. Por ejemplo, `nir=0.30, red=0.70` da NDVI = −0.40 (crítica), no deficiente. Se recalcularon todos los valores usando la fórmula inversa y se verificó cada cuadrante antes de escribir el archivo.

**Error encontrado — fixture no accesible desde el contenedor**  
El GeoTIFF de prueba se generó dentro del contenedor pero `tests/` no estaba mapeado como volumen. Al reiniciar el worker, el archivo desaparecía. Se agregó `./tests:/app/tests` como volumen en el Compose y se incluyó la generación del fixture dentro del propio script de test para que sea reproducible.

**Resultado del test:**
```
✓ calcular_ndvi OK
✓ División por cero → NaN OK
✓ clasificar_ndvi OK
✓ 4 polígonos generados (uno por clase)
✓ Cada clase ocupa exactamente 25% del área (~109 ha)
✓ GeoJSON válido con propiedades clase, ndvi_promedio, area_ha
Todos los tests pasaron.
```

---

---

#### Modelos Lote/Vuelo · CRUD de lotes · Validación Pydantic
**Fecha:** 2026-06-24  
**Rama:** `main` (commit siguiente)

Se implementaron los modelos SQLAlchemy para `Lote` y `Vuelo`, los schemas Pydantic con validación geométrica, el service layer con lógica de negocio y el router FastAPI con 7 endpoints.

**Decisiones tomadas:**
- `usuario_id` nullable en `Lote` por ahora — se conecta al módulo Auth en la siguiente tarea sin tocar el service.
- Cálculo de área con `ST_Area(ST_Transform(geometry, 32721)) / 10000` dentro de PostGIS — más preciso que calcular en Python porque usa proyección métrica.
- Soft delete con `deleted_at` timestamp — `DELETE` físico prohibido, el registro persiste con el historial de vuelos y análisis vinculados.
- Índice GiST sobre la columna `geometry` — habilita consultas espaciales eficientes (`ST_Intersects`, `ST_Contains`) en el futuro.
- Shapely agregado a `requirements.api.txt` para validar geometrías en los schemas Pydantic antes de que lleguen a la DB.
- `ondelete="RESTRICT"` en FK `vuelos.lote_id` — no se puede borrar un lote que tenga vuelos asociados (protección de integridad).

**Resultado de los tests:**
```
POST /lotes    201 — area_ha calculada: 27.404 ha
GET  /lotes    200 — total: 1
GET  /lotes/{id} 200 — nombre correcto
PUT  /lotes/{id} 200 — estadio actualizado
GET  /vuelos   200 — lista vacía (correcto)
DELETE         204 — soft delete
GET  /lotes    200 — total: 0 (lote no aparece)
GET  /lotes/{id} 404 (esperado — lote borrado)
Verificación DB: deleted_at seteado, registro físico preservado ✓
```

---

#### Módulo Auth (JWT, registro, login)
**Fecha:** 2026-06-25
**Rama:** `main` (commit siguiente)

Se implementó el módulo de autenticación completo con JWT: modelo `Usuario`, schemas Pydantic con validación de email y contraseña, service con bcrypt (passlib), dependencia `get_current_user` y router con 5 endpoints. Los endpoints de lotes quedaron protegidos con JWT y filtran por `usuario_id`.

**Decisiones tomadas:**
- JWT stateless: `access_token` (30 min) + `refresh_token` (7 días). Logout solo limpia tokens en el cliente — blacklist en Redis queda para un sprint posterior si se requiere invalidación inmediata.
- `ondelete="SET NULL"` en `lotes.usuario_id → usuarios.id` — si un usuario se elimina, sus lotes quedan huérfanos pero no se pierden.
- `email-validator` agregado a `requirements.api.txt` — requerido por `EmailStr` de Pydantic v2.
- Relación `Usuario.lotes` usa `foreign_keys` explícito para evitar ambigüedad con SQLAlchemy al resolver la FK circular entre módulos.

**Error encontrado — NoForeignKeysError al iniciar la API**
```
sqlalchemy.exc.NoForeignKeysError: Could not determine join condition between
parent/child tables on relationship Usuario.lotes
```
`Lote.usuario_id` no tenía `ForeignKey("usuarios.id")` declarado en el modelo SQLAlchemy (la FK existía solo en la migración). SQLAlchemy necesita la FK también en el ORM para resolver las relaciones. Se agregó el `ForeignKey` al modelo y se usó `foreign_keys=` en la relación de `Usuario`.

**Resultado de los tests:**
```
POST /auth/register    201 — agronomo@test.com creado
POST /auth/login       200 — tokens emitidos
GET  /auth/me          200 — Juan Perez
POST /auth/login       401 — password incorrecta (esperado)
GET  /auth/me          401 — sin token (esperado)
POST /auth/register    409 — email duplicado (esperado)
POST /lotes (auth)     201 — lote creado con usuario_id
POST /lotes (no auth)  401 — rechazado (esperado)
```

---

#### Frontend base — Vite + React + Login + Dashboard
**Fecha:** 2026-06-25
**Rama:** `main` (commit siguiente)

Se implementó el frontend base completo: scaffold Vite + React (JS), cliente HTTP axios con interceptores JWT, hook `useAuth`, pantalla de Login con manejo de errores, Dashboard con lista de lotes y placeholder del mapa, rutas protegidas con `PrivateRoute`, CSS plano funcional y servicio Docker con hot reload.

**Decisiones tomadas:**
- JavaScript puro (sin TypeScript) — alineado con el stack definido en CLAUDE.md.
- Proxy Vite `/api → http://api:8000` resuelve CORS en dev sin configuración extra en el backend.
- `localStorage` para tokens — suficiente para el contexto académico; en producción se evaluaría httpOnly cookies.
- CSS plano con paleta verde oscuro (#1a3a2a) coherente con identidad agrícola. Sin Tailwind por ahora.
- Botones "Nuevo lote" y "Ver análisis" deshabilitados — se habilitan cuando existan los endpoints de upload y análisis (Sprint 4).

**Resultado verificado:**
```
docker compose up frontend   → Vite v6 ready in 192ms en puerto 5173
GET http://frontend:5173/    → 200 HTML con React + Vite HMR
Proxy /api → api:8000        → configurado en vite.config.js
```

---

#### Usuario por defecto para desarrollo — migración 0006
**Fecha:** 2026-07-01
**Rama:** `main`

Se agregó la migración 0006 que inserta un usuario de desarrollo al correr `alembic upgrade head`. Usa `ON CONFLICT DO NOTHING` para que sea idempotente — si el usuario ya existe, no falla.

**Credenciales del usuario por defecto:**
- **Email:** `admin@agronexo.com`
- **Contraseña:** `password123`

No hay que crear usuario manualmente en un entorno de desarrollo fresco. Solo levantar el stack y correr las migraciones.

**Decisiones tomadas:**
- Hash bcrypt generado en la propia migración con passlib — no se guarda la contraseña en texto plano en ningún lado.
- `ON CONFLICT (email) DO NOTHING` — la migración es segura de correr múltiples veces.

---

#### Carga de GeoTIFF desde el frontend — Modal y endpoint combinado
**Fecha:** 2026-07-01
**Rama:** `main`

Se implementó el flujo completo de carga desde la UI. Botón "Cargar GeoTIFF" en el Dashboard abre un modal con formulario (nombre, cultivo, sensor, estadio opcional) y zona drag & drop. Llama a `POST /lotes/desde-geotiff` que crea el lote y encola el vuelo en un solo paso. Al confirmar, el modal se cierra, la lista se refresca y el lote queda seleccionado con la barra de progreso arrancando automáticamente.

**Decisiones tomadas:**
- Geometry del lote se crea como `NULL` (migración 0005) — el worker la actualiza con el bounding box del GeoTIFF tras reproyectar a EPSG:4326.
- `lote_id` se pasa como kwarg a la tarea Celery para que el worker identifique qué lote actualizar.
- La extracción de bounds falla silenciosamente en el worker para no bloquear el pipeline GIS.

---

#### Rediseño Login y fixes CI — integración rama Denise
**Fecha:** 2026-07-01  
**Rama:** `main` (merge `76e2b23`)

Se integraron los cambios de la rama de Denise: rediseño visual del Login (split-panel con imagen de fondo, tipografía mejorada), Login2 como variante, y correcciones al `ci.yml`.

**Decisiones tomadas:**
- `.github/workflows/ci.yml` reescrito con bloque `env:` raíz para eliminar duplicación de variables entre jobs.
- `JWT_SECRET_KEY` usa `${{ secrets.CI_JWT_SECRET_KEY || 'ci-secret-key-only-for-testing-not-production' }}` — fallback seguro para forks sin el secret configurado.
- `curl --retry 15 --retry-connrefused` reemplaza el `sleep 3` para esperar a que la API levante — más robusto en runners con carga variable.
- `./frontend/public:/app/public` agregado como volumen en docker-compose.yml — las imágenes (`logo.png`, `fondo.jpeg`) no cargaban porque solo estaba montado `frontend/src`.

---

#### Umbralización dinámica + stats por polígono + tests
**Fecha:** 2026-07-01  
**Rama:** `main` (commits `63419a8` / `cab071c`)

Se implementó umbralización dinámica con tres métodos intercambiables y estadísticas correctas por polígono individual.

**Piezas implementadas:**
- `workers/gis/clasificacion.py` (módulo nuevo): `calcular_umbrales(valores, metodo)` soporta `"fijo"` (agronómico: 0.20/0.40/0.70), `"otsu"` (threshold_multiotsu de scikit-image, 4 clases) y `"percentil"` (p25/p50/p75). Fallback a `"fijo"` si la imagen es uniforme o todos son NaN.
- `vectorizar_zonas()`: stats por polígono individual con `geometry_mask()` de rasterio — antes usaba el promedio de toda la clase, lo cual era incorrecto.
- Tolerancia de simplificación adaptativa: `abs(transform.a) * 0.5` en lugar de valor hardcodeado.
- `connectivity=8` en `shapes()` — conecta píxeles diagonales de la misma clase (antes `connectivity=4` fragmentaba zonas en diagonal).
- `area_minima_m2` configurable como parámetro de `vectorizar_zonas()` y `ejecutar_pipeline()`.
- `tests/test_clasificacion.py` con 12 tests: umbrales, fallbacks, clasificación, stats por polígono y pipeline con Otsu.

**Error encontrado — GeoTIFF sintético con sensor incorrecto**  
Los tests del pipeline usaban `sensor="sentinel2"` (1 banda), pero las fixtures sintéticas tenían 5 bandas (DJI Mavic 3). Error: `ValueError: El archivo tiene 1 banda(s) pero NDVI requiere la banda NIR en posición 8`. Se corrigió el fixture a 5 bandas con `sensor="dji_mavic3"`.

---

#### Estadísticas por zona — z-score y detección de zonas atípicas
**Fecha:** 2026-07-01  
**Rama:** `main`

Se agregó detección de polígonos atípicos por z-score sobre `ndvi_promedio` dentro de cada análisis.

**Implementación:**
- `vectorizar_zonas()`: calcula z-score de `ndvi_promedio` entre todos los polígonos del lote. Si `|zscore| > 1.5` → `es_atipica = True`.
- Con < 3 polígonos no se calculan atípicas (evita falsos positivos en rasters pequeños).
- Campos nuevos en el GeoJSON de salida: `zscore: float` y `es_atipica: bool`.
- GeoDataFrame vacío también declara estas columnas para que el schema sea consistente.
- Tests: verifican presencia de campos, que un outlier claro (NDVI=0.05 vs grupo en 0.77) recibe `es_atipica=True` y que lotes con < 3 polígonos no marcan atípicas.

**Decisiones tomadas:**
- Z-score se calcula con `std(ddof=1)` (muestral) — apropiado para n pequeño.
- Si `std == 0` (todos los polígonos tienen el mismo NDVI) → zscore = 0 para todos.

---

#### Límites del lote — endpoint + UI con vista previa Leaflet
**Fecha:** 2026-07-01  
**Rama:** `main` (commit `72ee9ca`)

Se implementó la carga de límites geográficos del lote con vista previa interactiva en el frontend.

**Piezas implementadas:**
- `PUT /lotes/{id}` ya existía con validación Shapely. No se necesitó cambio de backend.
- `frontend/src/components/ModalLimites.jsx`: drag & drop de archivo `.geojson`, extrae Polygon de Feature/FeatureCollection, muestra preview en `MapContainer` (react-leaflet) con `FitBounds`, llama a `PUT /lotes/{id}` al confirmar.
- Dashboard: botón "Límites" en cada card abre el modal. Al guardar exitosamente recarga la lista de lotes.
- CSS: `.modal-box--limites`, `.limites-preview-map`, `.dropzone` variantes.

**Decisiones tomadas:**
- `extraerPoligono()` acepta Polygon directo, Feature con Polygon, o FeatureCollection — cubre los formatos que exportan QGIS y las apps GIS más comunes.
- `boundsDesdePoligono()` calcula bounds manualmente desde coordenadas en lugar de usar `getBounds()` de Leaflet — disponible antes de que el mapa se monte.
- `FitBounds` como componente interno que llama a `map.fitBounds()` desde `useMap()` — patrón react-leaflet para acceder al mapa después del mount.

---

#### Fixes CI — pytest faltante y rutas absolutas en worker
**Fecha:** 2026-07-02  
**Rama:** `main` (commit `e2ce605`)

Se corrigieron dos errores que hacían fallar los jobs de CI.

**Error 1 — `No module named pytest` en job test-api**  
`pytest` no estaba en `docker/requirements.api.txt`. El job instala ese archivo y luego corre `python3 -m pytest tests/test_ingesta.py`. Fix: agregar `pytest==8.3.4` al archivo.

**Error 2 — `sentinel_ndvi_test.tif: No such file or directory` en job test-gis**  
`test_ndvi_pipeline.py` tenía `FIXTURE = "/app/tests/fixtures/..."` hardcodeado al contenedor Docker. En el runner de CI el checkout está en otro path. Además `crear_fixture()` solo se llamaba desde `__main__`, no cuando pytest invocaba los tests directamente.  
Fix: rutas relativas con `Path(__file__).parent / "fixtures"` y función `setup_module()` para que pytest genere el fixture antes de correr los tests.

---

#### Vista previa low-res de cobertura en cards de lote
**Fecha:** 2026-07-02  
**Rama:** `main` (commit `08c5c76`)

Se agregó un mapa estático miniatura dentro de cada card de lote mostrando el polígono límite.

**Piezas implementadas:**
- `frontend/src/components/MiniMapaLote.jsx`: recibe `lote.geometry` (ya viene en `GET /lotes`), renderiza un `MapContainer` de 110px no interactivo (sin drag, zoom, teclado ni attributionControl). Polígono en verde con relleno semitransparente.
- Si `geometry` es `null` muestra un placeholder punteado gris con texto "Sin límites definidos".
- Dashboard: `<MiniMapaLote geometry={lote.geometry} />` entre header y body de cada card.
- Sin llamadas adicionales a la API — geometry ya viene en la lista de lotes.

**Decisiones tomadas:**
- Margen negativo lateral (`.mini-mapa-lote { margin: 0 -1rem }`) para que el mapa llegue al borde del card sin padding.
- `dragging={false}`, `scrollWheelZoom={false}`, `touchZoom={false}` etc. — el mapa es decorativo, no interactivo.

---

#### Vincular análisis a vuelo/lote — columna geojson_key
**Fecha:** 2026-07-02  
**Rama:** `main` (commit `61a1046`)

Se estableció el vínculo explícito entre el análisis GIS y el vuelo en la base de datos, y se corrigió un bug donde el worker no actualizaba `lote.geometry` en el flujo de upload a lote existente.

**Problema raíz:**  
El GeoJSON de resultados no tenía referencia directa en la BD. `obtener_resultado_geojson` derivaba la ruta desde `vuelo.archivo_original` mediante `split("/")[:3] + "/zonas.geojson"`, lo cual es frágil. Además, `crear_vuelo_desde_upload` no pasaba `lote_id` a la tarea Celery, así que el worker no podía actualizar `lote.geometry` con el bounding box del GeoTIFF.

**Cambios:**
- Migración `0007`: columna `geojson_key VARCHAR(500) NULLABLE` en `vuelos`.
- `Vuelo` model: campo `geojson_key`.
- `tasks.py`: al completar el upload del GeoJSON a MinIO, guarda la key en `vuelos.geojson_key` via `_actualizar_vuelo(..., geojson_key=...)`.
- `ingesta/service.py`: `obtener_resultado_geojson` usa `vuelo.geojson_key` directamente; si es `None` (vuelos procesados antes de la migración) cae al método legacy de derivación.
- `ingesta/service.py`: fix bug — `lote_id` ahora se pasa al task en `crear_vuelo_desde_upload`.

**Decisiones tomadas:**
- Fallback legacy preservado para vuelos anteriores a la migración 0007 — no se necesita backfill de datos, el fallback cubre la transición.
- `geojson_key = None` si el upload al MinIO falla — el análisis en disco sigue siendo válido; el error queda en `estadisticas["advertencia_upload"]`.

---

#### Eliminar/reintentar diagnóstico + desacoplar creación de lote de la carga de GeoTIFF
**Fecha:** 2026-07-03
**Rama:** `main`

Se agregaron dos acciones sobre la tabla "Análisis Recientes" del dashboard (eliminar y reintentar un vuelo) y se redefinió el flujo de alta: un "lote" ahora se crea de forma independiente (con su límite GeoJSON, sin GeoTIFF), y cada "vuelo" se sube posteriormente a un lote ya existente.

**Piezas implementadas:**
- Migración `0008`: columna `deleted_at` en `vuelos` (soft delete, mismo patrón que `lotes`).
- `app/ingesta/service.py`: `obtener_vuelo`, `eliminar_vuelo`, `reintentar_vuelo` (reencola el mismo `archivo_original` ya en MinIO, sin pedir un nuevo upload).
- `app/ingesta/router.py`: `DELETE /{lote_id}/vuelos/{vuelo_id}` y `POST /{lote_id}/vuelos/{vuelo_id}/reintentar`.
- Frontend: `ModalConfirmarEliminar.jsx` (confirmación genérica), botones 🗑️/↻ en la tabla, "Análisis Recientes" ahora filtra solo lotes con vuelo activo.
- `ModalNuevoLote.jsx` (nuevo): formulario nombre/cultivo/estadio + límite GeoJSON (reusa el patrón de `ModalLimites.jsx`) → `POST /lotes`.
- `ModalCargaGeoTIFF.jsx` (reescrito): ya no crea lote — pide seleccionar un lote existente + sensor + archivo → `POST /lotes/{id}/vuelos`.

**Error encontrado — ruta duplicada `GET /{lote_id}/vuelos`**
Al agregar el filtro `deleted_at IS NULL` en `app/ingesta/service.py`, un vuelo eliminado seguía apareciendo en el dashboard. Causa: `app/lotes/router.py` y `app/ingesta/router.py` registraban la misma ruta `GET /{lote_id}/vuelos` bajo el mismo prefijo; por orden de registro en `main.py`, ganaba la de `app/lotes/router.py`, que llamaba a un `service.listar_vuelos` distinto (sin el filtro). Se eliminó la ruta y el service duplicados de `app/lotes/` (`VueloResponse`, `listar_vuelos`) — sin consumidores propios, confirmado por búsqueda en `tests/`.

**Decisiones tomadas:**
- El botón "Reintentar" solo aparece si `vuelo.estado === 'error'` y reencola el mismo archivo (no permite cambiar sensor en el reintento — si el sensor elegido fue el problema, hay que subir un vuelo nuevo).
- La tabla "Análisis Recientes" excluye lotes sin ningún vuelo activo (antes mostraba "Sin análisis" y la fila nunca desaparecía tras un delete).

---

#### Wizard de carga de ortomosaico (2 pasos) + inspección preliminar de bandas
**Fecha:** 2026-07-05
**Rama:** `main`

Se reemplazó el modal simple de carga de GeoTIFF por un wizard de 2 pasos ("Carga" y "Análisis"), y se agregó un chequeo instantáneo de compatibilidad de bandas antes de subir el archivo.

**Piezas implementadas:**
- `ModalCargaGeoTIFF.jsx`: paso "Carga" (lote, sensor, dropzone) → paso "Análisis" (card de info del lote + selector múltiple de índices — solo visual, no afecta el procesamiento real, que sigue siendo NDVI vía Celery).
- `app/ingesta/tiff_inspector.py` (nuevo): parser manual del header TIFF clásico (`SamplesPerPixel`, tag 277) sin depender de GDAL/rasterio — el contenedor API no tiene rasterio instalado a propósito (`validator.py` ya documentaba esto). Verificado contra `rasterio` en el worker con archivos reales de 4 y 5 bandas: coincide exacto.
- `POST /lotes/inspeccionar-geotiff` (nuevo endpoint): recibe archivo + sensor, devuelve `{n_bandas, bandas_requeridas, compatible, mensaje}`. `bandas_requeridas` sale de `workers.gis.band_mapping.MAPEO_SENSORES` (máximo índice de banda no nulo para ese sensor).
- Frontend dispara la inspección automáticamente al elegir archivo o cambiar sensor (`useEffect([archivo, sensor])`). Si `compatible === false`, la caja verde "Requerimientos Técnicos" se reemplaza por una caja roja con el mensaje de error — no bloquea el flujo, es informativo (la validación dura sigue estando en el worker).

**Decisiones tomadas:**
- Índices mostrados en el paso "Análisis" acotados a los 4 que el worker realmente calcula (`ndvi`, `ndre`, `savi`, `exg` — ver `band_mapping.py`), no una lista aspiracional.
- El chequeo de bandas es "best-effort": si el parseo del header falla (BigTIFF, archivo corrupto, etc.) devuelve `n_bandas: None` y se trata como compatible por defecto — nunca bloquea la carga por un parseo fallido, ya que el worker vuelve a validar todo con rasterio de todas formas.

---

#### Corrección del perfil de bandas de `dji_mavic3` (era incorrecto, no un sensor faltante)
**Fecha:** 2026-07-05
**Rama:** `main`

El chequeo de bandas agregado en la tarea anterior expuso una contradicción: el perfil `dji_mavic3` en `band_mapping.py` esperaba 5 bandas con Blue (`BLUE=1, GREEN=2, RED=3, RE=4, NIR=5`), pero el DJI Mavic 3 Multispectral real captura solo 4 bandas — **no tiene canal Blue** (confirmado con orthomosaicos reales: archivos `_MS_G`, `_MS_R`, `_MS_RE`, `_MS_NIR`, sin `_MS_B`). Esto es exactamente el archivo de 4 bandas (`Green, Red, RedEdge, NIR`) que veníamos fallando en tareas anteriores (ver entrada "Bug: geotiff no se analizó bien" — antes registrado como problema abierto #3, ya resuelto acá).

**Cambio:** `band_mapping.py` — `dji_mavic3` pasa a `GREEN=1, RED=2, RE=3, NIR=4` (sin `BLUE`). No hacía falta un tercer sensor nuevo: el perfil existente estaba mal definido desde el principio (documentado erróneamente como "mismas bandas que Sentinel-2 en distinto orden").

**Piezas actualizadas:**
- `workers/gis/band_mapping.py`: mapeo corregido + comentario explicando por qué no tiene Blue.
- `tests/test_indices_worker.py`: aserciones de `numero_banda("dji_mavic3", ...)` y fixture de `test_pipeline_ndvi_dji` (5→4 bandas).
- `tests/test_clasificacion.py`: fixture `_geotiff_cuatro_zonas` (bandas 5→4, índices de NIR/RED recalculados).
- `tests/test_celery_integracion.py`: fixture `_geotiff_dji_sintetico` (5→4 bandas).
- Los 3 archivos de test corridos y pasando con el nuevo mapeo (incluido el E2E completo con worker+MinIO reales).

**Verificación con archivo real:** el GeoTIFF de 4 bandas que fallaba con ambos sensores (ver tarea anterior) ahora procesa correctamente con `sensor=dji_mavic3`: 2 polígonos, NDVI promedio 0.6053 (min 0.1565, max 0.7616) — resultado coherente, no el ruido fragmentado que se obtenía cuando el sensor no calzaba con el contenido real de la imagen.

**Efecto colateral esperado (correcto):** `ExG` requiere banda `BLUE` (`BANDAS_POR_INDICE["exg"] = ["GREEN","RED","BLUE"]`). Como `dji_mavic3` ya no tiene Blue, pedir ExG con ese sensor ahora falla con un `ValueError` claro — es el comportamiento correcto: un sensor sin banda azul real no puede calcular un índice que la necesita.

---

#### Fix: fragmentación "sal y pimienta" al clasificar índices con gradiente continuo
**Fecha:** 2026-07-05
**Rama:** `main`

Un archivo con gradiente suave (mancha circular de vigor, sin saltos discretos de valor) se vectorizaba en 2 `MultiPolygon` de **100 y 140 fragmentos** cada uno en vez de 2 polígonos limpios. Reportado por el usuario al notar que un análisis dejó de verse "prolijo" como antes. Diagnóstico: no era una regresión de código — era un problema de fondo que afecta a **cualquier imagen real** (el vigor de un cultivo real siempre varía gradualmente, nunca en bloques discretos), así que había que arreglarlo en el pipeline, no aceptarlo como comportamiento esperado.

**Causa raíz (dos partes):**
1. Al clasificar un gradiente continuo con un umbral binario píxel a píxel, muchísimos píxeles vecinos caen a un lado u otro del umbral por redondeo — produce cientos de fragmentos diminutos justo en la zona de transición.
2. El filtro de área mínima no los descartaba porque `rasterio.features.shapes()` sobre una máscara con esa topología produce un contorno autointersecado (inválido); el `geom.buffer(0)` usado para repararlo fusiona todos los fragmentos en **un solo registro** `MultiPolygon` — y el área mínima se comparaba contra el área TOTAL del grupo (que sí supera el mínimo), no contra cada fragmento individual.

**Cambios:**
- `workers/gis/zonas.py` (renombrado de `ndvi.py` el mismo día, ver tarea siguiente): nueva función `suavizar_indice()` — filtro Gaussiano (sigma=1 píxel) NaN-safe (normaliza por el peso de la máscara de validez, no mezcla nodata con píxeles vecinos).
- `workers/gis/pipeline.py`: `ejecutar_pipeline` aplica `suavizar_indice()` al array **antes** de clasificar. Las estadísticas reportadas (`ndvi_promedio`, min/max) siguen calculándose sobre el valor SIN suavizar — el suavizado es solo una ayuda para la clasificación espacial.
- `workers/gis/zonas.py::vectorizar_zonas`: se agregó `gdf.explode(index_parts=False)` **antes** del filtro de área mínima, separando cualquier `MultiPolygon` en polígonos individuales para que el área se mida por fragmento real, no por grupo agregado.

**Verificación:**
- Los 30 tests existentes (`test_clasificacion.py`, `test_indices_worker.py`) y el E2E (`test_celery_integracion.py`) siguen pasando sin cambios en sus valores esperados — el suavizado con sigma=1 no altera resultados en imágenes con bloques discretos (cuadrantes de prueba).
- El archivo real con gradiente que daba 2 `MultiPolygon` de 100/140 fragmentos ahora da 2 `Polygon` limpios de una sola pieza.

**Decisiones tomadas:**
- `sigma=1.0` píxel como valor fijo inicial — no depende de la resolución real del GeoTIFF (heurística simple, igual que `área_mínima_m2=1000` y la tolerancia de simplificación ya existentes). Si en la práctica resulta insuficiente para ciertas resoluciones muy finas o gruesas, ajustar por sensor/resolución en una iteración futura.
- El suavizado se aplica solo en `ejecutar_pipeline` (el pipeline de producción), no dentro de `clasificar_ndvi`/`vectorizar_zonas` — mantiene esas funciones puras y testeables sin efectos secundarios ocultos para quien las llame directamente.

---

#### Análisis de robustez de los 4 índices + rename `ndvi.py` → `zonas.py`
**Fecha:** 2026-07-05
**Rama:** `main`

El usuario pidió analizar si NDVI, NDRE, SAVI y ExG pueden mostrarse en el mapa de la misma forma, y renombrar `ndvi.py` (nombre engañoso — el archivo es genérico para los 4 índices, no específico de NDVI).

**Hallazgo:** NDVI, NDRE y SAVI son índices "razón" (diferencia sobre suma) — su rango es siempre ~[-1,1] sin importar la escala de las bandas de entrada (reflectancia 0-1 o DN crudo sin calibrar), así que el umbral fijo `[0.20, 0.40, 0.70]` (agronómico, pensado para NDVI) aplica razonablemente a los tres. **ExG (`2·GREEN-RED-BLUE`) no es una razón — es una resta lineal absoluta cuya escala depende directamente de las unidades crudas de la cámara.** Verificado con datos controlados: en reflectancia 0-1 la vegetación sana da ExG≈0.5 (subestimada por el umbral); con DN de 8-bit sin calibrar da ExG≈130, muy por encima del máximo (0.70) — **el umbral fijo clasificaría todo el lote como "vigorosa" sin relación con el vigor real.**

**Cambios:**
- `workers/gis/ndvi.py` → `workers/gis/zonas.py` (`git mv`, preserva historial). Actualizadas todas las referencias: `workers/gis/pipeline.py`, `tests/test_clasificacion.py`, `tests/test_ndvi_pipeline.py`, `CLAUDE.md`.
- `workers/gis/pipeline.py`: nueva función `_metodo_umbral_efectivo(indice, metodo_umbral)` — si el índice es `exg` y no se pidió explícitamente un método adaptativo, fuerza `otsu` (calcula el corte según la distribución real de los datos, sea cual sea su escala) en vez de usar el umbral fijo. El método efectivamente usado se agrega a las estadísticas (`stats["metodo_umbral"]`) para transparencia.

**Verificación:** con datos sintéticos de reflectancia (mitad vegetación ExG≈0.5, mitad suelo ExG≈0.02), el fix separa correctamente el lote 50/50 en dos clases distintas vía Otsu, en vez de depender de un umbral absoluto que no tiene sentido para esa escala.

**Decisiones tomadas:**
- No se tocaron las funciones legacy `calcular_ndvi`/`leer_bandas`/`pipeline_ndvi` dentro de `zonas.py` (duplican lógica de `indices.py`, solo las usa el test standalone `test_ndvi_pipeline.py`, no el pipeline de producción) — fuera de alcance de esta tarea, es un cleanup aparte.

---

#### Multi-índice real: NDRE/SAVI/ExG dejan de ser cosmética en el wizard
**Fecha:** 2026-07-06
**Rama:** `main`

Hasta ahora el selector de índices del wizard de carga era **solo visual** — sin importar qué se tildara, el backend siempre calculaba NDVI nomás (hardcodeado en `crear_vuelo_desde_upload`). Esta tarea lo conecta de verdad: cada índice tildado se analiza en serio, y "Vista geoespacial" ahora tiene un selector para cambiar cuál ver.

**Modelo de datos:** un vuelo puede tener MUCHOS índices analizados, cada uno con su propio ciclo de vida async (pendiente → procesando → completado/error) — igual que un vuelo, pero acotado a un índice puntual. NDVI sigue siendo especial: se calcula siempre al subir (retrocompatible, vive en `vuelos.estado/geojson_key`, sin cambios); los adicionales (NDRE/SAVI/ExG) viven en una tabla nueva.

**Piezas implementadas:**
- Migración `0011` + modelo `AnalisisIndice` (`app/lotes/models.py`): `vuelo_id` FK CASCADE, `indice` (enum nuevo `IndiceEnum`), `estado`, `task_id`, `geojson_key`, `error_detalle`, `metodo_umbral`. Unique `(vuelo_id, indice)`.
- `workers/gis/tasks.py::analizar_indice` — tarea Celery nueva, reusa `ejecutar_pipeline` igual que `procesar_vuelo`, pero actualiza `analisis_indices` en vez de `vuelos`. GeoJSON se guarda como `zonas_{indice}.geojson` (NDVI sigue siendo `zonas.geojson`, sin prefijo, retrocompatible).
- Endpoints nuevos en `app/ingesta/router.py`: `GET/POST /lotes/{id}/vuelos/{id}/indices`, `GET .../indices/{indice}/estado`, `GET .../indices/{indice}/resultado`. El `GET` de listado sintetiza siempre una entrada `ndvi` (`es_primario: true`) desde el propio vuelo, sin duplicar datos.
- Frontend: `ModalCargaGeoTIFF.jsx` ahora dispara `analizarIndice()` para cada índice tildado (menos NDVI, que ya se calculó al subir). `useVueloProgreso` acepta un tercer parámetro `indice` y elige el endpoint correcto. `Dashboard.jsx`: "Vista geoespacial" pide `listarIndicesVuelo()` al seleccionar un vuelo y muestra un selector de pastillas (solo si hay más de un índice) para cambiar cuál ver — cada click cambia `selectedVuelo.indice` y el mapa vuelve a pollear ese índice puntual.

**Verificación E2E (API real, no scripts internos):** subida de un vuelo con `dji_mavic3` + disparo de SAVI y NDRE en paralelo → los 3 (NDVI+SAVI+NDRE) terminan `completado` y cada `resultado` devuelve su GeoJSON propio. Confirmado además que pedir `ExG` sobre `dji_mavic3` (sin Blue) falla con el mensaje de error correcto vía el nuevo endpoint de estado (`analisis_indices.error_detalle`), sin romper el resto del vuelo.

**Decisiones tomadas:**
- Reencolar (no duplicar) si el usuario pide el mismo índice dos veces sobre el mismo vuelo — `crear_analisis_indice` reutiliza la fila existente por el unique `(vuelo_id, indice)` en vez de fallar.
- El worker es un proceso de larga duración — cada vez que se agrega una tarea Celery nueva (`analizar_indice`) hay que reiniciarlo (`docker compose restart worker`) para que la registre; no hot-reload como la API.

---

#### Optimización de rendimiento del pipeline GIS
**Fecha:** 2026-08-04
**Rama:** `feat/optimizar-pipeline`

Se redujo drásticamente el tiempo de procesamiento de GeoTIFF para índices de vegetación, apuntando a < 1 minuto en cualquier tamaño dentro del límite de upload (3 GB). Cuatro cuellos de botella identificados y corregidos:

**Cambios en `workers/gis/zonas.py`:**
- `suavizar_indice`: reemplazado `gaussian_filter` por `uniform_filter` (filtro de caja 1D separable) — 3-5× más rápido para el mismo efecto práctico de reducción de sal-y-pimienta.
- `vectorizar_zonas`: una sola llamada a `shapes()` sobre el array `clase` completo en lugar de 4 llamadas (una por clase) — 4× más rápido en el paso de shapes.
- `vectorizar_zonas`: filtro de área movido ANTES del cálculo de estadísticas por polígono — evita computar stats para polígonos que se descartarán.
- `vectorizar_zonas`: el loop `geometry_mask` por polígono (O(n_polígonos × H×W)) reemplazado por `rasterize` + `np.bincount` vectorizado (O(H×W) constante sin importar cantidad de polígonos). Para 200 polígonos en un raster 10k×10k: de ~60 s a < 3 s solo en ese paso.

**Cambios en `workers/gis/pipeline.py`:**
- Downsampling automático para rasters > 9 MP (≈3000×3000 px): `_factor_downsample`, `_downsample_array`, `_downsample_meta` aplican average pooling NaN-safe antes de suavizar/clasificar/vectorizar. Las estadísticas globales (ndvi_promedio_lote, min/max) siguen usando la resolución completa. Para un lote de dron a 10 cm con 100ha (~100MP): factor 4, reduce a 25MP → todas las ops 16× más rápidas.

**Cambios en `workers/gis/reproyeccion.py`:**
- Salida de reproyección usa `rasterio.MemoryFile()` (VSIMEM de GDAL) en lugar de `io.BytesIO` — evita copias de buffer Python para archivos grandes.

**Decisiones tomadas:**
- Threshold de downsampling en 9 MP: por debajo de eso el pipeline ya es rápido; por encima activa reducción automática.
- `uniform_filter` con `size = max(3, int(sigma*3) | 1)` — equivalente práctico al gaussian para reducción de ruido pre-clasificación.
- Los porcentajes de clase (`porcentaje_px`) se calculan sobre el `clase` downsampled para mantener consistencia denominador/numerador.
- La precisión de los polígonos de salida se reduce al aplicar downsample, pero sigue siendo adecuada para zonas de manejo agrícola (mínimo 40m a 10× downsample de imagen 10cm).

---

#### Streaming upload/download para GeoTIFF > 3 GB
**Fecha:** 2026-08-04  
**Rama:** `main`

El sistema rechazaba archivos de más de 3 GB y cargaba en RAM el archivo completo en el API y en el worker. Refactor de todo el stack de I/O para que ningún componente necesite el archivo completo en memoria a la vez.

**Problema raíz (tres puntos):**
1. `app/ingesta/validator.py` rechazaba con HTTP 413 cualquier archivo > 3 GB.
2. `app/ingesta/router.py` hacía `await archivo.read()` — cargaba el archivo completo en RAM del contenedor API.
3. `workers/gis/tasks.py` hacía `download_geotiff(key)` → `response.read()` — cargaba el archivo completo en RAM del worker.

**Cambios:**
- `app/core/storage.py`: `upload_geotiff_stream(stream, length=-1)` — usa multipart upload de MinIO con partes de 64 MB sin buffer completo en RAM. `download_geotiff_to_file(key, destino)` — descarga en chunks de 8 MB directo a disco con `shutil.copyfileobj`.
- `app/ingesta/validator.py`: eliminado el límite de 3 GB y el chequeo de `len(contenido)`. Solo valida extensión y magic bytes (primeros 4 bytes).
- `app/ingesta/router.py`: lee solo los primeros 4 bytes para validación, luego `seek(0)` y pasa `archivo.file` (stream) a service. El archivo grande ya está en disco (SpooledTemporaryFile de Starlette) — no se carga en RAM.
- `app/ingesta/service.py`: firma cambiada de `file_data: bytes` a `file_stream + file_size` en `crear_vuelo_desde_upload` y `crear_lote_y_vuelo_desde_geotiff`.
- `workers/gis/reproyeccion.py`: `reproyectar_a_4326_archivo(src_path, dst_path)` — reproyecta de disco a disco. GDAL hace el I/O tileado sin cargar el raster completo en RAM. El archivo destino se escribe con `compress=lzw, tiled=True`.
- `workers/gis/pipeline.py`: `ejecutar_pipeline_archivo(path, ...)` — versión file-path del pipeline. `rasterio.open(path)` + `src.read(banda)` carga solo las bandas necesarias (no el archivo entero). `ejecutar_pipeline(data, ...)` se mantiene intacto para los tests.
- `workers/gis/tasks.py`: `procesar_vuelo` y `analizar_indice` usan `download_geotiff_to_file` + `ejecutar_pipeline_archivo`. Los archivos temporales se limpian en bloques `finally` para no acumular basura en disco.

**Decisiones tomadas:**
- `length=-1` para multipart upload: no requiere conocer el tamaño del archivo antes de empezar. MinIO gestiona las partes internamente.
- Eliminar el límite de tamaño en la capa API: el límite de almacenamiento lo define MinIO/disco. Si se necesita un límite por razones de negocio, configurar en nginx al llegar a producción.
- Mantener `_validar_geotiff_gis(data: bytes)` además de la nueva `_validar_geotiff_gis_archivo(path)` — backward compat con los tests que usan bytes sintéticos.
- El inspector de bandas TIFF ya funcionaba solo con los primeros bytes (lee IFD del header) — solo se redujo el read de full-file a 512 bytes.

---

#### Optimización automática de GeoTIFF en el worker (pre-compresión)
**Fecha:** 2026-08-04  
**Rama:** `main`

Archivos de dron exportados sin compresión y con layout strip-based (como "Recorte 1.tif" de 916 MB) tardaban varios minutos porque GDAL tiene que leer el archivo completo desde el inicio para acceder a cualquier banda. Con el formato tileado, GDAL accede directamente al bloque de 512×512 px que necesita, sin pasar por el resto del archivo.

**Cambio:** `workers/gis/tasks.py` — función `_optimizar_si_necesario(src_path)` llamada automáticamente en `procesar_vuelo` y `analizar_indice`, entre la validación y el inicio del pipeline. La función:
1. Lee solo el perfil del archivo (rápido — no carga datos).
2. Si ya tiene compresión Y tileado: retorna `src_path` sin tocar nada.
3. Si falta cualquiera de los dos: reescribe con DEFLATE + predictor=2 + tiles 512×512, usando lectura por ventanas (nunca carga una banda completa en RAM), borra el original y retorna la ruta del nuevo archivo.

Si la optimización falla (e.g. disco lleno), se loguea un warning y el pipeline continúa con el archivo original (degradación graceful, no error fatal).

**Decisiones tomadas:**
- DEFLATE en lugar de LZW: mejor ratio para datos de índices espectrales (float32 con muchos NaN).
- `predictor=2` (diferenciación horizontal): compatible con todos los tipos de dato (float32, uint8, uint16). `predictor=3` (float) tiene mejor compresión pero soporte variable entre versiones de GDAL.
- Window-based copy con `dst.block_windows(1)`: jamás se carga más de un tile (512×512 px × n_bandas) en RAM, independientemente del tamaño del archivo.
- La función no fuerza la compresión sobre archivos ya optimizados → Sentinel-2 COGs que ya vienen comprimidos+tileados no pagan ningún costo extra.

---

#### Fix: pantalla en blanco al visualizar análisis con GeoJSON grande
**Fecha:** 2026-08-04  
**Rama:** `main`

Al completar el análisis de un GeoTIFF de Sentinel-2 (3000×3000 px), el pipeline generaba 3 567 polígonos y un GeoJSON de 8.7 MB. Al hacer clic en "Ver análisis" el navegador quedaba con pantalla en blanco sin mensaje de error. Dos causas:

1. **Stack overflow en cálculo de bounds**: `MapaIndice.jsx` usaba `Math.min(...lats)` con spread sobre un array de cientos de miles de coordenadas — el motor JS lanza `RangeError: Maximum call stack size exceeded` silencioso.
2. **Demasiados polígonos para Leaflet**: React-Leaflet intentaba crear 3 567 capas DOM + event listeners + tooltips de golpe, agotando memoria en el render thread.

**Cambios:**

- `workers/gis/zonas.py`: `AREA_MINIMA_M2` subido de 1 000 a 10 000 m² (1 ha). Para Sentinel-2 a 10 m/px, 1 ha = 100 píxeles — umbral razonable que elimina ruido sin perder zonas reales. Reduce el conteo de ~3 500 a decenas de polígonos en imágenes de escala kilométrica.
- `frontend/src/components/MapaIndice.jsx`: bounds calculados con loop iterativo en lugar de spread + `Math.min/max` — O(coordenadas) sin riesgo de stack overflow independientemente del tamaño del GeoJSON.
- `frontend/src/components/MapaIndice.jsx`: guardia `MAX_FEATURES_RENDER = 1500` — si el GeoJSON supera ese umbral se muestra un mensaje informativo en lugar de intentar renderizar (protección para análisis de drones de muy alta resolución).
- `frontend/src/components/MapaIndice.jsx`: `MapaBoundary` (React class error boundary) envuelve el `MapContainer` — cualquier excepción futura en el render del mapa muestra el mensaje de error en lugar de pantalla en blanco.

**Decisiones tomadas:**
- 10 000 m² como umbral general en el worker, no por sensor — si en el futuro se procesan drones de alta resolución donde 1 ha es excesivo, el parámetro `area_minima_m2` ya es configurable por llamada en `vectorizar_zonas` y `ejecutar_pipeline`.
- La guardia de 1 500 features en el frontend es una red de seguridad adicional, no la solución principal — la solución real es el threshold de área en el worker.

---

#### Fix: GeoTIFF de dron no se veía en el mapa (CRS EngineeringCRS mal resuelto + límite 4 GiB de TIFF)
**Fecha:** 2026-08-04
**Rama:** `main`

Tres archivos reales subidos por el usuario ("ORTOMOSAICO.tif" de Pix4D, 2.7 GB, y dos "Recorte de la prueba N.tif") no se visualizaban. Se probó cada uno directamente contra el worker (`docker compose exec worker`, copiando los archivos con `docker cp`) para separar problema de datos vs. de código:

- **"Recorte de la prueba 1.tif"**: las 4 bandas están 100% vacías (`STATISTICS_VALID_PERCENT=0`, todo NaN) — no es un bug, es un archivo de exportación corrupto/vacío. La validación de imagen vacía agregada hoy en `_validar_geotiff_gis_desde_src` (muestra 128×128) lo detecta y rechaza correctamente.
- **"Recorte de la prueba 2.tif"**: tiene datos válidos (50%), CRS EPSG:4326 correcto — sin problema de código, solo se beneficia de la optimización de compresión/tileado agregada hoy.
- **"ORTOMOSAICO.tif"**: expuso dos bugs reales de código, además de un tercero de alineación de validación:

**Bug 1 — método inexistente:** `_resolver_crs()` y la detección de `EngineeringCRS` en `tasks.py` llamaban `crs.to_json_dict()`. Ese método existe en `pyproj.CRS` pero **no en `rasterio.crs.CRS`** (la clase real de `src.crs`) — lanzaba `AttributeError`, silenciado por un `except Exception: pass`, así que la detección nunca se activaba y el pipeline moría más adelante con el error crudo de PROJ (`Cannot find coordinate operations from ... to EPSG:4326`).

**Bug 2 — `reproject()` ignora `src_crs` con fuente tipo `Band`:** aun resolviendo bien el CRS, `rasterio.warp.reproject(source=rasterio.band(src, i), ...)` relee el CRS directamente de los metadatos del dataset en disco/memoria, **ignorando el parámetro `src_crs` explícito**. Confirmado reproduciendo el fallo con el archivo real. Solución: corregir el CRS embebido antes de reproyectar — `rasterio.open(path, "r+")` + `dst.crs = src_crs` para archivos en disco; para el flujo en memoria (bytes), como `MemoryFile` no admite reasignar `.crs` en modo `r+`, se reescribe una copia en un nuevo `MemoryFile` con el CRS ya corregido.

**Bug 3 — límite de 4 GiB de TIFF clásico:** al reproyectar, el bounding box rotado de "ORTOMOSAICO.tif" se expande al alinearse a ejes (18878×41050 → 22442×39216 px), y el archivo de salida se acerca/supera 4 GiB. Sin `BIGTIFF`, GDAL falla a mitad de escritura (`error occurred while writing a dirty block`). Se agregó `bigtiff="IF_SAFER"` al perfil de salida en `reproyectar_a_4326_archivo` y en `_optimizar_si_necesario`.

**Ajuste de alineación:** la validación de `EngineeringCRS` en `_validar_geotiff_gis_desde_src` rechazaba con error duro *cualquier* `EngineeringCRS`, pero corre **antes** de la reproyección en el pipeline (`procesar_vuelo`/`analizar_indice`) — con el Bug 1 corregido, esa validación bloqueaba archivos que `reproyectar_a_4326_archivo` ya sabe resolver. Ahora solo rechaza cuando el CRS no trae un código EPSG reconstruible (mismo criterio que `_resolver_crs`).

**Cambios:**
- `workers/gis/reproyeccion.py`: `_resolver_crs()` usa `json.loads(crs._projjson())` en vez de `crs.to_json_dict()`. `reproyectar_a_4326_archivo()` corrige el CRS in-place (`r+`) antes de reproyectar y agrega `bigtiff="IF_SAFER"`. `reproyectar_a_4326()` (bytes) reescribe una copia corregida en `MemoryFile` cuando hace falta.
- `workers/gis/tasks.py`: mismo fix de `_projjson()` en la detección de `EngineeringCRS`; el rechazo ahora solo aplica cuando no hay código EPSG recuperable; `_optimizar_si_necesario()` agrega `bigtiff="IF_SAFER"`.

**Verificación:** reproyección end-to-end del archivo real de 2.7 GB completada en ~972 s con CRS final EPSG:4326 y bounds válidos. Los 37 tests de la suite GIS (`test_indices_worker`, `test_clasificacion`, `test_ndvi_pipeline`, `test_celery_integracion`) pasan sin cambios.

**Decisiones tomadas:**
- No se intentó "arreglar" los archivos vacíos/corruptos del usuario — la validación de imagen vacía ya los detecta correctamente, el problema es de origen (exportación).
- Se mantiene `bigtiff="IF_SAFER"` (no `"YES"` forzado) para no penalizar con overhead de BigTIFF a archivos pequeños que nunca se acercan al límite.

---

#### Pantalla "Lotes" + navegación real del sidebar + botón expandir mapa
**Fecha:** 2026-07-06
**Rama:** `main`

El sidebar tenía 3 items de "PRINCIPAL" que no llevaban a ningún lado (solo cambiaban un estado local sin efecto visible) y "Diagnósticos" mostraba un badge "2" que no correspondía a nada real. Se conecta la navegación de verdad y se agrega la pantalla de lotes que faltaba.

**Cambios:**
- `frontend/src/components/SidebarNav.jsx` (nuevo, extraído de `Dashboard.jsx` donde estaba duplicado sin reutilizarse): "Dashboard" y "Lotes" navegan de verdad vía `react-router` (`useNavigate`/`useLocation` para resaltar el activo por `pathname`); "Cargar Ortomosaico" dispara un callback (`onCargarOrtomosaico`) que cada página resuelve abriendo su propio `ModalCargaGeoTIFF`; "Diagnósticos"/"Informes"/"Configuración" quedan deshabilitados con tag "Próximamente" — se sacó el badge "2" que no reflejaba nada real.
- `frontend/src/pages/Lotes.jsx` (nueva) + ruta `/lotes` en `App.jsx`: grilla de cards con nombre, cultivo, área, cantidad de vuelos y fecha — cada card tiene botón "Ver detalle" (`/lotes/{id}`, reusa `DetalleLote.jsx` ya existente) y "Eliminar" (soft delete, reusa `ModalConfirmarEliminar.jsx`). El endpoint `DELETE /lotes/{id}` ya existía en el backend (`app/lotes/router.py`) — no hizo falta tocar nada ahí.
- `frontend/src/api/lotes.js` (nuevo): `listarLotes()`, `eliminarLote()`.
- `Dashboard.jsx`: removida la definición local (duplicada) de `SidebarNav` y el estado `activeSection` que ya no se usa.

**Verificación E2E (API real):** crear lote → aparece en `GET /lotes` → `DELETE /lotes/{id}` → 204 → ya no aparece en el listado (soft delete confirmado).

**Decisiones tomadas:**
- No se replicaron campos que no existen en el modelo de datos (el mockup de referencia tenía "ID de Reporte", "ubicación" como texto) — la card muestra solo datos reales (`nombre`, `cultivo`, `area_ha`, cantidad de vuelos, `created_at`).
- `SidebarNav` quedó como componente compartido en vez de duplicarse en cada página nueva — cualquier página futura que necesite el sidebar completo lo importa y le pasa `onCargarOrtomosaico`.

---

#### Motor de reglas de diagnóstico (RFDR-01)
**Fecha:** 2026-08-27
**Rama:** `main`

Se implementó el motor de reglas de diagnóstico completo a partir de un documento de referencia provisto por el usuario (20 reglas en 9 bloques, extraídas de `AgroNexo_Motor_Reglas_Referencia.docx`). Dado un análisis ya calculado (NDVI + opcionalmente NDRE/SAVI/ExG/GNDVI), el motor evalúa cada zona vectorizada contra las reglas en cascada y devuelve causa probable, nivel de confianza, acción recomendada, cómo confirmar en campo y productos sugeridos.

**Decisiones de alcance acordadas con el usuario antes de implementar:**
- Sin persistencia por ahora — el diagnóstico se calcula on-demand (síncrono) en cada `GET`, sin tabla nueva ni Celery. Ver "Problemas abiertos" — el usuario ya anticipó que el historial persistido es tarea de una release futura (release 4).
- GNDVI se agregó como quinto índice (antes solo NDVI/NDRE/SAVI/ExG) para cubrir la única regla del documento que lo requiere (R21, enfermedad tardía en soja).

**Piezas implementadas:**
- `workers/gis/indices.py` + `band_mapping.py` + `app/lotes/models.py` (`IndiceEnum.gndvi`): GNDVI como quinto índice, mismo patrón que NDRE/SAVI/ExG. Migraciones `0012` (ALTER TYPE del enum Postgres) y `0013` (`estadio_fenologico` de `VARCHAR(10)` a `VARCHAR(30)`, para tokens de algodón como `apertura_de_capsulas`).
- `app/diagnostico/forma.py` (nuevo): clasificación de patrón espacial (circular, lineal, difuso_homogeneo, manchas_irregulares, bordes_lote, focos_aislados, por_sectores) — no existía ningún cálculo de esto en el código, era solo aspiracional en CLAUDE.md. Heurística con Shapely puro (circularidad, elongación vía `minimum_rotated_rectangle`, distancia/fracción de borde, densidad de zonas por clase).
- `app/diagnostico/estadios.py`, `productos.py`, `reglas.py` (las 20 reglas), `engine.py` (evaluador en cascada), `service.py` (orquestación: MinIO + DB), `router.py`: `GET /api/v1/lotes/{lote_id}/vuelos/{vuelo_id}/diagnostico`.

**Decisión de arquitectura no obvia — sin GeoPandas en `app/diagnostico/`:** el primer intento usó GeoPandas (igual que `workers/gis/zonas.py`) tanto en `workers/gis/forma.py` como en `app/diagnostico/service.py`. Al correr los tests contra el contenedor `api` real, falló con `ModuleNotFoundError: No module named 'geopandas'` — `docker/requirements.api.txt` deliberadamente no incluye GeoPandas/GDAL (esas dependencias pesadas están reservadas al worker, ver CLAUDE.md: "El Worker GIS es un proceso separado"). Como el motor de diagnóstico corre dentro del proceso FastAPI (no reprocesa el GeoTIFF, solo lee GeoJSON ya generado), se rediseñó `app/diagnostico/forma.py` con Shapely puro + una proyección equirectangular local (matemática pura, sin pyproj) para convertir grados a metros locales antes de medir área/perímetro/distancias. `workers/gis/forma.py` se eliminó (la lógica vive en `app/diagnostico/`, no en `workers/gis/`, porque no corre en el worker).

**Resolución de reglas multi-índice (R10 malezas: NDVI+ExG; R44 fósforo: NDVI+NDRE):** los índices se vectorizan de forma independiente (bordes de polígono distintos entre NDVI y ExG del mismo vuelo). Se resuelve con `enriquecer_con_indice()`: para cada zona NDVI (partición canónica), se calcula el promedio del otro índice ponderado por área de intersección geométrica real contra el GeoDataFrame de ese índice. Si el segundo índice no fue calculado para ese vuelo, la regla se salta sin error (cae al siguiente nivel del cascade).

**Verificación:**
- 39 tests nuevos (`test_forma.py`, `test_diagnostico_engine.py`, `test_diagnostico_api.py`) + 1 test agregado a `test_indices_worker.py` (GNDVI) — todos pasando, agregados al CI.
- Suite completa existente (86 tests API + 38 tests GIS) sigue pasando sin regresiones.
- Verificación E2E manual contra el stack Docker real: lote soja (R2) + GeoTIFF sintético con una zona circular de NDVI bajo (~0.30) → `GET .../diagnostico` devolvió `regla_id=R20` (enfermedad fúngica) con confianza alta y los 5 fungicidas correctos; la zona sana circundante cayó correctamente en `R99`.

**Bug real encontrado y corregido — "Ver resultados" navegaba a `vuelos/undefined`**
Al probar la integración desde la UI real (no Swagger), `DetalleLote.jsx` → botón "Ver resultados" navegaba a `/lotes/{id}/vuelos/undefined`, rompiendo el acceso a la página de resultados (y por lo tanto a la nueva pestaña de Diagnóstico) para cualquier usuario real. Causa raíz: `GET /lotes/{id}/vuelos` (`app/ingesta/router.py`, schema `VueloListItem`) devuelve el id del vuelo en el campo `vuelo_id` (mismo criterio que `VueloUploadResponse`), pero `DetalleLote.jsx` leía `vuelo.id` (inexistente en la respuesta). `Dashboard.jsx` ya tenía el fallback correcto (`v.vuelo_id ?? v.id`) — `DetalleLote.jsx` nunca lo tuvo. Esto es lo mismo que la falla ya registrada como "Problema abierto #3" (`tests/test_vuelos_estado.py::test_listar_vuelos_de_lote`, `KeyError: 'id'`) — no era un conflicto de rutas como se sospechaba inicialmente, sino un desajuste simple de nombre de campo entre frontend y API.

**Cambios:**
- `frontend/src/pages/DetalleLote.jsx`: los 5 usos de `vuelo.id`/`v.id` pasan a `vuelo.vuelo_id`/`v.vuelo_id`.
- `tests/test_vuelos_estado.py::test_listar_vuelos_de_lote`: corregida la aserción para esperar `vuelo_id` (el test tenía la misma suposición incorrecta que el componente).

**Verificación:** reproducido el bug en vivo con Claude in Chrome navegando el flujo real (Dashboard → Lotes → detalle de lote → "Ver resultados"), confirmado el fix con el mismo flujo, y `tests/test_vuelos_estado.py` completo (13 tests) pasa.

**Decisiones tomadas:**
- `ndvi_promedio` (nombre de columna heredado de `zonas.py`, fijo sin importar el índice real procesado) no se renombra — es un contrato de API vivo consumido por `MapaIndice.jsx`, `TablaZonas.jsx` y `MapaZonas.jsx` (confirmado por grep). El motor de reglas simplemente sabe leerlo como "el valor del índice que sea".
- Catálogo de estadios fenológicos válidos (`app/diagnostico/estadios.py`) extraído de la **sección 5** del documento de referencia (las condiciones de cada regla), no de la sección 3 (descriptiva, con tokens más largos e inconsistentes entre cultivos).

---

#### Caché de GeoTIFF preparado + fix leyenda tapando modales + fix overflow en tarjetas de diagnóstico
**Fecha:** 2026-08-28
**Rama:** `main`

El usuario reportó que el cálculo de índices era muy lento, más al pedir varios sobre el mismo vuelo, y dos bugs de UI: la leyenda de colores del mapa se proyectaba por encima de cualquier modal (tapando información al cargar un ortomosaico nuevo), y en la pestaña Diagnóstico había textos que se salían de la tarjeta sin poder leerse completos.

**Causa raíz del rendimiento:** cada índice adicional (NDRE/SAVI/ExG/GNDVI) pedido sobre un vuelo ya existente (`workers/gis/tasks.py::analizar_indice`) volvía a descargar el archivo original completo desde MinIO y repetía desde cero la optimización (recompresión tileada) y la reproyección a EPSG:4326 — el mismo trabajo pesado que `procesar_vuelo` ya había hecho para el NDVI del mismo vuelo, sin ningún tipo de caché entre llamadas.

**Cambios — caché del GeoTIFF preparado:**
- `app/core/storage.py`: `object_exists(key)` (HEAD sin descargar) y `upload_file(key, local_path)` (`fput_object`, streaming sin cargar en RAM).
- `workers/gis/tasks.py`: nuevas funciones `_key_preparado()` (deriva `.../preparado_4326.tif` del key del original), `_preparar_geotiff()` (reproyecta si hace falta — reproyectar ya deja el archivo tileado+comprimido, así que solo se corre `_optimizar_si_necesario` por separado si NO hace falta reproyectar, evitando reescribir el archivo dos veces), `_descargar_preparado()` y `_guardar_preparado_en_cache()`. `procesar_vuelo` y `analizar_indice` ahora chequean la caché antes de descargar/validar/optimizar/reproyectar — si existe, se saltan esos pasos enteros y solo calculan el índice pedido. `procesar_vuelo` además ya no reproyecta dos veces para extraer el bounding box del lote — lee los bounds directo del archivo ya preparado.
- Sin migración de BD: la clave de caché se deriva del `minio_key` existente (mismo prefijo `{usuario}/{lote}/{vuelo}/`), no hace falta persistir nada nuevo.

**Verificación de la caché:** probado en vivo contra el stack real — primer pedido de un índice nuevo (GNDVI) sobre un vuelo existente mostró `cache=False` + los pasos de optimización/reproyección en los logs del worker; un segundo pedido sobre el mismo vuelo mostró `cache=True` y saltó completamente esos pasos (`GeoTIFF preparado encontrado en caché`).

**Fix — leyenda de mapa tapando modales:** `.mapa-leyenda` y `.modal-overlay` compartían el mismo `z-index: 1000` en `frontend/src/index.css` — al empatar, ganaba el que apareciera después en el DOM, que en el Dashboard (mapa "Vista geoespacial" persistente) terminaba siendo la leyenda. Se subió `.modal-overlay` a `z-index: 2000`.

**Fix — texto desbordado en tarjetas de Diagnóstico:** bug clásico de flexbox — `.diagnostico-card-header` (flex row con el nombre de la regla + badge de confianza) no tenía `min-width: 0` en el span de texto, así que nombres de regla largos ("Enfermedad fúngica en soja — estadio reproductivo") no envolvían y desbordaban la tarjeta en vez de hacer wrap. Se agregó `min-width: 0` + `overflow-wrap: break-word` al texto y `flex-wrap: wrap` al header; mismo tratamiento preventivo en `.diagnostico-accion`, `.diagnostico-confirmar p` y `.diagnostico-card-meta`. `.resultados-sidebar` suma `overflow-x: hidden` como red de seguridad adicional.

**Verificación de los dos fixes de UI:** reproducidos y confirmados en vivo con Claude in Chrome (Dashboard con mapa+leyenda abierto → modal "Cargar Ortomosaico" ahora aparece por encima; pestaña Diagnóstico con el nombre de regla largo ahora hace wrap dentro de la tarjeta sin desbordar).

**Decisiones tomadas:**
- Caché best-effort: si `_guardar_preparado_en_cache` falla (ej. MinIO caído momentáneamente), se loguea un warning y el pipeline sigue con el archivo ya preparado en memoria — nunca bloquea el análisis en curso, solo se pierde el beneficio de caché para la próxima llamada.
- No se creó un mecanismo de invalidación de caché — la clave depende solo del vuelo (que nunca cambia de archivo original una vez subido), así que la caché es válida indefinidamente para ese vuelo. Un "reintentar" vuelo reusa el mismo `archivo_original`, por lo que también se beneficia de la caché si ya existe.

---

#### Cálculo batch de múltiples índices (evita releer el GeoTIFF una vez por índice)
**Fecha:** 2026-08-28
**Rama:** `main`

El usuario reportó que probar el motor de diagnóstico con imágenes más pesadas "se hacía imposible" al tildar varios índices (NDRE/SAVI/ExG/GNDVI) al subir un vuelo — su teoría era que la imagen se reducía (downsample) 3 veces antes de los cálculos.

**Diagnóstico (la teoría del usuario era incorrecta):** revisando `workers/gis/pipeline.py`, el downsample ocurre una sola vez por corrida de pipeline, y ocurre **después** de calcular el índice a resolución completa, no antes. El cuello de botella real es otro: `ModalCargaGeoTIFF.jsx` disparaba un `POST /indices` **por cada índice tildado** (`Promise.allSettled`), y cada uno encolaba una task de Celery independiente (`analizar_indice`) que repetía el pipeline completo desde cero — descarga del GeoTIFF preparado desde MinIO, lectura de banda(s) a resolución completa, cálculo — aunque la caché de `_preparar_geotiff` (ver tarea anterior) ya evitara repetir la reproyección/optimización. Con 3-4 índices tildados, el archivo se descargaba 3-4 veces y bandas compartidas (NIR la usan NDVI/NDRE/SAVI/GNDVI, RED la usan NDVI/SAVI/ExG) se releían 3-4 veces cada una.

**Cambios:**
- `workers/gis/pipeline.py`: extraído `_procesar_indice_desde_bandas()` (núcleo compartido: calcular índice → downsample → suavizar → clasificar → vectorizar → exportar → estadísticas) reusado por `ejecutar_pipeline`/`ejecutar_pipeline_archivo` (sin cambio de comportamiento) y por la nueva `ejecutar_pipeline_multi_indice_archivo()`, que reproyecta y abre el archivo **una sola vez** y lee cada banda distinta **una sola vez** con un cache compartido entre índices de la lista. Un índice que falla (banda faltante para ese índice puntual) no aborta los demás — vía callbacks `on_indice_completado`/`on_indice_error`.
- `workers/gis/tasks.py`: extraído `_preparar_archivo_para_pipeline()` (descarga con caché + validación + optimización/reproyección, antes triplicado entre `procesar_vuelo`/`analizar_indice`/la nueva task). Nueva task `analizar_indices_batch(analisis_ids, minio_key, sensor, indices, ...)` — `analisis_ids` mapea índice → fila `AnalisisIndice`, cada una se actualiza de forma independiente a medida que su índice termina (o falla), así que el polling por índice existente no se tocó.
- `app/ingesta/schemas.py` (`IndicesBatchRequest`/`IndicesBatchIniciarResponse`), `service.py` (`crear_analisis_indices_batch` — crea las filas y encola UNA sola task con todos los índices), `router.py` (`POST /{lote_id}/vuelos/{vuelo_id}/indices/batch`, nuevo, no reemplaza el endpoint single).
- `frontend/src/api/analisis.js` (`analizarIndicesBatch`), `ModalCargaGeoTIFF.jsx`: el `Promise.allSettled` de un POST por índice pasa a un único `POST .../indices/batch`.

**Decisiones tomadas:**
- El endpoint/task single (`POST .../indices`, `analizar_indice`) se mantiene intacto — sigue siendo el camino para cuando el usuario pide un único índice adicional después de subir (switcher de `Dashboard.jsx`). El batch solo se usa al tildar varios índices juntos en el modal de carga.
- Las filas `AnalisisIndice` del batch comparten el mismo `task_id` de Celery (una sola task real) pero se actualizan individualmente en DB — el frontend (`useVueloProgreso.js`) no necesitó ningún cambio, sigue haciendo polling por índice contra `GET .../indices/{indice}/estado`.

**Verificación:**
- `tests/test_indices_worker.py`: 2 tests nuevos — `test_pipeline_multi_indice_bandas_compartidas` (el batch da exactamente el mismo resultado que llamar al pipeline individual por índice) y `test_pipeline_multi_indice_error_no_aborta_batch` (ExG sin banda Blue en DJI falla sin frenar el cálculo de NDVI en la misma corrida). Suite completa (17 tests) pasando.
- Suites existentes sin regresiones: `test_ingesta_worker.py`, `test_celery_integracion.py` (E2E real contra MinIO+Redis+worker), `test_vuelos_estado.py` + `test_diagnostico_api.py` (21 tests API) — todo verde tras el refactor de `tasks.py`/`pipeline.py`.
- Verificación E2E manual contra el stack Docker real (API + worker + MinIO reales, usuario/lote/vuelo de prueba creados y luego eliminados): `POST .../indices/batch` con `["ndre","savi","gndvi"]` devolvió las 3 filas con el mismo `task_id`; logs del worker confirmaron **una sola** línea de descarga MinIO, **una sola** reproyección, y 4 lecturas de banda distintas (NIR, RE, RED, GREEN — sin repetir NIR entre NDRE/SAVI/GNDVI); `GET .../diagnostico` devolvió `indices_disponibles: [ndvi, ndre, savi, gndvi]`.

---

#### Fix crítico: OOM del worker + reproyección duplicada en imágenes grandes reales
**Fecha:** 2026-08-28
**Rama:** `main`

Al probar la tarea anterior (batch de índices) con una imagen real de producción (2.5 GB, no un fixture sintético), aparecieron dos problemas graves que el usuario resumió como "sigue tardando demasiado, esto no lo puedo publicar así" — verificados en vivo contra el stack Docker real, no en tests.

**Bug 1 — reproyección duplicada por condición de carrera:** el frontend dispara `POST /vuelos` (NDVI) y, apenas responde, `POST /indices/batch` (NDRE/SAVI/GNDVI) casi al mismo tiempo. Ambas tasks de Celery (`procesar_vuelo` y `analizar_indices_batch`) revisan la caché de `preparado_4326.tif` antes de reproyectar — pero como NDVI todavía no terminó de escribirla, el batch no la encuentra y **también** descarga y reproyecta el archivo de 2.5 GB desde cero, en paralelo. Confirmado en los logs reales: dos reproyecciones simultáneas de **672 s y 671 s** (~11 min cada una, compitiendo por CPU) en vez de una sola.

**Bug 2 — out-of-memory real, worker matado con SIGKILL:** `workers/gis/pipeline.py::_leer_bandas_requeridas` leía cada banda a resolución completa (`src.read(num)`) y recién *después* de calcular el índice se aplicaba el downsample (ver tarea de "caché de GeoTIFF preparado"). Para un raster grande ya reproyectado, una sola banda float32 puede pesar varios GB — con el VM de Docker Desktop en 7.4 GiB compartidos entre todos los servicios, el proceso terminó devorando >4 GiB y el kernel lo mató: `billiard.exceptions.WorkerLostError: Worker exited prematurely: signal 9 (SIGKILL)`. El vuelo real del usuario quedó trabado en `estado='procesando'` para siempre (el `except`/`finally` que marca error nunca corrió porque el proceso fue matado, no lanzó una excepción Python) — se corrigió a mano en la base (`UPDATE vuelos/analisis_indices SET estado='error'`) para que "Reintentar" funcione.

**Cambios:**
- `workers/gis/tasks.py`: nuevo lock distribuido en Redis (`_cliente_redis_lock`, `_esperar_preparacion_en_curso`, TTL 30 min) dentro de `_preparar_archivo_para_pipeline` — si dos tasks del mismo vuelo intentan optimizar/reproyectar a la vez, la segunda espera (sondeando cada 3s si la caché ya está lista) y la reusa, en vez de reproyectar en paralelo. Si Redis no responde por algún motivo, se sigue sin lock (mismo comportamiento que antes) en vez de bloquear el pipeline — nunca es un punto de falla dura.
- `workers/gis/pipeline.py`: nueva `_leer_banda()` — si el raster supera `_UMBRAL_DOWNSAMPLE_PX` (9M px), lee la banda **ya decimada por GDAL** (`out_shape` + `Resampling.average`, `masked=True` para no promediar el nodata crudo del borde) en vez de leer a resolución completa y reducir después en NumPy. `_procesar_indice_desde_bandas` se simplificó — ya no hay downsample posterior al cálculo, todo (índice, estadísticas, vectorización) corre sobre la resolución que decidió `_leer_banda`. Se eliminó `_downsample_array` (ya no se usa).

**Decisión de trade-off no obvia:** antes, las estadísticas globales del lote (min/max/promedio) se calculaban siempre sobre resolución completa por diseño explícito (documentado en un comentario que ahora se removió). Con este cambio, para rasters grandes las estadísticas se calculan sobre la resolución ya decimada, no la completa — se prioriza que el análisis **termine sin tirar el worker** por sobre precisión estadística exacta en imágenes muy grandes. La diferencia es marginal en la práctica (promediar bandas antes de calcular el índice vs. promediar el índice ya calculado da resultados muy cercanos para vegetación con variación suave), y no aplica en absoluto a rasters por debajo del umbral (la inmensa mayoría de los casos reales).

**Verificación:**
- 2 tests nuevos en `test_indices_worker.py`: `test_lectura_decimada_raster_grande_no_materializa_resolucion_completa` (raster sintético 3100×3100 con borde de nodata — confirma shape decimada correcta y que el nodata crudo no contamina el promedio) y `test_pipeline_archivo_grande_completa_sin_cargar_resolucion_completa` (pipeline completo end-to-end sobre ese mismo raster). Suite completa (19 tests) pasando.
- Reproducción real del bug del lock: dos tasks de Celery reales (`procesar_vuelo` + `analizar_indices_batch`) disparadas casi simultáneamente sobre el mismo archivo (100 MB, UTM, fuerza reproyección) — **antes** del fix ambas reproyectaban (6.05s y 6.19s cada una); **después** del fix, logs confirmaron que solo una reproyectó y la otra esperó y reusó ("otro análisis del mismo vuelo ya preparó el archivo (6s esperados) — se reusa").
- Detectado y corregido en el camino un bug real en el primer intento del lock: `object_exists` no estaba importado dentro de `_esperar_preparacion_en_curso`, así que el lock fallaba silenciosamente (`NameError` capturado por el `except Exception` defensivo) y ambas tasks reproyectaban igual — encontrado recién al probar la carrera real contra el stack, no en tests unitarios.
- Suites existentes sin regresiones: `test_ndvi_pipeline.py`, `test_clasificacion.py` (16 tests), `test_celery_integracion.py` (E2E real), `test_vuelos_estado.py` + `test_diagnostico_api.py` (21 tests API).

**Problema abierto (no resuelto en esta tarea):** el worker sigue sin límite de memoria explícito (`mem_limit` en `docker-compose.yml`) ni límite de concurrencia acorde a la RAM disponible (`concurrency: 16` por defecto de Celery, heredado del conteo de CPUs) — con Docker Desktop en 7.4 GiB totales, varias tasks pesadas concurrentes (aunque ya no dupliquen trabajo entre sí) todavía podrían competir por memoria. Ver "Problemas abiertos".

**Addendum — mismo día, probando contra el archivo real de producción (2.5 GB):**

**Bug 3 — `TypeError: Cannot convert fill_value nan to dtype uint8`:** al probar el fix anterior contra el archivo real (no un fixture sintético — todos los fixtures de test usan `dtype="float32"`), `_leer_banda()` reventó: el archivo real tiene bandas en `uint8` (DN crudo sin calibrar), y `np.ma.filled(banda, np.nan)` no puede rellenar un array entero con NaN. Fix: castear a `float32` **antes** de rellenar (`np.ma.filled(banda.astype(np.float32), np.nan)`) — un `MaskedArray.astype()` preserva la máscara. Test de regresión agregado: `test_lectura_decimada_dtype_entero_no_falla` (raster sintético `uint8` que cruza el umbral de downsample).

**Optimización adicional — reproyección con GDAL multi-hilo:** con el lock puesto, la reproyección del archivo real de 2.5 GB seguía tardando ~11-16 min (942s medido, con variación entre corridas por contención de recursos) porque `rasterio.warp.reproject()` usa `num_threads=1` y `warp_mem_limit=0` (~64 MB de caché) por defecto — fuerza a GDAL a hacer muchas pasadas chicas en un solo hilo para un archivo de varios GB. Se agregó `num_threads=4` y `warp_mem_limit=512` (MB) a las dos llamadas a `reproject()` en `workers/gis/reproyeccion.py` (`_WARP_NUM_THREADS`/`_WARP_MEM_LIMIT_MB`, valores conservadores a propósito porque el worker corre con `concurrency=16` y varias tasks podrían reproyectar a la vez). **Importante:** esto ataca el costo de la reproyección en sí — es distinto del fix del lock (que evita *duplicar* ese costo) y del fix del downsample (que evita el OOM al *calcular el índice* después). Los tres fixes son complementarios, no alternativos.

**Vuelo real recuperado:** el vuelo que había quedado trabado (ver bug 2 más arriba) se corrigió a mano en la base; el reintento posterior falló limpiamente con el bug 3 recién descrito (ya con mensaje de error claro en vez de SIGKILL) — la caché del archivo ya reproyectado sobrevivió ambos intentos fallidos, así que el próximo "Reintentar" del usuario debería saltarse directo a la lectura de bandas (ahora corregida) sin volver a pagar los ~15 min de reproyección.

**Problema abierto nuevo:** no hay ninguna prueba automatizada contra un archivo con dtype entero real de gran tamaño en CI (solo el test sintético agregado) — el bug 3 solo apareció al probar contra producción. Vale la pena, en algún momento, sumar un fixture de test más representativo de archivos reales (dtype entero + tamaño que cruce el umbral) en vez de depender de probar contra producción para encontrar este tipo de bug.

**Addendum 2026-08-28 — Bug 4, el usuario nunca podía ni empezar a procesar `ORTOMOSAICO.tif` (2.57 GB):** con los bugs 1-3 ya resueltos, el pipeline en sí funcionaba, pero el archivo nunca llegaba a encolarse — la **subida** (`POST /lotes/{id}/vuelos`, `multipart/form-data`) tardaba **42 minutos** para 2.57 GB (~1 MB/s) y para cuando terminaba el JWT ya había expirado (access token: 30 min), así que la request moría con 401 antes de que el endpoint corriera. El usuario reportó "nunca lo pude procesar" — no era el pipeline GIS, era la subida.

Diagnóstico por descarte (cada capa medida por separado): MinIO directo 62-92 MB/s, red host↔contenedor (Docker Desktop/WSL2) 74-92 MB/s en ambos sentidos, disco (escrituras chicas o grandes) 180-230 MB/s, `run_in_threadpool` ~1200 llamadas/s, `python_multipart.MultipartParser.write()` >1000 MB/s en aislado — todas las capas individuales eran rápidas. El síntoma solo aparecía en vivo, a través de `uvicorn`, y solo por encima de ~2 GiB: subidas de 200 MB y 1 GB (mismo endpoint, mismo contenedor) andaban a 78-88 MB/s; 2.2 GB se colgaba igual que el archivo real. **Causa raíz:** `httptools` (parser HTTP por defecto de `uvicorn[standard]`) tiene un bug de rendimiento severo con request bodies mayores a 2³¹ bytes (2 GiB) — confirmado subiendo el mismo archivo de prueba de 2.2 GB contra una instancia de `uvicorn` corriendo con `--http h11` en vez de `httptools`: 12.4s (177 MB/s) vs. >10 min con `httptools`.

**Fix:** agregar `--http h11` al comando de `uvicorn` en el servicio `api` de `docker-compose.yml`. Verificado con el archivo real: la subida completa de `ORTOMOSAICO.tif` (2.57 GB) pasó de 42+ min (con 401 final) a **1m27s**. Con eso, el pipeline completo (descarga MinIO 27.5s → reproyección ~14 min, one-time y cacheada → cálculo de índices) corrió de punta a punta por primera vez con este archivo: NDVI completó en 1281.7s totales (incluye la reproyección de la primera vez), NDRE reusando la caché en 113s.

**Problema abierto nuevo:** confirmado en vivo (dos vuelos con archivos de ~2.5 GB procesando en simultáneo durante esta prueba) que el worker llegó a 4.4 GiB / 7.4 GiB (59%) con solo 2 tasks pesadas concurrentes — refuerza el problema abierto #3 (sin `mem_limit` ni concurrencia acotada). No se tocó en esta tarea.

---

## Tareas en progreso

_Ir completando a medida que avanza el desarrollo._

| Tarea | Responsable | Estado | Rama |
|---|---|---|---|
| Upload GeoTIFF → MinIO | universoparalelo | completado | main |
| Conectar pipeline NDVI a tarea Celery | universoparalelo | completado | main |
| Frontend — modal carga GeoTIFF | universoparalelo (modal, `760d716`) · Amilcar Aguirre (wizard, `7fe91fb`) | completado | main |
| Frontend — dashboard de resultados (mapa + tabla) | Matías Machado, Denise Macarena Pujalte | completado | main |
| Optimización de rendimiento del pipeline GIS | _nombre_ | completado | feat/optimizar-pipeline |
| Motor de diagnóstico (RFDR-01) | _nombre_ | completado (sin persistencia, ver Problemas abiertos) | main |
| Exportación Shapefile y PDF | _nombre_ | pendiente | — |

---

#### Integración continua — GitHub Actions
**Fecha:** 2026-06-25
**Rama:** `main` (commit siguiente)

Se configuró el pipeline CI en `.github/workflows/ci.yml` con 3 jobs paralelos que corren en cada push y PR a `main`.

**Jobs implementados:**
- `test-api`: levanta PostGIS 16 + Redis como services de Actions, corre las 3 migraciones Alembic y verifica `/health` y `/health/db`.
- `test-gis`: usa la imagen `osgeo/gdal:ubuntu-small-3.9.0` (misma del worker), instala dependencias y corre `tests/test_ndvi_pipeline.py`.
- `build-frontend`: Node 20, `npm install` + `npm run build`, verifica que `dist/index.html` existe.

**Decisiones tomadas:**
- PostGIS como container service (Opción A) — hit real a la DB, alineado con la regla de no mockear la base de datos.
- `PYTHONPATH=$(pwd)` en el job GIS para que Python encuentre `workers/` y `app/` desde la raíz del repo en CI, sin modificar el script de tests que tiene el path `/app` hardcodeado para el contenedor Docker.
- Cache de pip y npm activado — acelera las corridas sucesivas.

#### Ingesta de GeoTIFF — Upload, validación y encolado
**Fecha:** 2026-06-30
**Rama:** `main` (commit `33cd77d`)

Se implementó el módulo `app/ingesta/` completo: cliente MinIO (`app/core/storage.py`), validador de archivos en dos capas (API + Worker), servicio de orquestación, router con dos endpoints y task Celery `procesar_vuelo`.

**Decisiones tomadas:**
- Validación en dos capas: extensión + magic bytes en la API (sin rasterio); CRS + bandas + dtype en el worker (tiene rasterio). Evita agregar GDAL como dependencia del contenedor API.
- `task_id` y `error_detalle` agregados al modelo `Vuelo` (migración 0004). Permite que `GET /lotes/{id}/vuelos/{id}/estado` cruce el estado de la DB con el de Celery `AsyncResult` en tiempo real.
- El worker actualiza `vuelo.estado` en DB via sync SQLAlchemy (`create_engine` + `Session`) — el único punto donde se hace esto fuera de la API async.
- Se mantuvo la tarea legacy `procesar_analisis` para no romper los tests de CI existentes.

**Error encontrado — `features.shapes()` rechaza float64**
Documentado en CLAUDE.md y validado en el worker: si el dtype es `float64` o `int8`, el worker lanza `ValueError` con mensaje claro antes de intentar vectorizar.

#### Worker GIS — Índices, mapeo de bandas y reproyección CRS
**Fecha:** 2026-06-30
**Rama:** `main` (commit `a39ecce`)

Se implementó el pipeline GIS generalizado que soporta NDVI, NDRE, SAVI y ExG con mapeo configurable de bandas por sensor y reproyección automática de CRS.

**Decisiones tomadas:**
- `band_mapping.py` centraliza los números de banda por sensor — esto evita números hardcodeados en el pipeline. *(Corrección 2026-07-05: la premisa original de que "Sentinel-2 y DJI Mavic 3 tienen las mismas bandas en distinto orden" era incorrecta — el Mavic 3M real no tiene banda Blue. Ver tarea "Corrección del perfil de bandas de `dji_mavic3`" más abajo.)*
- `indices.py` opera exclusivamente sobre arrays NumPy completos (sin iterar píxel a píxel). Toda función retorna `float32` y convierte nodata y denominador cero a `NaN` explícitamente.
- `reproyeccion.py` reproyecta en memoria con `rasterio.warp`; si el CRS ya es EPSG:4326 devuelve los bytes originales sin tocarlos (zero-copy).
- `pipeline.py` reutiliza `clasificar_ndvi` y `vectorizar_zonas` de `ndvi.py` para todos los índices — los umbrales cualitativos (crítica/deficiente/normal/vigorosa) aplican igual a NDRE y SAVI al ser índices ratio en [-1,1].
- La tarea `procesar_vuelo` sube `zonas.geojson` a MinIO en `{usuario}/{lote}/{vuelo}/zonas.geojson`. Un error en ese paso no cancela el análisis (error no crítico).
- `sensor` e `indice` se pasan como kwargs al encolar la tarea en Celery desde `ingesta/service.py`; el índice por defecto es `ndvi`.

#### Frontend — Dashboard de resultados (Sprint 5)
**Fecha:** 2026-07-02
**Rama:** `main` (commit siguiente)

Se implementó el dashboard de resultados completo: mapa interactivo de zonas clasificadas con React-Leaflet, tabla de estadísticas por zona y flujo de navegación completo entre lotes, vuelos y resultados.

**Decisiones tomadas:**
- GeoJSON servido a través de FastAPI (endpoint `GET /lotes/{id}/vuelos/{id}/zonas`) en lugar de URLs firmadas de MinIO — evita el problema de resolución de hostname `minio` desde el browser del usuario.
- `download_object()` en `storage.py` como función genérica de descarga; `download_geotiff()` se mantiene por compatibilidad con el worker.
- Colores de zonas: crítica (#ef4444), deficiente (#f97316), normal (#86efac), vigorosa (#16a34a). Alineados con la paleta de riesgo estándar en agronomía.
- `FitBounds` como componente interno de React-Leaflet que usa `useMap()` + `useEffect` para ajustar el viewport automáticamente al GeoJSON cargado.
- Polling de estado cada 3 segundos para vuelos en curso; se cancela automáticamente cuando todos los vuelos del lote están completados o en error.
- CSS Leaflet importado en `main.jsx` — evita el problema de estilos faltantes en Vite.

**Flujo de navegación implementado:**
```
/dashboard → listado de lotes, botón "Ver análisis"
/lotes/:loteId → lista de vuelos con estado y barra de progreso
/lotes/:loteId/vuelos/:vueloId → mapa de zonas + tabla de estadísticas
```

---

#### Worker asíncrono — Celery + cola Redis + progreso
**Fecha:** 2026-06-30
**Rama:** `main` (commit `8d5252b`)

Se completó la configuración operacional de Celery y se verificó el ciclo completo end-to-end.

**Decisiones tomadas:**
- `task_queues={"gis": {}}` declara la cola explícitamente en lugar de dejar que Celery la cree on-demand, evitando race conditions si el worker arranca antes que la primera tarea.
- `result_expires=3600` — los resultados de tareas expiran en Redis a la hora. Sin esto se acumulan indefinidamente.
- `autoretry_for=(ConnectionError, OSError)` con `max_retries=3` y `default_retry_delay=30s` cubre caídas momentáneas de MinIO o red, sin reintentar errores de validación GIS (que son `ValueError`).
- `_actualizar_vuelo` pasó de usar el ORM (`app.lotes.models`) a SQL directo con `text()` — el modelo arrastra `app.core.database` → `asyncpg`, que no está instalado en el contenedor worker.

**Error encontrado — tarea no registrada en worker**
El worker corría desde el 24/06 y no conocía `procesar_vuelo` (agregada después). Resuelto con `docker compose restart worker`. Documentado como paso obligatorio al agregar nuevas tareas Celery.

---

#### Visualización del índice — Polling, barra de progreso y mapa Leaflet
**Fecha:** 2026-06-30
**Rama:** `feat/visualizacion-indice`

Se implementó la visualización completa del resultado de análisis en el frontend: polling de estado en tiempo real, barra de progreso animada y mapa Leaflet interactivo con zonas coloreadas por clase NDVI.

**Piezas implementadas:**

Backend:
- `GET /lotes/{lote_id}/vuelos` — endpoint nuevo que lista vuelos de un lote ordenados por fecha descendente.
- `GET /lotes/{lote_id}/vuelos/{vuelo_id}/resultado` — endpoint nuevo que descarga `zonas.geojson` desde MinIO y lo retorna como JSON. Solo disponible si el vuelo está `completado`.
- `download_bytes()` en `app/core/storage.py` — función genérica para descargar cualquier objeto de MinIO.

Frontend:
- `hooks/useVueloProgreso.js` — hook que hace polling al endpoint de estado cada 2 segundos hasta que el estado sea `completado` o `error`, luego carga el GeoJSON. Limpia el interval en el cleanup del `useEffect`.
- `components/BarraProgreso.jsx` — muestra el porcentaje (0–100%) con transición CSS suave y el mensaje del paso actual del worker.
- `components/MapaIndice.jsx` — mapa Leaflet (react-leaflet v4) con capa GeoJSON donde cada zona se colorea según su clase: crítica (rojo), deficiente (naranja), normal (amarillo), vigorosa (verde). Leyenda posicionada sobre el mapa. Tooltips con NDVI promedio y área en ha.
- Dashboard actualizado: "Ver análisis" selecciona el lote; el panel derecho muestra `AnalisisPanel` que coordina polling + barra + mapa según el estado del vuelo más reciente.

**Decisiones tomadas:**
- CSS de Leaflet importado en `main.jsx` antes de `index.css` para evitar que los estilos locales lo sobreescriban.
- `key={selectedLoteId}` en `AnalisisPanel` garantiza que el componente se remonta (y reinicia el polling) al cambiar de lote.
- El endpoint `/resultado` retorna el GeoJSON directamente, no una URL firmada, para simplificar el consumo desde el frontend. Si el GeoJSON creciera mucho (> 10 MB), se revisaría a URL firmada.
- Bounds del mapa calculados manualmente desde las coordenadas del GeoJSON para no depender de `getBounds()` de Leaflet.
- Paleta de colores alineada con el pipeline: crítica `#c0392b`, deficiente `#e67e22`, normal `#f1c40f`, vigorosa `#27ae60`.

---

#### Tests del pipeline — cobertura completa en CI
**Fecha:** 2026-07-01
**Rama:** `main`

Se completó la cobertura de tests del pipeline GIS y se incorporaron al CI. Antes, el job `test-gis` solo corría `test_ndvi_pipeline.py` y el job `test-api` no corría ningún test de Python. Ahora todos los tests existentes corren automáticamente en cada push.

**Tests incorporados al CI:**
- `test-api` job: agrega `tests/test_ingesta.py` (validación de extensión, magic bytes, archivo vacío)
- `test-gis` job: agrega `tests/test_indices_worker.py` (índices, mapeo de bandas, reproyección, pipeline completo) y `tests/test_ingesta_worker.py` (validación GIS: CRS, dtype)
- `test-gis` job: agrega los dos tests de configuración de `tests/test_celery_integracion.py` (`result_expires` y cola `gis`)

**Test E2E verificado localmente:**
`test_ciclo_completo_encolar_y_esperar` en `test_celery_integracion.py` pasó correctamente con el stack levantado:
```
✓ GeoTIFF subido → MinIO
✓ Tarea encolada y completada en 2s
✓ 1 polígono generado, NDVI prom=0.6
✓ zonas.geojson en MinIO con 1 feature
```

**Decisiones tomadas:**
- El test E2E completo (`test_ciclo_completo_encolar_y_esperar`) queda fuera del CI — requiere MinIO + worker corriendo, lo cual implica un cuarto job con imagen GDAL + MinIO service + worker en background. Complejidad no justificada antes de la demo del 7/jul.
- Los dos tests de configuración Celery sí corren en CI porque solo verifican la configuración del objeto `celery_app`, sin necesitar servicios externos.

---

---

#### Tests de integración HTTP — Auth JWT, CRUD lotes, estado y resultado de vuelos
**Fecha:** 2026-07-04  
**Rama:** `main`

Se implementaron 44 tests de integración HTTP que cubren las brechas detectadas en el plan de testing. Todos los tests usan `starlette.testclient.TestClient` (modo sincrónico, compatible con FastAPI async) y golpean la DB real (PostGIS).

**Archivos creados:**
- `tests/test_auth.py` (15 tests): register nuevo/duplicado/inválido, login ok/password incorrecta/email inexistente, GET /me con token válido/sin token/token inválido/firma incorrecta, POST /refresh con refresh_token/access_token/token inválido, POST /logout.
- `tests/test_lotes.py` (16 tests): crear lote, listar, obtener por ID, actualizar, CRUD sin auth → 401, cultivo inválido/geometry inválida → 422, soft delete → 204, lote borrado → 404 en GET y no aparece en lista, aislamiento por usuario (lote de otro usuario → 404).
- `tests/test_vuelos_estado.py` (13 tests): `/estado` con vuelo pendiente/completado/error, vuelo inexistente → 404, sin auth → 401; `/resultado` para vuelos no completados → 404, vuelo inexistente → 404, sin auth → 401; listar vuelos, lote inexistente → 404. Vuelos insertados directamente en BD con psycopg2 para evitar dependencia de MinIO.
- CI actualizado: `test-api` job agrega tres `run` steps (uno por archivo).

**Decisiones tomadas:**
- `TestClient` se abre con `_tc.__enter__()` en `setup_module` y se cierra con `_tc.__exit__()` en `teardown_module` — mantiene el mismo event loop de anyio en todo el módulo. Cada request de TestClient sin esta técnica crea un nuevo event loop, lo cual causa "Future attached to a different loop" en asyncpg.
- `engine.sync_engine.dispose(close=False)` al inicio de cada `setup_module` — limpia el pool de asyncpg sin necesitar un event loop, permitiendo que los tests de varios módulos corran juntos en un mismo proceso (`python3 -m pytest tests/*.py`).
- Vuelos en `test_vuelos_estado.py` insertados con psycopg2 (`CAST(:id AS uuid)` en lugar de `:id::uuid` — la sintaxis `::` colisiona con el parser de parámetros de psycopg2).
- 48 tests API + 37 tests GIS = **85 tests en total**, todos pasando.

**Problema resuelto — Problema abierto #2 cerrado**

## Problemas abiertos

_Problemas conocidos sin solución todavía. Borrar cuando se resuelvan._

| # | Descripción | Impacto | Detectado |
|---|---|---|---|
| 1 | Test E2E (`test_ciclo_completo_encolar_y_esperar`) no corre en CI — necesita MinIO + worker | Bajo — pasa localmente, demostrable en la demo | 2026-07-01 |
| 2 | Motor de diagnóstico sin persistencia — cada `GET .../diagnostico` recalcula on-demand contra los GeoJSON en MinIO, sin tabla de zonas/diagnósticos ni historial entre vuelos. Bloquea RFGL-03 (distinguir patrones persistentes de episódicos) y el criterio técnico versionable de RFDR-04 (aceptar/modificar/rechazar). Planificado para release 4 con una entidad "zona" unificada y persistida. | Medio — funcional para demo, no para producción con historial multi-vuelo | 2026-08-27 |
| 3 | El worker no tiene `mem_limit` en `docker-compose.yml` ni concurrencia acotada a la RAM disponible (`concurrency` de Celery hereda el conteo de CPUs, hoy 16). Con Docker Desktop en 7.4 GiB totales compartidos con db/redis/minio/api/frontend, varias tasks pesadas concurrentes (imágenes de varios GB) todavía pueden competir por memoria y provocar un SIGKILL por OOM, aunque ya no dupliquen trabajo entre sí (ver fix del 2026-08-28). Mitigación pendiente: `mem_limit` explícito + `--concurrency` acorde, o una cola/prioridad separada para archivos grandes. | Alto — un archivo lo bastante grande puede seguir matando el worker | 2026-08-28 |

---

## Decisiones de arquitectura tomadas en esta release

_Registro de las decisiones importantes que no son obvias desde el código._

| Decisión | Alternativa descartada | Razón |
|---|---|---|
| Worker GIS separado del API | Procesar en FastAPI directamente | GeoTIFF grandes bloquearían la API; necesidad de reintentos |
| MinIO para archivos binarios | Sistema de archivos local | Escalabilidad y URLs firmadas temporarias |
| PostGIS para vectores | GeoJSON en disco | Consultas espaciales, índices GiST, historial |
| GeoTIFF sintético como fixture | Descargar imagen real de Sentinel-2 | Sin dependencia de red, tamaño mínimo, valores controlados |
| Celery con `result_backend` en Redis | Solo broker sin backend | El polling de `/analisis/{id}/estado` necesita `AsyncResult` para leer el estado; sin `result_backend` siempre devuelve PENDING |
| Cast a `float32` antes de `features.shapes()` | Pasar el array NDVI directamente (float64) | `rasterio.features.shapes()` rechaza `float64` e `int8` — confirmado en docs de Rasterio (Context7 2026-06-26) |
| `rasterio.band(src, n)` en vectorización de archivos grandes | `src.read()` + `shapes()` | Evita cargar el array completo en memoria RAM antes de vectorizar; crítico para GeoTIFFs > 500 MB |
| Motor de diagnóstico sin GeoPandas, con Shapely + proyección local equirectangular | Usar GeoPandas (como `workers/gis/zonas.py`) también en `app/diagnostico/` | El motor corre dentro del proceso FastAPI, que no tiene GeoPandas/GDAL instalados a propósito (`docker/requirements.api.txt` los reserva al worker). Confirmado por error real (`ModuleNotFoundError`) al testear contra el contenedor `api`. |
| NDVI como partición espacial canónica del motor de reglas; NDRE/GNDVI/SAVI/ExG se resuelven por overlay geométrico ponderado por área en vez de re-vectorizar por regla | Persistir una entidad "zona" unificada entre índices | NDVI siempre existe (se calcula al subir el vuelo); evita duplicar geometrías para reglas multi-índice (R10, R44) a costa de resolución reducida cuando NDVI ya está saturado (afecta solo a R21/GNDVI) — limitación aceptada y documentada, a resolver junto con la persistencia en release 4. |

---

## Notas del equipo

_Espacio libre para observaciones, aprendizajes o cosas a recordar para la presentación._

---

## Checklist de cierre de release

- [ ] Todos los endpoints del sprint responden correctamente
- [x] Migraciones corren sin errores desde cero (`docker compose down -v` + `upgrade head`)
- [x] Tests del pipeline GIS pasan (`docker compose exec worker python3 tests/test_ndvi_pipeline.py`)
- [ ] No hay secretos ni `.env` commiteados
- [ ] README actualizado con cambios de esta release
- [ ] Tag `v1.0.0` creado en GitHub
- [ ] Branch `release/v1.0.0` mergeada y cerrada
- [ ] CI de GitHub Actions en verde en el commit de corte `f35e422`
- [ ] Flujo de demo end-to-end verificado con un GeoTIFF real (DJI Mavic 3M)

---

## Presentación — puntos a destacar

_Completar antes de la presentación._

**¿Qué problema resuelve AgroNexo?**
AgroNexo es una plataforma de agricultura de precisión que procesa ortomosaicos GeoTIFF multiespectrales (dron o satélite), calcula índices de vegetación y detecta zonas de distinto vigor dentro de un lote, como base para el diagnóstico agronómico y la aplicación diferenciada de insumos. Foco: NEA (Chaco, Formosa, Corrientes).

**¿Qué puede hacer el sistema en esta release?**
Login con JWT; lotes con límite GeoJSON (vista previa en mapa) y área calculada en PostGIS; carga de GeoTIFF con inspección de bandas según sensor; procesamiento asíncrono en Celery con barra de progreso; mapa de zonas clasificadas por índice (NDVI/NDRE/SAVI/ExG) con zonas atípicas (z-score); estadísticas por zona (área, índice promedio).

**Decisiones técnicas a mencionar:**
- Worker GIS separado con Celery + Redis: la API nunca procesa GeoTIFF.
- PostGIS para vectores, MinIO para archivos binarios.
- Umbralización dinámica (fijo/Otsu/percentil) + suavizado gaussiano contra la fragmentación "sal y pimienta".
- Vectorización con connectivity=8, área mínima y z-score por polígono.
- Stack completo con `docker compose up` + CI en GitHub Actions con 3 jobs.

**Demo flow sugerido:**
1. Login con el usuario seed de desarrollo.
2. Pantalla Lotes → crear lote con formulario y límite GeoJSON (vista previa en mapa).
3. "Cargar ortomosaico": wizard de 2 pasos (lote, sensor e índices + inspección preliminar de bandas).
4. Seguir el procesamiento con la barra de progreso.
5. Ver el mapa de zonas y cambiar de índice con el selector.
6. Revisar la tabla de estadísticas por zona.
7. Eliminar / reintentar un análisis desde la lista.

**Preguntas frecuentes que pueden surgir:**
- ¿Por qué la API no procesa el GeoTIFF? → Worker separado para no bloquear la API con archivos grandes.
- ¿Qué pasa con archivos grandes? → En R1 el worker es lento con archivos reales; la optimización se planifica para R2.
- ¿Por qué todavía no hay diagnóstico agronómico? → El motor de reglas es alcance de R2.
- ¿Por qué no hay ExG para DJI Mavic 3M? → El sensor no tiene banda azul (limitación del hardware, no un bug).
(propuesta, revisar con el equipo)

---

## Cierre de release

- **Corte de la release:** commit `f35e422` (2026-07-06, Amilcar Aguirre, "Pantalla para mostrar e eliminar lotes"), último commit antes de la demo del 2026-07-07. No se creó el tag `v1.0.0` ni la rama `release/v1.0.0`; en R1 no se usaron PRs.
- **Entradas de esta bitácora que corresponden a la Release 2:** todas las posteriores al corte — las tareas de agosto 2026 (optimización del pipeline GIS, streaming de GeoTIFF > 3 GB, pre-compresión, fix pantalla en blanco, fix CRS EngineeringCRS/BigTIFF, motor de reglas RFDR-01, caché de GeoTIFF preparado, batch de índices, fix OOM), los problemas abiertos #2 y #3, las filas "Optimización de rendimiento del pipeline GIS", "Motor de diagnóstico (RFDR-01)" y "Exportación Shapefile y PDF" de Tareas en progreso, y las dos últimas filas de "Decisiones de arquitectura" (motor de diagnóstico). Los commits `2b0566e` y `8644be4` (2026-07-09) también son de R2.
- **Verificadas en el corte:** las entradas del 2026-07-03 al 2026-07-06 sin hash de commit (eliminar/reintentar, wizard de carga, perfil `dji_mavic3`, fix "sal y pimienta", rename `zonas.py`, multi-índice, pantalla Lotes) están presentes en el código de `f35e422`.
- **CI en el corte:** 2 de 3 jobs en verde (build del frontend y worker GIS). El job de API pasó migraciones y health, pero falló en el paso `pytest tests/test_vuelos_estado.py` (1 failed, 12 passed): `test_listar_vuelos_de_lote` da `KeyError: 'id'` porque `GET /lotes/{id}/vuelos` devuelve el campo `vuelo_id` y el test espera `id`. El mismo desajuste afecta al frontend: `DetalleLote.jsx` usa `vuelo.id`, por lo que "Ver resultados" navega a `vuelos/undefined` (corregido en R2, commit `fc9ebb2`).
- **Credenciales de desarrollo:** la migración 0006 incluye la contraseña del usuario seed de desarrollo (solo desarrollo). Por eso queda sin tildar "No hay secretos ni `.env` commiteados", aunque nunca se commiteó un `.env`.
- **Documento formal de la release:** `docs/releases/v1.0.0.md`.
