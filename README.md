# AgroNexo

Plataforma de agricultura de precisión para el NEA argentino (Chaco, Formosa, Corrientes). Procesa imágenes satelitales y de drones (GeoTIFF multiespectrales), calcula índices de vegetación (NDVI, GNDVI, SAVI, NDRE, EVI, MSAVI) y genera diagnósticos agronómicos con prescripción diferenciada por zona.

---

## Arquitectura

```
Frontend (React + Leaflet)
         ↕ REST + GeoJSON
Backend FastAPI  ←→  Redis  ←→  Worker GIS (Celery)
         ↕                            ↕
  PostgreSQL + PostGIS           MinIO (archivos)
```

El procesamiento de GeoTIFF **nunca ocurre en FastAPI**. Siempre se encola en Celery y lo ejecuta el Worker GIS en un contenedor separado. Esto evita que archivos grandes (> 500 MB) bloqueen la API y permite reintentos automáticos.

---

## Stack

### Backend
| Tecnología | Rol |
|---|---|
| **FastAPI** | API REST, routing, coordinación de tareas |
| **SQLAlchemy + GeoAlchemy2** | ORM con soporte de geometrías PostGIS |
| **Alembic** | Migraciones de base de datos versionadas |
| **python-jose + passlib/bcrypt** | JWT stateless + hashing de contraseñas |
| **Celery + Redis** | Cola de tareas asíncronas (broker db 0, result backend db 1) |
| **WeasyPrint** | Generación de reportes PDF desde HTML/CSS |

### Worker GIS
| Tecnología | Rol |
|---|---|
| **Rasterio** | Lectura de bandas, windowed reading para archivos grandes, vectorización |
| **NumPy** | Cálculo de índices pixel a pixel sobre arrays completos |
| **GDAL** | Motor geoespacial base (dependencia de Rasterio) |
| **scikit-image** | Umbralización Otsu para clasificación de zonas |
| **GeoPandas + Shapely** | Manipulación vectorial, cálculo de métricas de forma, exportación GeoJSON |

### Datos
| Tecnología | Rol |
|---|---|
| **PostgreSQL + PostGIS** | Metadatos y geometrías vectoriales con índices GiST |
| **MinIO** | Archivos binarios (GeoTIFF, PDF, SHP) — S3-compatible |

### Frontend
| Tecnología | Rol |
|---|---|
| **React + Vite** | UI principal, hot reload en desarrollo |
| **React-Leaflet** | Mapas, capas GIS, polígonos GeoJSON |
| **CSS plano** | Estilos (Tailwind previsto para un sprint posterior) |

---

## Decisiones técnicas clave

**Worker GIS en contenedor separado**
El procesamiento de rasters grandes consume mucha RAM y CPU durante varios minutos. Correrlo en FastAPI bloquearía toda la API. El Worker GIS tiene su propia imagen (`osgeo/gdal`) con las dependencias geoespaciales, sin afectar el contenedor API.

**PostGIS + MinIO, no todo en disco**
PostGIS guarda vectores y metadatos — permite consultas espaciales (`ST_Intersects`, `ST_Contains`) con índices GiST. MinIO guarda archivos binarios (GeoTIFF, PDF, SHP) con URLs firmadas de acceso temporario; el frontend nunca accede con credenciales permanentes.

**Redis con `result_backend`**
Celery necesita un `result_backend` (Redis db 1) además del broker (db 0). Sin él, el endpoint de polling `/analisis/{id}/estado` siempre devuelve PENDING porque `AsyncResult` no tiene dónde guardar el progreso real.

**Cast a `float32` antes de vectorizar**
`rasterio.features.shapes()` rechaza arrays `float64` e `int8`. El worker castea el resultado NDVI a `float32` antes de vectorizar. Si el dtype es incompatible, lanza un error descriptivo antes de intentarlo.

**`rasterio.band()` en lugar de `src.read()` para archivos grandes**
Para GeoTIFFs > 500 MB, `src.read()` carga el array completo en RAM. Usar `rasterio.band(src, n)` pasa una referencia lazy a `shapes()`, que lee por ventanas sin materializar el array completo.

