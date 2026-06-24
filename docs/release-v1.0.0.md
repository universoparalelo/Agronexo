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

## Tareas en progreso

_Ir completando a medida que avanza el desarrollo._

| Tarea | Responsable | Estado | Rama |
|---|---|---|---|
| Módulo Auth (JWT, registro, login) | _nombre_ | pendiente | — |
| Modelo Lote + migración | _nombre_ | pendiente | — |
| Upload GeoTIFF → MinIO | _nombre_ | pendiente | — |
| Conectar pipeline NDVI a tarea Celery | _nombre_ | pendiente | — |
| Motor de diagnóstico (RFDR-01) | _nombre_ | pendiente | — |
| Frontend — mapa con React-Leaflet | _nombre_ | pendiente | — |
| Exportación Shapefile y PDF | _nombre_ | pendiente | — |

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
| _agregar acá_ | — | — |

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
