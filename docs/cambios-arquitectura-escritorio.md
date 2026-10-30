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

## Hecho en otras ramas (locales, sin mergear)

| Rama | Cambio |
|---|---|
| `feat/pdf-weasyprint-opcional` (`36b6a80`) | WeasyPrint se importa dentro de `generar_pdf_reporte` y `generar_pdf_orden_trabajo` y no al cargar el módulo, para que la API arranque aunque falten las librerías de GTK/Pango. Solo falla el pedido del PDF, con el error que el endpoint ya captura ("No se pudo generar el PDF"). Test nuevo `tests/test_weasyprint_opcional.py` (3 tests) y un ajuste en `tests/test_reporte_ejecutivo.py`, que ahora reemplaza `weasyprint.HTML`. 91 tests de reportes y diagnóstico pasan, y los dos PDF reales salen igual que antes. |
| `chore/limpieza-repo` (`af9f194`) | Se borran el componente `MiniMapaLote.jsx` y sus estilos, `app/diagnostico/productos.py` (diccionario viejo, ya no se importaba), la landing `docs/landing-estatica.html`, 8 imágenes sin uso de `frontend/public/`, los scripts `poc_reporte_pdf.py` y `poc_satelital_earthsearch.py`, y dos líneas de `.gitignore`. Se sacan además los dos fondos que solo se precargaban en `index.html` y se comprimen `logo.png`, `logo_hoja.png` y `fondozaira1.jpeg`: `frontend/public/` pasa de 22 MB a 0,4 MB, lo que achica el instalador. |
| `feat/arranque-autonomo` (`520aab4`) | Que la app de escritorio prepare la base y entregue las pantallas por sí sola. **`app/core/migraciones.py`** (nuevo): `aplicar_migraciones()` corre `alembic upgrade head` en el mismo proceso; busca `migrations/` en `sys._MEIPASS` cuando está empaquetada. Se llama **antes** de arrancar la API, no desde adentro, porque `migrations/env.py` abre su propio loop con `asyncio.run()`. **`escritorio/api.py`** (nuevo): punto de entrada que migra y recién después arranca uvicorn (`AGRONEXO_HOST` y `AGRONEXO_PORT`). **`app/frontend.py`** (nuevo): `montar_frontend()` sirve la carpeta `dist` de Vite con respaldo a `index.html` para las rutas de React, y deja intactas `/api/...`; se activa solo si se define `FRONTEND_DIR` (variable nueva en `app/core/config.py`), así que Docker y desarrollo no cambian. `app/main.py`, `README.md` y `.env.example` ajustados. 19 tests nuevos (`tests/test_migraciones_arranque.py` crea una base vacía, migra y la borra; `tests/test_frontend_estatico.py` cubre las pantallas, la API intacta y que no se lean archivos fuera de la carpeta) y 79 tests existentes siguen pasando. **Al mergear con `feat/almacenamiento-en-disco` hay un choque trivial en `app/main.py`** (dos bloques contiguos al final). |

## Probado: el motor empaquetado en una Windows limpia (2026-10-29)

No es código del repo. Se hizo en una copia temporal que combina esta rama con `feat/pdf-weasyprint-opcional`, sin Docker y sin tocar ninguna rama. Los scripts de armado y de prueba están fuera del repo (en la carpeta temporal de la sesión).

