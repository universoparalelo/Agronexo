# Release v1.0.0 — AgroNexo

**Estado:** En desarrollo  
**Fecha de inicio:** 2026-06-24  
**Fecha de cierre estimada:** _por definir_  
**Responsables:** _completar con nombres del equipo_  
**Contexto:** Primera release del proyecto. Presentación académica incluida.

---

## Objetivo de la release

_Describir en 2-3 oraciones qué debe poder hacer el sistema al cierre de esta release. Qué puede ver o hacer un usuario al final._

---

## Equipo

| Nombre | Rol | Área principal |
|---|---|---|
| _nombre_ | _rol_ | _backend / frontend / GIS / infra_ |
| _nombre_ | _rol_ | _backend / frontend / GIS / infra_ |
| _nombre_ | _rol_ | _backend / frontend / GIS / infra_ |

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

## Tareas en progreso

_Ir completando a medida que avanza el desarrollo._

| Tarea | Responsable | Estado | Rama |
|---|---|---|---|
| Upload GeoTIFF → MinIO | _nombre_ | completado | main |
| Conectar pipeline NDVI a tarea Celery | _nombre_ | completado | main |
| Frontend — modal carga GeoTIFF | _nombre_ | completado | main |
| Frontend — dashboard de resultados (mapa + tabla) | _nombre_ | completado | main |
| Motor de diagnóstico (RFDR-01) | _nombre_ | pendiente | — |
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

## Problemas abiertos

_Problemas conocidos sin solución todavía. Borrar cuando se resuelvan._

| # | Descripción | Impacto | Detectado |
|---|---|---|---|
| 1 | Test E2E (`test_ciclo_completo_encolar_y_esperar`) no corre en CI — necesita MinIO + worker | Bajo — pasa localmente, demostrable en la demo | 2026-07-01 |
| 2 | No hay tests para endpoints HTTP (auth, lotes, ingesta) | Bajo — cubiertos implícitamente por el E2E; no están en el plan de R1 | 2026-07-01 |

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

---

## Notas del equipo

_Espacio libre para observaciones, aprendizajes o cosas a recordar para la presentación._

---

## Checklist de cierre de release

- [ ] Todos los endpoints del sprint responden correctamente
- [ ] Migraciones corren sin errores desde cero (`docker compose down -v` + `upgrade head`)
- [ ] Tests del pipeline GIS pasan (`docker compose exec worker python3 tests/test_ndvi_pipeline.py`)
- [ ] No hay secretos ni `.env` commiteados
- [ ] README actualizado con cambios de esta release
- [ ] Tag `v1.0.0` creado en GitHub
- [ ] Branch `release/v1.0.0` mergeada y cerrada
- [ ] _agregar checks específicos del proyecto_

---

## Presentación — puntos a destacar

_Completar antes de la presentación._

**¿Qué problema resuelve AgroNexo?**
_completar_

**¿Qué puede hacer el sistema en esta release?**
_completar_

**Decisiones técnicas a mencionar:**
- _completar_

**Demo flow sugerido:**
1. _paso 1_
2. _paso 2_
3. _paso 3_

**Preguntas frecuentes que pueden surgir:**
- _completar_
