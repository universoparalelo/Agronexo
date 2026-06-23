# AgroNexo

Plataforma de agricultura de precisión para el NEA argentino. Procesa imágenes satelitales y de drones (GeoTIFF multiespectrales), calcula índices de vegetación (NDVI, GNDVI, SAVI, NDRE, EVI) y genera diagnósticos agronómicos con prescripción diferenciada.

---

## Requisitos previos

### 1. Git
- **Windows / Mac / Linux:** https://git-scm.com/downloads

### 2. Docker Desktop
Docker es la única dependencia real que necesitás instalar en tu máquina. Todo lo demás (Python, PostgreSQL, Redis, etc.) corre adentro de contenedores.

| Sistema | Descarga |
|---|---|
| **Windows** | https://docs.docker.com/desktop/setup/install/windows-install/ |
| **Mac (Apple Silicon / Intel)** | https://docs.docker.com/desktop/setup/install/mac-install/ |
| **Linux** | https://docs.docker.com/desktop/setup/install/linux/ |

> **Windows:** durante la instalación, Docker Desktop va a pedirte habilitar WSL 2 (Windows Subsystem for Linux). Aceptá — es necesario para que funcione correctamente.

Verificá que quedó bien instalado:
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

Abrí `.env` y completá los campos marcados con `change_me`:

| Variable | Qué poner |
|---|---|
| `POSTGRES_PASSWORD` | Cualquier contraseña segura (solo uso local) |
| `MINIO_ROOT_PASSWORD` | Mínimo 8 caracteres |
| `JWT_SECRET_KEY` | Generalo con el comando de abajo |

Para generar el JWT secret:
```bash
# Mac / Linux
openssl rand -hex 32

# Windows (PowerShell)
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Levantar el stack
```bash
docker compose up -d --build
```

La primera vez tarda varios minutos porque descarga las imágenes base y compila las dependencias. Las siguientes veces es instantáneo.

### 4. Verificar que todo está corriendo
```bash
docker compose ps
```

Todos los servicios deben aparecer como `healthy`:
```
NAME         STATUS
agronexo-db-1       running (healthy)
agronexo-redis-1    running (healthy)
agronexo-minio-1    running (healthy)
agronexo-api-1      running (healthy)
agronexo-worker-1   running (healthy)
```

### 5. Probar la API
```bash
curl http://localhost:8000/api/v1/health
# → {"status": "ok", "env": "development"}
```

---

## Servicios y puertos

| Servicio | URL / Puerto | Descripción |
|---|---|---|
| **API (FastAPI)** | http://localhost:8000 | Backend principal |
| **Docs Swagger** | http://localhost:8000/api/docs | Documentación interactiva de la API |
| **MinIO Console** | http://localhost:9001 | Explorador de archivos (usuario/contraseña del `.env`) |
| **PostgreSQL** | `localhost:5432` | Base de datos (conectar con DBeaver, TablePlus, etc.) |
| **Redis** | `localhost:6379` | Broker de tareas |

---

## Comandos frecuentes

```bash
# Levantar todo
docker compose up -d

# Ver logs en tiempo real
docker compose logs -f

# Ver logs de un servicio específico
docker compose logs -f api
docker compose logs -f worker

# Correr migraciones de base de datos
docker compose exec api alembic upgrade head

# Acceder a la base de datos (psql)
docker compose exec db psql -U agronexo

# Apagar todo (preserva los datos)
docker compose down

# Apagar y borrar todos los datos (reset completo)
docker compose down -v
```

---

## Estructura del proyecto

```
agronexo/
├── app/                    # Backend FastAPI
│   ├── auth/               # Registro, login, JWT
│   ├── lotes/              # CRUD de lotes agrícolas
│   ├── ingesta/            # Upload GeoTIFF, encolar análisis
│   ├── diagnostico/        # Motor de reglas, resultados
│   ├── reportes/           # PDF, Shapefile, ISO-XML
│   ├── core/               # Config, base de datos, utilidades
│   └── main.py             # Punto de entrada FastAPI
├── workers/
│   ├── celery_app.py       # Configuración Celery
│   └── gis/tasks.py        # Tareas de procesamiento GIS
├── migrations/             # Migraciones Alembic (base de datos)
├── frontend/               # React + Vite (en desarrollo)
├── docker/
│   ├── Dockerfile.api
│   ├── Dockerfile.worker
│   ├── requirements.api.txt
│   └── requirements.worker.txt
├── docker-compose.yml
├── .env.example            # Plantilla de variables de entorno
└── docs/                   # Investigación y especificaciones
```

---

## Flujo de trabajo Git

```bash
# Siempre trabajar en una rama, nunca directamente en main
git checkout -b feature/nombre-de-la-tarea

# Commits frecuentes con mensajes descriptivos
git add .
git commit -m "feat: descripción de lo que hice"

# Push y abrir Pull Request
git push origin feature/nombre-de-la-tarea
```

---

## Problemas comunes

**`docker compose up` falla con "permission denied" en Linux**
```bash
sudo usermod -aG docker $USER
# Cerrar sesión y volver a entrar
```

**El worker no levanta / error de GDAL**
La imagen del worker (`osgeo/gdal`) es grande (~1 GB). Si el build falla por timeout, intentá de nuevo — suele ser un problema de red.

**Puerto 5432 ya en uso**
Tenés PostgreSQL instalado localmente. Cambiá el puerto en `docker-compose.yml`:
```yaml
ports:
  - "5433:5432"   # usar 5433 en tu máquina
```

**MinIO no arranca / contraseña muy corta**
MinIO requiere mínimo 8 caracteres en `MINIO_ROOT_PASSWORD`. Actualizá el `.env` y reiniciá con `docker compose up -d`.