| Pieza | Cómo se armó | Resultado |
|---|---|---|
| API | PyInstaller `--onedir`, 114 MB, sin Electron ni Tauri | Arranca en ~3 s (PC de desarrollo) y ~12 s (Sandbox). Probados: health, `health/db` (ve PostGIS 3.6), registro, login con bcrypt y JWT, lote con geometría, cultivo y estadios. |
| Worker | PyInstaller `--onedir`, 425 MB, Celery con `--pool=solo` | Listo en ~7 s (PC) y ~13 s (Sandbox), conectado a la cola en Postgres. |
| Postgres + PostGIS | Zip de binarios de EDB 16.15 + bundle de PostGIS 3.6.2, sueltos, arrancados con `pg_ctl start -w` | Arranca en ~3 s con las 28 migraciones (revisión 0028). |
| Recorrido completo | Usuario, lote, cultivo, subir `lote_prueba_con_problemas.tif` | Vuelo completado en **21 s** (Sandbox) y 11 s (PC): 3 zonas, diagnóstico con 2 unidades de manejo, exportación de zonas con su enlace firmado (12.858 bytes) y archivos en disco (original, `preparado_4326.tif`, `zonas.geojson`). |

**Entorno del Sandbox:** Windows 11 Enterprise 10.0.26100, 10 GB de RAM, sin Python, sin GTK y sin Postgres instalados. Con 4 GB el Sandbox se había cerrado solo (`0x80370106`) al descomprimir el zip de Postgres.

### Arranque autónomo desde una base vacía (2026-10-29)

Segunda ronda, con el código de `feat/arranque-autonomo`: la API empaquetada (139 MB, con `migrations/`, `alembic` y el frontend compilado de 24 MB junto al programa) contra una base **recién creada y vacía**, en tu PC y en el Sandbox limpio (mismas condiciones que arriba, con las DLL de Visual C++ de Postgres).

| Paso | Resultado en el Sandbox |
|---|---|
| Base nueva antes de arrancar | 0 tablas |
| Arranque de la API | Respondió en ~23 s, contando la creación del esquema |
| Base después de arrancar | 13 tablas, revisión **0028**, usuario inicial (`ADMIN_EMAIL`) |
| Pantallas | `/`, `/login`, `/dashboard` y `/lotes/abc` devuelven la pantalla; el JavaScript principal (1.149 KB) se entrega como archivo; `/api/...` inexistente da 404 y no la pantalla |
| Login con el usuario inicial | OK |
| Worker + GeoTIFF | Worker listo en ~19 s; el vuelo se completó en **28,6 s**, 3 zonas y diagnóstico con 2 unidades de manejo |

Opciones de PyInstaller nuevas para esto: `--add-data migrations;migrations`, `--collect-submodules alembic`, y copiar `frontend/dist` junto al programa (se indica con `FRONTEND_DIR`). Las migraciones se cargan como archivos, por eso PyInstaller no ve sus imports; los de terceros que usan (`sqlalchemy`, `alembic`, `geoalchemy2` y `bcrypt`) ya los importa el resto de la app, así que quedan incluidos. Otro detalle: si el Sandbox anterior sigue abierto, bloquea las carpetas que tiene mapeadas y la compilación falla con `PermissionError [WinError 32]`; hay que cerrarlo o compilar en otra carpeta.

### Hallazgos

1. **Postgres necesita las librerías de Visual C++.** En la primera prueba no arrancó: `vcruntime140.dll` la piden 179 archivos de Postgres y PostGIS, `msvcp140.dll` las librerías de ICU y `vcruntime140_1.dll` otros ocho. Una Windows limpia no las trae; la PC de desarrollo sí (Visual C++ Redistributable). Con las tres junto a `postgres.exe` arrancó bien. El instalador tiene que incluirlas (o instalar el redistribuible); **falta verificar las condiciones de Microsoft para redistribuirlas.** La API no tiene el problema porque PyInstaller ya trae las suyas.
2. **El PDF falla en el programa empaquetado, aunque GTK esté instalado:** `OSError: cannot load library 'libgobject-2.0-0': error 0x7e`. WeasyPrint solo registra sus rutas de DLL cuando la aplicación no está congelada (`weasyprint/text/ffi.py`). La API siguió viva y respondió después del error, gracias al import diferido. Pendiente: las DLL de GTK junto al `.exe`, o `printToPDF` de Electron.
3. **Opciones de PyInstaller necesarias** (el primer intento falló con `ModuleNotFoundError: No module named 'celery.fixups'`): para la API, `--collect-submodules` de `uvicorn`, `celery`, `kombu`, `billiard` y `sqlalchemy.dialects.postgresql`, más las plantillas de `app/reportes/` y `app/ordenes_trabajo/` y los imports ocultos `multipart`, `email_validator`, `asyncpg` y `psycopg2`. **No incluir `workers` en la API**: arrastra rasterio, scipy y pandas y el paquete pasa de 114 a 349 MB. Para el worker, `--collect-all` de `rasterio`, `pyproj`, `pyogrio` y `skimage`, y `--collect-submodules` de `workers` y `scipy`.
4. **Peso:** API 114 MB y worker 425 MB, con librerías repetidas; conviene unirlos en un solo paquete. La carpeta de Postgres pesa 1,2 GB y se puede podar mucho (pgAdmin, StackBuilder, lenguajes opcionales, documentación).

