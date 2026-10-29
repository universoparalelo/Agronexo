# Cambios al proyecto por el empaquetado de escritorio

Registro vivo de **cada cambio** en la arquitectura, el código, la configuración, la infraestructura y la documentación que se hace, o se va a hacer, para entregar AgroNexo como aplicación de escritorio (camino B). **Cada cambio nuevo se agrega acá.**

- Por qué se decidió cada cosa: `docs/decisiones-app-escritorio.md` (decisiones D1 a D12).
- Resultados de las pruebas previas: `spike-escritorio/INFORME.md`.
- Seguimiento por release: `docs/release-v4.0.0.md`.

**Estados:** *Hecho* = escrito en una rama, todavía sin mergear a `main` · *En curso* · *Planificado* = decidido, sin empezar · *Sin decidir*.

Última actualización: 2026-10-29.

## Qué NO cambia

- La lógica de negocio: índices, zonificación, diagnóstico, reportes.
- Los contratos de la API existentes (solo se agregan endpoints).
- Desarrollo y CI siguen usando Docker (D1). Lo que cambia ahí es el almacenamiento (D3).

## Arquitectura: antes y después

| Pieza | Hoy (Docker) | Con el instalador |
|---|---|---|
| PostgreSQL + PostGIS | Contenedor | `postgres.exe` embebido (zip de binarios de EDB más el bundle de PostGIS, con `uuid-ossp`), datos en `%APPDATA%\AgroNexo\`. Probado en el spike con las 28 migraciones. |
| MinIO | Contenedor | **Se elimina** (D2, D3). Los archivos van a una carpeta de `%APPDATA%\AgroNexo\`. |
| Redis | Contenedor: broker de Celery (db 0) y result backend (db 1) | Propuesto eliminarlo solo en escritorio: Celery sobre Postgres (`sqla+postgresql://` y `db+postgresql://`). Validado en el spike; **falta decidirlo formalmente.** |
| API (FastAPI) | Contenedor con uvicorn | Ejecutable empaquetado (PyInstaller propuesto) que corre `alembic upgrade head` al arrancar y sirve el frontend compilado. |
| Worker GIS | Contenedor Celery (prefork) | Celery con `--pool=solo` en un proceso propio: un análisis a la vez. |
| Frontend | Servidor de Vite en desarrollo, Nginx en producción | Build estático servido por la API (hoy la API no sirve archivos estáticos). |
| Lanzador | No existe | **Nuevo.** Electron o Tauri (sin decidir). |
| Instalador | No existe | **Nuevo.** NSIS u otro, con firma de código. |
| Autenticación | Registro y login manual | Sesión automática (D4) más pantalla de bienvenida (D10). |
| PDF | WeasyPrint con GTK/Pango del contenedor | WeasyPrint con las DLL de GTK empaquetadas, o `printToPDF` de Electron. |
| Mapas | Base de internet | Con internet igual que hoy; sin internet, fondo neutro (D6, D8, D9). |

## Hecho: backend de disco (paso 1 de D3)

Rama `feat/almacenamiento-en-disco`, sin mergear.

