# AgroNexo — Release 4 (v4.0.0)

**Historial, comparación y gestión del lote**

Proyecto Final de Ingeniería en Sistemas · UTN FRRe · Equipo 6
Profesores: Acuña, César J · Mendez, Graciela L

---

## Ficha de release

| Campo | Valor |
|---|---|
| Versión | v4.0.0 (sin tag; corte provisional [`7eadf83`][7eadf83], merge del PR #93, fechado en git el 14 de octubre de 2026 a las 10:19) |
| Estado | En curso (documentado al corte provisional [`7eadf83`][7eadf83], 14 de octubre de 2026). Este documento se actualiza al cierre del Sprint 16 |
| Período | Desde el 22 de septiembre de 2026 (cierre de R3, dato del equipo). Primer commit de R4 en git: [`697ca21`][697ca21] (PR #20, 27 de septiembre). Último commit al corte: [`7eadf83`][7eadf83] (14 de octubre). Fin: a confirmar |
| Demo | A confirmar |
| Equipo | Amilcar Aguirre, Matías Machado, Celeste Martín Rodich, Denise Pujalte, Zaira Rosin |
| Metodología | Scrum — 3 sprints planificados (S14 a S16), 13 historias y 58 puntos según el plan del equipo en Trello. Fechas de sprint: a confirmar |
| Entorno | Local con Docker Compose. Al corte existe una base de despliegue de producción (`docker-compose.prod.yml`, Nginx, Certbot, backups), pero no hay servidor desplegado ni HTTPS activo (ver HU-R4-06) |
| Repositorio | universoparalelo/Agronexo (privado) |
| Hito de entrega | El productor consulta la trazabilidad y la evolución de su lote en el tiempo (calendario de vuelos, comparación de vuelos y de capas, ahorro entre campañas) y administra sus lotes, su perfil y sus preferencias, con aislamiento de datos entre usuarios. Derivado de los tres objetivos de R4 de la presentación de R3 |

**Commit de corte provisional.** Como R4 está en curso, el corte es el HEAD de `origin/main` al momento de documentar: [`7eadf83`][7eadf83]. Todo el estado técnico de este documento es el de ese commit, leído con `git show 7eadf83:<ruta>`; "estado al corte" y "estado actual" coinciden. Quedan fuera del corte, por no estar mergeados en `main`:
- la rama `feat/hu-r4-07-resumen-vuelo-historial` (ver HU-R4-07);
- la rama `feat/grafico-evolucion-ndvi-lote`;
- el archivo `docs/catalogo_productos_fitosanitarios.xlsx` (ver HU-R4-05).

**Rango.** De [`ba39b2a`][ba39b2a] (tag `v3.0.0`, exclusive) a [`7eadf83`][7eadf83]: 49 Pull Requests y 1 commit directo a `main` ([`84ccbf6`][84ccbf6], documentación). Son 72 commits sin contar merges, 24 de ellos de Dependabot. Los IDs de historia (HU-R4-NN) figuran en los mensajes de commit de 9 de las 13 historias y en la bitácora `docs/release-v4.0.0.md`.

## Equipo y roles

| Integrante | Rol en la release | Área |
|---|---|---|
| Matías Machado | A confirmar (en R3: Scrum Master / Release Manager) | A confirmar (en R3: Frontend · API) |
| Celeste Martín Rodich | A confirmar (en R3: Desarrollo) | A confirmar (en R3: Backend · GIS · DevOps) |
| Denise Pujalte | A confirmar (en R3: QA) | A confirmar (en R3: Testing · Documentación) |
| Zaira Rosin | A confirmar (en R3: Investigación) | A confirmar (en R3: GIS · Análisis espacial) |
| Amilcar Aguirre | A confirmar (en R3: Desarrollo) | A confirmar (en R3: Frontend · UI) |

La Review de R3 incluye la nota "Dejar roles anteriores"; no se infiere de ella un cambio de roles.

---

## 1. Planificación de la Release

### 1.1 Objetivo y alcance

La presentación de R3 fija tres objetivos para R4:
1. Historia y trazabilidad de vuelos, análisis e índices de cada lote, organizados cronológicamente.
2. Comparación del estado del cultivo entre dos momentos sobre el mismo lote.
3. Gestión centralizada de lotes, vuelos y análisis, garantizando el aislamiento de datos entre usuarios.

El plan del equipo suma el despliegue del sistema en un entorno accesible (HU-R4-06) y el ahorro de insumos entre campañas (HU-R4-11), pendiente desde R2 (RFGL-05). Al corte provisional, la mayor parte de los objetivos 1 y 3 está implementada, la comparación entre vuelos y capas funciona en el frontend, y el despliegue y el ahorro quedan con su base técnica lista pero sin resultado en uso real.

**Incluido en el alcance (al corte):**

- **Datos:** migraciones Alembic 0021 → 0024. Cadena lineal con único head `0024`.
  - Trazabilidad de vuelos y diagnósticos: `subido_por_id`, `metodo_umbral`, `mapeo_bandas`, `motor_version`.
  - Perfil del usuario: avatar, descripción, CUIT, teléfono, matrícula, empresa y logo.
  - Tabla `precios_productos`, con 21 precios de referencia en USD.
  - Preferencias de uso: índice, unidad de área y producto habitual.
- **API:** 8 endpoints nuevos con JWT (de 41 a 49):
  - ahorro: `GET .../vuelos/{id}/ahorro` y `GET /lotes/{id}/ahorro-comparativo`;
  - perfil: `PUT /auth/me`, `POST /auth/me/password`, `/me/avatar` y `/me/logo-empresa`;
  - precios: `GET` y `POST /productos-fitosanitarios/{id}/precios`.

  `GET /lotes` suma filtros (`q`, `cultivo`, `campana`, `estado`) y paginación. Se corrigió el IDOR de los endpoints de índices adicionales.
- **Frontend:**
  - calendario de vuelos en el detalle del lote (`CalendarioMensual.jsx`, `VuelosCalendario.jsx`);
  - comparación de dos vuelos lado a lado con resumen de diferencias (`PanelResultadoVuelo.jsx`, `ResumenDiferenciaVuelos.jsx`);
  - superposición de capas por fecha (`MapaCapas.jsx`);
  - panel de trazabilidad;
  - listado de lotes con filtros y paginación;
  - páginas `/perfil` y `/lotes/:loteId/ahorro`.
- **Despliegue:**
  - `docker-compose.prod.yml`: sin bind mounts, migraciones automáticas al arrancar, y `db`, `redis` y `minio` sin puertos publicados;
  - Nginx como proxy con build estático del frontend;
  - Certbot con renovación cada 12 h y el bloque HTTPS comentado;
  - `.env.prod.example`;
  - scripts de backup de Postgres y MinIO.
- **Seguridad y mantenimiento:**
  - workflow `.github/workflows/security.yml` (Gitleaks, Semgrep, Bandit, pip-audit, npm audit, Trivy) y `.github/dependabot.yml`;
  - Actions fijadas a SHA;
  - actualización de dependencias: React 19, react-leaflet 5, react-router 7, Vite 8, SQLAlchemy 2.1, geoalchemy2 0.20, bcrypt 5, GDAL 3.13.3 y rasterio 1.5.1, entre otras;
  - imagen de MinIO reemplazada por `cgr.dev/chainguard/minio`.

**En curso o pendiente al corte:**
- **HU-R4-07** (resumen por vuelo en el historial): rama sin merge.
- **HU-R4-13** (ajustes de diseño): sin trabajo en el repositorio.
- **HU-R4-06:** sin servidor real.
- **HU-R4-11:** sin dosis de referencia cargadas, no produce cifras de ahorro.
- La tarea "Documentación de la R4".

**Queda fuera del alcance de esta release:** RFDR-04 (validación del diagnóstico por el usuario y criterio técnico), que el plan asigna a R5, y la exportación ISO-XML, que el plan deja como evolución futura.

### 1.2 Sprints que la componen

| S | Título | Entregable demostrable | Fecha | Historias | RF/RNF |
|---|---|---|---|---|---|
| S14 | Seguridad, trazabilidad y gestión de lotes | Workflow de seguridad activo, IDOR corregido, trazabilidad visible en resultados y PDF, listado de lotes con filtros, calendario de vuelos y base de despliegue | A confirmar (la bitácora registra el período 2026-09-27) | HU-R4-01 (3), HU-R4-02 (3), HU-R4-03 (2), HU-R4-04 (5), HU-R4-05 (3), HU-R4-06 (8, continúa en S15) | RFGL-01, RFGL-02, RFGL-03, RFDR-05, RNF-07, RNF-08, RNF-15, RNF-19 |
| S15 | Comparación y perfil | Comparación de dos vuelos, superposición de capas por fecha y perfil del usuario | A confirmar | HU-R4-06 (continuación), HU-R4-07 (3), HU-R4-08 (5), HU-R4-09 (8), HU-R4-10 (3) | RFGL-03, RFGL-04, RFSA-01 |
| S16 | Ahorro, preferencias y cierre | Ahorro comparativo entre campañas y preferencias de uso | A confirmar (en curso) | HU-R4-11 (8), HU-R4-12 (2), HU-R4-13 (5), "Documentación de la R4" (sin puntos) | RFGL-05 |

Los títulos de sprint son **derivados** del contenido de las historias: no hay presentación de R4, y la bitácora v4 usa un único encabezado ("Sprint 14 — CI/CD: seguridad (SAST, SCA, secretos, imágenes)") para todas sus entradas. Las historias van en el sprint del plan. El trabajo sin historia se ubica por orden de merge y por las fechas en git; esos límites de sprint son derivados y quedan **a confirmar**. Los RF/RNF son una **derivación** por contenido a partir de `docs/2_ERS.md` y de `docs/5_Plan_de_Releases.md` (que asigna a R4 RFGL-03, RFGL-04, RFGL-06 y RNF-19). RNF-07 (HTTPS) figura en el plan como alcance de R7, pero HU-R4-06 lo aborda. RFGL-06 (eliminar lotes, vuelos o análisis propios) no tiene trabajo nuevo en R4: la baja lógica existe desde R1 y R2.

### 1.3 Duración y fechas clave

| Evento | Fecha |
|---|---|
| Inicio de la Release 4 | 22 de septiembre de 2026 (cierre de R3, dato del equipo) |
| Primer commit de R4 en git ([`697ca21`][697ca21], PR #20) | 27 de septiembre de 2026 |
| Fin de los Sprints 14, 15 y 16 | A confirmar |
| Corte provisional de este documento ([`7eadf83`][7eadf83], PR #93) | 14 de octubre de 2026, 10:19 |
| Demo de la Release 4 | A confirmar |

**Fechas según la bitácora `docs/release-v4.0.0.md` (a confirmar).** La bitácora tiene un único sprint ("Sprint 14", período 2026-09-27) y fecha sus entradas entre el 27 de septiembre y el 14 de octubre. No registra los Sprints 15 y 16. Dos entradas (HU-R4-09 y HU-R4-11) todavía dicen "sin commitear", aunque al corte están mergeadas (PRs #91 y #93).

### 1.4 Definición de Terminado (DoD)

No se encontró en el repositorio una DoD específica de R4: `docs/5_Plan_de_Releases.md` y `docs/2_ERS.md` no tienen cambios entre `ba39b2a` y `7eadf83`. Se mantiene la DoD de las releases anteriores. Una tarea se considera terminada cuando cumple todos los criterios siguientes:

- La funcionalidad es demostrable de punta a punta en el entorno local con `docker compose up`.
- Los endpoints involucrados responden con los códigos HTTP esperados.
- Existe al menos un test automatizado que cubre el caso principal.
- Los tests existentes siguen pasando (sin regresiones en CI).
- Si se modificó la base de datos, existe la migración Alembic correspondiente.
- Si se agregó una tarea Celery nueva, el worker fue reiniciado y verificado.
- La tarea fue documentada en el archivo de seguimiento de la release.

`docs/5_Plan_de_Releases.md` agrega para los sprints de construcción que cada funcionalidad debe estar mergeada a `main` y **verificada por al menos 2 integrantes** (revisión de código y prueba funcional).

No hay presentación de R4 que defina criterios de cierre. Los siguientes **se derivaron** de los tres objetivos de R4 y de los entregables de HU-R4-06 y HU-R4-01. Evaluados contra el corte provisional: 1 cumple, 5 parciales, 1 no cumple y 1 en curso.

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| 1 | Historia y trazabilidad: cada vuelo y análisis registra su origen, y el historial del lote se recorre en el tiempo | Parcial | Trazabilidad completa en la migración 0021 ([`bc59329`][bc59329], PR #51) y calendario de vuelos ([`d080951`][d080951], PR #52). Falta el resumen por vuelo (HU-R4-07, rama sin merge); el historial de diagnósticos sigue siendo de uno por vuelo |
| 2 | Comparación entre dos momentos del mismo lote | Parcial | Comparación de dos vuelos ([`278845f`][278845f], PR #91) y de capas ([`f13dcab`][f13dcab], PR #90). Falta el mapa de diferencia (criterio opcional de HU-R4-09, según la bitácora), y el ahorro entre campañas no produce cifras sin dosis |
| 3 | Gestión centralizada de lotes, vuelos y análisis | Parcial | Listado multi-lote con filtros y paginación ([`38b475f`][38b475f], PR #53), perfil ([`dcc1811`][dcc1811], PR #75) y preferencias ([`682afd3`][682afd3], PR #92). No hay una vista unificada de análisis de todos los lotes |
| 4 | Aislamiento de datos entre usuarios | Parcial | Todos los endpoints que cuelgan de un lote validan el lote del usuario, y los de vuelo validan el vuelo dentro del lote (IDOR corregido en [`537f671`][537f671], PR #49). Pero los precios cargados por un usuario se aplican a todos (`precios_productos` sin `usuario_id`), y los tests de aislamiento no corren en CI |
| 5 | Sistema desplegado en un entorno accesible y seguro (HU-R4-06) | En curso | Base de despliegue lista (PR #54); sin servidor, sin dominio y con HTTPS comentado en `docker/nginx/nginx.conf` |
| 6 | Controles de seguridad automatizados | Parcial | `security.yml` con 6 jobs ([`697ca21`][697ca21], PR #20); solo Gitleaks bloquea, los otros 5 corren con `continue-on-error: true` |
| 7 | Los tests de la funcionalidad nueva corren en CI | No cumple | De 38 tests de Python nuevos, 8 entraron al CI; quedan fuera los de aislamiento (`test_multi_tenant_indices.py`) y de ahorro (`test_ahorro_*.py`). En R4 no se agregó ningún archivo de test a `ci.yml`. Resultado de CI en el corte: a confirmar |
| 8 | Las migraciones aplican en una cadena única desde cero | Cumple | Verificación estática: 0001 → 0024 lineal por `down_revision`, único head `0024`. Según la bitácora, el 14 de octubre "las 24 migraciones corren limpias de punta a punta" contra una base nueva. Resultado del job `test-api` en el corte: a confirmar |

---

## 2. Sprint 14 — Seguridad, trazabilidad y gestión de lotes

| Sprint | Título | Fechas | Historias | RF/RNF |
|---|---|---|---|---|
| S14 | Seguridad, trazabilidad y gestión de lotes (derivado) | A confirmar (la bitácora registra el período 2026-09-27) | HU-R4-01, HU-R4-02, HU-R4-03, HU-R4-04, HU-R4-05, HU-R4-06 | RFGL-01, RFGL-02, RFGL-03, RFDR-05, RNF-07, RNF-08, RNF-15, RNF-19 |

### Objetivo

Asegurar la base antes de construir sobre ella. Se cerró el aislamiento de datos entre usuarios, se agregaron controles de seguridad automatizados al CI, y se registró de dónde sale cada análisis. También se ordenó la gestión de lotes y se empezó a preparar el despliegue fuera del entorno local.

### Tareas realizadas

#### Aislamiento multi-tenencia (HU-R4-01)

**Qué se implementó.**
- Una auditoría de aislamiento por usuario sobre todos los routers, según la bitácora v4. El modelo no tiene `tenant_id`: la pertenencia es `lotes.usuario_id`, y vuelos, cultivos, análisis e índices se aíslan a través del lote.
- La corrección del único IDOR encontrado ([`537f671`][537f671], PR #49) y una suite de 7 tests de acceso cruzado.

**Detalle técnico.**
- **IDOR corregido:**
  - `GET .../indices/{indice}/estado` y `.../resultado` validaban el lote, pero `obtener_analisis_indice` (`app/ingesta/service.py`) buscaba el análisis solo por `vuelo_id`.
  - Ahora hace `JOIN` con `Vuelo` y filtra por `Vuelo.lote_id == lote_id`. El parámetro `lote_id` se propagó a `obtener_estado_analisis_indice`, `obtener_resultado_geojson_indice` y sus llamadores, incluido `app/diagnostico/service.py::generar_diagnostico`.
- **Decisiones** (bitácora v4):
  - No se creó una dependencia FastAPI centralizada: el patrón `obtener_lote(db, lote_id, usuario_id=...)` → 404 "ya es consistente en todos los routers".
  - No se agregó `lote_id` a `analisis_indices`, porque el `JOIN` alcanza sin migración.
  - Las URLs firmadas de MinIO se consideraron ya cubiertas: hay un único punto de generación con expiración, `app/core/storage.py::presigned_url`.

**Verificación de pertenencia de todos los endpoints al corte** (49: 47 en routers más `GET /api/v1/health` y `/health/db`, que no requieren autenticación):

| Módulo | Método y ruta | Verificación al corte | Cambio respecto de R3 |
|---|---|---|---|
| auth | `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout` | Públicos (no operan sobre datos de otro usuario) | Sin cambios |
| auth | `GET /auth/me` | JWT; solo el propio usuario | Responde además los campos de perfil y preferencias |
| auth | `PUT /auth/me`, `POST /auth/me/password`, `POST /auth/me/avatar`, `POST /auth/me/logo-empresa` | JWT; solo el propio usuario | **Nuevos** (HU-R4-10) |
| lotes | `GET /lotes` | JWT; filtra por `usuario_id` del token | Filtros y paginación (HU-R4-03) |
| lotes | `POST /lotes`; `GET`, `PUT`, `DELETE /lotes/{lote_id}`; `GET /lotes/{lote_id}/historial` | JWT; lote del usuario o 404 | Sin cambios |
| lotes | `GET`, `POST /lotes/{lote_id}/cultivos`; `PUT`, `DELETE .../cultivos/{cultivo_id}` | JWT; lote del usuario y cultivo dentro del lote | Sin cambios |
| ingesta | `POST /lotes/inspeccionar-geotiff` | JWT; no lee datos persistidos | Sin cambios |
| ingesta | `POST /lotes/desde-geotiff`; `POST`, `GET /lotes/{lote_id}/vuelos`; `GET .../vuelos/imagenes-satelitales`; `POST .../vuelos/desde-satelite` | JWT; lote del usuario | Sin cambios |
| ingesta | `GET .../vuelos/{vuelo_id}/resultado`, `GET .../estado`, `DELETE .../vuelos/{vuelo_id}`, `POST .../reintentar`, `GET` y `POST .../indices`, `POST .../indices/batch` | JWT; lote del usuario y vuelo dentro del lote | Sin cambios |
| ingesta | `GET .../indices/{indice}/estado`, `GET .../indices/{indice}/resultado` | JWT; lote del usuario y vuelo dentro del lote | **Corregido** ([`537f671`][537f671]); en R3 solo validaban el lote |
| diagnostico | `GET .../vuelos/{vuelo_id}/diagnostico`, `POST .../diagnostico/recalcular` | JWT; lote del usuario y vuelo dentro del lote (`generar_diagnostico`) | Sin cambios |
| diagnostico | `GET /productos-fitosanitarios`, `GET /estadios-fenologicos` | JWT; catálogos globales | Sin cambios |
| diagnostico | `GET /productos-fitosanitarios/{producto_id}/precios`, `POST .../precios` | JWT; **globales: los precios no tienen dueño** | **Nuevos** (HU-R4-11) |
| reportes | `GET .../reporte/pdf`, `.../zonas/geojson`, `.../zonas/shapefile`, `.../zonas/export` | JWT; lote del usuario y vuelo dentro del lote | Sin cambios |
| ordenes_trabajo | `GET .../orden-trabajo/pdf` | JWT; lote del usuario y vuelo dentro del lote | Sin cambios |
| ahorro | `GET .../vuelos/{vuelo_id}/ahorro` | JWT; lote del usuario y vuelo dentro del lote | **Nuevo** (HU-R4-11) |
| ahorro | `GET /lotes/{lote_id}/ahorro-comparativo?cultivo_a=&cultivo_b=` | JWT; lote del usuario y cultivos del lote | **Nuevo** (HU-R4-11) |

**Hallazgo clave — precios compartidos entre usuarios.**
- La tabla `precios_productos` (migración 0023) no tiene `usuario_id`.
- `POST /productos-fitosanitarios/{id}/precios` (`app/diagnostico/precios.py::crear_precio_usuario`) guarda un precio de tipo `"usuario"` sin dueño.
- `resolver_precio()` toma el precio `"usuario"` más reciente de menos de 90 días, sin filtrar por quién lo cargó.

Consecuencia: el precio que carga un usuario se aplica al cálculo de ahorro de todos los usuarios. No expone lotes ni vuelos ajenos, pero cualquier usuario autenticado puede alterar los resultados económicos de los demás. Además, la unidad del precio es texto libre y no se valida contra la unidad de dosis del producto. Se registra como riesgo en la sección 6.

**Pruebas.** `tests/test_multi_tenant_indices.py` (7, [`537f671`][537f671]):
- `vuelo_id` de otro usuario con `lote_id` propio → 404, que es el caso exacto del IDOR;
- `lote_id` ajeno → 404;
- camino propio → 200;
- sin auth → 401.

**No corren en CI.** Los endpoints nuevos de R4 no tienen tests de acceso cruzado: ni precios ni perfil, y los de ahorro solo prueban lote y vuelo ajenos.

**Criterio del estado Parcial:** el IDOR conocido está corregido y todos los endpoints que cuelgan de un lote verifican la pertenencia. Pero los precios cargados por un usuario se comparten con todos, y la suite de aislamiento no corre en el CI.

#### Trazabilidad completa del análisis (HU-R4-02)

**Qué se implementó.** Cada vuelo registra quién lo subió y con qué mapeo de bandas y método de umbral se calculó su NDVI. Cada diagnóstico registra la versión del motor de reglas que lo generó. Los datos se muestran en la vista de resultados y en el PDF ejecutivo ([`bc59329`][bc59329], [`61ba7ad`][61ba7ad], PR #51).

**Detalle técnico por capa.**
- **Base de datos** (migración `0021_trazabilidad_analisis.py`, revision `0021`, down_revision `0020`):

| Columna | Definición |
|---|---|
| `vuelos.subido_por_id` | FK a `usuarios.id` con `SET NULL`; índice `ix_vuelos_subido_por_id` |
| `vuelos.metodo_umbral` | `VARCHAR(20)` |
| `vuelos.mapeo_bandas` | JSONB |
| `diagnosticos.motor_version` | `VARCHAR(20)` |

  El downgrade borra las cuatro columnas.
- **Backfill:**
  - `subido_por_id` se completa con el dueño del lote. Es una aproximación, según el docstring.
  - `metodo_umbral = 'fijo'` y `mapeo_bandas` según el sensor (Sentinel-2 o DJI Mavic 3) en los vuelos completados. Según el docstring, son los valores reales usados, no una aproximación.
  - `motor_version = '1.0.0'` en los diagnósticos existentes.
- **Captura:**
  - `subido_por_id` se graba en los 3 puntos que crean un `Vuelo` (`app/ingesta/service.py`).
  - El worker completa `metodo_umbral` y `mapeo_bandas` al terminar `procesar_vuelo`.
  - `MOTOR_VERSION`, una constante nueva en `app/diagnostico/reglas.py`, se graba en cada cálculo de diagnóstico, junto con una copia de los datos de trazabilidad en `metadata`.
- **API:** `VueloListItem` (`app/ingesta/schemas.py`) suma `archivo_original`, `subido_por` (resumen del usuario), `metodo_umbral` y `mapeo_bandas`. No hay endpoint de escritura sobre estos campos: según la bitácora, "no editable desde la interfaz" ya se cumplía.
- **Frontend y PDF:**
  - panel colapsable "Trazabilidad del análisis", de solo lectura (`frontend/src/components/PanelResultadoVuelo.jsx`, en la vista de resultados);
  - versión del motor en la línea de metadata de `TablaDiagnostico.jsx`;
  - sección nueva en `app/reportes/templates/reporte_ejecutivo.html`.

**Errores corregidos** ([`bc59329`][bc59329], [`61ba7ad`][61ba7ad]): `Vuelo.subido_por` devolvía `None` aunque `subido_por_id` estuviera bien cargado.
- **Causa:** `Usuario.id` está mapeado como `str` (`UUID(as_uuid=False)`) y `subido_por_id` como `uuid.UUID`, así que la carga `selectin` no emparejaba las filas.
- **Corrección:** se tipó `subido_por_id` como `as_uuid=False`. El mismo desajuste en `Lote.usuario_id` se corrigió en [`61ba7ad`][61ba7ad].

**Pruebas.**
- [`bc59329`][bc59329] agrega 1 test en `tests/test_diagnostico_api.py` (de 10 a 11: trazabilidad completa en el diagnóstico, en CI) y 1 en `tests/test_cultivos.py` (de 25 a 26: captura de quién sube el vuelo, fuera del CI).
- [`61ba7ad`][61ba7ad] agrega `test_lote_usuario_carga_via_selectinload` en `tests/test_lotes.py` (en CI).

#### Listado multi-lote (HU-R4-03)

**Qué se implementó.** El listado de lotes pasó a filtrarse y paginarse en el backend, y a traer el último vuelo de cada lote en la misma consulta. Así se eliminaron las N consultas por lote que hacía el frontend ([`38b475f`][38b475f], PR #53).

**Detalle técnico por capa.**
- **API:** `GET /api/v1/lotes` (JWT) acepta:
  - `q`: búsqueda por nombre;
  - `cultivo`: cultivo actual;
  - `campana`: año de siembra del cultivo actual;
  - `estado`: estado del último análisis;
  - `page` (≥ 1) y `page_size` (1 a 100, por defecto 20).
- **Respuesta:** `LoteListResponse` suma `page` y `page_size`; cada `LoteResponse` suma `ultimo_vuelo_fecha` y `ultimo_vuelo_estado`. `app/lotes/service.py::listar_lotes` resuelve el último vuelo y el cultivo actual con `DISTINCT ON`. Sin migración.
- **Frontend:** `Lotes.jsx` deja de pedir `GET /lotes/{id}/vuelos` por cada lote. Suma una barra de filtros (buscador con espera de 350 ms, cultivo, campaña, estado) y paginación. Para los modales de carga y de elección de lote mantiene una lista aparte de hasta 100 lotes sin filtrar.

**Decisiones de diseño** (bitácora v4): el dato "productor/campo" que pedía la tarjeta se descartó a pedido del equipo porque no existe en el modelo.

**Pruebas.** 6 tests nuevos en `tests/test_lotes.py` según la bitácora: último vuelo, lote sin vuelos, búsqueda, filtros y paginación. Ese archivo pasa de 21 a 28 tests en total en R4 y corre en CI.

**Hallazgo:** según la bitácora, SQLAlchemy 2.1 marca como obsoleto pasar una expresión a `.distinct()` (`listar_lotes`). Sigue funcionando, con un warning.

#### Línea de tiempo del lote (HU-R4-04)

**Qué se implementó.** El detalle del lote muestra los vuelos en un calendario mensual, con la lista de vuelos del día elegido. La vista de resultados suma un calendario lateral para ubicar el vuelo actual entre los demás y elegir otro para comparar ([`d080951`][d080951], PR #52). Asignado a HU-R4-04 porque la rama del PR se llama "Línea-de-tiempo-mismo-lote-y-Comparar-dos-vuelos-mismo-lote" y el commit agrega la vista temporal de los vuelos del lote. La parte de comparación se documenta en HU-R4-09.

**Detalle técnico (frontend).**
- `CalendarioMensual.jsx`: grilla mensual con navegación por mes y año, días con vuelos y leyenda.
- `DetalleLote.jsx`: el calendario y la lista "Vuelos del {día}", con tarjetas de fecha, estado, progreso, error y "Ver resultados".
- `VuelosCalendario.jsx`: calendario de solo lectura con todos los vuelos del lote, junto al panel de diagnóstico, con las acciones "Seleccionar para comparar" y nuevo análisis.
- `frontend/src/utils/fechas.js`: fecha local y formato `DD/MM/AAAA`.
- Usa los endpoints existentes `GET /lotes/{id}/vuelos` y `/estado`; no hay endpoint nuevo.

**Criterio del estado Parcial:** el plan etiqueta la historia [Backend][Frontend], y el objetivo 1 de R4 y RFGL-03 piden una línea de tiempo que relacione vuelos, análisis (fecha, índice, estado y resultados) y diagnósticos. Lo implementado ordena en el tiempo los **vuelos** y su estado. No muestra los análisis por índice ni los diagnósticos como eventos, y no tiene soporte de backend propio.

**Pruebas.** No hay tests de frontend para estos componentes.

#### Investigación de costos de fitosanitarios (HU-R4-05)

**Qué se implementó.** Un relevamiento de precios de referencia para los 21 productos del catálogo, cargado en la base por la migración `0023_crear_tabla_precios_productos.py` ([`fb945af`][fb945af], PR #89, fechado el 13 de octubre aunque la historia está planificada para S14).

**Detalle técnico.**
- **Tabla `precios_productos`** (revision `0023`, down_revision `0022`):
  - columnas: `id`, `producto_id` (FK a `productos_fitosanitarios`, `CASCADE`), `precio_usd`, `unidad` (`VARCHAR(10)`), `fuente`, `fecha` y `tipo` (`"referencia"` o `"usuario"`);
  - índices `ix_precios_productos_producto_id` e `ix_precios_productos_tipo_fecha`;
  - el downgrade borra la tabla.
- **Seed:** 21 precios de tipo `referencia`, fechados el 2026-10-13, en USD por L o por kg. Las fuentes citadas por fila son "CASAFE Lista 2026-S1", "CIAFA 2026-T3", INTA EEA Sáenz Peña, INTA EEA Reconquista, INTA NEA, y listas de fabricantes y distribuidoras. Rango: de 0,45 USD/kg (urea) a 95 USD/L (spinosad).
- **Decisiones** (bitácora v4):
  - precio cargado por el usuario, con fecha, como valor principal, y el de referencia como respaldo, porque los precios cambian mensualmente;
  - precios expresados por L o kg y no por envase.
  - Según la bitácora, 3 productos (boro foliar, thiamethoxam y clorpirifos) tienen precio estimado sin fuente específica confirmada.

**Entregable documental.**
- **Al corte, no está en el repositorio.** La bitácora v4 y el docstring de la 0023 nombran `docs/precios_fitosanitarios_referencia.md` y `docs/catalogo_productos_fitosanitarios.xlsx`, y ninguno de los dos existe en `7eadf83` ni en otra rama remota.
- Existe una versión local sin commitear de `docs/catalogo_productos_fitosanitarios.xlsx`, que según el equipo va en un PR todavía no mergeado. Se revisó en solo lectura y queda **fuera del corte**:
  - **Estructura:** una hoja ("Productos fitosanitarios") con 17 columnas: nombre, tipo, causa, dosis por ha, unidad de dosis, precio en USD por unidad, costo por ha, producto de referencia, fecha y fuente del precio, cultivos, observaciones del marbete, restricciones, instrucciones de seguridad, estado, grupo y variante, y nota del precio.
  - **Contenido:** 37 filas de productos: los 21 del catálogo ("En catálogo") y 16 nuevos ("Nuevo — falta migración"), entre ellos variantes comerciales de glifosato, 2,4-D, atrazina y haloxyfop.
  - **Dosis:** solo 6 productos nuevos traen dosis por hectárea (halauxifen-metil, haloxyfop-R-metil, diclosulam, clopyralid, picloram y flumetsulam). Ninguno de los 21 del catálogo la trae, y la columna "Costo por ha" está vacía en todas las filas.
  - **Precios contra la 0023:** 17 de los 21 coinciden. Difieren Glifosato (5,50 contra 3,50 USD/L), 2,4-D (4,95 contra 3,80), Atrazina (6,50 USD/kg de una formulación WG, contra 5,20 USD/L de una SC en la 0023) y Cletodim (6,90 contra 15,00).
  - **Fuentes:** el Excel cita para esos 4 "camposimple.com.ar, 10/2026", y para los demás un "Relevamiento PDF HU-R4-05 (2026-10)" que tampoco está en el repositorio.

**Criterio del estado Parcial:** la historia es de investigación y se juzga por su entregable documentado. Al corte, el resultado está cargado en la base (0023) con sus fuentes por fila, pero el documento del relevamiento no está en el repositorio.

**Pruebas.** No aplica para la investigación. La tabla se ejercita indirectamente en `tests/test_ahorro_api.py` (HU-R4-11), que resuelve contra el precio de referencia sembrado.

#### Despliegue (HU-R4-06)

**Qué se implementó.** Toda la parte del despliegue que no depende de tener un servidor ([`bc95528`][bc95528], [`9e87cdf`][9e87cdf], [`cbf1e4d`][cbf1e4d], [`465f6b8`][465f6b8]):
- un compose de producción;
- Nginx como único punto de entrada;
- HTTPS preparado para Certbot;
- migraciones automáticas;
- plantilla de variables;
- scripts de backup.

La rama se desarrolló en S14 y se mergeó en S15 (PR #54, 8 de octubre), después de resolver conflictos con `main`.

**Detalle técnico.**

| Archivo | Contenido |
|---|---|
| `docker-compose.prod.yml` | Sin bind mounts ni `--reload`. `db`, `redis` y `minio` sin `ports:` publicados. `api` corre `alembic upgrade head && uvicorn ... --http h11` y no levanta si la migración falla. Healthchecks en `db`, `redis` y `minio`; `restart: unless-stopped` en todos los servicios. Servicio `certbot` que ejecuta `certbot renew` cada 12 h |
| `docker/Dockerfile.nginx` | Build multi-etapa: `node:25-slim` (con `npm ci`) para el build de Vite y `nginx:1.27-alpine` para servirlo. Instala `docker/certs/avast-root.crt` |
| `docker/nginx/nginx.conf` | Puerto 80 activo, `server_name _`, `client_max_body_size 3072M`; `/api/` hacia `http://api:8000/api/`; ruta para el desafío de Certbot; SPA con `try_files ... /index.html`. Bloque `listen 443 ssl` (TLS 1.2 y 1.3) y redirección HTTP→HTTPS **comentados**, con `DOMINIO_AQUI` como marcador |
| `.env.prod.example` | Variables (solo nombres): `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `REDIS_HOST`, `REDIS_PORT`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `MINIO_ENDPOINT`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `MINIO_BUCKET`, `MINIO_USE_SSL`, `MINIO_PRESIGNED_URL_EXPIRY`, `MINIO_PUBLIC_ENDPOINT`, `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`, `APP_ENV`, `APP_DEBUG`, `ALLOWED_ORIGINS`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`. El `.env.prod` real está en `.gitignore` |
| `scripts/backup_postgres.sh`, `scripts/backup_minio.sh` | `pg_dump` con `docker compose exec` y gzip; `mc mirror` dentro del contenedor `minio` hacia un volumen de backups. Retención de 14 días. Pensados para cron en el servidor |
| `migrations/versions/0006_seed_usuario_default.py` | El usuario seed lee `ADMIN_EMAIL` y `ADMIN_PASSWORD` del entorno; sin esas variables usa los valores de desarrollo |
| `README.md`, sección "Despliegue en producción" | Guía de 10 pasos para el primer despliegue (servidor, `.env.prod`, `up -d --build`, verificación, DNS, certificado, activación de HTTPS, firewall, cron de backups) y de los siguientes (`git pull` + `up -d --build`) |

- **Automatizado:** las migraciones al arrancar `api`, la renovación de certificados y el aislamiento de red de `db`, `redis` y `minio`.
- **Manual:** el deploy completo, la activación de HTTPS, el firewall y la instalación del cron de backups.
- **Lo que no hay al corte:** **CD** (no hay workflow de despliegue en `.github/workflows/`), procedimiento de reversión del deploy, y script o guía de restauración de backups.
- **Sin servidor:** según la bitácora v4, se intentó Oracle Cloud Free Tier del 17 al 30 de septiembre sin conseguir capacidad. Hay una tabla de proveedores evaluados (Google Cloud, AWS, Azure for Students, Linode, Hetzner, Vultr), y la decisión está pendiente del equipo.

**Decisiones de diseño** (bitácora v4):
- Producción va en un archivo de compose aparte para no afectar el flujo de desarrollo.
- Nginx sirve el build estático, en lugar del servidor de desarrollo de Vite.
- La 0006 se modificó en lugar de crear una migración nueva, porque el cambio es de comportamiento (leer del entorno) y no de esquema.

**Errores corregidos.** Semgrep (`request-host-used`) marcó `proxy_set_header Host $host` y `return 301 https://$host...` en `nginx.conf`. Se reemplazó `$host` por `$server_name` y por el dominio fijo ([`cbf1e4d`][cbf1e4d]).

**Criterio del estado Parcial:** la historia pide desplegar el sistema en un entorno accesible y seguro. Al corte no hay servidor, ni HTTPS activo, ni prueba con un GeoTIFF de más de 500 MB en producción, y los backups no están programados en ningún host. El entorno sigue siendo local.

**Hallazgos.**
- La imagen de producción de Nginx también instala el certificado raíz de Avast, igual que las de desarrollo.
- Usa `node:25-slim`, mientras `docker/Dockerfile.frontend` está en `node:26-slim`.
- En `docker-compose.prod.yml`, `api`, `worker` y `nginx` no tienen healthcheck, y el worker no tiene `mem_limit`.

#### Otros cambios del sprint

Trabajo sin historia, ubicado en S14 por orden de merge (límites de sprint derivados, a confirmar):

- **Mejora del flujo de integración continua — workflow de seguridad (tarea e)** ([`697ca21`][697ca21], [`4f99d2f`][4f99d2f], [`45b03d1`][45b03d1], [`9af8061`][9af8061], [`d648213`][d648213], PR #20; [`b925724`][b925724], [`ed96d29`][ed96d29], PR #48):
  - **`.github/workflows/security.yml`**, con 6 jobs: Gitleaks (secretos), Semgrep (SAST, Python y JS), Bandit (SAST, Python), pip-audit (SCA de los dos `requirements`), npm audit (SCA del frontend, `--audit-level=high`) y Trivy (CVE `CRITICAL`/`HIGH` de las imágenes `api`, `worker` y `frontend`).
  - **`.github/dependabot.yml`**, para pip, npm, docker y github-actions, con espera de 7 días.
  - **En `ci.yml`:** Actions fijadas a SHA, y `JWT_SECRET_KEY` sacado del nivel del workflow y declarado solo en los jobs que lo usan.
  - **Hallazgos atendidos según la bitácora:** Semgrep pasó de 25 hallazgos a 0; `python-multipart` 0.0.20 → 0.0.32 (6 CVE); `pytest` 9.1.1.
  - **Historial de git:** dos tokens de ejemplo ya vencidos, en un commit de junio. Se decidió no reescribir el historial ([`7faf3c5`][7faf3c5]).
  - Ningún archivo de test se agregó a `ci.yml`.
- **Imagen de MinIO** ([`7e7182d`][7e7182d], PR #46): `minio/minio:latest` → `cgr.dev/chainguard/minio:latest` en `docker-compose.yml`. Según la bitácora, `minio/minio` se dio de baja de Docker Hub el 11 de septiembre y `quay.io` exige login desde el 24 de septiembre. Cierra el ítem de reproducibilidad heredado de R2 y R3. La nueva imagen no tiene shell.
- **Actualización de React** ([`e5054d3`][e5054d3], [`8b5f698`][8b5f698], PR #50): `react` y `react-dom` 18 → 19.3, `react-leaflet` 4 → 5, `react-router-dom` 6 → 7.18 (4 líneas de `package.json`). [`8b5f698`][8b5f698] corrige la etiqueta "Procesando imagen" del widget "Vista geoespacial", que mostraba una barra de progreso falsa mientras se pedía el GeoJSON; según la bitácora, no fue causado por el upgrade.
- **Primera tanda de Dependabot:** PRs #29, #31 a #34, #36 a #38 y #42, y Grupo E en el PR #47 ([`8aa1e97`][8aa1e97]): `fastapi` 0.141.1 (con `starlette` 1.7.0, que según la bitácora resuelve sus CVE), `alembic` 1.20.0, `shapely` 2.1.2, `scikit-image` 0.26.0, `sqlalchemy` 2.0.54, `psycopg2-binary` 2.9.13, `pydantic-settings` 2.15.0, `axios` 1.20.0, `redis` 8.1.0, `weasyprint` 70.0, `pyshp` 3.1.6, `geotiff` 3.0.5 y `node` 25-slim.
- **Bitácora de R1** ([`84ccbf6`][84ccbf6], directo a `main`, 30 de septiembre): completa la bitácora `docs/release-v1.0.0.md` y registra su cierre (tarea b).

### Estado de las historias

| Historia | Estado | Evidencia |
|---|---|---|
| HU-R4-01 — Aislamiento multi-tenencia (3) | Parcial | IDOR corregido y `tests/test_multi_tenant_indices.py` ([`537f671`][537f671], PR #49). Faltan el aislamiento de los precios cargados por usuario y la suite de aislamiento en CI |
| HU-R4-02 — Trazabilidad completa del análisis (3) | Completa | Migración 0021, `PanelResultadoVuelo.jsx` y sección en el PDF ([`bc59329`][bc59329], [`61ba7ad`][61ba7ad], PR #51) |
| HU-R4-03 — Listado multi-lote (2) | Completa | `GET /lotes` con filtros y paginación, `Lotes.jsx` ([`38b475f`][38b475f], PR #53) |
| HU-R4-04 — Línea de tiempo del lote (5) | Parcial | `CalendarioMensual.jsx`, `VuelosCalendario.jsx` ([`d080951`][d080951], PR #52). Faltan los análisis y diagnósticos como eventos y el soporte de backend |
| HU-R4-05 — Investigación de costos (3) | Parcial | Precios y fuentes en la migración 0023 ([`fb945af`][fb945af], PR #89). El documento del relevamiento no está en el repositorio al corte |
| HU-R4-06 — Despliegue (8) | Parcial | Base de despliegue ([`bc95528`][bc95528], [`9e87cdf`][9e87cdf], PR #54). Sin servidor, sin HTTPS activo y sin CD. Continúa en S15 |

### Resultado

El sprint cerró el aislamiento entre usuarios para lotes, vuelos e índices y sumó un workflow de seguridad que, en su primera corrida, llevó a actualizar dependencias y fijar las Actions. Cada análisis registra ahora quién lo subió y con qué parámetros y motor se calculó, y el listado de lotes dejó de hacer una consulta por lote. El despliegue quedó preparado pero sin servidor. Los 7 tests de aislamiento se escribieron junto con la corrección, pero no se agregaron al CI.

---

## 3. Sprint 15 — Comparación y perfil

| Sprint | Título | Fechas | Historias | RF/RNF |
|---|---|---|---|---|
| S15 | Comparación y perfil (derivado) | A confirmar | HU-R4-06 (continuación), HU-R4-07, HU-R4-08, HU-R4-09, HU-R4-10 | RFGL-03, RFGL-04, RFSA-01 |

### Objetivo

Permitir comparar el estado del lote entre dos momentos (vuelo contra vuelo y capas por fecha), sumar un resumen por vuelo al historial, y dar al usuario un perfil propio que se refleje en los documentos que genera.

### Tareas realizadas

#### Despliegue — continuación (HU-R4-06)

En este sprint se mergeó la rama de despliegue (PR #54, 8 de octubre), después de resolver su conflicto con `main` en la migración 0006. Esa migración había cambiado en paralelo por el reemplazo de `passlib` por `bcrypt` (PR #78), y quedó con los dos cambios (merge [`4f9513f`][4f9513f]). El detalle está en la sección 2.

#### Resumen por vuelo en el historial (HU-R4-07)

**No encontrado en el corte.** No hay en `7eadf83` un resumen por vuelo en el historial del lote: las tarjetas de `DetalleLote.jsx` muestran fecha, estado, progreso y error, y no hay componentes de resumen. Se buscó en los commits del rango, en los archivos nuevos de `frontend/src/` y con `git log --grep="HU-R4-07"`.

**Rama sin merge, fuera del corte:** `origin/feat/hu-r4-07-resumen-vuelo-historial`, último commit `4c3d3cf` ("feat: resumen por vuelo en el historial (HU-R4-07)", 8 de octubre). Según su mensaje, agrega `ResumenVuelo.jsx` y `useResumenVuelo.js`: NDVI mínimo, promedio y máximo; distribución de superficie por severidad; y enlaces de descarga, reutilizando el endpoint de diagnóstico. La rama `origin/feat/grafico-evolucion-ndvi-lote` (`af883e3`, "gráfico de evolución de NDVI por lote") se construye sobre ese commit y tampoco está mergeada. Ninguna de las dos se toma como parte del corte.

#### Superposición de capas por fecha (HU-R4-08)

**Qué se implementó.** En el Dashboard, cuando el lote activo tiene al menos 2 vuelos completados, el botón "Comparar capas" abre un mapa que superpone los resultados de varios vuelos del lote. Cada capa tiene visibilidad y opacidad propias, y un panel muestra la diferencia entre el vuelo más antiguo y el más reciente visibles ([`f13dcab`][f13dcab], PR #90; corrección de centrado y panel en [`60de671`][60de671], PR #93).

**Detalle técnico (frontend).**
- `frontend/src/components/MapaCapas.jsx` carga el GeoJSON de cada vuelo y lo dibuja como capa de Leaflet, con toggle de visibilidad y control de opacidad por capa.
- **Escala de colores fija.** Reclasifica cada zona con `UMBRALES_FIJOS` (NDVI 0,20 / 0,40 / 0,70; GNDVI 0,25 / 0,45 / 0,60; NDRE 0,10 / 0,20 / 0,35; SAVI 0,15 / 0,30 / 0,50; ExG 0,05 / 0,15 / 0,30) en lugar de usar la `clase` del GeoJSON, que puede venir de un umbral adaptativo. Así la misma zona recibe el mismo color en todos los vuelos.
- **Panel de diferencia:** valor medio del índice ponderado por área, y distribución de superficie por clase entre el primer y el último vuelo visible.
- No hay endpoint nuevo: usa `GET .../resultado` y `GET .../indices/{indice}/resultado`.

**Decisiones de diseño** (mensaje de [`f13dcab`][f13dcab]): se ignoran los umbrales adaptativos para que las capas sean comparables entre sí.

**Hallazgo:** `UMBRALES_FIJOS` duplica `workers/gis/clasificacion.py::_UMBRALES_POR_INDICE`. Al corte los dos coinciden, pero un cambio de cortes en el worker exige actualizar el frontend a mano; así lo advierte el comentario del componente.

**Pruebas.** No hay tests de frontend para este componente.

#### Comparar dos vuelos del mismo lote (HU-R4-09)

**Qué se implementó.** La vista de resultados de un vuelo puede abrir un segundo vuelo del mismo lote al lado ("Seleccionar para comparar" desde el calendario lateral), con un panel completo de zonas y diagnóstico por cada uno ([`d080951`][d080951], PR #52). Arriba se muestra un resumen de diferencias entre ambos ([`278845f`][278845f], PR #91). Se asignó [`d080951`][d080951] en parte a esta historia porque la rama se llama "…Comparar-dos-vuelos-mismo-lote" y el commit agrega el doble panel.

**Detalle técnico (frontend).**
- `PanelResultadoVuelo.jsx`: mapa más pestañas Zonas y Diagnóstico de **un** vuelo. Se instancia dos veces en modo comparación, y cada instancia carga sus datos con su propio `useResultadoVuelo.js`.
- `ResumenDiferenciaVuelos.jsx` y `frontend/src/utils/statsZonas.js::calcularStatsZonas`, con los deltas siempre calculados como **B − A** (A = el vuelo abierto; B = el elegido para comparar):
  - por clase: área y NDVI promedio, este último como promedio simple de las zonas de la clase;
  - índice promedio general del lote: Σ(área × NDVI) / Σ área de las zonas con valor;
  - área por clase (Alto / Medio / Bajo / Muy bajo).
- `TablaZonas.jsx` pasa a usar la misma función.
- No hay endpoint nuevo: el cálculo es del navegador.

**Decisiones de diseño** (bitácora v4):
- Cálculo en el frontend, porque cada panel ya traía sus zonas.
- Promedio general ponderado por área, no el promedio de los promedios por clase.
- Delta B − A sin suponer cuál de los dos vuelos es más reciente.

**Errores corregidos** ([`278845f`][278845f]): el sidebar marcaba "Lotes" y no "Diagnósticos" en `/lotes/{id}/vuelos/{id}` (`SidebarNav.jsx`).

**Criterio del estado Parcial:** según la bitácora v4, falta el mapa de diferencia (vuelo B − vuelo A remuestreado a una grilla común y vectorizado en zonas "mejoró / empeoró / igual"). La tarjeta lo marca como opcional, pero "vale la diferencia entre 5 y 8 pts". El plan etiqueta la historia [Backend], y no hay cambios de backend.

**Pruebas.** No hay tests de frontend para el cálculo de diferencias.

#### Personalización del perfil (HU-R4-10)

**Qué se implementó.** Una página `/perfil` donde el usuario edita sus datos personales y de empresa, cambia la contraseña y sube un avatar y el logo de su empresa. El logo se incorpora al reporte ejecutivo y a la orden de trabajo ([`dcc1811`][dcc1811], PR #75).

**Detalle técnico por capa.**
- **Base de datos** (migración `0022_personalizacion_perfil_usuario.py`, revision `0022`, down_revision `0021`): agrega a `usuarios` `avatar_key`, `descripcion`, `cuit` (`VARCHAR(13)`), `telefono_contacto`, `matricula_aplicador`, `nombre_empresa` y `logo_empresa_key`, todas nullable. El downgrade las borra.
- **API** (JWT, solo el propio usuario):
  - `PUT /api/v1/auth/me`: valida el formato del CUIT; 422 si es inválido.
  - `POST /api/v1/auth/me/password`: exige la contraseña actual; 400 si no coincide, 204 si se cambia.
  - `POST /api/v1/auth/me/avatar` y `POST /api/v1/auth/me/logo-empresa`: multipart; `app/auth/validator.py` valida extensión y *magic bytes* JPG o PNG.
  - Las imágenes se guardan en MinIO por clave, y `GET /auth/me` devuelve URL firmadas.
- **Documentos:** `app.auth.service.resolver_datos_aplicador()` descarga el logo y lo pasa en base64 a `generar_pdf_reporte` y a `generar_pdf_orden_trabajo`.
- **Frontend:**
  - `PerfilUsuario.jsx` y `frontend/src/api/perfil.js`;
  - `useAuth.js` suma `actualizarUsuario()`;
  - en `SidebarNav.jsx`, "Configuración" pasa a "Mi perfil", y el bloque de usuario muestra el avatar y el nombre de la empresa.

**Decisiones de diseño** (bitácora v4): página propia en lugar de un modal, por la cantidad de campos, y conexión del logo con los PDF incluida en la misma tarea.

**Pruebas.** No hay tests automatizados de los endpoints `/auth/me` nuevos: `tests/test_auth.py` mantiene sus 15 tests. La bitácora registra pruebas manuales contra el stack: CUIT inválido → 422, contraseña incorrecta → 400 y correcta → 204, y carga de un PNG real.

#### Otros cambios del sprint

Trabajo sin historia, ubicado en S15 por orden de merge (límites de sprint derivados, a confirmar):

- **Cierre de R3 mergeado en R4** ([`f01c301`][f01c301], PR #82, rama `sync/merge-equipo-main`, commit del 1 de octubre, mergeado el 8 de octubre). Agrega a la bitácora v3 un "Sprint 15 — Cierre de release v3.0.0" con tres arreglos fechados el 22 de septiembre:
  1. **Mapa por clase en lugar de severidad, en Diagnóstico y en el PDF.** Según la bitácora, ambos se veían "todo verde" porque coloreaban por severidad, y casi todas las zonas caen en "normal". `MapaZonas.jsx` y `app/reportes/mapa.py::generar_imagen_mapa_zonas` (por defecto `modo="clase"`) colorean ahora por clase del índice. La severidad sigue en el popup, que muestra `regla_nombre`, clase y severidad, y en el contorno de las unidades de manejo.
  2. **"Acción recomendada" restituida como sección propia.** Va en `TablaDiagnostico.jsx` y en el reporte PDF, y se quitó del párrafo de `generar_texto_zona()` (`app/diagnostico/texto.py`). Según la bitácora, se había perdido en `e435402` (R2). Test nuevo: `test_accion_recomendada_no_se_repite_en_el_parrafo` (`tests/test_texto.py`, de 26 a 27, fuera del CI).
  3. **Análisis que no se mostraban al hacer clic en la lupa del Dashboard (tarea a, "mapa sin visualizarse en el dashboard").**
     - **Causa raíz** según la bitácora y el diff: dos errores de manejo de errores, no la actualización de React. `useVueloProgreso.js` reintentaba para siempre y en silencio ante cualquier error, incluso 404 o 500. Y `AnalisisMap` (`Dashboard.jsx`) evaluaba `!estado` antes que `errorMsg`, así que quedaba en "Cargando análisis..." aunque el hook hubiera detectado el error.
     - **Arreglo:** un error con respuesta HTTP corta el polling y muestra un mensaje ("Este análisis ya no está disponible." para 404). Un error de red se reintenta hasta 5 veces seguidas.
     - La bitácora aclara que no se identificó el disparador exacto que vio el usuario.
- **Documentación formal de las releases 1 a 3 (tarea b):**
  - `docs/releases/release-v1.0.0.md` y `release-v2.0.0.md` ([`06afb2a`][06afb2a], [`93451e0`][93451e0], PR #73, 4 de octubre);
  - `docs/releases/release-v3.0.0.md` y la plantilla `docs/releases/_TEMPLATE-release.md` ([`0928e47`][0928e47], [`463f2da`][463f2da], PR #74, 5 de octubre).
  - La bitácora de R1 ([`84ccbf6`][84ccbf6]) se documentó en S14.
- **Segunda tanda de dependencias (tarea e):** Dependabot, PRs #55 a #72, y bumps coordinados que la bitácora registra como arreglos.

  | Bump | PR / commit | Motivo según la bitácora |
  |---|---|---|
  | `sqlalchemy` 2.1.1 + `greenlet` 3.5.6 explícito | [`08734f3`][08734f3], PR #76 | `ModuleNotFoundError: greenlet` |
  | `geoalchemy2` 0.20.0 | [`68ebc67`][68ebc67], PR #80 | Con SQLAlchemy 2.1, `alembic upgrade head` desde una base vacía fallaba, porque `ColumnCollection` pasó a ser abstracta |
  | `bcrypt` 5.0.0, sin `passlib` | [`5cda43b`][5cda43b], PR #78 | `passlib` es incompatible con bcrypt 5. `app/auth/service.py` y la 0006 usan `bcrypt` directo, y se valida un máximo de 72 bytes en las contraseñas |
  | `ghcr.io/osgeo/gdal:ubuntu-small-3.13.3` + `rasterio` 1.5.1 + `pydantic` 2.13.5 (solo worker) | [`5703434`][5703434], PR #77 | La imagen nueva trae Python 3.14; `rasterio` 1.3.11 no compilaba |
  | `vite` 8.3.4 + `@vitejs/plugin-react` 6.1.2 | [`955034e`][955034e], PR #79 | Peer dependencies incompatibles si se actualizaban por separado |
  | `python-jose` 3.5.0 + `pillow` 12.3.0 | [`f627b13`][f627b13], PR #81 | CVE señalados por pip-audit |

  Además, Dependabot actualizó `node` a 26-slim, `vitest` a 5.0.3, `uvicorn` a 0.54.0, `celery` a 5.6.3, `minio` 7.2.20, `geopandas` 1.1.4, `asyncpg` 0.31.0, `email-validator` 2.3.0, `jinja2` 3.1.6 y las Actions (`checkout` 7.0.1, `setup-python` 7.0.0, `setup-node` 7.0.0, `gitleaks-action` 3.0.0).

### Estado de las historias

| Historia | Estado | Evidencia |
|---|---|---|
| HU-R4-06 — Despliegue (continuación) | Parcial | Merge del PR #54 ([`507a2bd`][507a2bd]); detalle en la sección 2 |
| HU-R4-07 — Resumen por vuelo en el historial (3) | No implementada | Sin evidencia en el corte. Rama sin merge, fuera del corte: `origin/feat/hu-r4-07-resumen-vuelo-historial` (`4c3d3cf`) |
| HU-R4-08 — Superposición de capas por fecha (5) | Completa | `MapaCapas.jsx` ([`f13dcab`][f13dcab], PR #90; [`60de671`][60de671], PR #93) |
| HU-R4-09 — Comparar dos vuelos del mismo lote (8) | Parcial | Doble panel ([`d080951`][d080951], PR #52) y `ResumenDiferenciaVuelos.jsx` ([`278845f`][278845f], PR #91). Falta el mapa de diferencia |
| HU-R4-10 — Personalización del perfil (3) | Completa | Migración 0022, `/auth/me/*`, `PerfilUsuario.jsx`, logo en los PDF ([`dcc1811`][dcc1811], PR #75). Sin tests automatizados |

### Resultado

La comparación entre momentos del lote quedó resuelta en el navegador: dos vuelos lado a lado con sus diferencias de índice y de superficie por clase, y varias capas superpuestas con una escala fija. El usuario tiene perfil propio, y su logo aparece en los documentos. El resumen por vuelo quedó en una rama sin mergear. Gran parte del sprint se dedicó a actualizar dependencias marcadas por el workflow de seguridad; una de esas actualizaciones rompió temporalmente las migraciones desde cero en `main`, hasta el bump de geoalchemy2.

---

## 4. Sprint 16 — Ahorro, preferencias y cierre (en curso)

| Sprint | Título | Fechas | Historias | RF/RNF |
|---|---|---|---|---|
| S16 | Ahorro, preferencias y cierre (derivado) | A confirmar (en curso) | HU-R4-11, HU-R4-12, HU-R4-13, "Documentación de la R4" | RFGL-05 |

### Objetivo

Calcular el ahorro de insumos de la aplicación variable frente a la uniforme, por prescripción y por campaña; guardar preferencias de uso; cerrar los ajustes de diseño pendientes; y documentar la release.

### Tareas realizadas

#### Ahorro comparativo entre campañas (HU-R4-11)

**Qué se implementó.** Un módulo que compara cuánto producto y cuánto dinero se usa al tratar solo las unidades de manejo con problema ("variable") contra tratar todo el lote a la misma dosis ("uniforme"). Funciona por vuelo y acumulado por campaña, con la opción de comparar dos campañas ([`cbf1f69`][cbf1f69], PR #93).

**Detalle técnico por capa.**
- **Cálculo** (`app/ahorro/calculo.py`, puro):
  - `calcular_ahorro_vuelo()` toma la salida de `generar_orden_trabajo()`. Por producto:
    - cantidad variable = el `volumen_total` de la orden;
    - cantidad uniforme = `area_total_lote_ha × dosis_referencia`;
    - ahorro = uniforme − variable;
    - porcentaje = ahorro / uniforme × 100;
    - ahorro en dinero = ahorro × `precio_usd`.
  - `acumular_ahorro()` suma los vuelos de una campaña por producto. Marca `sin_dosis_referencia` y `sin_precio` en lugar de descartar el producto, y sigue sumando lo que sí se pudo calcular.
- **Servicio y precios:**
  - `app/ahorro/service.py` reutiliza `generar_diagnostico` → `generar_orden_trabajo`.
  - `app/diagnostico/precios.py::resolver_precio` prioriza el precio `"usuario"` más reciente con menos de 90 días; si no hay, usa el de referencia (migración 0023).
  - Modelo ORM `PrecioProducto` en `app/diagnostico/models.py`.
- **API** (JWT):

| Endpoint | Validación | Errores |
|---|---|---|
| `GET /api/v1/lotes/{lote_id}/vuelos/{vuelo_id}/ahorro` | Lote del usuario y vuelo dentro del lote | 404 |
| `GET /api/v1/lotes/{lote_id}/ahorro-comparativo?cultivo_a=&cultivo_b=` | Lote del usuario; campañas del lote | 409 si el lote no tiene área; 404 si una campaña no existe |
| `GET /api/v1/productos-fitosanitarios/{producto_id}/precios` | Global | — |
| `POST /api/v1/productos-fitosanitarios/{producto_id}/precios` | Global; siempre crea tipo `"usuario"`; `precio_usd > 0`, fecha no futura | 201, 404, 422 |

- **Respuesta:** incluye `area_total_lote_ha` y `area_tratada_ha`. No se persiste nada: se recalcula en cada consulta.
- **Frontend:**
  - página `/lotes/:loteId/ahorro` (`AhorroComparativo.jsx`), a la que se entra desde `DetalleLote.jsx`;
  - selector de una o dos campañas (`lote.cultivos`);
  - tabla por producto con cantidad variable, uniforme, ahorro, porcentaje y ahorro en US$;
  - `ModalCargarPrecio.jsx` para cargar un precio cuando falta;
  - `frontend/src/api/ahorro.js`.

**Decisiones de diseño** (bitácora v4):
- **"Variable contra uniforme" es sobre el área tratada, no sobre la dosis:** ninguno de los dos escenarios varía la dosis por zona.
- **"Campaña" = `Cultivo`.**
- **Sin tabla de ahorro:** se recalcula como el diagnóstico.
- **Un precio faltante no anula el acumulado.**
- **Carga de precio en la misma pantalla,** porque no hay administración del catálogo en el frontend.

**Errores corregidos** (según la bitácora): `acumular_ahorro()` descartaba el ahorro real de un vuelo cuando otro vuelo de la misma campaña no tenía precio. Lo detectó `test_acumular_ahorro_vuelo_sin_precio_marca_campana_parcial` antes del merge.

**Pruebas.** No corren en CI.
- `tests/test_ahorro_calculo.py` (7): cálculo puro.
- `tests/test_ahorro_api.py` (14): carga y listado de precios, fecha futura y producto inexistente; ahorro por vuelo variable contra uniforme, sin unidades de manejo y estados de error; acumulado de campaña, campañas inexistentes, lote sin área (409) y sin auth.

**Hallazgo clave — sin dosis no hay ahorro.**
- Ninguna migración carga `dosis_referencia`: la 0015 la dejó en `NULL` y ni la 0018, la 0019 ni la 0023 la completan.
- Por eso, con datos reales, "Uniforme", "Ahorro" y el ahorro en US$ salen `—` para todos los productos. La bitácora lo confirma en la base de desarrollo.
- La única verificación con cifras fue con un lote temporal y una dosis cargada a mano para Glifosato: según la bitácora, Variable 90,00 L, Uniforme 1.318,27 L, Ahorro 1.228,27 L (93 %). No hay script reproducible de esa prueba.
- El Excel local de HU-R4-05 tampoco trae dosis para los 21 productos del catálogo. Aunque se mergeara, `dosis_referencia` seguiría sin cargarse en la base hasta que una migración la complete.

**Relación con RFGL-05.** RFGL-05 pide "la diferencia entre el área total del lote y el área prescrita". La respuesta de la API incluye ambas áreas (`area_total_lote_ha`, `area_tratada_ha`), pero `AhorroComparativo.jsx` no las muestra: la pantalla solo presenta cantidades de producto y dinero, que dependen de la dosis. RFGL-05 queda parcialmente implementado.

**Discrepancia de nombres:** los campos `ahorro_pesos` y `ahorro_total_pesos` contienen dólares (`precio_usd`); la interfaz los rotula como "US$".

**Criterio del estado En curso:** el código está mergeado, pero la historia no produce cifras de ahorro con los datos reales de la base hasta que se cargue `dosis_referencia`.

#### Preferencias de uso (HU-R4-12)

**Qué se implementó.** El usuario guarda un índice preferido, una unidad de área y un producto habitual desde una tarjeta "Preferencias de uso" en `/perfil` ([`682afd3`][682afd3], PR #92).

**Detalle técnico por capa.**
- **Base de datos** (migración `0024_preferencias_uso_usuario.py`, revision `0024`, down_revision `0023`):
  - en `usuarios`: `indice_preferido` (enum `indiceenum` existente), `unidad_area_preferida` (enum nuevo `unidadareaenum`: `ha`, `acre`) y `producto_habitual_id` (FK a `productos_fitosanitarios`, `SET NULL`), todas nullable;
  - el downgrade borra las columnas y el enum.
- **API:** reutiliza `PUT /api/v1/auth/me` (`exclude_unset`); 422 ante un valor de enum inválido. `frontend/src/api/productos.js` trae el catálogo para el selector de producto.
- **Uso actual:**
  - el índice preferido preselecciona la pastilla de índice en `ModalCargaGeoTIFF.jsx` y en el Dashboard;
  - la unidad de área y el producto habitual se guardan, pero **ningún formulario los consume todavía**, según la bitácora.

**Decisiones de diseño** (bitácora v4): columnas en `usuarios`, sin tabla aparte, porque son tres valores escalares. "Unidad" se interpretó como unidad de área.

**Pruebas.** No hay tests automatizados. La bitácora registra pruebas manuales: las 24 migraciones contra una base nueva, `PUT /auth/me` con valores válidos e inválidos, y la persistencia en el navegador.

#### Ajustes de diseño pendientes (HU-R4-13)

Sin trabajo en el repositorio al corte. Se buscó en los commits del rango y en las ramas remotas sin merge (`git branch -r --no-merged origin/main`).

#### Otros cambios del sprint

- **Documentación de la R4** (tarea sin puntos): la bitácora `docs/release-v4.0.0.md` se actualizó junto con las historias (por ejemplo [`f896ebf`][f896ebf], PR #90; [`278845f`][278845f], PR #91). Este documento formal todavía no está en el repositorio al corte.

### Estado de las historias

| Historia | Estado | Evidencia |
|---|---|---|
| HU-R4-11 — Ahorro comparativo entre campañas (8) | En curso | `app/ahorro/`, `AhorroComparativo.jsx`, 21 tests ([`cbf1f69`][cbf1f69], PR #93). No produce cifras con datos reales porque `dosis_referencia` no está cargada |
| HU-R4-12 — Preferencias de uso (2) | Completa | Migración 0024, tarjeta en `PerfilUsuario.jsx` ([`682afd3`][682afd3], PR #92). Unidad de área y producto habitual guardados pero sin consumidor |
| HU-R4-13 — Ajustes de diseño pendientes (5) | Pendiente | Sin trabajo en el repositorio |
| Documentación de la R4 (sin puntos) | En curso | Bitácora actualizada; documento formal sin commitear al corte |

### Resultado

Al corte provisional, el sprint tiene el cálculo de ahorro implementado y probado con datos simulados. Con los datos reales no da cifras por falta de dosis en el catálogo, un hueco que viene de R2. Las preferencias se guardan, pero solo el índice preferido tiene uso. Los ajustes de diseño no empezaron.

---

## 5. Calidad y estado al cierre

Al corte provisional hay 329 funciones de test de Python (R3 tenía 291) y los mismos 9 tests de Vitest.
- **Tests nuevos:** R4 agregó 38 tests de Python, en 3 archivos nuevos y 4 existentes. Solo 8 entraron al CI, y no se agregó ningún archivo de test a `.github/workflows/ci.yml`.
- **CI de pruebas:** conserva sus 3 jobs (`test-api`, `test-gis`, `build-frontend`) y ejecuta 161 de los 329 tests.
- **Workflow de seguridad:** nuevo, `.github/workflows/security.yml`.
- **Resultados de ambos:** a confirmar. El repositorio es privado y no se pudo consultar GitHub Actions.

### Pruebas automatizadas

| Tipo | Herramienta | Tests | Resultado en el corte |
|---|---|---|---|
| Unitarias GIS (worker) | pytest | 64: `test_ndvi_pipeline` 4, `test_indices_worker` 22, `test_ingesta_worker` 3, `test_clasificacion` 20, `test_cobertura_geotiff` 4, `test_sin_datos` 9, configuración de Celery 2 | Job `test-gis`: a confirmar |
| Unitarias del motor, salidas y ahorro (sin base de datos) | pytest | 111: `test_diagnostico_engine` 14, `test_forma` 12, `test_texto` 27, `test_zonificacion` 19, `test_diagnostico_service` 2, `test_orden_trabajo` 12, `test_absorcion` 12, `test_satelital_catalogo` 6, `test_ahorro_calculo` 7 (nuevo) | `engine` y `forma` (26) en el job `test-api`: a confirmar. Los otros 85 no corren en CI |
| Integración HTTP contra PostGIS | pytest + TestClient | 151: `test_auth` 15, `test_lotes` 28, `test_vuelos_estado` 13, `test_ingesta` 4, `test_diagnostico_api` 11, `test_cultivos` 26, `test_estadios` 5, `test_exportacion_api` 13, `test_reportes_api` 7, `test_orden_trabajo_pdf_api` 8, `test_ahorro_api` 14 (nuevo), `test_multi_tenant_indices` 7 (nuevo) | Los 5 primeros (71) en el job `test-api`: a confirmar. Los otros 80 no corren en CI |
| Worker con base de datos | pytest | 2: `test_lote_limites_worker` | No corre en CI |
| End-to-end | pytest (`test_celery_integracion.py::test_ciclo_completo_encolar_y_esperar`) | 1 (de R1) | Solo local; según la bitácora pasó el 28 de septiembre contra el stack completo con la imagen nueva de MinIO |
| Frontend | Vitest (`npm test`) | 9: `geometria.test.js` 5, `coordenadas.test.js` 4 (sin cambios desde R3) | No corre en CI: `build-frontend` solo ejecuta `npm run build` |
| Seguridad | Gitleaks, Semgrep, Bandit, pip-audit, npm audit, Trivy | 6 jobs | A confirmar |
| Rendimiento | — | — | Sin tests automatizados |

La cobertura no se midió: no hay `pytest-cov` ni configuración de cobertura en el repositorio. Los tests se contaron leyendo `def test_` (y `it`/`test` en Vitest) en el snapshot de `tests/` y `frontend/src/` de `7eadf83`, sin ejecutarlos.

**Qué no corre en CI, comparado con R3.** R3 dejó fuera del CI 138 tests de Python y los 9 de Vitest. Al corte siguen fuera los mismos 138, y se suman 30 de R4:

| Grupo | Archivo | Tests |
|---|---|---|
| Heredados de R3 y anteriores, todavía fuera del CI (138) | `test_texto.py`, `test_zonificacion.py`, `test_diagnostico_service.py`, `test_cultivos.py`, `test_exportacion_api.py`, `test_orden_trabajo.py`, `test_absorcion.py`, `test_orden_trabajo_pdf_api.py`, `test_reportes_api.py`, `test_satelital_catalogo.py`, `test_estadios.py`, `test_lote_limites_worker.py`, E2E de `test_celery_integracion.py` | 138 (conteo de R3) |
| Nuevos de R4 fuera del CI (30) | `test_ahorro_api.py` | 14 |
| | `test_ahorro_calculo.py` | 7 |
| | `test_multi_tenant_indices.py` (aislamiento, HU-R4-01) | 7 |
| | `test_cultivos.py` (+1, [`bc59329`][bc59329]) | 1 |
| | `test_texto.py` (+1, [`f01c301`][f01c301]) | 1 |
| Nuevos de R4 dentro del CI (8) | `test_lotes.py` (+7, [`38b475f`][38b475f] y [`61ba7ad`][61ba7ad]) | 7 |
| | `test_diagnostico_api.py` (+1, [`bc59329`][bc59329]) | 1 |

La "mejora del flujo de integración continua" (tarea e) no incorporó ninguno de los 138 tests al CI. Sus cambios fueron:
- el workflow de seguridad;
- Dependabot;
- las Actions fijadas a SHA;
- el alcance de `JWT_SECRET_KEY` reducido a los jobs que lo usan.

### Workflow de seguridad

| Job | Herramienta | Qué analiza | Bloquea |
|---|---|---|---|
| Secretos | Gitleaks (`gitleaks/gitleaks-action` 3.0.0, fijada a SHA) | Historial completo del push o PR (`fetch-depth: 0`) | **Sí** |
| SAST | Semgrep (`p/security-audit`, `p/owasp-top-ten`, `p/secrets`) | Python y JS/React | No (`continue-on-error: true`) |
| SAST | Bandit | `app/` y `workers/` | No |
| SCA | pip-audit | `docker/requirements.api.txt`, `docker/requirements.worker.txt` | No |
| SCA | npm audit (`--audit-level=high`, tras `npm ci`) | `frontend/` | No |
| Imágenes | Trivy (por `docker run`, matriz `api`, `worker`, `frontend`; `--severity CRITICAL,HIGH --exit-code 0`) | Imágenes construidas con los Dockerfiles reales | No |

- **Disparadores:** `push` y `pull_request` a `main`, y semanal (`cron: "0 6 * * 1"`, lunes 06:00 UTC).
- **Modo de rollout:** según la bitácora, los 5 jobs no bloqueantes están en ese modo "solo reportar". Quitar `continue-on-error` quedó como problema abierto.
- **Hallazgos atendidos en R4** (según la bitácora):
  - Semgrep de 25 a 0;
  - `python-multipart`, `starlette` (vía `fastapi` 0.141.1), `python-jose` 3.5.0, `pillow` 12.3.0 y `pytest` 9.1.1;
  - falsos positivos de `urlopen` en Earth Search, documentados.
- **Abiertos según la bitácora:**
  - `ecdsa` (PYSEC-2026-1325), sin versión con corrección, dependencia transitiva de `python-jose`;
  - un CVE nuevo de `python-jose` (CVE-2026-85394), sin corrección, evaluado como no explotable porque `jwt.decode` restringe el algoritmo;
  - la carga de SARIF a GitHub, que requiere Advanced Security.
- **Fuera del alcance de los checks:** `security.yml` no analiza `docker/Dockerfile.nginx` ni las imágenes `nginx`, `certbot` y `postgis` del despliegue.

### Verificaciones manuales

| Fecha | Verificación | Resultado (según la bitácora `docs/release-v4.0.0.md`, salvo indicación) |
|---|---|---|
| 27 sep | Semgrep local tras fijar las Actions | "Ran 350 rules on 196 files: 0 findings" (antes, 25) |
| 27 sep | Suite completa tras `pytest` 9.1.1 | 313 tests pasan |
| 28 sep | Stack completo desde cero con `cgr.dev/chainguard/minio` | 6 servicios `healthy`/`running`; `/minio/health/live` → 200; `test_celery_integracion.py` (3, incluido el E2E) pasa |
| 30 sep | Upgrade a React 19 / react-leaflet 5 / router 7 | `npm run build` y `npm test` sin errores; recorrido manual login → dashboard → lotes → resultados, mapas y dibujo con geoman sin errores de consola |
| 30 sep | HU-R4-02: migración 0021 con `downgrade`/`upgrade` reales; PDF en 3 niveles; panel de trazabilidad en el navegador | Backfill correcto verificado con `psql`; 246 tests pasan; "motor de reglas v1.0.0" visible |
| 30 sep | HU-R4-03: búsqueda y filtro de estado contra datos reales | 253 tests pasan; el modal de carga sigue ofreciendo todos los lotes |
| 30 sep | HU-R4-01: suite completa con los 7 tests de aislamiento | Pasan |
| 8 oct | HU-R4-10 contra el stack | `PUT /auth/me` → 200, CUIT inválido → 422; contraseña incorrecta → 400, correcta → 204; PNG a `/me/logo-empresa` → 200; logo visible en el PDF (confirmado por el usuario) |
| 8 oct | Bumps coordinados de dependencias | 253 tests de `api`, 151 de `worker` y el E2E pasan tras el bump de `geoalchemy2` |
| 14 oct | HU-R4-12 con una base nueva | `alembic upgrade head` aplica las 24 migraciones; `PUT /auth/me` persiste las preferencias; enum inválido → 422 |
| 14 oct | HU-R4-11 contra datos reales y un lote temporal | 275 tests pasan. Con datos reales: "Uniforme" y "Ahorro" en `—`. Con dosis cargada a mano en un lote temporal: Variable 90,00 L / Uniforme 1.318,27 L / Ahorro 1.228,27 L (93 %) |
| 22 sep (fecha de la bitácora v3, mergeado en R4) | Mapa por clase y "Acción recomendada" ([`f01c301`][f01c301]) | PNG en modo clase con 4 colores; texto de la acción verificado en el PDF con `pypdf` temporal; 238 tests pasan |

Ninguna de estas verificaciones tiene un script reproducible en el repositorio. No hay registro de una prueba del despliegue en un servidor real.

### Errores corregidos durante el desarrollo

Ninguno afectó a una versión publicada. Los más relevantes:

- **IDOR en los endpoints de índices adicionales** (heredado de R1). Commit [`537f671`][537f671] (PR #49).
- **`Vuelo.subido_por` y `Lote.usuario_id` devolvían `None` al cargar la relación**, por mezclar tipos Python de UUID. Commits [`bc59329`][bc59329] y [`61ba7ad`][61ba7ad].
- **Migraciones desde cero rotas** tras actualizar a SQLAlchemy 2.1, por `geoalchemy2` 0.15. Commit [`68ebc67`][68ebc67] (PR #80).
- **`passlib` incompatible con bcrypt 5;** también afectaba la migración 0006. Commit [`5cda43b`][5cda43b] (PR #78).
- **Worker sin compilar con GDAL 3.13.3,** que trae Python 3.14 (`rasterio` y `pydantic`). Commit [`5703434`][5703434] (PR #77).
- **`ModuleNotFoundError: greenlet`** con SQLAlchemy 2.1. Commit [`08734f3`][08734f3] (PR #76).
- **Análisis que quedaban en "Cargando..." para siempre en el Dashboard** (tarea a). Commit [`f01c301`][f01c301] (PR #82).
- **`acumular_ahorro()` descartaba ahorro real cuando faltaba el precio de otro vuelo.** Commit [`cbf1f69`][cbf1f69].
- **Semgrep `request-host-used` en la configuración de Nginx.** Commit [`cbf1e4d`][cbf1e4d].
- **Bugs del workflow de seguridad en su primera corrida:** tag de `trivy-action` sin `v`, permisos de Gitleaks, `package-lock.json` desincronizado y el instalador de Trivy. Commits [`4f99d2f`][4f99d2f] y [`45b03d1`][45b03d1].
- **Sidebar sin marcar "Diagnósticos"** en la vista de resultados. Commit [`278845f`][278845f].

### Despliegue

**Entorno de desarrollo (el usado al corte).** Los pasos de instalación del `README.md` se reescribieron de forma más compacta ([`597937d`][597937d]), sin cambios de procedimiento:
1. clonar;
2. crear `.env` desde `.env.example`;
3. `docker compose up -d --build`;
4. `docker compose exec api alembic upgrade head`, que en desarrollo sigue siendo manual;
5. verificar con `docker compose ps` y `GET /api/v1/health`.

El tag `v4.0.0` no existe al corte.

**Producción (preparado, no desplegado).** La sección "Despliegue en producción" del README describe el primer despliegue: `.env.prod` desde `.env.prod.example`, `docker compose -f docker-compose.prod.yml up -d --build`, DNS, certificado con Certbot, activación del bloque HTTPS, firewall y cron de backups. Los despliegues siguientes son `git pull` más `up -d --build`, con migraciones automáticas. No hay CD, ni procedimiento de reversión, ni de restauración de backups.

Cambios respecto de R3:
- **Migraciones:** `upgrade head` aplica, en orden, la 0021 (trazabilidad, con backfill), la 0022 (perfil), la 0023 (precios de referencia) y la 0024 (preferencias, con el enum `unidadareaenum`). La 0006 lee `ADMIN_EMAIL` y `ADMIN_PASSWORD` del entorno, con el usuario de desarrollo como respaldo.
- **Variables:** `.env.example` sin cambios. `.env.prod.example` es nuevo y suma `ADMIN_EMAIL` y `ADMIN_PASSWORD`.
- **Dependencias de la API:**

  | Paquete | Versión al corte |
  |---|---|
  | `fastapi` | 0.141.1 |
  | `uvicorn[standard]` | 0.54.0 |
  | `sqlalchemy` | 2.1.1 (con `greenlet` 3.5.6) |
  | `geoalchemy2` | 0.20.0 |
  | `asyncpg` | 0.31.0 |
  | `alembic` | 1.20.0 |
  | `psycopg2-binary` | 2.9.13 |
  | `python-jose` | 3.5.0 |
  | `bcrypt` | 5.0.0 (sin `passlib`) |
  | `celery` | 5.6.3 |
  | `redis` | 8.1.0 |
  | `minio` | 7.2.20 |
  | `weasyprint` | 70.0 |
  | `jinja2` | 3.1.6 |
  | `pillow` | 12.3.0 |
  | `pyshp` | 3.1.6 |
  | `python-multipart` | 0.0.32 |
  | `shapely` | 2.1.2 |
  | `email-validator` | 2.3.0 |
  | `pydantic-settings` | 2.15.0 |
  | `pytest` | 9.1.1 |

- **Dependencias del worker:** además de las compartidas, `pydantic` 2.13.5, `rasterio` 1.5.1, `geopandas` 1.1.4 y `scikit-image` 0.26.0. `scipy` sigue sin declararse.
- **Dependencias del frontend:**

  | Paquete | Versión al corte |
  |---|---|
  | `react` / `react-dom` | ^19.3.0 |
  | `react-leaflet` | ^5.0.0 |
  | `react-router-dom` | ^7.18.4 |
  | `axios` | ^1.20.0 |
  | `geotiff` | ^3.0.5 |
  | `@geoman-io/leaflet-geoman-free` | ^2.20.2 |
  | `vite` | ^8.3.4 |
  | `@vitejs/plugin-react` | ^6.1.2 |
  | `vitest` | ^5.0.3 |

- **Imágenes base:**
  - `docker/Dockerfile.worker` pasa a `ghcr.io/osgeo/gdal:ubuntu-small-3.13.3`, que trae Python 3.14; la API sigue en `python:3.12-slim`.
  - `docker/Dockerfile.frontend` pasa a `node:26-slim`.
  - MinIO pasa a `cgr.dev/chainguard/minio:latest`.
  - Producción suma `nginx:1.27-alpine` (sobre una etapa de build `node:25-slim`) y `certbot/certbot:latest`.

---

## 6. Deuda técnica y trabajo pendiente

Al corte provisional quedan abiertos tres frentes:
- **Historias de R4 sin completar:** el resumen por vuelo (rama sin merge), los ajustes de diseño, el despliegue en un servidor real y el ahorro con datos reales.
- **Aislamiento:** los precios cargados por usuario se comparten entre todos.
- **Calidad:** ningún test nuevo de aislamiento ni de ahorro entró al CI, y los 138 tests que R3 dejó fuera siguen fuera.

Al cierre del Sprint 16 este documento debe actualizarse con lo que se mergee.

### Defectos y riesgos conocidos

| Ítem | Descripción | Impacto | Estado al corte |
|---|---|---|---|
| Precios compartidos entre usuarios | `precios_productos` no tiene `usuario_id`; un precio `"usuario"` cargado por cualquiera (`POST .../precios`) se aplica al ahorro de todos (`resolver_precio`). La unidad del precio es texto libre, sin validar contra la unidad de dosis | Alto (aislamiento e integridad de los resultados económicos) | Abierto |
| Ahorro sin cifras por falta de dosis | `dosis_referencia` sigue en `NULL` para los 21 productos; el ahorro y la orden de trabajo no calculan cantidades con datos reales | Alto (funcional) | Abierto |
| Tests de aislamiento y de ahorro fuera del CI | `test_multi_tenant_indices.py` (7) y `test_ahorro_*.py` (21) no están en `ci.yml`, junto con los 138 heredados | Alto (regresiones de seguridad no detectadas) | Abierto |
| Despliegue sin servidor | Sin servidor, dominio ni HTTPS activo; sin CD; sin procedimiento de reversión ni de restauración de backups; backups sin programar | Alto (objetivo de HU-R4-06) | Abierto |
| Controles de seguridad no bloqueantes | 5 de los 6 jobs de `security.yml` corren con `continue-on-error: true`; Trivy usa `--exit-code 0` | Medio (seguridad) | Abierto (rollout en modo reporte, según la bitácora) |
| Vulnerabilidades sin corrección disponible | `ecdsa` (PYSEC-2026-1325) y CVE-2026-85394 de `python-jose`, según la bitácora; evaluados como no explotables con `HS256` restringido | Bajo | Abierto |
| Certificado de Avast en producción | `docker/Dockerfile.nginx` instala `avast-root.crt`, igual que las imágenes de desarrollo | Medio (seguridad y reproducibilidad) | Abierto |
| Versiones distintas entre imágenes | Worker en Python 3.14 (imagen GDAL 3.13.3) y API en Python 3.12; build de producción en `node:25-slim` y frontend de desarrollo en `node:26-slim` | Bajo (reproducibilidad) | Abierto |
| Umbrales duplicados en el frontend | `MapaCapas.jsx::UMBRALES_FIJOS` copia `workers/gis/clasificacion.py::_UMBRALES_POR_INDICE`; hoy coinciden | Bajo (mantenimiento) | Abierto |
| Uso obsoleto de `.distinct()` | `app/lotes/service.py::listar_lotes` con SQLAlchemy 2.1 (warning), según la bitácora | Bajo | Abierto |
| Endpoints nuevos sin tests | `/auth/me/*` (perfil y preferencias) y la comparación de vuelos y capas no tienen tests automatizados | Medio | Abierto |

### Funcionalidades pendientes

| Ítem | Descripción | Release destino |
|---|---|---|
| Resumen por vuelo en el historial (HU-R4-07) | Implementado en una rama sin merge (`4c3d3cf`) | Release 4 (S16), a confirmar |
| Ajustes de diseño pendientes (HU-R4-13) | Sin trabajo en el repositorio | Release 4 (S16), a confirmar |
| Despliegue en un servidor real (HU-R4-06) | Proveedor, dominio, HTTPS, firewall, cron de backups, prueba con GeoTIFF grande | Release 4, a confirmar |
| Mapa de diferencia entre vuelos (HU-R4-09) | Remuestreo a una grilla común y zonas "mejoró / empeoró / igual" | A definir |
| Carga de dosis de referencia | Completar `dosis_referencia` y `unidad` en una migración, con fuente, para la orden de trabajo y el ahorro | A definir |
| Línea de tiempo con análisis y diagnósticos (HU-R4-04 / RFGL-03) | Hoy la línea de tiempo muestra solo los vuelos | A definir |
| Uso de la unidad de área y el producto habitual (HU-R4-12) | Guardados sin consumidor | A definir |
| Gráfico de evolución de NDVI por lote | Rama sin merge (`af883e3`) | A definir |
| Validación del diagnóstico por el usuario y criterio técnico (RFDR-04) | — | Release 5, según `docs/5_Plan_de_Releases.md` |
| Exportación ISO-XML | Evolución futura según el plan | A definir |

### Deuda heredada de R3

| Ítem | Estado al corte | Evidencia |
|---|---|---|
| Orden de trabajo sin dosis | Abierto | Ninguna migración hasta la 0024 carga `dosis_referencia`; el Excel local de HU-R4-05, fuera del corte, tampoco la trae para los 21 productos del catálogo |
| Textos de seguridad incompletos y sin revisión legal | Abierto | Sin cambios en las 0018 y 0019; la sección de la Ley 7032 sigue marcada "PENDIENTE DE REVISIÓN LEGAL". El Excel local repite los textos de 15 productos |
| Tests de R3 fuera del CI (90) | Abierto | Ningún archivo de test se agregó a `ci.yml` en R4 |
| Cambio de contrato sin versionar (migración 0020) | Abierto | Sin cambios; decisión aceptada en R3 |
| Downgrade de la 0020 con pérdida de datos | Abierto | Sin cambios |
| Caché de exportación sin invalidación | Abierto | `app/` no borra el objeto `export_` al recalcular (sin `remove_object` ni `delete_object`) |
| URLs firmadas como enlaces de portador | Abierto | Comportamiento por diseño; la bitácora v4 confirma un único punto de generación con expiración (`presigned_url`) |
| Servicios externos sin SLA ni alternativa | Abierto | Sin cambios en el manejo de errores de Earth Search (`app/ingesta/router.py`) ni de los tiles de Esri; producción suma `certbot/certbot:latest` |
| Validación de ubicación del GeoTIFF solo en el navegador | Abierto | Sin cambios |
| Cortes provisorios de ExG y GNDVI | Abierto | Sin commits sobre `clasificacion.py` en R4; `MapaCapas.jsx` replica los mismos cortes |
| Exportación solo de NDVI | Abierto | `/zonas/export` mantiene el 501 para otros índices |
| Geometrías perdidas en la base de desarrollo | Abierto | Sin cambios (dato de desarrollo) |
| IDOR en índices adicionales | Corregido | [`537f671`][537f671] (PR #49) y `tests/test_multi_tenant_indices.py`, fuera del CI |
| Carga y edición de dosis de referencia | Abierto | Ver "Orden de trabajo sin dosis" |
| Revisión legal y agronómica de la orden de trabajo | Abierto | Sin rastro en el repositorio |
| Exportación ISO-XML / integración con maquinaria | Abierto | Sin implementación en `app/` ni en `workers/` |
| Exportación y diagnóstico multi-índice | Abierto | Sin cambios |
| Historial y trazabilidad (objetivo 1 de R4) | Parcial | Trazabilidad (0021) y calendario de vuelos; falta el resumen por vuelo (rama sin merge) |
| Comparación entre campañas (objetivo 2 de R4) | Parcial | Comparación de vuelos y capas, ahorro entre campañas sin cifras; falta el mapa de diferencia |
| Gestión centralizada con aislamiento (objetivo 3 de R4) | Parcial | Listado multi-lote, perfil y preferencias; precios compartidos entre usuarios |
| Validación del diagnóstico por el usuario (RFDR-04) | Abierto | Sin endpoint ni modelo; asignado a R5 |
| Worker sin límite de memoria ni concurrencia acotada | Abierto | Ni `docker-compose.yml` ni `docker-compose.prod.yml` definen `mem_limit` |
| Certificado raíz de Avast | Abierto | Sigue en los Dockerfiles de `api`, `worker` y `frontend`, y se suma a `Dockerfile.nginx` |
| Imagen `minio/minio:latest` | Corregido | [`7e7182d`][7e7182d] (PR #46): `cgr.dev/chainguard/minio:latest` en ambos compose |
| Tests del motor fuera del CI (texto, zonificación, service) | Abierto | Siguen fuera de `ci.yml` |
| Cobertura insuficiente de la API de R2 | Parcial | Sin tests del 200 del diagnóstico, de `recalcular`, de `GET /productos-fitosanitarios` ni de `indices/batch` |
| Catálogo sin dosis ni fuente | Parcial | Precios de referencia con fuente por fila (0023); restricciones con fuente desde R3; `dosis_referencia` y `unidad` vacías |
| Atributos del lote sin uso en el motor | Abierto | Sin cambios en `app/diagnostico/` |
| Código muerto `app/diagnostico/productos.py` | Abierto | Existe y no se importa |
| Downgrades no reversibles (0012, 0013) | Abierto | Sin cambios |
| Estadísticas sobre el raster decimado | Abierto | Sin cambios |
| Ahorro de insumos (RFGL-05) | Parcial | HU-R4-11 implementa el cálculo y expone `area_total_lote_ha` y `area_tratada_ha` ([`cbf1f69`][cbf1f69]), pero la pantalla no muestra la diferencia de áreas, y las cantidades y montos requieren `dosis_referencia` |
| Popup del mapa con confianza y producto | Abierto | `MapaZonas.jsx::onEachZonaSeveridad` muestra regla, clase y severidad ([`f01c301`][f01c301]); sin confianza ni producto |
| Reglas configurables sin código | Abierto | Las 20 reglas siguen como `condicion=lambda` |
| Test E2E del flujo con diagnóstico, en CI | Abierto | Sin E2E nuevo |
| Historial de diagnósticos entre vuelos (RFGL-03) | Parcial | `diagnosticos` mantiene uno por vuelo; R4 agrega trazabilidad y `motor_version`, no historial |
| Reporte, exportación y orden de trabajo | Parcial | La orden de trabajo sigue sin dosis |
| Validación de índices y reglas del motor | Abierto | Los chequeos de reglas e índices (tareas c y d) no dejaron rastro en el repositorio (dato del equipo): ningún commit de R4 toca `reglas.py`, `engine.py`, `indices.py`, `clasificacion.py`, `docs/reglas_diagnostico.md` ni sus tests, salvo `MOTOR_VERSION` ([`bc59329`][bc59329]) |
| Registro desde la interfaz | Abierto | El botón "Registrarse" de `Login.jsx` sigue sin handler |
| Usuario seed con credenciales conocidas | Parcial | La 0006 lee `ADMIN_EMAIL` y `ADMIN_PASSWORD` del entorno ([`bc95528`][bc95528]); sin esas variables vuelve a los valores de desarrollo |
| Archivos grandes en memoria | Mitigado | Sin cambios; sigue el riesgo de memoria del worker |
| Dependencias sin fijar (`scipy`, `npm install` con rangos) | Abierto | `scipy` sin declarar; `npm install` en `Dockerfile.frontend` y en `ci.yml` (producción y `security.yml` usan `npm ci`) |
| Migraciones manuales | Parcial | Automáticas en `docker-compose.prod.yml`; manuales en desarrollo |
| Severidad, zonificación y ahorro de insumos | Parcial | Ver "Ahorro de insumos (RFGL-05)" |
| Roles y permisos | Abierto | Sin roles en `app/auth/` |
| Cobertura de tests | Abierto | Sin medición |
| Zonas en PostGIS | Abierto | La única columna geométrica sigue siendo `lotes.geometry` |

### Compromisos de mejora de la release anterior

| Compromiso | Estado | Evidencia |
|---|---|---|
| Seguir con el manejo de ramas por feature y bugs | Cumplido | 49 PRs desde ramas `feat/`, `fix/`, `sync/` y de Dependabot; un solo commit directo a `main` ([`84ccbf6`][84ccbf6], documentación) |
| Seguir usando Trello | Cumplido | IDs `HU-R4-NN` en los mensajes de commit de 9 historias y referencias a "la tarjeta" en la bitácora v4 |
| Sprint dedicado a deuda técnica | Parcial | El primer tramo de R4 (bitácora: "Sprint 14 — CI/CD: seguridad") atendió seguridad, dependencias, la imagen de MinIO y el IDOR. Siguen abiertas las deudas funcionales de R3: dosis, tests fuera del CI, caché de exportación |
| Bajar el nivel técnico para las exposiciones | No verificable en el repo | — |
| No dejar el testing y la documentación para el último sprint | Parcial | **Tests:** llegaron en el mismo commit que la funcionalidad en HU-R4-01 ([`537f671`][537f671]), HU-R4-02 ([`bc59329`][bc59329]), HU-R4-03 ([`38b475f`][38b475f]) y HU-R4-11 ([`cbf1f69`][cbf1f69]); HU-R4-04, 08, 09, 10 y 12 no tienen tests, y 30 de los 38 tests nuevos no están en CI. **Documentación:** la bitácora v4 se actualizó por tarea; la documentación formal de R1 a R3 se escribió en S15 (PRs #73 y #74), no en el último sprint; la de R4 queda para S16 |
| Test E2E en CI (incumplido en R3) | No cumplido | `ci.yml` no corre ningún E2E |
| Cobertura completa (incumplido en R3) | No cumplido | Sin medición de cobertura |
| Tests dentro del CI (incumplido en R3) | No cumplido | Ningún archivo de test agregado a `ci.yml`; siguen fuera 138 + 30 |

[06afb2a]: https://github.com/universoparalelo/Agronexo/commit/06afb2a
[08734f3]: https://github.com/universoparalelo/Agronexo/commit/08734f3
[0928e47]: https://github.com/universoparalelo/Agronexo/commit/0928e47
[278845f]: https://github.com/universoparalelo/Agronexo/commit/278845f
[38b475f]: https://github.com/universoparalelo/Agronexo/commit/38b475f
[45b03d1]: https://github.com/universoparalelo/Agronexo/commit/45b03d1
[463f2da]: https://github.com/universoparalelo/Agronexo/commit/463f2da
[465f6b8]: https://github.com/universoparalelo/Agronexo/commit/465f6b8
[4f9513f]: https://github.com/universoparalelo/Agronexo/commit/4f9513f
[4f99d2f]: https://github.com/universoparalelo/Agronexo/commit/4f99d2f
[507a2bd]: https://github.com/universoparalelo/Agronexo/commit/507a2bd
[537f671]: https://github.com/universoparalelo/Agronexo/commit/537f671
[5703434]: https://github.com/universoparalelo/Agronexo/commit/5703434
[597937d]: https://github.com/universoparalelo/Agronexo/commit/597937d
[5cda43b]: https://github.com/universoparalelo/Agronexo/commit/5cda43b
[60de671]: https://github.com/universoparalelo/Agronexo/commit/60de671
[61ba7ad]: https://github.com/universoparalelo/Agronexo/commit/61ba7ad
[682afd3]: https://github.com/universoparalelo/Agronexo/commit/682afd3
[68ebc67]: https://github.com/universoparalelo/Agronexo/commit/68ebc67
[697ca21]: https://github.com/universoparalelo/Agronexo/commit/697ca21
[7e7182d]: https://github.com/universoparalelo/Agronexo/commit/7e7182d
[7eadf83]: https://github.com/universoparalelo/Agronexo/commit/7eadf83
[7faf3c5]: https://github.com/universoparalelo/Agronexo/commit/7faf3c5
[84ccbf6]: https://github.com/universoparalelo/Agronexo/commit/84ccbf6
[8aa1e97]: https://github.com/universoparalelo/Agronexo/commit/8aa1e97
[8b5f698]: https://github.com/universoparalelo/Agronexo/commit/8b5f698
[93451e0]: https://github.com/universoparalelo/Agronexo/commit/93451e0
[955034e]: https://github.com/universoparalelo/Agronexo/commit/955034e
[9af8061]: https://github.com/universoparalelo/Agronexo/commit/9af8061
[9e87cdf]: https://github.com/universoparalelo/Agronexo/commit/9e87cdf
[b925724]: https://github.com/universoparalelo/Agronexo/commit/b925724
[ba39b2a]: https://github.com/universoparalelo/Agronexo/commit/ba39b2a
[bc59329]: https://github.com/universoparalelo/Agronexo/commit/bc59329
[bc95528]: https://github.com/universoparalelo/Agronexo/commit/bc95528
[cbf1e4d]: https://github.com/universoparalelo/Agronexo/commit/cbf1e4d
[cbf1f69]: https://github.com/universoparalelo/Agronexo/commit/cbf1f69
[d080951]: https://github.com/universoparalelo/Agronexo/commit/d080951
[d648213]: https://github.com/universoparalelo/Agronexo/commit/d648213
[dcc1811]: https://github.com/universoparalelo/Agronexo/commit/dcc1811
[e5054d3]: https://github.com/universoparalelo/Agronexo/commit/e5054d3
[ed96d29]: https://github.com/universoparalelo/Agronexo/commit/ed96d29
[f01c301]: https://github.com/universoparalelo/Agronexo/commit/f01c301
[f13dcab]: https://github.com/universoparalelo/Agronexo/commit/f13dcab
[f627b13]: https://github.com/universoparalelo/Agronexo/commit/f627b13
[f896ebf]: https://github.com/universoparalelo/Agronexo/commit/f896ebf
[fb945af]: https://github.com/universoparalelo/Agronexo/commit/fb945af
