# Release v4.0.0 — Seguimiento

**Estado:** En desarrollo
**Rama principal:** `main`
**Inicio:** Sprint 15

---

## Sprint 15 — CI/CD: seguridad (SAST, SCA, secretos, imágenes)

**Período:** 2026-09-27

### Tareas completadas

| Tarea | Estado |
|---|---|
| Workflow `security.yml`: SAST (Semgrep + Bandit) | Completada |
| Workflow `security.yml`: SCA (pip-audit + npm audit) | Completada |
| Workflow `security.yml`: escaneo de secretos (Gitleaks) | Completada |
| Workflow `security.yml`: escaneo de imágenes Docker (Trivy) | Completada |
| `dependabot.yml` (pip, npm, docker, github-actions) | Completada |
| Escaneo de secretos sobre todo el historial (una sola vez) | Completada — ver hallazgo abajo |

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

### Problemas abiertos (Sprint 15)

 **Sacar `continue-on-error` de los jobs de `security.yml`** una vez triageado el volumen inicial de hallazgos de Semgrep/Bandit/pip-audit/npm-audit/Trivy (dar 1-2 semanas de rodaje, como se hizo explícito arriba).
- **Evaluar upload de SARIF al tab de Security de GitHub** si la org obtiene licencia de GitHub Advanced Security.
- **Bump de `fastapi`/`starlette`** para resolver los CVEs de `starlette` — necesita correr toda la suite de tests antes de mergear, no es un cambio aislado.
- **Migrar `react-router-dom` de v6 a v7** para resolver su CVE de moderate severity — major version, requiere testear todas las rutas del frontend.
- **Revisar los 25 hallazgos de Semgrep** (todavía no se miraron en detalle, solo el conteo) y decidir si el ruleset actual (`p/security-audit` + `p/owasp-top-ten` + `p/secrets`) es el punto justo o conviene acotarlo.
