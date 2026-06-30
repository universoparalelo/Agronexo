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

## Tareas en progreso

_Ir completando a medida que avanza el desarrollo._

| Tarea | Responsable | Estado | Rama |
|---|---|---|---|
| Upload GeoTIFF → MinIO | _nombre_ | completado | main |
| Conectar pipeline NDVI a tarea Celery | _nombre_ | pendiente | — |
| Motor de diagnóstico (RFDR-01) | _nombre_ | pendiente | — |
| Frontend — mapa con React-Leaflet (Sprint 4) | _nombre_ | pendiente | — |
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

---

## Problemas abiertos

_Problemas conocidos sin solución todavía. Borrar cuando se resuelvan._

| # | Descripción | Impacto | Detectado |
|---|---|---|---|
| — | _completar cuando surja_ | — | — |

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