### Lo que no se probó

- No hay lanzador: cada programa se arrancó a mano.
- ~~No se corrió `alembic upgrade head` desde el paquete~~: resuelto el mismo día en `feat/arranque-autonomo` (ver "Arranque autónomo desde una base vacía").
- No hay instalador, ni firma de código, ni desinstalador.
- ~~La API no sirve el frontend compilado~~: resuelto el mismo día en `feat/arranque-autonomo`.
- El PDF no funciona dentro del paquete (hallazgo 2).
- No se probó un GeoTIFF grande (más de 500 MB) ni el procesamiento de varios vuelos seguidos.

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
- El lanzador genera una contraseña aleatoria por instalación, la guarda en AppData y la pasa como `ADMIN_PASSWORD`. Hoy la migración `0006` siembra el usuario `admin@agronexo.com` con una contraseña de desarrollo fija si faltan las variables: **en el instalador siempre deben estar definidas.**
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
- Fondo neutro cuando falla el mapa base, en los 6 componentes que hoy lo bajan de internet: `MapaDibujoLote.jsx`, `MapaNEA.jsx`, `ModalCargaGeoTIFF.jsx`, `MapaIndice.jsx`, `MapaZonas.jsx` y `ModalLimites.jsx`. (`MiniMapaLote.jsx`, que figuraba como el séptimo, nadie lo usaba y se borra en `chore/limpieza-repo`.)

### Backend empaquetado
Probado en parte, ver "Probado: el motor empaquetado en una Windows limpia".
- Un solo entorno de Python y de `pydantic`: hoy la API usa `pydantic 2.10.4` y Python 3.12, y el worker `2.13.5` y Python 3.14.
- Empaquetar API y worker con `migrations/`, `alembic.ini` y los datos de PROJ.
- ~~La API sirve el frontend compilado.~~ Hecho en `feat/arranque-autonomo`.
- Celery con Postgres como broker y result backend y `--pool=solo`. El lock de deduplicación de Redis en `workers/gis/tasks.py` ya está dentro de un `try/except`; con `solo` deja de hacer falta.
- Revisar que ningún `os.unlink` de `workers/gis/tasks.py` corra con un dataset de rasterio abierto (da `PermissionError [WinError 32]` en Windows).
- PDF: las DLL de GTK junto al `.exe` (o `os.add_dll_directory` a mano), `fonts.conf`, y la fuente DejaVu (`app/reportes/mapa.py` apunta a una ruta de Linux).
- Datos de zona horaria (`tzdata`) para `America/Argentina/Buenos_Aires`.
- Incluir `vcruntime140.dll`, `vcruntime140_1.dll` y `msvcp140.dll` junto a Postgres, y podar su carpeta (hoy 1,2 GB). Verificar las condiciones de redistribución de Microsoft.
- Unir la API y el worker en un solo paquete para no repetir librerías.
- ~~Correr `alembic upgrade head` desde el paquete al arrancar.~~ Hecho en `feat/arranque-autonomo` (no hace falta `alembic.ini`).

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