| Archivo | Cambio |
|---|---|
| `app/core/config.py` | Variables nuevas `STORAGE_BACKEND` (`minio` o `disk`, por defecto `minio`) y `STORAGE_PATH`. `MINIO_ENDPOINT`, `MINIO_ROOT_USER` y `MINIO_ROOT_PASSWORD` pasan de obligatorias a opcionales. Un validador hace fallar el arranque si falta lo que pide el backend elegido, o si el valor de `STORAGE_BACKEND` no es válido. |
| `app/core/storage_disco.py` (nuevo) | Backend de disco con las mismas funciones que `storage.py`. Rechaza claves absolutas, con letra de unidad, con `\` o con `..`. Escribe de forma atómica, porque la API y el worker comparten la carpeta y `object_exists()` se usa como caché. Las URLs firmadas pasan a ser `/api/v1/archivos/{token}`: un JWT firmado con `JWT_SECRET_KEY`, con `type="archivo"` (no sirve como token de acceso) y vencimiento `MINIO_PRESIGNED_URL_EXPIRY`. |
| `app/core/storage.py` | Cada función delega en `storage_disco` cuando `STORAGE_BACKEND=disk`. Con `minio` no cambia nada. Los módulos que lo usan (`ingesta`, `reportes`, `auth`, el worker) no se tocan. |

| `app/archivos/` (nuevo módulo) | `GET /api/v1/archivos/{token}`: sirve el archivo si el token es válido y no venció. Responde 401 si el token es inválido, vencido o de otro tipo, 404 si el archivo no existe o si el backend no es disco. |
| `app/main.py` | Registra ese router en `/api/v1/archivos`. |
| `tests/test_almacenamiento_disco.py` (nuevo) | 37 tests: ida y vuelta de archivos, escritura atómica, claves con `..`, validación de la configuración, tokens y endpoint. No necesitan base de datos. |
| `.env.example` | `STORAGE_BACKEND` y `STORAGE_PATH`. |
| `README.md` | Módulo `app/archivos/` y la nota del backend de disco. |

**Cómo se probó:** los 37 tests nuevos; las suites `test_auth`, `test_lotes`, `test_cultivos` y `test_exportacion_api` con `STORAGE_BACKEND=disk` contra una base real (127 tests en total, sin fallos); y una prueba de punta a punta: subir un avatar, recibir `/api/v1/archivos/{token}` y descargar exactamente el mismo archivo. Los frontends no cambian: `<img src>` y `window.open` aceptan la ruta relativa (en desarrollo Vite redirige `/api`).

**Prueba con el worker (2026-10-29, en Windows, sin Docker, sin Redis y sin MinIO):** Postgres embebido como cola y como result backend de Celery (`sqla+postgresql://` y `db+postgresql://`), worker con `--pool=solo` y `STORAGE_BACKEND=disk`. Se subió `lote_prueba_con_problemas.tif` (4 bandas, EPSG:32721, 3,4 MB) por la API:
- El vuelo pasó de pendiente a completado en 13 s, con progreso visible (`Validando CRS y bandas`, `Calculando NDVI`).
- Quedaron en la carpeta de datos el original, la versión reproyectada preparada (`preparado_4326.tif`) y `zonas.geojson` (3 zonas).
- El diagnóstico, el reporte PDF (32 KB, 4 págs.) y la exportación de zonas funcionaron, y el enlace `/api/v1/archivos/{token}` devolvió el archivo exportado.
- Único aviso del worker: `lock de preparación (Redis) no disponible, se continúa sin dedupe`, que el código ya manejaba con un `try/except`. Con `--pool=solo` no hace falta ese lock; queda anotado para silenciar el aviso más adelante.
- Es Windows con Python 3.14, no Linux: valida la lógica de disco y de la cola en Postgres, pero no reemplaza el CI.

**Qué no cambia en el código:** `app/auth/router.py`, `app/reportes/router.py`, `app/ingesta/` y el worker siguen llamando a `storage.py` con los mismos nombres; por eso no se tocaron.

## Pendiente de esta rama

- Commit y pull request.
- **Hecho: `tests/test_almacenamiento_disco.py` está en el CI** (paso nuevo en el job `test-api` de `.github/workflows/ci.yml`, porque esa lista de tests es fija). Falta ver que pase en GitHub.
- No se verificó cuál endpoint carga el archivo entero en RAM al subir.

## Planificado

### Almacenamiento: quitar MinIO (paso 2 de D3)
- Sacar el servicio `minio` y el volumen `minio_data` de `docker-compose.yml` y de `docker-compose.prod.yml`.
- Sacar la dependencia `minio` de los requirements y las variables `MINIO_*` de `.env.example`, `.env.prod.example`, el CI y el README. Renombrar `MINIO_PRESIGNED_URL_EXPIRY`.
- Montar un volumen compartido entre API y worker para la carpeta de archivos.
- Cambiar a una carpeta temporal los tests que dependen de MinIO (`test_celery_integracion.py`, `test_exportacion_api.py`) y ajustar el CI.
- Quitar `scripts/backup_minio.sh`.

