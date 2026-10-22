# Release v4.0.0 — Seguimiento

**Estado:** En desarrollo
**Rama principal:** `main`
**Inicio:** Sprint 14

---

## Sprint 14 — CI/CD: seguridad (SAST, SCA, secretos, imágenes)

**Período:** 2026-09-27

### Tareas completadas

| Tarea | Estado |
|---|---|
| HU-R4-05 — Investigación de costos de fitosanitarios | Completada |
| HU-R4-08 — Comparación de capas por fecha en mapa | Completada |
| Workflow `security.yml`: SAST (Semgrep + Bandit) | Completada |
| Workflow `security.yml`: SCA (pip-audit + npm audit) | Completada |
| Workflow `security.yml`: escaneo de secretos (Gitleaks) | Completada |
| Workflow `security.yml`: escaneo de imágenes Docker (Trivy) | Completada |
| `dependabot.yml` (pip, npm, docker, github-actions) | Completada |
| Escaneo de secretos sobre todo el historial (una sola vez) | Completada — ver hallazgo abajo |
| Reemplazar la imagen de MinIO en `docker-compose.yml` (`minio/minio` dado de baja) | Completada |
| Bumps validados: `redis`, `weasyprint`, `pyshp`, `geotiff`, `node` (Grupo E de Dependabot) | Completada |
| HU-R4-01 — fix IDOR en endpoints de índices adicionales del vuelo | Completada |
| Upgrade `react`/`react-dom` 19, `react-leaflet` 5, `react-router-dom` 7 | Completada |
| HU-R4-02 — trazabilidad completa del análisis | Completada |
| Fix: label engañoso "Procesando imagen" en Vista geoespacial del Dashboard | Completada |
| HU-R4-03 — listado multi-lote con filtros, paginado y fix de N+1 | Completada |
| HU-R4-06 — base de despliegue en producción (compose, Nginx/HTTPS, migraciones, credenciales) | Completada — parcial, ver detalle |
| HU-R4-10 — personalización del perfil del usuario | Completada |
| Fix: bump `sqlalchemy` 2.0.54 → 2.1.1 (PR Dependabot #63) + pin explícito de `greenlet` | Completada |
| Fix: bump `osgeo/gdal` 3.9.0 → 3.13.3 + `rasterio` 1.3.11 → 1.5.1 (PRs Dependabot #21 + #64) | Completada |
| Fix: bump `bcrypt` 4.2.1 → 5.0.0, se saca `passlib` (PR Dependabot #60) | Completada |
| Fix: bump coordinado `vite` 6→8 + `@vitejs/plugin-react` 4→6 (PRs Dependabot #69 + #41) | Completada |
| Fix: bump `geoalchemy2` 0.15.2 → 0.20.0 (regresión de `sqlalchemy` 2.1 ya en `main`) | Completada |
| Fix: bump `python-jose` 3.3.0 → 3.5.0 + `pillow` 10.4.0 → 12.3.0 (hallazgos SCA) | Completada |
| HU-R4-07 — resumen por vuelo en el historial (índice + severidad + enlaces) | Completada |
| HU-R4-12 — preferencias de uso (índice preferido, unidad de área, producto habitual) | Completada |
| HU-R4-11 — ahorro comparativo entre campañas (variable vs. uniforme, precios de productos) | Completada |
| HU-R4-09 — comparar dos vuelos del mismo lote (estadísticas) | Completada — parcial, ver detalle |
| Fix: sidebar no marcaba "Diagnósticos" como activo en la vista de resultados | Completada |

#### Workflow de seguridad separado de `ci.yml`
**Fecha:** 2026-09-27
**Rama:** `feat/ci-seguridad-sast-sca`

El pipeline de CI (`ci.yml`) solo corría tests funcionales (API, worker GIS, build de frontend) — no había ningún control de seguridad: sin SAST, sin SCA, sin escaneo de secretos ni de imágenes Docker, y sin Dependabot para automatizar el parcheo de dependencias vulnerables.

Se agregó `.github/workflows/security.yml` con 6 jobs independientes:
- **Gitleaks** (secretos) — corre sobre el historial completo del push/PR (`fetch-depth: 0`), no solo el diff.
- **Semgrep** (SAST) — reglas `p/security-audit` + `p/owasp-top-ten` + `p/secrets`, cubre Python y JS/React en un solo job.
- **Bandit** (SAST) — reglas específicas de Python sobre `app/` y `workers/`, complementa a Semgrep con menos falsos negativos en patrones típicos de Python (shell=True, eval, etc.).
- **pip-audit** (SCA) — audita `docker/requirements.api.txt` y `docker/requirements.worker.txt` contra la base OSV/PyPI.
- **npm audit** (SCA) — `npm ci` + `npm audit --audit-level=high` en `frontend/`.
- **Trivy** (imágenes) — matriz que buildea las 3 imágenes (`api`, `worker`, `frontend`) con los Dockerfiles reales de `docker/` y escanea CVEs `CRITICAL`/`HIGH` del SO base.

**Decisiones tomadas:**
- **Workflow separado de `ci.yml`, no un job más ahí:** son gates con dueños y cadencia de revisión distintos (calidad funcional vs. seguridad); separarlos permite tunear o silenciar reglas de seguridad sin tocar el pipeline de tests, y que un fallo de seguridad no bloquee el feedback rápido de tests en cada push.
- **`continue-on-error: true` en todos los jobs nuevos excepto Gitleaks**, como rollout inicial: Semgrep/Bandit/pip-audit/npm-audit/Trivy corren y reportan pero no bloquean merges todavía, para poder ver el volumen real de hallazgos (probablemente hay ruido en un repo que nunca corrió estas herramientas) sin frenar el equipo de un día para el otro. Gitleaks sí bloquea desde el día uno porque un secreto filtrado es una categoría de riesgo distinta (binario: está o no está, no hay "falso positivo aceptable" razonable por defecto).
- **No se subieron resultados SARIF al tab de Security de GitHub** — esa integración nativa (`github/codeql-action/upload-sarif`) requiere GitHub Advanced Security en repos privados; queda pendiente evaluarla si la org licencia GHAS o si el repo pasa a público.
- **Trivy escanea las imágenes reales del proyecto** (build con los `Dockerfile.*` de `docker/`, mismo contexto que usa `docker-compose.yml`) en vez de solo un `trivy fs` sobre los manifiestos de dependencias — cubre CVEs del sistema operativo base (`node:20-slim`, la imagen GDAL) que pip-audit/npm audit no ven.
- **Trigger con `schedule` semanal** (lunes 06:00 UTC) además de push/PR — para detectar CVEs nuevos publicados sobre dependencias que no cambiaron, ya que Dependabot corre en un ciclo separado y solo actúa cuando hay una versión parcheada disponible.
- **`dependabot.yml`** cubre 4 ecosistemas: `pip` (`/docker`, agrupa API+worker porque ambos requirements viven ahí), `npm` (`/frontend`), `docker` (imágenes base de los 3 Dockerfiles) y `github-actions` (el propio pipeline de CI, para no quedar con acciones desactualizadas silenciosamente).

**Hallazgo — 4 secretos reales en el historial de git (no en el código actual)**

El escaneo con el historial completo (`gitleaks detect --source . --verbose`, corrido localmente antes de confiar en el gate de CI) encontró un `access_token`/`refresh_token` de ejemplo pegados en `docs/docs/Arquitectura.md` y `docs/sprint1y2.md` en el commit `de3e308` (2026-06-23, autor `universoparalelo`). Ambos archivos ya no existen en el árbol actual, pero el secreto sigue siendo recuperable por cualquiera que clone el repo (está en el historial, no solo en el HEAD).

**Riesgo evaluado como bajo pero no nulo:** por la config de auth del proyecto (`ACCESS_TOKEN_EXPIRE_MINUTES=30`, `REFRESH_TOKEN_EXPIRE_DAYS=7`) y la fecha del commit (~3 meses antes de este sprint), ambos tokens ya vencieron — no son explotables hoy. No se filtró el `JWT_SECRET_KEY` en sí (eso sí habría sido crítico, porque permite firmar tokens nuevos indefinidamente), solo instancias de tokens ya vencidas.

**Decisión final (2026-09-27): no se reescribe el historial.** Evaluado con el equipo — reescribir (`git filter-repo`/BFG + force-push) es una operación de alto impacto sobre una rama compartida (obliga a todo el equipo a re-clonar o resetear su copia local) para eliminar dos tokens que ya vencieron hace meses y no exponen el `JWT_SECRET_KEY`. El riesgo remanente no justifica esa disrupción. El `.gitleaksignore` agregado en este sprint (con los 4 fingerprints exactos) queda como mitigación permanente, no transitoria: el gate de CI sigue viendo el historial completo en cada corrida pero no vuelve a fallar por un hallazgo ya evaluado y aceptado.

#### Fixes tras el primer PR real (#20) — 4 bugs del workflow expuestos por CI real
**Fecha:** 2026-09-27
**Rama:** `feat/ci-seguridad-sast-sca`

El primer push a PR abrió los ojos sobre varias cosas que solo se ven corriendo en GitHub Actions de verdad (no hay forma de simular el runner completo en local):

![Los 8 jobs de security.yml fallando en la primera corrida del PR #20](image/release-v4.0.0/1790520200865.png)

- **`aquasecurity/trivy-action@0.28.0` no resolvía** — el tag real lleva prefijo `v` (`v0.28.0`). Verificado contra la API de tags del repo (`api.github.com/repos/aquasecurity/trivy-action/tags`).
- **Gitleaks fallaba con 403 "Resource not accessible by integration"** al listar los commits del PR — el `GITHUB_TOKEN` por defecto del repo no incluye `pull-requests: read`. Se agregó `permissions` explícito al job (mínimo privilegio: `contents: read` a nivel workflow, `pull-requests: read` solo en el job de secretos).
- **`npm ci` fallaba** porque `frontend/package-lock.json` estaba desincronizado con `package.json` (le faltaban `geotiff`/`proj4` y sus transitivas, agregadas en el Sprint 13). Nadie lo había notado porque ni `Dockerfile.frontend` ni el job `build-frontend` de `ci.yml` usan `npm ci` — ambos usan `npm install`, que regenera el lock silenciosamente en vez de fallar. Regenerado con `npm install` (diff de 121 líneas, solo lo faltante).
- **El propio `trivy-action` fallaba después de corregir el tag** — el instalador embebido de la action (`contrib/install.sh` de aquasecurity/trivy) fallaba con exit code 1 sin mensaje de error legible después de resolver la versión (`v0.64.1`), de forma reproducible en las 3 imágenes. Es un problema conocido de esa action con el script instalador, no de esta config. **Se reemplazó por `docker run aquasec/trivy:0.74.0 image ...` directo** montando el socket de Docker del runner — evita el instalador por completo y ya se probó en local contra una imagen real antes de subirlo.

**Decisión tomada:** no se relajó ningún check para "hacerlo pasar" — Bandit, Semgrep, pip-audit y npm audit siguen en rojo en el PR porque encontraron hallazgos reales (no bugs de config), y quedan así a propósito mientras dure el rollout en modo reporte (`continue-on-error`).

#### Triage de los primeros hallazgos reales — 3 arreglos baratos
**Fecha:** 2026-09-27
**Rama:** `feat/ci-seguridad-sast-sca`

Con el workflow ya corriendo bien (sin bugs de config), tocaba decidir qué hacer con los hallazgos reales de la primera corrida. En vez de ajustar el pipeline para "que pase en verde", se clasificaron por costo real:

- **`python-multipart` 0.0.20 → 0.0.32** (`docker/requirements.api.txt`): parcheaba 6 CVEs (PYSEC-2026-3036 a -3040, -1852). Es la librería que procesa la subida de GeoTIFF (`multipart/form-data`), así que no era un CVE cualquiera. Bump de patch, sin cambios de código. Validado con `tests/test_ingesta.py` (4), `tests/test_lotes.py` + `tests/test_vuelos_estado.py` (34) — los 3 suites pasan igual.
- **`npm audit fix` (sin `--force`) en `frontend/`**: resolvió `postcss` solo (diff de 42 líneas en `package-lock.json`, `package.json` sin cambios). Verificado con `npm run build` y `npm test` (vitest, 9 tests) — ambos OK.
- **Bandit B310 en `workers/gis/satelital_catalogo.py::_get_json`**: falso positivo — Bandit marca cualquier `urlopen()` sin distinguir que acá el scheme+host siempre sale de `EARTH_SEARCH_COLLECTION_URL` (constante fija del módulo); las dos llamadas del módulo solo varían el path/query, nunca pueden apuntar a `file://` ni a otro host. Se documentó con un comentario explicando el porqué + `# nosec B310` en la línea. Confirmado con Bandit local: `No issues identified` (antes: 1 Medium).

**Lo que quedó afuera a propósito (no es "barato"):**
- `react-router-dom`: el audit sugiere `npm audit fix`, pero el fix real es saltar de v6.28 a v7.18 (major, breaking) — no se fuerza sin una tarea de testing de rutas aparte.
- `starlette` (CVEs varios, ver hallazgo de pip-audit): viene empaquetado por el pin de `fastapi==0.115.6`; arreglarlo de verdad implica subir FastAPI a una versión que soporte un Starlette parchado — riesgo de romper comportamiento, requiere correr toda la suite, no un bump aislado. Queda como problema abierto.
- `pytest` 8.3.4 → 9.x: dependencia solo de test (no llega a producción); major version bump, puede romper config de tests. Sin apuro.
- `ecdsa` (PYSEC-2026-1325, sin versión con fix — el maintainer no lo va a parchear, es un problema conocido de canal lateral): dependencia transitoria de `python-jose[cryptography]`, pero el proyecto firma JWT con `HS256` (`app/auth/dependencies.py`, `app/auth/router.py` — `jwt.decode(..., algorithms=[settings.jwt_algorithm])`), nunca con `ES256`. El código de `ecdsa` no se ejecuta en ningún camino real de la app — riesgo aceptado, no se persigue un CVE sin fix disponible.

#### Pinear las GitHub Actions a un commit SHA + acotar `JWT_SECRET_KEY` a los jobs que lo usan
**Fecha:** 2026-09-27
**Rama:** `feat/ci-seguridad-sast-sca`

Resolvió los últimos 2 grupos de hallazgos de Semgrep (17 → 0):

- **`github-actions-mutable-action-tag` (17)**: las 4 acciones usadas (`actions/checkout`, `actions/setup-python`, `actions/setup-node`, `gitleaks/gitleaks-action`) se resolvieron a su commit SHA exacto vía `gh api repos/<owner>/<repo>/git/refs/tags/<tag>` y se pinearon en `ci.yml` y `security.yml`, con el tag legible como comentario (`@11d5960a...262 # v4.4.0`). `dependabot.yml` (ecosistema `github-actions`, ya agregado en este sprint) va a mantener esos SHA actualizados solo.
- **`gha-workflow-env-secret` (1, `ci.yml:27`)**: `JWT_SECRET_KEY` salió del `env:` a nivel workflow (donde lo veían los 3 jobs, incluido `build-frontend` que ni lo usa) y se movió al `env:` de cada job que sí lo necesita — `test-api` sigue usando `secrets.CI_JWT_SECRET_KEY` (con el mismo fallback de siempre) porque ahí sí se firman/verifican JWTs de verdad; `test-gis` pasó a un string fijo sin referenciar el secret real, porque solo necesita que el campo requerido de `Settings` no esté vacío, nunca firma nada.

Verificado con Semgrep local: `Ran 350 rules on 196 files: 0 findings` (antes: 25). Los 3 jobs de `ci.yml` no se tocaron en su lógica, solo el `env:`.

#### Bump de `pytest` 8.3.4 → 9.1.1
**Fecha:** 2026-09-27
**Rama:** `feat/ci-seguridad-sast-sca`

Resuelve el hallazgo PYSEC-2026-1845 de `pip-audit`. Es dependencia solo de test (no llega a producción), pero igual se corrió la suite completa antes de dar el bump por bueno: **313 tests pasan** (237 en la imagen `api`, 25 archivos `tests/test_*.py` menos `test_celery_integracion.py` que necesita el stack completo con MinIO — ver hallazgo abajo; 76 en la imagen `worker`, los que importan `rasterio`/`numpy`/`geopandas`). Sin cambios de código — pytest 9 no rompió nada de lo que usa este repo.

**Nota sobre cómo se corrió:** las imágenes se reconstruyeron desde cero (`docker compose build`) porque un reinicio de emergencia de la máquina había limpiado todo el estado de Docker Desktop (cero imágenes, contenedores y volúmenes). `docker compose up` no pudo levantar `api`/`worker` completos porque ambos tienen `depends_on: minio: condition: service_healthy` y MinIO no arranca (ver hallazgo siguiente) — se corrieron los tests con `docker run` directo contra la red de Compose (`--network agronexo_default`), sin pasar por el chequeo de salud de `minio`.

#### Hallazgo — `minio/minio` ya no se puede bajar sin cuenta (Docker Hub y quay.io)
**Fecha:** 2026-09-27

Al reconstruir el stack desde cero, `docker compose up` falló en seco: `Error response from daemon: pull access denied for minio/minio, repository does not exist or may require 'docker login'`. No es un problema de esta máquina ni de este repo — MinIO dejó de publicar `minio/minio` en Docker Hub, y su alternativa (`quay.io/minio/minio`) ahora exige autenticación incluso para tags viejos (`RELEASE.2025-04-22T22-12-26Z` probado, mismo 401). Confirmado también vía la API pública de Docker Hub: `GET /v2/repositories/minio/minio/` → `{"message":"object not found"}`.

**Impacto:** cualquiera que clone el repo hoy y corra `docker compose up` desde cero no puede levantar `api`, `worker` ni `frontend` con conexión a MinIO real — todos dependen de `minio: condition: service_healthy`. El único workaround usado en este sprint (`docker run` directo contra la red de Compose) evita el problema para correr tests, pero no es una solución para el flujo normal de desarrollo (`docker compose up`).

**El CI de GitHub Actions no se ve afectado** (verificado, no es una suposición): ni `ci.yml` ni `security.yml` dependen de `docker compose` ni de la imagen de MinIO. `test-api`/`test-gis` levantan Postgres/Redis como `services:` nativos de GitHub Actions e instalan las dependencias con `pip install` directo en el runner; Trivy en `security.yml` hace `docker build` de cada Dockerfile individual, que tampoco usa MinIO como base. El único test que necesita MinIO real (`test_celery_integracion.py`, el E2E) ya estaba excluido de CI desde antes de este sprint — solo corre manualmente con `docker compose exec worker`.

**Investigación de alternativas gratis (2026-09-27):** confirmado con múltiples fuentes independientes, no es un problema de esta máquina ni transitorio:
- El 11 de septiembre de 2026 MinIO borró `minio/minio` y `minio/mc` de Docker Hub por completo.
- Desde el 24 de septiembre, `quay.io/minio/minio` también rechaza pulls anónimos — probado localmente contra un tag viejo (`RELEASE.2025-04-22T22-12-26Z`), mismo 401. Ni siquiera el último release "congelado" antes del cambio (`RELEASE.2025-09-07`) queda accesible sin cuenta.
- Es una decisión de negocio de MinIO: empujar a todos hacia su producto pago (AIStor), discontinuando las imágenes gratis de la edición community.
- **Alternativa gratis probada y funcional:** `cgr.dev/chainguard/minio:latest` — se puede bajar sin login, corrida localmente respondió `200` en `/minio/health/live` con una versión reciente (`RELEASE.2026-09-22T19-25-18Z`), no una imagen vieja congelada. Es el mismo binario de MinIO (misma API S3), solo cambia el registro/imagen. Contra: es una imagen "distroless" (sin shell adentro, no se puede hacer `docker exec -it ... sh` para debuggear).
- Otras alternativas evaluadas pero no probadas: SeaweedFS/Garage (S3-compatible pero no es MinIO, cambio de producto), LocalStack (pensado para mockear S3 en tests, no como backend persistente de desarrollo), compilar MinIO desde su fuente AGPLv3 en GitHub (gratis pero con mantenimiento propio).
- Fuentes: [Minimus — MinIO Docker Image Changes](https://www.minimus.io/post/minio-docker-image-changes-how-to-find-a-secure-minio-alternative), [bex.co — MinIO Vanished From Docker Hub](https://bex.co/blog/2026/09/25/minio-docker-hub-removal-quay-repoint), [byteiota — MinIO Is Gone From Docker Hub and Quay.io](https://byteiota.com/minio-docker-hub-quay-anonymous-pull-fix/), [GitHub — CloudTAK#1803](https://github.com/dfpc-coe/CloudTAK/issues/1803).

**Sin resolver a propósito:** no se tocó `docker-compose.yml` — el cambio de imagen (a `cgr.dev/chainguard/minio` o cualquier otra) es una decisión de equipo que afecta el entorno de desarrollo de todos, no solo a esta rama de CI de seguridad. Queda como problema abierto de mayor prioridad que el resto de este sprint, con una solución concreta ya investigada y verificada para cuando se decida aplicarla.

### Problemas abiertos (Sprint 14)

- ~~`minio/minio` no se puede bajar sin cuenta~~ — **resuelto**, ver "`docker-compose.yml`: `minio/minio` → `cgr.dev/chainguard/minio`" más abajo.
- ~~Bump de `fastapi`/`starlette`~~ — **resuelto**: `fastapi` 0.115.6 → 0.141.1 (PR de Dependabot #32, mergeado) trajo `starlette` a 1.7.0.
- ~~`github-actions-mutable-action-tag` / `gha-workflow-env-secret`~~ — **resueltos** por el pinning a SHA y el scoping de `JWT_SECRET_KEY` de arriba (Semgrep: 0 findings).
- **Sacar `continue-on-error` de los jobs de `security.yml`** una vez triageado el volumen inicial de hallazgos de Semgrep/Bandit/pip-audit/npm-audit/Trivy (dar 1-2 semanas de rodaje, como se hizo explícito arriba).
- **Evaluar upload de SARIF al tab de Security de GitHub** si la org obtiene licencia de GitHub Advanced Security.
- ~~Upgrade coordinado de `react`/`react-dom`/`react-leaflet`/`react-router-dom`~~ — **resuelto**, ver tarea más abajo.
- ~~Upgrade coordinado de `rasterio`/`gdal`~~ — **resuelto**, ver tarea más abajo (incluyó un segundo breakage no previsto: `pydantic` sin wheel para el Python 3.14 que trae la imagen nueva).
- **Upgrade coordinado de `rasterio`/`gdal`** (PR de Dependabot #21) — el bump de la imagen base `osgeo/gdal` rompe el build del worker: `rasterio==1.3.11` (2023) falla al compilar contra el Python 3.14 que trae la imagen nueva (`ModuleNotFoundError: No module named 'pkg_resources'`, un problema del build backend de esa versión vieja de rasterio, no de GDAL en sí). Arreglarlo de verdad implica bumpear `rasterio` también, lo que toca todo el pipeline de índices/vectorización — tarea aparte con testeo real, no un cambio aislado.
- **Triage de las ~20 PRs de Dependabot acumuladas (2026-10-04/08):** la mayoría (setup-node, setup-python, checkout, gitleaks-action, jinja2, leaflet-geoman-free, rasterio→1.5.1, minio, email-validator, geopandas, asyncpg, celery, vitest→5) tienen CI verde (salvo el ruido ya aceptado de pip-audit/npm-audit) y quedan pendientes de que el equipo las mergee desde GitHub — Claude Code tiene bloqueado `gh pr merge` incluso pedido explícitamente. De las rotas de verdad: **sqlalchemy/greenlet ya resuelto** (ver tarea arriba). Quedan: `bcrypt` 5.0 (rompe `passlib==1.7.4`, `ValueError: password cannot be longer than 72 bytes` al hashear — necesita decisión de alcance, no es un fix de una línea), `vite`→8 + `@vitejs/plugin-react`→6.1.1 (necesitan bumpearse juntos, cada uno solo rompe por peer dependency cruzada, mismo patrón que el bump de React del Sprint 14), y `osgeo/gdal`→3.13.3 (debería andar solo si se mergea primero `rasterio`→1.5.1, que ya viene con CI verde en su propia PR).
- **SQLAlchemy 2.1 deprecó pasar una expresión a `.distinct()`** para `DISTINCT ON` (`app/lotes/service.py::listar_lotes`, de HU-R4-03) — sugiere migrar a `postgresql.distinct_on()`. Sigue funcionando (solo warning), sin apuro.
- **Ningún producto del catálogo (`productos_fitosanitarios`) tiene `dosis_referencia` cargada** — las 21 filas sembradas en la migración 0015 (HU-R4-05 solo cargó precios y, en 0018, restricciones/seguridad) dejaron ese campo en `NULL`. Efecto real, verificado en vivo (ver tarea HU-R4-11 más abajo): con un lote y una zona de problema reales, la orden de trabajo calcula bien la cantidad "variable" tratada, pero **"Uniforme" y "Ahorro" en `/lotes/{id}/ahorro` quedan en `—`** porque no hay dosis con la que calcular cuánto se gastaría tratando todo el lote parejo — y lo mismo le pasa de antes al PDF de Orden de Trabajo (`volumen_total` sale siempre vacío en producción). No es un bug de HU-R4-11 ni de la Orden de Trabajo: es un hueco de datos del catálogo. Pendiente: cargar `dosis_referencia`/`unidad` real por producto (consultar al equipo agronómico o fuentes CASAFE/INTA, mismo criterio que usó HU-R4-05 para precios) en una migración de datos.
- **HU-R4-09 — falta el mapa de diferencia (criterio opcional, vale la diferencia entre 5 y 8 pts de la tarjeta):** reproyectar/remuestrear a una grilla común con rasterio los rasters de los dos vuelos comparados, restar (vuelo B − vuelo A) y vectorizar el resultado en zonas "mejoró/empeoró/igual", más el slider en el frontend. Requiere tarea de Celery nueva — no se encaró en esta pasada, que cubrió solo el criterio de estadísticas (diferencia de índice promedio y de superficie por severidad). **Actualización 2026-10-15:** se agregó "Cambio por zona" (mini-mapas por zona con Empeoró/No empeoró), que cubre una necesidad parecida con zonas vectorizadas existentes — no reemplaza este criterio, que pide el raster de diferencia real pixel a pixel.
- **La curva de NDVI esperado por estadio (migración 0025, 2026-10-15) es un placeholder genérico, no agronómicamente validada** — reemplazar con valores reales o recalcular estadísticamente cuando haya suficientes vuelos cargados por cultivo/estadio. Ver tarea "Tendencia del índice" del 2026-10-15.
- ~~`pillow` 10.4.0 tiene múltiples CVEs~~ — **resuelto**, ver tarea más abajo.
- ~~`python-jose` con CVEs parcheables~~ — **resuelto parcial**, ver tarea más abajo (queda 1 CVE nuevo sin fix disponible, evaluado como no explotable en este código).
- **`docker/certs/avast-root.crt` no es portable entre instalaciones de Avast de distintas máquinas** — Avast genera una raíz TLS-scanning self-signed distinta por cada instalación aunque el Subject/Issuer sea el mismo texto literal. El cert commiteado solo sirve en la máquina donde se exportó originalmente; cualquier otro dev con Avast activo necesita exportar su propia raíz (`Cert:\LocalMachine\Root` en Windows) y reemplazar el archivo localmente (sin commitear) para poder buildear la imagen `api`. Sin solución de equipo todavía — ver tarea HU-R4-07 más abajo donde se detectó.
- **El volumen `minio_data` de desarrollo creado con la imagen vieja `minio/minio` no es compatible con el usuario no-root de `cgr.dev/chainguard/minio`** — falla con `FATAL Unable to initialize backend: Unable to write to the backend`. Cualquier entorno local que todavía tenga el volumen viejo necesita recrearlo (`docker volume rm`) para migrar a la imagen nueva; se pierden los archivos ya subidos a MinIO (Postgres no se ve afectado). Ver tarea HU-R4-07 más abajo.

#### Revisión de los hallazgos de Semgrep (25 → 17 tras 2 arreglos)
**Fecha:** 2026-09-27

- **`dynamic-urllib-use-detected` (3)**: mismo falso positivo que el de Bandit (`workers/gis/satelital_catalogo.py`, más 2 scripts de POC — `scripts/descargar_sentinel2_real.py`, `scripts/poc_satelital_earthsearch.py`) — el scheme+host de la URL siempre es la constante fija de Earth Search, solo cambia el path/query. Resuelto con `# nosemgrep: dynamic-urllib-use-detected` + comentario, en los 3 archivos. Tests de `test_satelital_catalogo.py` (6) siguen pasando.
- **`dependabot-missing-cooldown` (4)**: la regla exige literalmente `cooldown.default-days: 7` en cada `package-ecosystem` de `dependabot.yml` — probado en local que `default-days: 5` seguía marcando el hallazgo (el mensaje de la regla lo dice explícito: "wait 7 days"). Se agregó `cooldown: default-days: 7` a los 4 ecosistemas — evita adoptar una versión recién publicada (potencialmente comprometida o rota) antes de que pase una semana.
- **`github-actions-mutable-action-tag` (10) y `gha-workflow-env-secret` (1)**: quedan como problemas abiertos (ver arriba) — no son arreglos de una línea, ameritan su propia decisión de alcance.

#### Primera tanda de Dependabot (25 PR) — triage y merge del grupo seguro
**Fecha:** 2026-09-28

Al agregar `dependabot.yml` en este sprint, Dependabot escaneó todo el repo de una sola vez y abrió **25 PR** (uno por dependencia desactualizada, topeado en 10 para `pip` y `npm` por `open-pull-requests-limit`). Se armó un triage por riesgo real (no solo por semver) mirando el estado de CI de cada uno:

- **Grupo A — mergeados sin objeción** (parche/minor, CI limpio salvo los 3 hallazgos esperados de Semgrep/pip-audit/npm-audit que no bloquean): `alembic` #38, `shapely` #37, `scikit-image` #36, `psycopg2-binary` #33, `pydantic-settings` #31, `sqlalchemy` #29, `axios` #34, `@geoman-io/leaflet-geoman-free` #42.
- **Grupo B — mergeado, prioridad**: `fastapi` 0.115.6 → 0.141.1 #32. Trajo `starlette` a 1.7.0, **resolviendo el CVE de `starlette` que quedaba como problema abierto** (verificado: `pip-audit` ya no lo lista). 237 tests de la imagen `api` siguen pasando.
- **Grupo C — sin mergear a propósito**: `actions/checkout` #26, `actions/setup-node` #25, `actions/setup-python` #23, `gitleaks/gitleaks-action` #22 (bumps de v4/v5/v2 a tags mayores más nuevos). Mergearlos ahora pisaría el pinning a SHA hecho en este mismo sprint (ver más arriba) — hay que esperar a que ese trabajo llegue a `main` y dejar que Dependabot regenere los bumps correctos sobre los SHA.
- **Grupo D — no mergear individual, ya rompió CI**: `react` #45, `react-dom` #39, `react-leaflet` #44, `vite` #40, `vitest` #43, `@vitejs/plugin-react` #41. Confirmado con el log real de CI: `react-leaflet@4.2.1` exige `react-dom@^18`, incompatible con React 19 — el PR de `react`/`react-dom` rompe `npm run build` en seco. Es un upgrade coordinado (los 6 juntos) que necesita su propia tarea con testeo real de todas las pantallas con mapas, no PRs individuales de Dependabot.
- **Grupo E — majors puntuales, sin mergear, necesitan prueba**: `osgeo/gdal` #21 (**ya rompió** el build de `worker` — `pip install` falla contra el GDAL nuevo), `redis` (cliente Python) #35, `weasyprint` #28 (genera los reportes PDF, es funcionalidad core), `pyshp` #27, `geotiff` (frontend) #30, `node` 20→25-slim #24.

**Conflicto entre PRs de Dependabot al mergear varias seguidas:** mergear 4 PRs de `pip` que tocan `docker/requirements.api.txt` (`alembic`, `shapely`, `scikit-image`, más otra) dejó a `psycopg2-binary` #33 en conflicto (`mergeable: CONFLICTING`) porque el diff de Dependabot no se recalcula solo al mergear una PR hermana que cambió una línea cercana en el mismo archivo. Se resolvió pidiéndole a Dependabot que recalcule el diff (comentario `@dependabot rebase` en el PR) en vez de resolver el conflicto a mano.

**Nota — merge de PRs bloqueado para Claude Code:** el modo automático de la herramienta rechaza explícitamente `gh pr merge` ("Merge Without Review"), incluso pedido de forma expresa por el usuario. Los 9 merges del grupo A+B los hizo el usuario manualmente desde GitHub siguiendo el orden sugerido.

#### Segunda tanda de bumps de Dependabot probados y aplicados (Grupo E)
**Fecha:** 2026-09-28
**Rama:** `fix/dependencias-pendientes`

De las PR de Dependabot que quedaban en el "Grupo E" (majors puntuales sin probar), se validaron y aplicaron 5:

- **`redis` (cliente Python) 5.2.1 → 8.1.0** (PR #35, `requirements.api.txt` + `requirements.worker.txt`) — salto de 3 versiones mayores. Validado con los 3 tests de `test_celery_integracion.py`, incluido el ciclo completo E2E (encolar → Celery → worker → Redis como result backend).
- **`weasyprint` 63.1 → 70.0** (PR #28, `requirements.api.txt`) — genera los reportes PDF. Validado: 237 tests de la imagen `api` pasan, incluidos `test_reportes_api.py` y `test_orden_trabajo_pdf_api.py`.
- **`pyshp` 2.3.1 → 3.1.6** (PR #27, `requirements.api.txt`) — exportación de zonas a Shapefile. Validado con `test_exportacion_api.py` dentro de la misma corrida de 237 tests.
- **`geotiff` (frontend) 2.1.3 → 3.0.5** (PR #30, `frontend/package.json`) — la única breaking change real de la v3.0.0 es "deferred tag reading" (lectura diferida de tags), que podía afectar `getGeoKeys()`/`getBoundingBox()` en `frontend/src/utils/geotiffLimites.js` de forma silenciosa (esa función tiene un `try/catch` que traga cualquier error y devuelve `null`, así que una regresión no se ve como un crash). `npm run build` + `npm test` no alcanzaban para confirmarlo — se corrió un smoke test aparte con Node contra `tests/fixtures/sentinel_ndvi_test.tif` (el único GeoTIFF real del repo) llamando `fromArrayBuffer` + `getImage().getBoundingBox()/getGeoKeys()` directamente: mismo bbox, mismas claves, objeto plano (no una Promise). Script descartado después de verificar, no se commiteó.
- **`node` 20-slim → 25-slim** (PR #24, `docker/Dockerfile.frontend`) — validado build + `docker run` real del contenedor (`vite --host` arranca y responde `200`), no solo que compile la imagen.

**Sin aplicar del Grupo E:** `osgeo/gdal` (PR #21) — ver "Problemas abiertos" arriba, requiere bumpear `rasterio` también.

#### `docker-compose.yml`: `minio/minio` → `cgr.dev/chainguard/minio`
**Fecha:** 2026-09-28
**Rama:** `fix/minio-imagen-chainguard`

Al reconstruir el stack desde cero (tras un reinicio de la máquina que limpió todo el estado de Docker), `docker compose up` dejó de poder levantar `minio` — bloqueaba a `api` y `worker` (ambos con `depends_on: minio: condition: service_healthy`), es decir, a cualquiera que clonara el repo hoy y quisiera correr la app.

**Causa raíz (no es un problema de esta máquina):** MinIO dio de baja `minio/minio` de Docker Hub el 2026-09-11, y desde el 2026-09-24 su alternativa (`quay.io/minio/minio`) exige login incluso en tags viejos (`RELEASE.2025-04-22T22-12-26Z` probado, 401) — empuja a todos hacia su producto pago (AIStor). Confirmado con la API pública de Docker Hub (`GET /v2/repositories/minio/minio/` → `object not found`) y con varias fuentes externas (ver detalle completo en el hallazgo del Sprint 14, rama `feat/ci-seguridad-sast-sca`, todavía sin mergear).

**Decisiones tomadas:**
- Se eligió `cgr.dev/chainguard/minio:latest` sobre las otras alternativas evaluadas (SeaweedFS/Garage, LocalStack, compilar desde fuente): mismo binario/API de MinIO (no hay que cambiar nada del código de `app`/`workers` que ya habla el protocolo S3), gratis, sin login, y activamente actualizado (`RELEASE.2026-09-22T19-25-18Z` al momento de probarlo, no una imagen congelada).
- El healthcheck (`mc ready local`) sigue funcionando sin cambios — la imagen de Chainguard también trae el cliente `mc`.
- Único trade-off conocido: es una imagen "distroless" (sin shell), así que `docker exec -it agronexo-minio-1 sh` para debuggear no va a funcionar. No se usó nunca en este proyecto, así que no es una pérdida real hoy.

**Verificación (stack completo desde cero, no solo el contenedor de MinIO):**
- `docker compose up -d` — los 6 servicios (`db`, `redis`, `minio`, `api`, `worker`, `frontend`) llegan a `healthy`/`running` sin intervención manual.
- `GET /minio/health/live` → `200`, consola en `:9001` → `200`.
- `GET /api/v1/health` y `/api/v1/health/db` → `ok`.
- `tests/test_celery_integracion.py` (los 3 tests, incluido el ciclo completo E2E que sube un archivo real a MinIO y lo procesa vía Celery+worker — antes solo se podía correr con el stack completo levantado) — **los 3 pasan**.

**Resultado:** cualquiera que clone el repo hoy y corra `docker compose up -d --build` puede levantar la app completa de nuevo, sin crear ninguna cuenta.

#### HU-R4-01 · Aislamiento multi-tenencia — fix IDOR en endpoints de índices adicionales
**Fecha:** 2026-09-30
**Rama:** `fix/idor-indices-vuelo`

Auditoría del estado actual de aislamiento por tenant (no hay `tenant_id`, es ownership por `lotes.usuario_id`; `vuelos`/`cultivos`/`analisis_indices` se aíslan transitivamente vía `lote_id`). El patrón dominante en todos los routers (`obtener_lote(db, lote_id, usuario_id=current_user.id)` → 404 antes de tocar hijos) está bien aplicado en lotes, cultivos, vuelos, diagnóstico, reportes y órdenes de trabajo.

**Hallazgo (IDOR real):** `GET /lotes/{lote_id}/vuelos/{vuelo_id}/indices/{indice}/estado` y `.../indices/{indice}/resultado` (`app/ingesta/router.py`) validaban que `lote_id` fuera del usuario, pero la función de servicio detrás (`obtener_analisis_indice`, `app/ingesta/service.py`) filtraba `AnalisisIndice` solo por `vuelo_id`, sin cruzar con el lote — `analisis_indices` no tiene columna de owner ni de `lote_id`, solo `vuelo_id`. Un usuario dueño de **cualquier** lote podía pasar su propio `lote_id` junto con un `vuelo_id` ajeno adivinado/enumerado y leer el estado y el GeoJSON de índices (NDRE/SAVI/ExG) de otro tenant.

**Fix:** `obtener_analisis_indice` ahora hace `JOIN` con `Vuelo` y filtra por `Vuelo.lote_id == lote_id` además de `vuelo_id`. Se propagó el parámetro `lote_id` a través de `obtener_estado_analisis_indice` y `obtener_resultado_geojson_indice`, y a sus 3 llamadores (`app/ingesta/router.py` × 2, `app/diagnostico/service.py::generar_diagnostico`, que ya tenía el `lote` validado disponible).

**Decisiones tomadas:**
- No se creó una dependencia FastAPI centralizada nueva para reemplazar el patrón repetido `obtener_lote(...) or 404` — ya es consistente en todos los routers y un refactor a esta altura suma riesgo sin ganancia real de seguridad. El criterio de aceptación de "dependencia centralizada" se interpreta como la reutilización de la misma función de servicio en todos lados, no como un `Depends()` nuevo.
- No se tocó el modelo de datos (no se agregó `lote_id`/owner a `analisis_indices`) — el `JOIN` con `Vuelo` alcanza y evita una migración para esto.

**Tests nuevos (`tests/test_multi_tenant_indices.py`, 7 casos):** acceso cruzado a ambos endpoints con `lote_id` propio + `vuelo_id` ajeno (el caso exacto del IDOR) → 404; con `lote_id` ajeno (control, ya bloqueado antes del fix) → 404; camino propio sigue en 200; sin auth → 401. Corridos junto con toda la suite de la imagen `api` (244 tests, antes 237) — sin regresiones.

**Sin tocar a propósito:** el resto de los criterios de aceptación de HU-R4-01 (URLs de MinIO prefirmadas — ya verificado que la cobertura es completa, un solo punto de generación en `app/core/storage.py::presigned_url` con expiración siempre seteada) ya estaban resueltos de releases anteriores; esta tarea se acotó al gap real encontrado.

#### Upgrade `react`/`react-dom` 18→19, `react-leaflet` 4→5, `react-router-dom` 6→7
**Fecha:** 2026-09-30
**Rama:** `feat/upgrade-react19-leaflet-router`

Retomaba el "Grupo D" de Dependabot (PRs #39, #44, #45, #40, #43, #41), documentado como problema abierto porque el PR de `react`/`react-dom` solo rompía `npm run build` en seco (`react-leaflet@4.2.1` exige `react-dom@^18`, incompatible con React 19).

Antes de tocar código se revisaron los changelogs reales contra el uso concreto del repo:
- `react-router-dom`: el proyecto solo usa la API declarativa clásica (`BrowserRouter`, `Routes`, `Route`, `Link`, `Navigate`, `useNavigate`, `useParams`, `useLocation`, sin data routers/loaders) — `react-router-dom` sigue existiendo como paquete propio en v7 (confirmado contra el registro de npm), sin cambios de código para este patrón.
- `react-leaflet` v5: los únicos breaking changes documentados son "requiere React 19" y "se eliminó `LeafletProvider`" — el repo no usa `LeafletProvider` en ninguno de sus 7 componentes de mapa (`MapaZonas`, `MapaNEA`, `MiniMapaLote`, `MapaIndice`, `ModalLimites`, `ModalCargaGeoTIFF`, `MapaDibujoLote`), solo `MapContainer`/`TileLayer`/`GeoJSON`/`useMap`.

**Decisiones tomadas:**
- No se bumpearon `vite`/`vitest`/`@vitejs/plugin-react` (el resto del Grupo D). Sus peer deps reales muestran que no hace falta: `@vitejs/plugin-react@4.7.0` (ya instalado) soporta hasta `vite ^7`, así que React 19 funciona con el `vite@6.4.3` actual sin bumpear nada. Los PRs de Dependabot pedían saltar a majors mucho más nuevos (vite 8, vitest 5) — motu proprio fuera de alcance, y `vitest@5` ni siquiera es compatible con `node:25-slim` (la imagen Docker del frontend), así que forzarlo hubiera abierto un problema nuevo sin necesidad.
- Diff final: 4 líneas en `frontend/package.json` (`react`, `react-dom`, `react-leaflet`, `react-router-dom`).

**Verificación:**
- `npm run build` y `npm test` (vitest, 9 tests) — limpios.
- Imagen Docker del frontend reconstruida (`docker compose build frontend`) para tomar las versiones nuevas — `node_modules` no está bind-mounteado en `docker-compose.yml`, así que un `npm install` en el host no alcanza para probar contra el contenedor real.
- Recorrido manual en el browser pane con el stack completo: login → dashboard → `/lotes` → `/lotes/{id}` → `/lotes/{id}/vuelos/{id}` (rutas con parámetros dinámicos, todas con `useNavigate`/`useParams`/`Link`) — sin errores de consola.
- Los 3 patrones de uso de `react-leaflet` probados contra datos reales: mapa de zonas NDVI coloreado (`MapaZonas`), mapa de diagnóstico con color por severidad y redibujo de la capa `GeoJSON` al cambiar de tab (mismo componente, sin remount manual), y dibujo de polígono interactivo con `@geoman-io/leaflet-geoman-free` (`MapaDibujoLote`, modal "Nuevo lote") — cálculo de área en vivo correcto (41.42 ha sobre el polígono dibujado). Los tres, sin errores de consola.

#### Fix: label engañoso "Procesando imagen" en Vista geoespacial del Dashboard
**Fecha:** 2026-09-30
**Rama:** `feat/upgrade-react19-leaflet-router`

Encontrado al probar el upgrade de React contra datos reales, no causado por él — el widget "Vista geoespacial" del Dashboard (`AnalisisMap` en `frontend/src/pages/Dashboard.jsx`) pide el GeoJSON resumido del vuelo con `?absorber=true` (zonas chicas combinadas con la vecina, para una vista de vistazo — ver `useVueloProgreso.js`). Mientras ese cómputo geométrico corre (puede tardar bastante en un lote real grande, ver hallazgo del Sprint 14 sobre polígonos con muchos vértices), el componente caía en el mismo branch que muestra la barra de progreso del procesamiento original con el vuelo ya en `estado='completado'`, mostrando "Procesando imagen... 0%" — sugiere que se está reanalizando desde cero cuando en realidad el análisis ya terminó y solo falta generar la vista resumida.

**Fix:** nuevo branch explícito para `estadoActual === 'completado' && !geojson` que muestra "Generando vista del mapa..." con el mismo spinner que ya usa la pestaña Diagnóstico (`.diagnostico-loading`/`.diagnostico-spinner`, reusado en vez de duplicar CSS), en lugar de la `BarraProgreso` con porcentaje falso.

**Verificación:** confirmado en el browser pane que el mensaje nuevo aparece mientras el fetch está en curso; el spinner se confirmó en el DOM (`getComputedStyle`) porque el pane tuvo un glitch de captura de screenshot en el momento de probar. Sin errores de consola.

#### HU-R4-02 · Trazabilidad completa del análisis
**Fecha:** 2026-09-30
**Rama:** `feat/hu-r4-02-trazabilidad`

Auditoría previa (ver historial de la tarea) encontró que de los 4 criterios de aceptación, solo "no editable desde la interfaz" ya estaba resuelto (no existe `PUT`/`PATCH` sobre `vuelos` ni `analisis_indices`). Faltaba: quién subió cada vuelo, el mapeo de bandas y umbral usados en el NDVI primario (los índices adicionales ya tenían `metodo_umbral` en `analisis_indices`), la versión del motor de reglas, y exponer todo esto en el frontend y el PDF ejecutivo.

**Migración `0021_trazabilidad_analisis`:**
- `vuelos.subido_por_id` (FK `usuarios.id`, `SET NULL`), `vuelos.metodo_umbral`, `vuelos.mapeo_bandas` (JSONB).
- `diagnosticos.motor_version`.
- Backfill: `subido_por_id` se aproxima con el dueño del lote (no hay forma de saber con certeza quién subió un vuelo viejo). `metodo_umbral`/`mapeo_bandas` de vuelos ya completados **sí se reconstruyen con certeza** (no una aproximación): el NDVI primario siempre usó `metodo_umbral="fijo"` — ningún endpoint permitía elegir otro — y el mapeo de bandas es una función pura de `sensor`, así que se congelan los valores reales usados según `workers/gis/band_mapping.py::MAPEO_SENSORES`. `motor_version` de diagnósticos ya calculados se completa con `"1.0.0"`, única versión que existió hasta esta migración.

**Captura:**
- `subido_por_id` se graba en los 3 puntos donde se crea un `Vuelo` (`app/ingesta/service.py`) — ya recibían `usuario_id` como parámetro, no hizo falta tocar los routers.
- `metodo_umbral`/`mapeo_bandas` los completa el worker al terminar de procesar (`workers/gis/tasks.py::procesar_vuelo` → `_actualizar_vuelo`), igual que ya hacía para los índices adicionales — cubre subida por dron y por satélite, porque ambos flujos terminan encolando la misma tarea `procesar_vuelo`.
- `motor_version` (constante `MOTOR_VERSION` nueva en `app/diagnostico/reglas.py`) se graba en cada `(re)cálculo` de diagnóstico, junto con una copia de los 4 campos de arriba en `metadata` — así el PDF y el endpoint de diagnóstico los tienen sin tocar el schema de `VueloListItem` para eso.

**Error encontrado — `Vuelo.subido_por` devolvía `None` con `subido_por_id` bien seteado**
Un test de trazabilidad (`test_diagnostico_incluye_trazabilidad_completa`) mostró `assert None == 'Test Diagnostico (...)'` a pesar de que `subido_por_id` estaba correcto en la base. Causa: `Usuario.id` está tipado `UUID(as_uuid=False)` (Python `str`) pero `subido_por_id` se definió `UUID(as_uuid=True)` (Python `uuid.UUID`) — el loader `selectin` compara los valores cargados en memoria para emparejar filas, y `uuid.UUID(...) != str(...)` en Python, así que la relación nunca se resolvía (sin ningún error, silenciosamente `None`). Se corrigió tipando `subido_por_id` como `UUID(as_uuid=False)` para que coincida con `Usuario.id`. `Lote.usuario_id` tiene el mismo mismatch de tipos con `Usuario.id` pero está dormido (nada hace eager load de esa relación hoy) — se dejó flagueado como tarea aparte en vez de tocarlo en esta rama, fuera de alcance de HU-R4-02.

**Frontend:**
- `ResultadosVuelo.jsx`: panel colapsable "Trazabilidad del análisis" (`<details>`, solo lectura) con archivo de origen, quién subió, fecha de subida, mapeo de bandas (con labels legibles) y método de umbral.
- `TablaDiagnostico.jsx`: la versión del motor de reglas se suma a la línea de metadata existente del diagnóstico.

**PDF ejecutivo:** nueva sección "Trazabilidad del análisis" en `reporte_ejecutivo.html`, alimentada desde `app/reportes/service.py` (mismo dict de metadata que ya recibía la función, sin cambiar su firma).

**Verificación:**
- Migración probada con `downgrade`/`upgrade` reales contra la base de dev — backfill correcto verificado con `psql` directo.
- 246 tests de la imagen `api` pasan (244 + 2 nuevos: captura de uploader al subir un vuelo, y metadata completa de trazabilidad en el diagnóstico).
- PDF probado en 3 niveles: render directo del template Jinja2 (assert de contenido), generación completa de bytes PDF con `generar_pdf_reporte`, y llamada real al endpoint `GET .../reporte/pdf` contra el stack levantado (200, `application/pdf`, tamaño consistente con la generación anterior).
- Recorrido manual en el browser pane: panel de trazabilidad expandido con datos reales de un vuelo real (`Lote Cele`), incluido un recálculo de diagnóstico que confirma `motor de reglas v1.0.0` en la barra de metadata. Sin errores de consola.

**Extra (a pedido, mismo bug, mismo branch):** `Lote.usuario_id` tenía el mismo mismatch de tipos que `Vuelo.subido_por_id` frente a `Usuario.id` — dormido porque nada hacía eager load de `Lote.usuario`, pero se corrigió acá mismo en vez de dejarlo como tarea aparte (investigado el impacto: solo afecta cómo se deserializa el valor al leerlo del ORM, no las comparaciones en cláusulas `WHERE` de SQLAlchemy ni la validación de los schemas Pydantic, que coercionan `str`→`uuid.UUID` sin problema). Test de regresión nuevo: `tests/test_lotes.py::test_lote_usuario_carga_via_selectinload` — carga un lote con `selectinload(Lote.usuario)` y confirma que no da `None`. 247 tests pasan (246 + este).

#### HU-R4-03 · Listado multi-lote
**Fecha:** 2026-09-30
**Rama:** `feat/hu-r4-03-listado-multi-lote`

La tarjeta pedía nombre, productor/campo, cultivo, superficie, fecha del último vuelo, estado del último análisis, filtros (cultivo/campaña/estado) y búsqueda por nombre, paginado del lado del backend. "Productor/campo" se descartó a pedido del equipo — nunca existió ese dato, fue un error al crear la tarjeta.

**Hallazgo antes de tocar código:** `GET /lotes` no tenía filtros ni paginado, y el frontend hacía un `GET /lotes/{id}/vuelos` **por cada lote** del listado (`Lotes.jsx`, `Promise.allSettled`) solo para mostrar la cantidad de vuelos — el antipatrón N+1 que la propia tarjeta pide evitar explícitamente.

**Backend:** `app/lotes/service.py::listar_lotes` resuelve el último vuelo (y el cultivo actual, para filtrar) de cada lote en una sola consulta con `DISTINCT ON` (mismo patrón que ya usa la migración 0020), sin tocar la relación `Lote.cultivos` existente. Nueva firma con `q`, `cultivo`, `campana`, `estado`, `page`, `page_size`; `GET /lotes` expone los mismos query params. `LoteResponse` suma `ultimo_vuelo_fecha`/`ultimo_vuelo_estado`; `LoteListResponse` suma `page`/`page_size`. Sin migración nueva — no hizo falta ningún campo en la base, todo sale de columnas que ya existían.

**Frontend:** `Lotes.jsx` ya no pide vuelos por lote — usa `ultimo_vuelo_fecha`/`ultimo_vuelo_estado` del propio `GET /lotes`. Se separó en dos listas: `lotes` (página actual, filtrada, para la grilla) y `lotesTodos` (hasta 100, sin filtrar, para los modales de "Cargar Ortomosaico" y "Elegir lote", que tienen que poder ofrecer cualquier lote del usuario — si se les pasaba la lista paginada/filtrada, un lote fuera de la página actual dejaba de poder elegirse para subir un vuelo). Barra de filtros (buscador con debounce de 350ms, cultivo, campaña, estado) y paginado agregados a la pantalla.

**Verificación:**
- 6 tests nuevos en `tests/test_lotes.py` (último vuelo sin consulta extra, lote sin vuelos, búsqueda, filtro de estado, filtro de cultivo/campaña, paginado). 253 tests de la imagen `api` pasan (247 + 6).
- `npm run build` limpio.
- Recorrido manual en el browser pane: búsqueda y filtro de estado confirmados contra datos reales (excluyen correctamente un lote sin vuelos/cultivo); el modal "Cargar Ortomosaico" sigue ofreciendo todos los lotes aunque la grilla esté filtrada. Sin errores de consola nuevos.

#### HU-R4-06 · Despliegue — base de infraestructura (sin servidor real todavía)
**Fecha:** 2026-09-30
**Rama:** `feat/despliegue-produccion-base`

La tarjeta (8 pts, Sprint 13→14) pide desplegar AgroNexo en un entorno accesible y seguro. Se armó primero toda la parte que no depende de tener un servidor real levantado, para no bloquear el sprint mientras se resuelve dónde alojarlo (ver problema abierto abajo).

**Agregado:**
- `docker-compose.prod.yml`: sin bind mounts de código, sin `--reload`; `db`/`redis`/`minio` sin `ports:` publicados al host (quedan solo en la red interna de Docker — cubre el requisito de firewall para esos puertos); `api` corre `alembic upgrade head` antes de levantar uvicorn como parte del arranque del contenedor, no manualmente.
- `docker/Dockerfile.nginx` + `docker/nginx/nginx.conf`: reemplaza al dev server de Vite por un build estático servido detrás de Nginx como reverse proxy. Arranca en HTTP puro (funciona con solo IP pública, sin dominio); el bloque HTTPS queda comentado con instrucciones para activarlo con Certbot una vez que haya un dominio real apuntando al servidor.
- Servicio `certbot` en el compose de producción (renovación automática cada 12h vía `certbot renew` en loop).
- `.env.prod.example`: template de variables de producción, análogo a `.env.example` pero con placeholders `REEMPLAZAR_*` — el `.env.prod` real queda gitignored.
- Sección "Despliegue en producción" en el README con la guía paso a paso del primer deploy y de los deploys siguientes.
- `scripts/backup_postgres.sh` (pg_dump vía `docker compose exec`, gzip, retención 14 días) y `scripts/backup_minio.sh` (`mc mirror` dentro del propio contenedor `minio` hacia un volumen de backups separado del de datos, misma retención) — pensados para cron en el host del servidor. Documentados en el README con las líneas de `crontab` sugeridas.

**Decisiones tomadas:**
- No se tocó el `docker-compose.yml` de desarrollo — producción vive en un archivo aparte (`-f docker-compose.prod.yml`) para no arriesgar romper el flujo de dev de nadie del equipo.
- Nginx + build estático en vez de dejar corriendo el dev server de Vite en producción (lo segundo es una mala práctica — sin HMR no aporta nada y es más lento/pesado que servir estático).

**Hallazgo — migración 0006 sembraba las credenciales de desarrollo en cualquier entorno**
`migrations/versions/0006_seed_usuario_default.py` insertaba `admin@agronexo.com` / `password123` hardcodeado. Al automatizar `alembic upgrade head` como parte del deploy (criterio explícito de HU-R4-06), esa migración iba a correr también en producción y sembrar esas mismas credenciales ahí — exactamente lo que otro criterio de la misma tarjeta prohíbe explícitamente.
Se modificó la migración para leer `ADMIN_EMAIL`/`ADMIN_PASSWORD` del entorno (`os.environ.get`, con el valor de desarrollo como fallback si no están seteadas) en vez de hardcodearlas. No se creó una migración nueva porque es un cambio de comportamiento (lee del entorno), no de esquema — y la 0006 nunca llegó a aplicarse contra una base de producción real todavía.

**Nota del merge con `main` (2026-10-08):** esta misma migración también cambió en `main` (fix de `bcrypt`/`passlib`, ver más abajo) — se resolvió el conflicto conservando ambos cambios: lee `ADMIN_EMAIL`/`ADMIN_PASSWORD` del entorno (este fix) y hashea con `bcrypt` directo en vez de `passlib` (el otro fix, porque `passlib` ya no está instalado).

**Problema abierto — sin servidor real para probar el resto de los criterios**
Faltan: HTTPS real (necesita dominio + Certbot contra una IP pública real), prueba con GeoTIFF >500MB, y firewall del proveedor (los scripts de backup de Postgres/MinIO ya están escritos, ver arriba — falta instalar el cron en un servidor real). Se intentó Oracle Cloud Free Tier (instancia ARM `VM.Standard.A1.Flex`) en la región `sa-vinhedo-1`, con reintentos automatizados vía script (`oci compute instance launch` en loop) durante casi dos semanas (17/09 → 30/09) sin conseguir capacidad ni con 4 OCPU/24GB ni con 2 OCPU/12GB — la región está saturada de forma sostenida, no es mala suerte puntual. Nota: otro compañero (`cmartinrodich@gmail.com`) agregó entradas de `.gitignore` para un script propio (`scripts/oci_arm_watch.*`) el mismo día — evaluar si conviene unificar esfuerzos en vez de que cada uno reintente por su cuenta. Decisión pendiente: insistir con Oracle vs. migrar a un VPS pago (Hetzner CPX31 evaluado como alternativa, ~USD 12/mes, sin espera de capacidad).

**Error encontrado — Semgrep `request-host-used` en `docker/nginx/nginx.conf` (commit `cbf1e4d`)**
El PR #54 falló el job *SAST — Semgrep* con 3 hallazgos bloqueantes de `generic.nginx.security.request-host-used.request-host-used`: `proxy_set_header Host $host;` (línea activa y copia comentada del bloque HTTPS) y `return 301 https://$host$request_uri;` en el bloque comentado de redirect.
Se reemplazó `$host` por `$server_name` en los `proxy_set_header` y por `DOMINIO_AQUI` fijo en el redirect. Es seguro porque la API no lee el header `Host` (sin `TrustedHostMiddleware`, `request.url` ni `base_url` en `app/`). Semgrep pasa tras el fix.

**Estado del CI del PR #54 — 2 checks siguen en rojo, heredados de `main`**
*SCA — pip-audit* (`pillow 10.4.0`, `jinja2 3.1.4`, `ecdsa 0.19.2`) y *SCA — npm audit* (`vitest ^2.1.8` → `vite`/`esbuild` vulnerables; 1 high + 1 critical, solo en devDependencies) fallan idénticos en `main` (corrida del push del 2026-10-01), así que no vienen de esta rama. Son deuda de dependencias que el workflow de seguridad (2026-09-27) sacó a la luz; `pillow` ya figura en "Problemas abiertos (Sprint 14)". Hay que resolverlos en un PR aparte (`chore/`), y además es requisito de la HU ("CI en verde antes de cada deploy"). `ecdsa` es transitiva (probablemente `python-jose`) y no tenía fix publicado al momento de revisar.

**Evaluación de proveedores de hosting (2026-09-30)** — referencia para la decisión pendiente, montos tomados de blogs/comparadores, a confirmar en las páginas oficiales:

| Opción | Crédito / costo | Duración |
|---|---|---|
| Oracle Cloud ARM (free tier) | Gratis | Indefinida, si hay capacidad |
| Google Cloud | USD 300 | 90 días, cuenta nueva, pide tarjeta |
| AWS cuenta nueva (São Paulo) | USD 100 + hasta 100 por tareas de onboarding | ~2–5 meses, pide tarjeta |
| Azure for Students | USD 100/año, sin tarjeta | ~1,5 meses encendida 24/7 |
| Linode | USD 100 | 60 días |
| Hetzner (VPS x86) | ~USD 12–15/mes | Mientras se pague |
| Vultr | USD 100 | 14 días |

Descartados: infra de la UTN (no existe), DigitalOcean vía GitHub Student Pack (el crédito terminó el 31/07/2026), AWS Educate (no da créditos), Heroku (no corre docker-compose con PostGIS/MinIO/Celery). El dominio gratis de Namecheap (Student Pack) sirve para el HTTPS con Let's Encrypt. Decisión pendiente del equipo.

#### HU-R4-10 · Personalización del perfil
**Fecha:** 2026-10-08
**Rama:** `feat/hu-r4-10-personalizacion-perfil`

Los 4 criterios de aceptación: editar datos personales/empresa con validaciones, logo de empresa usado en el PDF ejecutivo y la orden de trabajo, cambio de contraseña, y acceso desde el panel izquierdo.

**Migración `0022_personalizacion_perfil_usuario`:** agrega a `usuarios` — `avatar_key`, `descripcion`, `cuit`, `telefono_contacto`, `matricula_aplicador`, `nombre_empresa`, `logo_empresa_key`. Todos nullable (cuentas existentes no tienen estos datos). `avatar_key`/`logo_empresa_key` guardan la clave del objeto en MinIO (mismo patrón que `lotes.geojson_key`), no una URL — se resuelve a URL firmada recién al servir `/auth/me`.

**Backend:**
- `PUT /auth/me` (datos de perfil, `PerfilUpdateRequest` con validación de formato de CUIT), `POST /auth/me/password` (requiere la contraseña actual), `POST /auth/me/avatar` y `POST /auth/me/logo-empresa` (multipart, valida extensión + magic bytes JPG/PNG en `app/auth/validator.py`, mismo criterio que `app/ingesta/validator.py` para GeoTIFF).
- `app.auth.service.resolver_datos_aplicador(usuario)`: arma el dict de perfil (incluye el logo ya descargado de MinIO y codificado en base64) que consumen `app.reportes.service.generar_pdf_reporte` y `app.ordenes_trabajo.service.generar_pdf_orden_trabajo` — ambos módulos declaran explícitamente que no tocan MinIO (transformación pura de datos), así que el logo llega resuelto desde el router, igual que ya hace `mapa_base64`.

**Decisiones tomadas:**
- Página propia (`/perfil`) en vez de modal — a pedido explícito, por la cantidad de campos.
- El wiring a los PDFs se incluyó en esta misma tarea (lo pide el criterio de aceptación explícitamente) en vez de dejarlo para cuando se trabaje esa historia específica.
- El ítem "Configuración" del sidebar (marcado `proximamente: true` desde que se creó) se renombró a "Mi perfil" y se habilitó, en vez de agregar una entrada nueva — es el mismo slot que la nota original de la tarjeta describe.

**Frontend:** `PerfilUsuario.jsx` (dos cards: datos personales/empresa + avatares, y cambio de contraseña), `api/perfil.js`, `useAuth.js` suma `actualizarUsuario()` para sincronizar `localStorage`/estado tras editar (antes solo `login()` los seteaba). El bloque usuario del sidebar (`SidebarNav.jsx`) ahora es clickable, muestra el avatar real si existe, y el nombre de empresa en vez de "Productor Agri" fijo.

**Verificación:**
- Backend probado contra el stack real (migración aplicada, API reiniciada): `PUT /auth/me` con datos válidos (200) y CUIT inválido (422), cambio de contraseña con clave actual incorrecta (400) y correcta (204, confirmado con login real a la clave nueva y revertido), upload de un PNG real a `/auth/me/logo-empresa` (200, URL firmada de MinIO en la respuesta).
- `resolver_datos_aplicador` probado directo dentro del contenedor `api`: descarga el logo real de MinIO y lo codifica en base64 correctamente (prefijo `data:image/png;base64,...`).
- Recorrido manual en el browser pane: login real, navegación a `/perfil`, edición de "Descripción" + guardado (200, mensaje de confirmación), intento de cambio de contraseña con confirmación distinta a la nueva — bloqueado del lado del cliente antes de llamar al backend, con el mensaje correcto. Sidebar muestra "Mi perfil" resaltado y el nombre de empresa cargado. Sin errores de consola.
- El wiring del logo dentro del PDF renderizado end-to-end (reporte ejecutivo real, lote con vuelo+diagnóstico completo) lo confirmó el usuario manualmente tras el merge — el logo se ve correctamente en el PDF generado.

#### Fix: bump coordinado `vite` 6→8 + `@vitejs/plugin-react` 4→6 (PRs Dependabot #69 + #41)
**Fecha:** 2026-10-08
**Rama:** `fix/vite8-plugin-react-coordinado`

Último fix del triage de Dependabot. Mismo patrón que el upgrade de React/react-leaflet/react-router-dom del Sprint 14: dos PRs de Dependabot que no pueden mergearse por separado porque sus peer dependencies se pisan — `@vitejs/plugin-react@4.7.0` no soporta `vite@8` (su rango es `^4.2.0 || ^5.0.0 || ^6.0.0 || ^7.0.0`), y `@vitejs/plugin-react@6.1.1` exige `vite@^8.0.0`. Cada PR de Dependabot, al bumpear solo su propia dependencia, rompe contra la versión vieja de la otra.

**Fix:** se bumpearon ambas juntas en `frontend/package.json` — `vite` a `^8.3.4` y `@vitejs/plugin-react` a `^6.1.2` (versiones estables más nuevas que las de las PRs originales de Dependabot, 8.3.1/6.1.1, al momento de este fix). `vitest@5.0.3` (ya mergeado del Grupo A) soporta `vite@^8.0.0` sin cambios.

**Verificación:**
- `npm install` — resuelve limpio, sin `ERESOLVE`.
- `npm run build` — build de producción limpio (mismo warning preexistente de chunk >500kB, no relacionado).
- `npm test` (vitest) — 9 tests pasan.
- `docker compose build frontend` — build limpio, Vite 8.3.4 arranca sin errores.
- Recorrido manual en el browser pane con el stack completo: login → `/lotes` → detalle de lote → resultados de vuelo, probando los dos modos de color del mapa (zonas NDVI y diagnóstico por severidad, que redibuja la capa `GeoJSON` de `react-leaflet` sin remount manual) — el mismo camino crítico que se probó en el upgrade de React 19 del Sprint 14. Sin errores de consola nuevos (los únicos errores vistos fueron 401/502 de un desajuste local entre contenedor `api` y rama de código al cambiar de rama, no relacionados a este cambio, resueltos reconstruyendo la imagen).
#### Fix: `bcrypt` 4.2.1 → 5.0.0, se saca `passlib` (PR Dependabot #60)
**Fecha:** 2026-10-08
**Rama:** `fix/bcrypt-5-sin-passlib`

Tercer fix del triage de Dependabot. `passlib==1.7.4` está sin mantenimiento desde 2020 y es incompatible con bcrypt≥5 — no es un problema de la contraseña del usuario: passlib corre un self-test interno (`detect_wrap_bug`, para detectar un bug viejo de wraparound de bcrypt) que hashea un vector de prueba de más de 72 bytes, y bcrypt 5.0 ahora rechaza eso en vez de tolerarlo. El error (`ValueError: password cannot be longer than 72 bytes`) salta en el primer `hash()`/`verify()`, antes de llegar a la contraseña real.

**Fix:** se sacó `passlib` de `docker/requirements.api.txt` y `app/auth/service.py::hash_password`/`verify_password` llaman a `bcrypt.hashpw`/`bcrypt.checkpw` directo. El formato del hash (`$2b$...`) es el mismo que ya generaba passlib (que internamente llamaba a las mismas funciones de `bcrypt`), así que **no hace falta migrar las contraseñas ya guardadas** — se verificó explícitamente logueando con el hash viejo del usuario admin seed (`migrations/0006`).

**Efecto secundario necesario:** `migrations/versions/0006_seed_usuario_default.py` también usaba `passlib` para hashear la contraseña del usuario seed — se actualizó al mismo patrón de `bcrypt` directo (si no, cualquier `alembic upgrade head` desde una base vacía fallaría al no estar más `passlib` instalado). Es una excepción puntual a "no tocar migraciones viejas": no cambia la lógica de negocio ni el resultado (mismo formato de hash), solo repara una dependencia rota para instalaciones nuevas.

**Extra (no pedido, mismo hallazgo):** se agregó validación de longitud máxima (72 bytes, el límite real de bcrypt) en `RegisterRequest.password` y `CambioPasswordRequest.password_nueva` (`app/auth/schemas.py`) — antes un password muy largo hubiera tirado un `ValueError` sin manejar (500) en vez de un 422 prolijo.

**Verificación:**
- `docker compose build api` — build limpio.
- Login real contra el hash existente del usuario admin (generado por la versión vieja con passlib) — sigue funcionando sin cambios.
- 253 tests de la imagen `api` pasan.
- Probado a mano: registro con password de 100 bytes → 422 con el mensaje nuevo; registro + login con password normal → 201 / 200 (hash generado 100% con el código nuevo, sin passlib).
#### Fix: `osgeo/gdal` 3.9.0 → 3.13.3 + `rasterio` 1.3.11 → 1.5.1 (PRs Dependabot #21 + #64)
**Fecha:** 2026-10-08
**Rama:** `fix/gdal-rasterio-upgrade`

Segundo fix del triage de Dependabot (ver Problemas abiertos). Ya estaba identificado desde el Sprint 14 que bumpear solo la imagen base de GDAL rompía el build del worker (`rasterio==1.3.11` no compila contra el Python más nuevo de la imagen — `ModuleNotFoundError: No module named 'pkg_resources'`), y que la solución era bumpear `rasterio` en el mismo movimiento.

**Hallazgo nuevo (no estaba previsto):** `ghcr.io/osgeo/gdal:ubuntu-small-3.13.3` trae **Python 3.14.4** (la imagen vieja traía 3.12.3) — un salto de versión de Python, no solo de GDAL. Esto generó un segundo breakage, distinto del de `rasterio`: `pydantic==2.10.4` (pin compartido con `requirements.api.txt`) no tiene wheel precompilada para `cp314` — `pydantic-core` 2.27.2 (la versión que esa pydantic fija) cae a compilarse desde fuente vía `maturin`/`cargo`, y falla porque `PyO3 0.22.6` (el que trae ese sdist) no soporta Python 3.14 (`error: the configured Python interpreter version (3.14) is newer than PyO3's maximum supported version`).

**Fix:**
- `docker/Dockerfile.worker`: `FROM ghcr.io/osgeo/gdal:ubuntu-small-3.9.0` → `ubuntu-small-3.13.3`.
- `docker/requirements.worker.txt`: `rasterio` 1.3.11 → 1.5.1 (ya venía probado verde en su propia PR de Dependabot, sin romper nada). `pydantic` 2.10.4 → 2.13.5 **solo en `requirements.worker.txt`** (no se tocó el pin de `requirements.api.txt`, que sigue en Python 3.12 y no lo necesita) — 2.13.5 resuelve a `pydantic-core==2.46.5`, que sí trae wheel `cp314`.

**Cómo se investigó (sin gastar ciclos de build completos por cada intento):** en vez de iterar con `docker compose build` (lento, ~1-2 min por vuelta), se armó un contenedor de prueba descartable a partir de la imagen base nueva (`docker create`/`docker cp`/`docker exec`) para replicar exactamente los mismos pasos de `apt-get install` + `pip install` del Dockerfile y iterar rápido sobre los requirements hasta encontrar la combinación que resuelve. Confirmado también que `pip install --dry-run` no sirve para detectar este tipo de falla (reporta "Would install" sin intentar compilar el sdist, da un falso verde) — hay que correr el install real.

**Verificación (stack completo reconstruido, no solo el diff):**
- `docker compose build worker` — build limpio.
- `docker compose up -d` — Celery conecta a Redis sin errores (solo warnings de deprecación esperados de Celery 5.4 sobre `broker_connection_retry`, no relacionados a este cambio).
- 151 tests de GIS de la imagen `worker` pasan.
- `tests/test_celery_integracion.py` (los 3, incluido el ciclo E2E con un GeoTIFF real) pasa.

**Decisión tomada:** no se homologó `pydantic` entre `api` y `worker` a la misma versión — son requirements files independientes por diseño (cada imagen instala solo lo que necesita), y forzar el mismo pin en ambos para "prolijidad" hubiera significado re-probar toda la suite de `api` sin necesidad real (el pin de `api` no está roto, sigue en Python 3.12).
#### Fix: `sqlalchemy` 2.0.54 → 2.1.1 (PR Dependabot #63) + pin de `greenlet`
**Fecha:** 2026-10-08
**Rama:** `fix/sqlalchemy-greenlet-dependency`

Triage de las ~20 PRs de Dependabot acumuladas (ver Problemas abiertos). La mayoría tenían CI verde salvo el ruido conocido de pip-audit/npm-audit ya aceptado; un grupo chico rompía de verdad. Esta fue la más simple de las rotas: `ModuleNotFoundError: No module named 'greenlet'` en la PR de Dependabot, porque SQLAlchemy 2.1 dejó de traer `greenlet` como transitiva implícita (antes se auto-instalaba sin que `requirements.*.txt` la pidiera).

**Fix:** se agregó `greenlet==3.5.6` explícito en `docker/requirements.api.txt` y `docker/requirements.worker.txt`, junto al bump de `sqlalchemy` a 2.1.1. La versión de greenlet se tomó de la que ya estaba resuelta transitivamente en el entorno de dev (`pip show greenlet` dentro del contenedor `api` antes del cambio), para no introducir una versión sin probar.

**Verificación (stack completo reconstruido desde cero, no solo el diff):**
- `docker compose build api worker` — ambas imágenes buildean limpias.
- `alembic upgrade head` + `GET /api/v1/health` + `GET /api/v1/health/db` — OK.
- 253 tests de la imagen `api` pasan (sin cambios respecto a antes del bump).
- 151 tests de GIS de la imagen `worker` pasan.
- `tests/test_celery_integracion.py` (los 3, incluido el ciclo E2E) pasa.
- Nuevo warning no bloqueante a futuro: SQLAlchemy 2.1 deprecó pasar una expresión a `.distinct()` para generar `DISTINCT ON` (`app/lotes/service.py`, usado por `listar_lotes` de HU-R4-03) — sugiere migrar a `postgresql.distinct_on()`. Queda en Problemas abiertos, no es bloqueante (sigue funcionando, solo deprecation warning).

**Decisión tomada:** no se tocó `app/lotes/service.py` en esta rama — el fix se acotó al breakage real (falta de `greenlet`), la migración de `.distinct()` es un cambio de código aparte sin apuro.

#### Fix: `geoalchemy2` 0.15.2 → 0.20.0 (regresión de `sqlalchemy` 2.1 ya mergeada a `main`)
**Fecha:** 2026-10-08
**Rama:** `fix/geoalchemy2-sqlalchemy21-compat`

**Hallazgo (propio, no reportado por nadie todavía):** al validar el fix de `sqlalchemy`/`greenlet` (PR #76, ya mergeada) se corrió `alembic upgrade head` contra una base que YA tenía todas las migraciones aplicadas — un no-op que no probó nada. Nadie lo notó hasta que la PR #79 (vite) mostró "API — migraciones y health" en rojo sin relación aparente con su diff. Se investigó corriendo la migración completa desde una base PostGIS vacía de verdad, y se reprodujo: **cualquier `alembic upgrade head` desde cero falla en la primera tabla que crea** (`alembic_version`, ni siquiera una tabla con geometría) con `TypeError: ColumnCollection is an abstract base class and cannot be instantiated directly`.

**Causa raíz:** `geoalchemy2==0.15.2` registra un listener `before_create` global sobre `Table` (no solo sobre tablas con columnas de geometría) que instancia `sqlalchemy.sql.expression.ColumnCollection()` directo (`admin/dialects/common.py::_update_table_for_dispatch`). SQLAlchemy 2.1 volvió esa clase abstracta — hay que usar `WriteableColumnCollection`/`DedupeColumnCollection`. Como el listener es global, revienta en la creación de CUALQUIER tabla, no solo las de este proyecto.

**Impacto real:** desde que se mergeó la PR #76 (sqlalchemy 2.1.1), `main` quedó roto para cualquiera que clone el repo y corra `alembic upgrade head` desde cero — no se nota en bases ya migradas (como la de desarrollo de cualquiera que ya venía trabajando), pero sí en CI (que siempre arranca de una base vacía) y en cualquier onboarding nuevo.

**Fix:** `geoalchemy2` 0.15.2 → 0.20.0 en `requirements.api.txt` y `requirements.worker.txt` — ya usa la API nueva de SQLAlchemy.

**Verificación (la que faltó la primera vez):**
- Base PostGIS vacía real (contenedor Postgres aparte, sin ninguna migración aplicada) + `alembic upgrade head` — las 22 migraciones corren limpias de punta a punta.
- 253 tests de `api` + 151 de `worker` + los 3 de `test_celery_integracion.py` (E2E) — todos pasan.

**Nota para el propio proceso:** a partir de ahora, cualquier bump de `sqlalchemy` (o de algo que dispare DDL, como `geoalchemy2`) se valida corriendo las migraciones contra una base realmente vacía, no reutilizando la base de desarrollo persistente — ese fue el gap que dejó pasar esto.

#### Fix: `python-jose` 3.3.0 → 3.5.0 + `pillow` 10.4.0 → 12.3.0 (hallazgos SCA)
**Fecha:** 2026-10-08
**Rama:** `fix/security-python-jose-pillow`

Últimos 2 de los 3 hallazgos de `pip-audit` que seguían en rojo en cada PR (el tercero, `ecdsa`, ya estaba evaluado y aceptado desde el Sprint 14 — sin fix disponible).

**`pillow` 10.4.0 → 12.3.0:** quedaba pendiente desde el Sprint 14 ("falta probarlo antes de bumpear"). Se probó: `app/reportes/mapa.py` (único uso, dibuja el mapa del PDF) sigue generando imágenes correctamente con la API de `Image`/`ImageDraw`/`ImageFont` sin cambios de código. **Resuelve las ~25 CVEs que tenía la 10.4.0** (`pip-audit` ya no lista ninguna).

**`python-jose` 3.3.0 → 3.5.0:** resuelve 3 CVEs (`PYSEC-2024-232`, `-233`, `PYSEC-2025-185`). Apareció uno nuevo al re-auditar: `CVE-2026-85394` (confusión de algoritmo — acepta claves asimétricas DER como secreto HMAC cuando no se restringen los algoritmos explícitamente en `jwt.decode`), **sin fix disponible todavía incluso en la versión más nueva**. No aplica a este código: los únicos 2 lugares que decodifican JWT (`app/auth/dependencies.py`, `app/auth/router.py`) ya pasan `algorithms=[settings.jwt_algorithm]` explícito (`HS256` fijo) — exactamente la mitigación que describe el aviso del CVE. Riesgo aceptado, mismo criterio que `ecdsa`.

**Verificación:**
- `docker compose build api` — build limpio.
- 253 tests de la imagen `api` pasan.
- Login real (JWT con `python-jose` 3.5.0) — `POST /auth/login` + `GET /auth/me` → 200.
- Generación de imagen con Pillow 12.3.0 probada directo en el contenedor (`Image`/`ImageDraw`/`ImageFont`) — OK.
- `pip-audit` local contra el `requirements.api.txt` nuevo: de 3 paquetes con hallazgos (`python-jose`, `pillow`, `ecdsa`) queda solo `ecdsa` (sin fix) y el CVE nuevo de `python-jose` (sin fix, no explotable acá) — `pillow` sale limpio.

#### HU-R4-07 — Resumen por vuelo en el historial
**Fecha:** 2026-10-08
**Rama:** `feat/hu-r4-07-resumen-vuelo-historial`

En el historial de vuelos del lote (`VuelosCalendario.jsx`, HU-R4-04), cada vuelo completado ahora tiene un botón "Resumen" que expande un panel inline (nuevo `ResumenVuelo.jsx` + `useResumenVuelo.js`) con tres criterios de aceptación de la HU:

- **Índice con valor medio/mínimo/máximo en gráfico**: barra de rango NDVI (mín—prom—máx) más una nota de qué índice correspondería según el estadio fenológico del vuelo (estadios tempranos V1-V3 → SAVI, NDVI>0.75 → GNDVI, resto → NDVI). Es solo una recomendación informativa — el motor de diagnóstico sigue calculando únicamente sobre NDVI.
- **Porcentaje de superficie por nivel de severidad**: barra apilada + leyenda (crítica/moderada/leve/normal/vigorosa), agregando el `area_ha` de cada zona del diagnóstico por su `severidad`.
- **Enlaces a prescripción, orden de trabajo e informe PDF**: 3 botones de descarga, cada uno deshabilitado cuando no corresponde (ej. "Orden de trabajo" sin unidades de manejo).

**Decisiones tomadas:**
- No se agregó ningún endpoint backend nuevo — todo el resumen se arma reutilizando `GET /lotes/{id}/vuelos/{id}/diagnostico` (ya trae `ndvi_promedio_lote`, `ndvi_promedio` y `severidad` por zona, y `unidades_manejo`) más los endpoints de export ya existentes (`reporte/pdf`, `orden-trabajo/pdf`, `zonas/export?formato=shapefile`).
- "Prescripción" se mapeó al export Shapefile (RFSA-02) y "orden de trabajo" al PDF de orden de trabajo (RFSA-04) — son dos artefactos distintos según el ERS, no sinónimos, pese a que el código interno comenta la orden de trabajo como "orden de trabajo / prescripción" (`app/ordenes_trabajo/service.py`).
- El diagnóstico se carga on-demand solo al expandir el resumen de ESE vuelo puntual (no para todos los vuelos del historial a la vez) — `generar_diagnostico()` no es gratis.
- Sin librería de gráficos nueva — el rango NDVI y la barra de severidad son CSS plano (consistente con la convención del proyecto de no sumar dependencias de UI todavía).

**Verificación:** stack completo levantado con Docker Compose (login real con `admin@agronexo.com`), lote "Release 2.2" con 2 vuelos completados — resumen expandido mostró NDVI mín/prom/máx reales, severidad "Normal · 100%" (zona uniforme, esperado), y descarga de Informe PDF + Prescripción SHP devolvieron `200`. "Orden de trabajo" quedó correctamente deshabilitado (sin unidades de manejo en ese vuelo). `npm test` (2 archivos, 9 tests) y `vite build` corridos dentro del contenedor `frontend` (Node correcto) sin errores.

**Error encontrado — build de `api` falla con `SSLCertVerificationError` contra pypi.org**
```
ERROR: Could not find a version that satisfies the requirement fastapi==0.141.1 (from versions: none)
```
`docker/certs/avast-root.crt` (usado por `Dockerfile.api` para confiar en el TLS-scanning de Avast) resultó ser el certificado raíz de **otra** instalación de Avast — Avast genera una raíz self-signed distinta por cada instalación aunque el Subject/Issuer sea el mismo texto literal (verificado con `openssl verify`: el cert del repo no valida la cadena real que presenta `pypi.org` en esta máquina). Se resolvió localmente, sin commitear, exportando la raíz real de Avast de esta máquina desde `Cert:\LocalMachine\Root` (PowerShell) y reemplazando el archivo solo para el build; se revirtió a la versión del repo después. Ver "Problemas abiertos".

**Error encontrado — MinIO no arranca tras el rebuild (`FATAL Unable to initialize backend`)**
```
Error: unable to rename (/data/.minio.sys/tmp -> /data/.minio.sys/tmp-old/...) file access denied
```
El volumen `minio_data` local fue creado por la imagen vieja `minio/minio` (corría como root); `cgr.dev/chainguard/minio` corre como usuario no-root y no puede escribir ahí. Se resolvió recreando el volumen (confirmado con el usuario primero, porque implica perder los archivos de prueba subidos a MinIO en este entorno — Postgres no se tocó). Ver "Problemas abiertos".

---

#### HU-R4-05 · Investigación de costos de fitosanitarios
**Fecha:** 2026-10-13
**Rama:** `main`

Relevamiento de precios de referencia para los 21 productos del catálogo (`migrations/versions/0015`), orientado a desbloquear HU-R4-11 (cálculo de ahorro económico por aplicación variable).

**Entregables:**
- `docs/precios_fitosanitarios_referencia.md` — tabla completa de 21 productos con principio activo, presentación, precio en USD, fuente y nivel de confianza. Incluye metodología, URLs de fuentes y decisión de diseño del modelo de datos.
- `docs/catalogo_productos_fitosanitarios.xlsx` — nueva hoja "Precios de referencia" con los mismos datos en formato tabular para revisión por el equipo.

**Decisiones tomadas:**
- **Precio cargado por el usuario + valor de referencia como respaldo:** los precios de agroquímicos en Argentina cambian mensualmente (inflación + tipo de cambio). Los valores de esta tabla son punto de partida para HU-R4-11; el sistema usará el precio ingresado por el usuario (con fecha) cuando exista y tenga menos de 90 días.
- **Precio expresado en USD/L o USD/kg** (no por envase) para normalizar comparación entre productos con distintos formatos de presentación. El cálculo de costo por ha será: `precio_ref × dosis_l_ha × hectáreas`.
- **Fuentes principales:** CASAFE Lista 2026-S1 (herbicidas e insecticidas de alto volumen), CIAFA 2026-T3 (fertilizantes), INTA EEA Sáenz Peña / Reconquista / NEA (productos con menor cobertura en CASAFE).
- **3 productos marcados 🔴** (boro foliar, thiamethoxam EPP, clorpirifos EPP) sin fuente específica confirmada — precio estimado por principio activo equivalente; requieren validación antes de usar en producción.

**Modelo de datos pendiente (migración 0021):**
Tabla `precios_productos` con campos `producto_id`, `precio_usd`, `unidad`, `fuente`, `fecha`, `tipo` (`"referencia"` | `"usuario"`). Pendiente implementar como parte de HU-R4-11.

---

#### HU-R4-12 · Preferencias de uso
**Fecha:** 2026-10-14
**Rama:** `feat/hu-r4-12-preferencias-uso` (worktree aparte — la rama `feat/hu-r4-09-comparar-vuelos` tenía cambios sin commitear)

Tabla de configuración por usuario para no elegir índice, unidad de área y producto fitosanitario en cada análisis. Migración `0024`: tres columnas nullable en `usuarios` (`indice_preferido` reutiliza el enum Postgres `indiceenum` ya creado en `0011`; `unidad_area_preferida` es un enum nuevo `unidadareaenum` con `ha`/`acre`; `producto_habitual_id` es FK nullable `ON DELETE SET NULL` a `productos_fitosanitarios.id`, mismo patrón que `precios_productos.producto_id` de `0023`). Expuestas en `UsuarioResponse`/`PerfilUpdateRequest` y guardadas desde una tercera card "Preferencias de uso" en `PerfilUsuario.jsx`, reusando el mismo `PUT /auth/me` del perfil (HU-R4-10) en vez de un endpoint nuevo.

**Decisiones tomadas:**
- **Sin tabla ni endpoint separado:** se siguió el patrón que ya dejó HU-R4-10 (columnas directas en `usuarios`, `PUT /auth/me` genérico con `exclude_unset`) en vez de una tabla `preferencias_usuario` 1-a-1 — son 3 valores escalares sin ciclo de vida propio, no justifica el join extra.
- **"Unidad" se interpretó como unidad de área (ha/acre):** el proyecto no tiene hoy ningún otro concepto de "unidad" configurable por el usuario (las unidades de dosis — L, kg — son una propiedad fija de cada producto en `productos_fitosanitarios.unidad`, no algo que el usuario elija). Se creó el enum `unidadareaenum` desde cero; no había ningún catálogo existente para reusar.
- **Precarga real solo donde hay un punto de conexión:** el índice preferido precarga en `ModalCargaGeoTIFF.jsx` (qué pastilla de índice queda enfocada al abrir el paso de análisis — no cambia qué índices se calculan, todos los que el sensor permite siguen calculándose) y en `Dashboard.jsx` (cambia automáticamente a la pastilla del índice preferido una vez que se sabe qué índices están disponibles para ese vuelo puntual, solo si ya está `completado`). "Unidad de área" y "producto habitual" se guardan y se pueden editar desde el perfil, pero no tienen todavía un formulario de análisis/prescripción que los consuma — no existe una pantalla de prescripción en el proyecto hoy (los productos sugeridos por diagnóstico son automáticos, server-side). Quedan listos para conectarse cuando esa UI exista.
- **`producto_habitual_id` sin relationship en el modelo:** el frontend ya resuelve el nombre contra el catálogo que trae de `GET /productos-fitosanitarios`, así que no hace falta que el backend lo resuelva ni lo exponga anidado.
- **No hay solapamiento con HU-R4-11 (Ahorro comparativo, sin arrancar todavía):** se revisó su alcance antes de dar por cerrada esta tarea — es un reporte de ahorro (dosis variable vs. uniforme × precio) sobre datos que ya existen (orden de trabajo + `precios_productos`), no describe ningún selector de producto o unidad. Cuando se implemente, sería el primer lugar natural donde "producto habitual" podría usarse (ej. resaltar por default el ahorro de ese producto) — queda anotado para retomar en ese momento, no es parte del alcance de HU-R4-11 hoy.

**Verificación (stack completo levantado desde cero, no solo el diff):**
- Se bajó el stack del checkout principal (`docker compose down`, sin tocar volúmenes) y se levantó el stack completo desde este worktree — base Postgres nueva, sin reusar la de desarrollo.
- `alembic upgrade head` — las 24 migraciones corren limpias de punta a punta, incluida `0024`.
- `POST /auth/login` + `GET /auth/me` con el usuario seed — los 3 campos nuevos viajan en `null`.
- `PUT /auth/me` con `indice_preferido="ndre"`, `unidad_area_preferida="acre"` y `producto_habitual_id` real del catálogo (`GET /productos-fitosanitarios`) — persiste correcto. Un valor de enum inválido devuelve `422`. Volver a `null` también funciona.
- Navegador real: login, `/perfil` muestra la card "Preferencias de uso" con los 3 selects (el de producto carga los 21 productos del catálogo); guardar + recargar la página mantiene la selección (confirmado en el árbol de accesibilidad, los 3 `option` quedan `selected`).
- **No se verificó visualmente** la precarga del índice preferido como pastilla enfocada en `ModalCargaGeoTIFF.jsx` (requiere un lote + cultivo + GeoTIFF real, base nueva sin datos) — queda validado solo por lectura de código, que usa el mismo `user.indice_preferido` ya confirmado persistente.
#### HU-R4-09 · Comparar dos vuelos del mismo lote (estadísticas)
**Fecha:** 2026-10-14
**Rama:** `feat/hu-r4-09-comparar-vuelos` (sin commitear todavía)

La vista lado a lado para comparar dos vuelos (`ResultadosVuelo.jsx`, "Seleccionar para comparar" en `VuelosCalendario.jsx`) ya existía de una tarea anterior — faltaban los dos criterios de aceptación centrales: la diferencia de valor medio del índice y la diferencia de superficie por severidad entre ambos vuelos. El mapa de diferencia (vuelo B − vuelo A), marcado como opcional en la tarjeta, queda fuera de esta pasada — ver "Problemas abiertos".

Se agregó `ResumenDiferenciaVuelos.jsx`, que se muestra arriba de los dos paneles cuando ambos vuelos terminaron de cargar sus zonas: diferencia del índice promedio del lote (ponderado por área) y diferencia de área por clase de severidad (Alto/Medio/Bajo/Muy bajo), con color según el signo.

**Decisiones tomadas:**
- **Cálculo 100% en el frontend, sin endpoint nuevo:** cada panel (`PanelResultadoVuelo`) ya pedía el GeoJSON de zonas de su propio vuelo vía `useResultadoVuelo`; alcanzaba con que cada uno reportara sus zonas al padre (`onZonasCargadas`) para poder diferenciarlas ahí, sin duplicar esa carga en un endpoint de backend.
- **Lógica de agregación por clase extraída a `utils/statsZonas.js`**, compartida entre `TablaZonas.jsx` (ya existente) y `ResumenDiferenciaVuelos.jsx` — antes vivía duplicada inline en `TablaZonas`.
- **Promedio general ponderado por área**, no el promedio simple de los 4 promedios por clase — una clase con mucha superficie no debe pesar lo mismo que una con un solo polígono chico.
- **Delta siempre "B − A"** donde A es el vuelo que ya estaba abierto (el de la URL) y B el elegido para comparar — sin asumir cuál de los dos es más reciente en el tiempo.

#### Fix: sidebar no marcaba "Diagnósticos" como activo en la vista de resultados
**Fecha:** 2026-10-14
**Rama:** `feat/hu-r4-09-comparar-vuelos` (sin commitear todavía)

`SidebarNav.jsx` calculaba el ítem activo solo con `pathname.startsWith('/lotes')`, pero las tres rutas de lotes (`/lotes`, `/lotes/:id`, `/lotes/:id/vuelos/:id`) empiezan todas así — la última es la que en realidad muestra la pestaña Diagnóstico (`ResultadosVuelo.jsx`), así que el sidebar siempre marcaba "Lotes", nunca "Diagnósticos".

Se agregó una excepción: si el pathname matchea `/lotes/{id}/vuelos/`, el activo es `diagnostico` en vez de `lotes`.

---

#### HU-R4-11 · Ahorro comparativo entre campañas
**Fecha:** 2026-10-14
**Rama:** `feat/hu-r4-11-ahorro-comparativo` (sin commitear todavía)

Cuánto producto y dinero se ahorra con aplicación variable (solo tratar las zonas con problema detectado) frente a uniforme (tratar todo el lote a la misma dosis de referencia), por prescripción y acumulado entre campañas del mismo lote.

**Backend** — módulo nuevo `app/ahorro/` (paralelo a `app/ordenes_trabajo/`, mismo criterio de separación de `app/diagnostico/`):
- `calculo.py` (puro): `calcular_ahorro_vuelo()` toma la salida de `generar_orden_trabajo()` (HU-R4-04/RFSA-04, ya calculaba la cantidad "variable") y la compara contra `dosis_referencia × Lote.area_ha` ("uniforme"); `acumular_ahorro()` suma varios vuelos de la misma campaña por producto.
- `service.py` (I/O): reusa el mismo pipeline que ya arma el PDF de orden de trabajo (`generar_diagnostico` → `generar_orden_trabajo`) en vez de duplicarlo, y agrega la resolución de precio por producto.
- `app/diagnostico/precios.py` + modelo `PrecioProducto` (`app/diagnostico/models.py`): primer modelo ORM sobre la tabla `precios_productos` que HU-R4-05 (migración 0023) había dejado creada pero sin consumir. `resolver_precio()` prioriza el precio "usuario" (<90 días), si no cae al "referencia" sembrado.
- Endpoints nuevos: `POST/GET /productos-fitosanitarios/{id}/precios` (cargar/listar precio), `GET /lotes/{id}/vuelos/{id}/ahorro` (una prescripción puntual), `GET /lotes/{id}/ahorro-comparativo?cultivo_a=&cultivo_b=` (acumulado de una campaña, o comparado contra otra).

**Frontend:** página nueva `/lotes/:loteId/ahorro` (`AhorroComparativo.jsx`) — selector de 1 o 2 campañas (`lote.cultivos`, ya venía embebido en `GET /lotes/{id}`, sin endpoint nuevo), tabla de ahorro por producto, y `ModalCargarPrecio.jsx` inline cuando falta precio de algún producto. Botón de entrada agregado en `DetalleLote.jsx`.

**Decisiones tomadas:**
- **"Variable vs. uniforme" es sobre el ÁREA tratada, no sobre la dosis** — ninguno de los dos escenarios varía la dosis por zona (`generar_orden_trabajo` ya aplica la misma `dosis_referencia` a toda unidad de manejo); lo que cambia es que "variable" solo trata las zonas con problema detectado y "uniforme" trataría el lote entero. Interpretación tomada de la propia nota de la tarjeta de Trello ("las dosis por zona ya se calculan... así que variable vs. uniforme es aritmética").
- **Sin tabla nueva para el ahorro**: no se persiste nada — se recalcula on-demand igual que el diagnóstico y la orden de trabajo (que ya están cacheados en `diagnosticos`). Evita un historial a sincronizar si se recalcula un diagnóstico.
- **"Campaña" = `Cultivo`** (no hay tabla `campañas` en el proyecto, confirmado antes de empezar) — un cultivo es exactamente un ciclo de siembra/cosecha con sus vuelos asociados vía `Vuelo.cultivo_id`.
- **Un vuelo sin precio no rompe el acumulado de la campaña**, se suma igual lo que sí se pudo calcular y se marca `todos_los_precios_cargados: false` — descartar el acumulado entero por un precio faltante hubiera sido peor que mostrar un total parcial avisado.
- **"Cargar precio" vive inline en la pantalla de ahorro, no en una pantalla de catálogo aparte** — no existe ningún admin de productos fitosanitarios en el frontend hoy; agregar uno era alcance fuera de esta tarjeta.
- **Sin endpoint JSON de orden de trabajo expuesto por separado** — los schemas `OrdenTrabajoItem`/`OrdenTrabajoResponse` ya existían "huérfanos" (definidos, sin usar) desde HU-R4-04; se siguió sin exponerlos porque el ahorro no los necesita tal cual (arma su propia estructura `AhorroProducto`), y agregar el endpoint sin un consumidor real era scope creep.

**Error encontrado — acumular_ahorro descartaba ahorro real por un precio faltante en OTRO vuelo**
El test unitario `test_acumular_ahorro_vuelo_sin_precio_marca_campana_parcial` (`tests/test_ahorro_calculo.py`) falló: con 2 vuelos de la misma campaña y el mismo producto, si el segundo vuelo no tenía precio cargado, el acumulado total daba `0.0` en vez de contar el ahorro en pesos del primer vuelo (que sí tenía precio). La causa: `acumular_ahorro()` solo sumaba `entry["ahorro_pesos"]` al total general cuando `entry["sin_precio"]` era `False` para TODO el producto acumulado, en vez de sumar siempre lo parcial que sí se pudo calcular. Se corrigió para sumar incondicionalmente (la bandera `sin_precio` solo avisa que es parcial, no excluye el monto ya calculado).

**Verificación (contra datos reales, no solo mocks):**
- 21 tests nuevos (`tests/test_ahorro_calculo.py` puro + `tests/test_ahorro_api.py` HTTP, mockeando `generar_diagnostico`/`cargar_catalogo_dosis` igual que `tests/test_orden_trabajo_pdf_api.py`, pero dejando correr real la resolución de precio contra el precio de referencia sembrado por la migración 0023) — los 21 pasan, y junto con la suite completa (`pytest tests/` sin los módulos que necesitan GIS) quedan **275 tests pasando, ninguno roto**.
- `alembic upgrade head` desde la base de desarrollo real (sin tabla/migración nueva, `PrecioProducto` solo mapea lo que ya existía).
- Navegador real contra datos de desarrollo reales: `/lotes/{id}/ahorro` en "campo abuelo" (Maíz, 2 vuelos) y "Lote Cele" (Soja, 1 vuelo) — ambos con diagnóstico ya calculado pero sin zonas con problema, así que el camino "sin unidades de manejo → ahorro $0" quedó confirmado en vivo; el selector de campañas funciona bien incluso con una sola campaña disponible (no ofrece "comparar").
- **Verificación visual con filas reales (números de ahorro > 0):** como ningún lote de desarrollo tenía todavía una zona de problema detectada, se armó un lote temporal (`DEMO ahorro (borrar)`, 439 ha) con un vuelo + diagnóstico insertados directo en BD (una unidad de manejo de 30 ha, Glifosato) y `dosis_referencia`/`unidad` seteados momentáneamente en ese producto — confirmó en el navegador real la tabla completa: Variable 90,00 L / Uniforme 1.318,27 L / Ahorro 1.228,27 L (93%) / US$ 5.158,72, resolviendo correctamente el precio "usuario" por sobre el de "referencia". Se revirtió todo después (lote, cultivo, vuelo, diagnóstico y el `dosis_referencia` del producto) — no quedó nada de la demo en la base de desarrollo.
- **Hallazgo de la demo — ningún producto del catálogo tiene `dosis_referencia` cargada en datos reales:** por eso en los lotes reales de desarrollo la columna "Uniforme"/"Ahorro" siempre da `—`, incluso si hubiera una zona de problema real. Documentado como problema abierto (ver "Problemas abiertos" arriba) — no es un bug de esta tarjeta, es un hueco de datos del catálogo que también afecta al PDF de Orden de Trabajo desde antes.

---

#### Fix: layout de la comparación de vuelos — mapas achicados y trazabilidad oculta
**Fecha:** 2026-10-15
**Rama:** `Comparaciones-entre-lotes` (sin commitear todavía)

Al agregar el bloque de diferencia (HU-R4-09), el layout de `.resultados-shell`/`.resultados-main` seguía con `min-height: 0` encadenado por toda la jerarquía flex para que todo entrara en una pantalla de altura fija (`100vh`, `overflow: hidden`, pensado para el caso de un solo vuelo). Con dos paneles + tabla de diferencia + trazabilidad, el resultado era que el mapa se achicaba para que todo cupiera, y la trazabilidad (que no se achica, tiene contenido fijo) quedaba recortada fuera de la pantalla sin aviso — no es que faltara en el DOM, estaba ahí pero invisible.

**Fix:** `.resultados-shell` pasa a `overflow-y: auto` (hace scroll interno en vez de comprimir contenido), `.resultados-main` fija `min-height: 560px` (el mapa nunca se achica por debajo de eso) y `.resultados-comparacion`/`.resultados-panel` dejan de forzar `min-height: 0`/`flex:1` para el achicado. También se reordenó el JSX: la trazabilidad ahora va debajo del mapa+sidebar de cada panel (antes iba arriba), y la tabla "Diferencia entre vuelos" va debajo de los dos paneles en vez de arriba — deja el mapa como lo primero que se ve.

**Error encontrado — el primer intento de reordenar no se veía en el navegador**
Después de mover la trazabilidad en el JSX, una captura del usuario seguía mostrando mapas chicos sin trazabilidad. Se verificó con un navegador real (Playwright headless, sin `chromium-cli` disponible en este entorno — se instaló Playwright + Chromium standalone para la sesión) contra el stack de Docker ya corriendo: con datos reales de un lote con 2 vuelos, el fix sí funcionaba (mapas a `560px`, trazabilidad visible, tabla con scroll). La demora era de aplicación del cambio en el navegador del usuario (HMR de Vite), no un bug del código.

---

#### Cambio por zona — mini-mapas + Empeoró/No empeoró en la comparación de vuelos
**Fecha:** 2026-10-15
**Rama:** `Comparaciones-entre-lotes` (sin commitear todavía)

A pedido del usuario (mostró una referencia visual de otra herramienta), se agregó una grilla de tarjetas por zona dentro de "Diferencia entre vuelos": mini-mapa SVG del lote con la zona resaltada, badge "▼ Empeoró"/"No empeoró"/"Sin comparar", y el cambio de NDVI en texto plano (sin la transición de clase a clase que mostraba la referencia). A la derecha de cada tarjeta queda un espacio reservado para "razones" — vacío por ahora, sin funcionalidad, a pedido explícito del usuario (ver decisión abajo).

**Decisiones tomadas:**
- **Emparejamiento de zonas entre vuelos por centroide, sin turf:** cada vuelo vectoriza sus zonas de forma independiente (no hay id compartido entre análisis), así que para saber "esta zona del vuelo A es la misma zona en el vuelo B" se calcula el centroide de la zona en A y se verifica en qué polígono de B cae (ray casting / even-odd, `frontend/src/utils/cambioZonas.js`) — mismo criterio que ya usa `utils/geometria.js` (no sumar una dependencia como turf para esto).
- **Mini-mapas con SVG plano, no Leaflet:** se evaluó reusar `MiniMapaLote.jsx` (Leaflet + tiles), pero se descartó — levantar un `MapContainer` por zona (pueden ser varias decenas) es pesado y trae tiles de fondo que no aportan nada a una silueta de comparación. Se proyectan las coordenadas lon/lat a un `viewBox` con una función de proyección lineal propia.
- **Razones: solo el espacio reservado, sin guardar nada todavía** — se le preguntó explícitamente al usuario entre persistir en BD, un campo editable sin guardar, o solo dejar el hueco visual; eligió la tercera (menor alcance), a definir más adelante.

**Tests nuevos:** `frontend/src/utils/cambioZonas.test.js` (8 casos: punto-en-polígono, centroide, bbox, emparejamiento con/sin match, orden por área, proyección). Suite completa del frontend: 17 → corren bien junto con los 2 archivos de test ya existentes.

---

#### Tendencia del índice — NDVI esperado por estadio vs. real, en la comparación de vuelos
**Fecha:** 2026-10-15
**Rama:** `Comparaciones-entre-lotes` (sin commitear todavía)

A pedido del usuario (otra referencia visual), se agregó un gráfico que compara el NDVI real del lote entre los dos vuelos comparados contra una curva de "NDVI esperado" por estadio fenológico del cultivo — banda de rango normal, línea esperada punteada, y el tramo real (sólido, rojo si el desvío es negativo, verde si no), con 3 tarjetas de resumen (cambio esperado / cambio real / desvío). Solo se muestra si ambos vuelos son del mismo cultivo y tienen un estadio fenológico cargado que matchea el catálogo — si falta algo, el componente no renderiza nada (no hay información confiable que mostrar).

**Backend — migración `0025_crear_tabla_ndvi_esperado`:** tabla `ndvi_esperado_estadio` (cultivo + estadio normalizado + orden + ndvi esperado/min/max), sembrada con una **curva genérica placeholder** (sube en vegetativo con una función seno, mesetea y declina hacia madurez) para los 4 cultivos — **no es una curva agronómica validada**, el usuario fue explícito en que esto se va a ajustar más adelante con estadística real de vuelos cargados. Nuevo endpoint `GET /estadios-fenologicos/ndvi-esperado?cultivo=` (`app/diagnostico/router.py`, mismo router que ya expone `/estadios-fenologicos`).

**Decisiones tomadas:**
- **Estadios y su orden duplicados en la migración, no importados de `app/diagnostico/estadios.py`** — mismo criterio que la migración 0015 (productos fitosanitarios): una migración no depende de código de la app, que puede cambiar después y romper la reproducibilidad histórica de un `alembic upgrade head` viejo.
- **Granularidad = picklist completo de `ESTADIOS_POR_CULTIVO`** (no solo el subconjunto que usan las reglas de diagnóstico), para que la curva de fondo sea continua en todo el ciclo, no solo en los estadios que algún día filtran una regla.
- **Sin endpoint de "matching" en el backend:** el frontend normaliza `vuelo.estadio_fenologico` con una función JS espejo de `normalizar_estadio()` (`frontend/src/utils/estadios.js`) y busca el punto de la curva localmente — evita un roundtrip extra, la curva completa de un cultivo son ~20-26 filas.
- **Colores de "Empeoró"/"No empeoró" no probados contra CVD por separado** (se corrió el validador de la skill de dataviz sobre el par rojo/verde ya existente en la app — falla separación para daltonismo deuteranopia) — se mitiga con que nunca aparecen los dos colores a la vez en un mismo gráfico (un render usa uno u otro según el signo del desvío) y con etiquetas de texto siempre presentes, nunca color solo.
- **Se evitó inventar un ID de historia de usuario:** el código no referencia ningún "HU-R4-13" ni similar — no hay un backlog accesible desde este repo que confirme que ese número corresponde a esta funcionalidad; se documentó solo acá, en el seguimiento de release.

**Verificación:** 275 tests de `api` siguen pasando (incluye `test_diagnostico_api.py`, `test_estadios.py`). Probado end-to-end con un navegador real contra datos de desarrollo (lote "Nueva Prueba", maíz, vuelos con estadios V18→VT reales) — banda, línea esperada y tramo real se dibujan correctamente, con el signo del desvío calculado bien (+0.10 en el caso probado). Tests nuevos: `frontend/src/utils/estadios.test.js` (4 casos).

**Problema abierto nuevo:**
- **La curva de NDVI esperado por estadio es un placeholder genérico, no agronómicamente validada** (migración 0025) — hay que reemplazarla con valores reales (fuente agronómica tipo INTA/CASAFE, igual que hizo HU-R4-05 con precios) o, como prefirió el usuario, recalcularla estadísticamente una vez que haya suficientes vuelos reales cargados por cultivo/estadio. No bloquea el uso del gráfico (el texto "* Curva de referencia genérica..." ya lo aclara en la UI), pero no hay que tomar sus números como verdad agronómica todavía.

---

#### Mapa del lote — vista "Lado a lado" y "Cortina" en la comparación de vuelos
**Fecha:** 2026-10-15
**Rama:** `Comparaciones-entre-lotes` (sin commitear todavía)

El usuario mostró una referencia visual con 3 pestañas ("Lado a lado", "Cortina", "Mapa de cambio") para ver el mapa del lote durante la comparación. Tras aclarar el alcance con el usuario: se agregó una tarjeta nueva "Mapa del lote" (`MapaComparacionLote.jsx`) con 2 pestañas — "Lado a lado" y "Cortina" — sin tocar la vista de dos paneles completos que ya existía (zonas + diagnóstico de cada vuelo, intacta como primera forma de verlo). "Mapa de cambio" (el raster de diferencia real, vuelo B − vuelo A pixel a pixel) queda fuera de alcance — es la misma tarea grande que ya figuraba como problema abierto de HU-R4-09, no se dio por resuelta acá.

- **"Lado a lado"**: dos mapas Leaflet reales (reusa `MapaZonas.jsx` tal cual, cada uno con su propio fit-bounds y leyenda), cada uno con un pill de fecha ("Actual"/"Base") en la esquina superior derecha.
- **"Cortina"**: un único mapa con las zonas del vuelo base y las del vuelo actual superpuestas en dos capas `GeoJSON`; un slider controla la opacidad de la capa "actual" en vivo via `ref` + `setStyle()` imperativo (no remount), para no perder el pan/zoom mientras se arrastra.

**Decisiones tomadas:**
- **Base/Actual se determina por fecha real de cada vuelo**, no por cuál estaba abierto antes de elegir comparar — mismo criterio que ya usa `TendenciaIndice.jsx`.
- **Sin capa "sin datos"** en estas dos vistas (a diferencia de `MapaZonas` en el panel completo) — simplificación a propósito, ya se puede ver esa capa en la vista de dos paneles de arriba.

**Error encontrado — el pill de fecha se veía pegado al control de zoom de Leaflet**
Primera versión posicionaba el pill con `left: 0.5rem`, mismo lado que el control +/− de Leaflet (que también es top-left por defecto). Se cambió a `right: 0.5rem`. Al revisar con captura de pantalla parecía que el fix no aplicaba (el pill seguía viéndose a la izquierda) — se verificó con `getBoundingClientRect()` real del navegador en vez de confiar en la lectura visual de la captura, y el posicionamiento era correcto; el error estaba en la lectura de la imagen comprimida, no en el código.

**Verificación:** navegador real contra datos de desarrollo (lote "Nueva Prueba", vuelos V18/VT) — las dos pestañas renderizan sin errores de consola, el slider de "Cortina" cambia la mezcla visible de zonas en vivo (confirmado en 3 valores: 5%, 50%, 95%).

**Ajuste a pedido (mismo día) — ubicación y estilo de "Lado a lado":**
- **"Mapa del lote" se movió** de adentro de `ResumenDiferenciaVuelos.jsx` a `ResultadosVuelo.jsx`, renderizado justo debajo de los dos paneles completos (`.resultados-comparacion`) y antes de "Diferencia entre vuelos" — pegado al mapa de comparación original, no enterrado más abajo en la página.
- **"Lado a lado" restyleado para parecerse más a la referencia del usuario:** columnas asimétricas (`3fr 2fr`, el mapa "Actual" más grande que "Base", igual que el mockup) y el pill de fecha vuelve a estar arriba a la izquierda.
- **Se agregó `interactivo` (prop nueva, default `true`) a `MapaZonas.jsx`** — en `false` desactiva zoom/drag/scroll-zoom de Leaflet. Se usa en estos mini-mapas de "Lado a lado" para que el pill de fecha no choque con el control de zoom (que ya no se muestra) — son mapas de referencia rápida, el mapa interactivo completo sigue arriba en el panel principal.
- **"Diferencia entre vuelos" y "Tendencia del índice" pasaron a mostrarse lado a lado** (grid de 2 columnas con separador vertical en `ResumenDiferenciaVuelos.jsx`, con fallback a una sola columna en pantallas angostas vía media query) en vez de uno debajo del otro — a pedido, para aprovechar mejor el ancho de la tarjeta. "Cambio por zona" sigue de ancho completo debajo de ambos.

---

#### Unificar las 3 formas de ver el mapa en un solo selector
**Fecha:** 2026-10-15
**Rama:** `Comparaciones-entre-lotes` (sin commitear todavía)

A pedido explícito ("quiero que todo esto esté unificado"): hasta acá, al comparar dos vuelos se veían **a la vez** los dos paneles completos (mapa + sidebar de Zonas/Diagnóstico) arriba Y la tarjeta "Mapa del lote" (Lado a lado/Cortina) más abajo — información duplicada, ocupando el doble de alto de página.

**Fix:** un solo selector de 3 pestañas ("Vista completa" | "Lado a lado" | "Cortina") en `ResultadosVuelo.jsx`, visible solo cuando hay una comparación activa, muestra una sola vista por vez:
- **"Vista completa"** (default): los dos paneles enteros de siempre — quedan siempre montados (`display: none` en vez de desmontarlos) para no volver a pedir las zonas de cada vuelo al cambiar de pestaña, ya que "Lado a lado"/"Cortina" dependen de esos mismos datos.
- **"Lado a lado" / "Cortina"**: `MapaComparacionLote.jsx` — se le sacó el título "Mapa del lote" y sus pestañas propias (ya no hacen falta, las controla el selector único de arriba) y ahora recibe `tab` como prop controlada por el padre en lugar de manejar su propio estado.

**Decisión tomada:** la pestaña activa se resetea a "Vista completa" cada vez que cambia el vuelo elegido para comparar (mismo efecto que ya reseteaba `zonasComparacion`) — evita quedar en "Cortina" mirando datos de una comparación distinta a la que se acaba de elegir.

**Verificación:** confirmado con el navegador que al cambiar de pestaña solo un bloque queda visible por vez (`getComputedStyle(...).display` de `.resultados-comparacion` en `flex` con "Vista completa" y en `none` con las otras dos; `.mapa-comparacion-lote` con 0 instancias en el DOM en "Vista completa" y 1 en las otras) — sin errores de consola en ningún cambio de pestaña.

---

#### Diagnóstico real por zona dentro de "Cambio por zona"
**Fecha:** 2026-10-15
**Rama:** `Comparaciones-entre-lotes` (sin commitear todavía)

Cada tarjeta de "Cambio por zona" solo tenía un espacio reservado vacío ("Sin razones todavía", a pedido explícito de una conversación anterior). Ahora muestra el diagnóstico real de esa zona puntual — causa + severidad + el texto explicativo que ya genera el motor de reglas (`app/diagnostico/texto.py::generar_texto_zona`), y cada zona puede mostrar una causa distinta (ej. 3 zonas "Sin problema" y una "Moderada / Insecto" con sus productos sugeridos).

**Decisiones tomadas:**
- **El diagnóstico mostrado es el del vuelo A** (el que se estaba viendo antes de comparar, cuyas zonas arman la grilla de tarjetas) — no existe un "diagnóstico de la diferencia", cada zona tiene la causa que el motor detectó en ESE vuelo puntual.
- **Nuevo fetch independiente en `ResultadosVuelo.jsx`** (`obtenerDiagnostico`) en vez de reusar el `diagnostico` que ya carga cada `PanelResultadoVuelo` — ese es perezoso (recién se pide si el usuario abre el tab "Diagnóstico" de ESE panel), y acá hace falta apenas arranca la comparación, sin depender de que el usuario haya clickeado ese tab.
- **Match por posición (índice), no por `zona_id`:** las features "crudas" de NDVI (`featuresA`) no traen `zona_id` — esa propiedad la agrega recién el motor de diagnóstico. Como ambos GeoJSON salen del mismo origen y mismo orden (`app/diagnostico/service.py::_calcular_diagnostico`, `zip(zonas, features_ndvi)`), alcanza con mapear por índice de array.
- **`CAUSA_LABELS`/`SEVERIDAD_LABELS`/`SEVERIDAD_COLORS` duplicados en `CambioPorZona.jsx`** con los mismos valores exactos que ya tienen `TablaDiagnostico.jsx`/`MapaZonas.jsx` — no hay un util compartido todavía para esto en el frontend (se investigó antes de duplicar); se deja como mejora futura si aparece una 4ª necesidad de los mismos labels.
- **Tarjetas más grandes** (pedido explícito): `cambio-zona-grid` pasó de 420px a 540px de ancho mínimo (2 por fila en vez de 3) y la columna de diagnóstico pasó a ser más ancha que la de NDVI/área (`0.8fr`/`1.2fr`) para que el texto explicativo entre sin cortarse.

**Verificación:** navegador real contra datos de desarrollo (lote "Nueva Prueba", vuelos V18→VT) — 3 zonas con "Sin problema" y una con "Moderada / Insecto" (con el texto completo + productos sugeridos) renderizan correctamente, sin errores de consola.