**Validación en dos capas**
La API valida extensión y magic bytes del GeoTIFF (sin GDAL). El worker valida CRS, bandas disponibles y dtype (con Rasterio). Esto evita agregar GDAL como dependencia del contenedor API.

**Soft delete, nunca `DELETE` físico**
Lotes, vuelos y análisis tienen columna `deleted_at`. El historial de intervenciones persiste entre campañas para detectar patrones edáficos permanentes vs. episódicos.

---

## Requisitos previos

### Git
Descargá desde https://git-scm.com/downloads

### Docker Desktop
Docker es la única dependencia que necesitás instalar en tu máquina. Todo lo demás corre adentro de contenedores.

| Sistema | Descarga |
|---|---|
| **Windows** | https://docs.docker.com/desktop/setup/install/windows-install/ |
| **Mac** | https://docs.docker.com/desktop/setup/install/mac-install/ |
| **Linux** | https://docs.docker.com/desktop/setup/install/linux/ |

> **Windows:** Docker Desktop va a pedirte habilitar WSL 2 durante la instalación. Es necesario para que funcione correctamente.

Verificá la instalación:
```bash
docker --version
docker compose version
```

---

## Instalación

### 1. Clonar el repositorio
```bash
git clone <url-del-repo>
cd agronexo
```

### 2. Crear el archivo de variables de entorno
```bash
cp .env.example .env
```

Abrí `.env` y completá los valores indicados. Para generar el JWT secret:
```bash
# Mac / Linux
openssl rand -hex 32

# Windows (PowerShell)
python -c "import secrets; print(secrets.token_hex(32))"
```

> No commitees el archivo `.env`. Está en `.gitignore` por diseño.

### 3. Levantar el stack
```bash
docker compose up -d --build
```

La primera vez tarda varios minutos porque descarga la imagen `osgeo/gdal` (~1 GB) y compila las dependencias. Las siguientes veces es inmediato.

### 4. Verificar que todo está corriendo
```bash
docker compose ps
```

Todos los servicios deben aparecer como `healthy`:
```
NAME                  STATUS
agronexo-db-1         running (healthy)
agronexo-redis-1      running (healthy)
agronexo-minio-1      running (healthy)
agronexo-api-1        running (healthy)
agronexo-worker-1     running (healthy)
agronexo-frontend-1   running (healthy)
```

### 5. Correr las migraciones
```bash
docker compose exec api alembic upgrade head
```

### 6. Verificar la API
```bash
curl http://localhost:8000/api/v1/health
# → {"status": "ok", "env": "development"}
```

### 7. Iniciar sesión en el Frontend
Ingresá a http://localhost:5173 con el usuario administrador por defecto:
* **Usuario:** `admin@agronexo.com`
* **Contraseña:** `password123`

---

## Servicios y puertos

| Servicio | URL / Puerto | Descripción |
|---|---|---|
| **Frontend** | http://localhost:5173 | Aplicación React (Usuario: `admin@agronexo.com` / Contraseña: `password123`) |
| **API (FastAPI)** | http://localhost:8000 | Backend principal |
| **Docs Swagger** | http://localhost:8000/api/docs | Documentación interactiva de la API |
| **MinIO Console** | http://localhost:9001 | Explorador de archivos (credenciales del `.env`) |
| **PostgreSQL** | `localhost:5432` | Base de datos (Database: `agronexo`, Usuario: `agronexo`, Password: el que pusiste en `.env`) |
| **Redis** | `localhost:6379` | Broker de tareas |

---

## Flujo principal de la API