### Autenticación y primer arranque (D4, D10)
- El lanzador genera una contraseña aleatoria por instalación, la guarda en AppData y la pasa como `ADMIN_PASSWORD`. Hoy la migración `0006` siembra `admin@agronexo.com` / `password123` si faltan las variables: **en el instalador siempre deben estar definidas.**
- Pantalla de bienvenida de una sola vez que pide nombre y correo, sin contraseña y sin internet.
- Decidir el orden: pedir el correo antes de migrar y pasarlo como `ADMIN_EMAIL`, o sembrar un usuario provisorio y actualizarlo con `/auth/me`.
- Decidir cómo recibe el frontend la sesión automática.
- Definir qué pasa con la bienvenida al importar un backup.

### Datos del usuario (D5, D7, D11)
- Endpoints y botones "Exportar todo" e "Importar": un `.zip` con el volcado de la base y los archivos.
- Casilla "borrar también mis datos" en el desinstalador, desmarcada por defecto.
- Copia automática de la base antes de `alembic upgrade head`, con las últimas 2 o 3 copias; falta decidir dónde se guardan y cómo se restauran.

### Con y sin internet (D6, D8, D9)
- Detección de conexión en el frontend (`navigator.onLine` por sí solo no es confiable).
- Indicador de "Modo sin conexión".
- Deshabilitar, con aviso al pasar el mouse, la búsqueda de direcciones (Nominatim) y las imágenes satelitales (`desde-satelite`).
- Fondo neutro cuando falla el mapa base, en los 7 componentes que hoy lo bajan de internet: `MapaDibujoLote.jsx`, `MapaNEA.jsx`, `ModalCargaGeoTIFF.jsx`, `MapaIndice.jsx`, `MapaZonas.jsx`, `MiniMapaLote.jsx` y `ModalLimites.jsx`.

### Backend empaquetado
- Un solo entorno de Python y de `pydantic`: hoy la API usa `pydantic 2.10.4` y Python 3.12, y el worker `2.13.5` y Python 3.14.
- Empaquetar API y worker con `migrations/`, `alembic.ini` y los datos de PROJ.
- La API sirve el frontend compilado.
- Celery con Postgres como broker y result backend y `--pool=solo`. El lock de deduplicación de Redis en `workers/gis/tasks.py` ya está dentro de un `try/except`; con `solo` deja de hacer falta.
- Revisar que ningún `os.unlink` de `workers/gis/tasks.py` corra con un dataset de rasterio abierto (da `PermissionError [WinError 32]` en Windows).
- PDF: las DLL de GTK junto al `.exe` (o `os.add_dll_directory` a mano), `fonts.conf`, y la fuente DejaVu (`app/reportes/mapa.py` apunta a una ruta de Linux).
- Datos de zona horaria (`tzdata`) para `America/Argentina/Buenos_Aires`.

### Lanzador, instalador y CI
- Lanzador: elige puertos libres, arranca Postgres, API y worker en orden, espera los health checks, abre la ventana y cierra todo al salir. Instancia única y logs en AppData.
- Credenciales y secretos por instalación (`JWT_SECRET_KEY`, contraseñas de Postgres y del usuario), guardados en AppData.
- Instalador, desinstalador y firma de código.
- Un job de CI con runner de Windows que construya el instalador y haga una prueba mínima de arranque.

### Documentación
- `docs/release-v4.0.0.md`: redefinir HU-R4-06 como distribución del instalador.
- `README.md`: módulo `app/archivos/` y variables nuevas, y después los cambios de infraestructura.
- `CLAUDE.md`: actualizar el estado del proyecto cuando el instalador exista.

## Sin decidir

- Electron o Tauri.
- Eliminar Redis en escritorio de manera formal.
- Fechas, sprint y responsables.