```
POST /api/v1/auth/login                              → tokens JWT
POST /api/v1/lotes                                   → crear lote con polígono GeoJSON
POST /api/v1/lotes/{id}/vuelos                       → subir GeoTIFF → encola Celery → 202 Accepted
GET  /api/v1/lotes/{id}/vuelos/{id}/estado           → polling de progreso (%)
GET  /api/v1/lotes/{id}/vuelos/{id}/diagnostico      → diagnóstico agronómico por zona
GET  /api/v1/productos-fitosanitarios                → catálogo de productos (?causa=...&tipo=...)
GET  /api/v1/analisis/{id}/reportes/shapefile        → .zip para maquinaria agrícola
```

Todos los endpoints (excepto `/auth/login` y `/auth/register`) requieren `Authorization: Bearer <token>`.

---

## Comandos frecuentes

```bash
# Levantar todo
docker compose up -d

# Solo backend + BD (sin frontend ni worker)
docker compose up -d api db redis

# Ver logs en tiempo real
docker compose logs -f

# Ver logs de un servicio específico
docker compose logs -f worker

# Correr migraciones
docker compose exec api alembic upgrade head

# Acceder a la base de datos
docker compose exec db psql -U agronexo

# Correr tests del pipeline GIS
docker compose exec worker python3 tests/test_ndvi_pipeline.py

# Apagar todo (preserva los datos)
docker compose down

# Reset completo — borra todos los datos
docker compose down -v
```

---

## Estructura del proyecto

```
agronexo/
├── app/                    # Backend FastAPI
│   ├── auth/               # Registro, login, JWT
│   ├── lotes/              # CRUD de lotes agrícolas con geometrías PostGIS
│   ├── ingesta/            # Upload GeoTIFF, validación, encolado Celery
│   ├── diagnostico/        # Motor de reglas (20 reglas en cascada), productos fitosanitarios
│   ├── reportes/           # PDF (WeasyPrint), Shapefile, ISO-XML
│   ├── core/               # Config (pydantic-settings), BD, cliente MinIO
│   └── main.py             # Punto de entrada FastAPI
├── workers/
│   ├── celery_app.py       # Configuración Celery (broker + result_backend)
│   └── gis/tasks.py        # Pipeline GIS: lectura → índices → vectorización
├── migrations/             # Migraciones Alembic
│   └── versions/           # Scripts versionados (0001 → 0015)
├── tests/                  # Tests del pipeline GIS con GeoTIFF sintético
├── frontend/               # React + Vite
├── docker/
│   ├── Dockerfile.api      # Python 3.11 + FastAPI
│   ├── Dockerfile.worker   # osgeo/gdal + Celery + dependencias GIS
│   ├── requirements.api.txt
│   └── requirements.worker.txt
├── docker-compose.yml
├── .env.example            # Plantilla de variables de entorno (sin valores reales)
└── docs/                   # Seguimiento de release y documentación técnica
```

---

## Problemas comunes

**`docker compose up` falla con "permission denied" en Linux**
```bash
sudo usermod -aG docker $USER
# Cerrar sesión y volver a entrar
```

**El worker no levanta / error de GDAL o numpy**
La imagen `osgeo/gdal` (~1 GB) tiene numpy instalado vía apt. pip no puede sobreescribirlo. El `Dockerfile.worker` usa `--ignore-installed` para resolver el conflicto. Si el build falla por timeout de red, volvé a correr `docker compose up -d --build`.

**Puerto 5432 ya en uso**
Tenés PostgreSQL instalado localmente. Cambiá el puerto expuesto en `docker-compose.yml`:
```yaml
ports:
  - "5433:5432"
```

**MinIO no arranca**
`MINIO_ROOT_PASSWORD` requiere mínimo 8 caracteres. Actualizá el `.env` y reiniciá con `docker compose up -d`.

**El Worker siempre reporta estado PENDING**
Redis debe configurarse como `result_backend` además de broker. Verificá que `CELERY_RESULT_BACKEND=redis://redis:6379/1` esté en el `.env` y que el worker haya arrancado después del cambio.

**`ValueError` en vectorización del Worker**
`rasterio.features.shapes()` rechaza arrays `float64` e `int8`. El worker castea a `float32` automáticamente, pero si agregás un índice nuevo asegurate de hacer el cast antes de llamar a `shapes()`.
