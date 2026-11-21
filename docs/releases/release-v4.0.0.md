# AgroNexo — Release 4 (v4.0.0)

**Historial, comparación y app instalable**

Proyecto Final de Ingeniería en Sistemas · UTN FRRe · Equipo 6
Profesores: Acuña, César J · Mendez, Graciela L

---

## Ficha de release

| Campo | Valor |
|---|---|
| Versión | v4.0.0 (tag anotado `v4.0.0`, commit de corte [`08fc74f`][08fc74f] del 19 de noviembre de 2026, PR #190) |
| Estado | Completa — Demo 29 de octubre de 2026 (dato del equipo). Historias: 16 completas y 1 parcial (HU-R4-01), 81 de 84 puntos completos. Publicada en GitHub Releases el 19 de noviembre de 2026 con el instalador adjunto |
| Período | 22 de septiembre — 20 de octubre de 2026 (4 semanas), según el calendario de planificación (dato del equipo). La presentación fija el cierre de R4 el 22 de octubre |
| Equipo | Amilcar Aguirre, Matías Machado, Celeste Martín Rodich, Denise Pujalte, Zaira Rosin |
| Metodología | Scrum — 4 sprints de 1 semana (S14 a S17), 17 historias y 84 puntos estimados con Planning Poker (escala Fibonacci) |
| Entorno | Aplicación de escritorio para Windows (instalador de Electron con Postgres + PostGIS, la API y el worker empaquetados) y Docker Compose para desarrollo y CI. Sin servidor desplegado |
| Repositorio | universoparalelo/Agronexo |
| Hito de entrega | El productor instala AgroNexo en su PC y, sin servidor y sin conexión para el flujo principal, recorre la historia y la trazabilidad de cada lote, compara vuelos y capas, ve el ahorro de insumos por aplicación selectiva y administra sus lotes, su perfil y sus preferencias |

**Fechas nominales y fechas reales.** Las fechas de sprint son las del calendario de planificación (dato del equipo) y reemplazan las fechas de referencia registradas en la bitácora el 3 de noviembre (PR #162: S14 22/9–2/10, S15 3/10–13/10, S16 14/10–22/10). Los commits se ubican en cada sprint por su contenido, no por su fecha. Como la bitácora ya lo aclara para el PR #162, "el trabajo hecho después del 22/10 (motor de diagnóstico, catálogo, ajustes de diseño y toda la app de escritorio) se ubica en el sprint 16", que en este documento se divide en S16 y S17. Las historias HU-R4-06, 13, 14, 15 y 17 se mergearon entre el 23 de octubre y el 19 de noviembre, y el tag es del 19 de noviembre, **posterior a la demo**. Cada hecho se cita con su fecha real de git.

**Trabajo posterior a la demo (29 de octubre) e incluido en el tag:**
- todo el empaquetado de escritorio salvo la decisión D1: lanzador, instalador, sesión automática, bienvenida, backup, modo sin conexión, copia antes de actualizar, scripts de armado y actualizaciones automáticas (PRs #129 a #158, #184 y #190, del 30 de octubre al 19 de noviembre);
- la carga del catálogo por migración 0029 (PR #165, 3 de noviembre);
- el motor v1.3.0 y la marca recomendada en la orden de trabajo (PR #164, 3 de noviembre);
- la corrección del worker de Docker para PyJWT (PR #161, 3 de noviembre). Es la excepción a otro cambio que no está en esta lista: el reemplazo de `python-jose` por PyJWT (PR #128) es del 28 de octubre, anterior a la demo;
- la agrupación de Dependabot (PR #185, 19 de noviembre).

**Rango.** De [`7eadf83`][7eadf83] (corte provisional, 14 de octubre) a [`08fc74f`][08fc74f]: 105 commits, 87 sin contar merges, de los cuales 27 son de Dependabot. Desde el tag `v3.0.0` ([`ba39b2a`][ba39b2a]) el rango completo de la release suma además los 72 commits sin merges documentados al corte provisional. En `origin/main` hay 12 commits posteriores al tag (actualizaciones agrupadas de Dependabot, corrección de `publicar_release.ps1` en [`cd9f6c7`][cd9f6c7] y reglas de escritorio en `CLAUDE.md`); quedan fuera del corte.

## Equipo y roles

| Integrante | Rol en la release | Área |
|---|---|---|
| Matías Machado | Scrum Master / Release Manager | Frontend · API |
| Celeste Martín Rodich | Desarrollo | Backend · GIS · DevOps |
| Denise Pujalte | QA | Testing · Documentación |
| Zaira Rosin | Investigación | GIS · Análisis espacial |
| Amilcar Aguirre | Desarrollo | Frontend · UI |

Los roles son los mismos de R3 (dato del equipo).

---

## 1. Planificación de la Release

### 1.1 Objetivo y alcance

La presentación de R4 fija tres objetivos: **historia y trazabilidad** (cada vuelo y análisis, ordenado en el tiempo), **comparación y cálculo de ahorro** (cómo evolucionó el cultivo y cuánto se ahorró) y **empaquetamiento** (que cualquiera pueda instalarla y usarla en su PC). El alcance declarado es historial y trazabilidad de vuelos, comparación de vuelos y capas, ahorro entre campañas, lotes, perfil y preferencias, datos aislados por usuario y seguridad, y app instalable. Al corte, el usuario instala AgroNexo con un `Setup.exe`, carga su ortomosaico, obtiene índices, zonas, diagnóstico por estadio y orden de trabajo con marca recomendada, compara vuelos y ve el ahorro, sin servidor y sin internet para ese flujo.

**Incluido en el alcance:**

- **Datos:** migraciones Alembic 0021 → 0029, cadena lineal con único head `0029`.
  - 0021 trazabilidad, 0022 perfil, 0023 precios de referencia, 0024 preferencias (documentadas al corte provisional).
  - 0025 tabla `ndvi_esperado_estadio` (curva genérica de NDVI esperado por cultivo y estadio, [`80e3413`][80e3413], PR #95).
  - 0026 `productos_fitosanitarios.confiabilidad_dosis` ([`dcfc9a3`][dcfc9a3], PR #112).
  - 0027 tabla `presentaciones_productos` (marcas y concentraciones, [`baa2fd4`][baa2fd4], PR #113).
  - 0028 tabla `revisiones_diagnostico` (criterio técnico RFDR-04, [`d31d4ff`][d31d4ff], PR #122).
  - 0029 carga del catálogo: 30 productos con dosis, 21 precios de referencia y 59 presentaciones ([`ec25a5d`][ec25a5d], PR #165).
- **API:** 60 endpoints al corte (58 en routers más `GET /api/v1/health` y `/health/db`); R4 sumó 19 sobre los 41 de R3.
  - Al corte provisional: ahorro, perfil y precios (8).
  - Después: backup (`/api/v1/backup`, 5), archivos con token que vence (`app/archivos/router.py`, 1), `POST /auth/me/bienvenida`, `PUT /lotes/{id}/vuelos/{id}` (edición de vuelos), `PUT` y `DELETE .../diagnostico/zonas/{zona_id}/revision` y `GET /estadios-fenologicos/ndvi-esperado`.
- **Motor de diagnóstico:** `MOTOR_VERSION` de 1.0.0 a 1.3.0. Reglas relativas al estadio, motor probabilístico (Naive Bayes, experimental) en paralelo, criterio técnico del agrónomo, recálculo automático por firma de datos y recomendación provisoria en zonas con empate.
- **Catálogo:** importador desde Excel (`app/catalogo/importador.py`), filtro de productos por cultivo, alternativas con marca, dosis, precio y costo por hectárea, y marca recomendada en la orden de trabajo.
- **Frontend:**
  - calendario de vuelos, resumen por vuelo y gráfico de evolución del NDVI con NDVI esperado;
  - comparación de vuelos (vista completa, lado a lado y cortina), "Cambio por zona" y tendencia del índice; superposición de capas;
  - listado de lotes con filtros, edición de lotes y vuelos, perfil, preferencias, copia de seguridad y bienvenida;
  - rediseño de paneles (HU-R4-13) y modo sin conexión.
- **App de escritorio:** lanzador de Electron 44.10.0 (`escritorio/electron/`), instalador NSIS con electron-builder 26.18.0, motor empaquetado con PyInstaller (`escritorio/empaquetado/`), almacenamiento en disco y actualizaciones automáticas con `electron-updater` 6.8.12.
- **Seguridad y mantenimiento:** workflow `security.yml` (6 jobs), Dependabot agrupado por semana y ecosistema, Actions fijadas a SHA, `python-jose` reemplazado por PyJWT 2.15.1, y actualización de dependencias (detalle en la sección 6).

**Queda fuera del alcance de esta release:**
- el despliegue en servidor, reemplazado por el instalador (decisión D1, sección 5);
- el paso 2 de D3 (quitar MinIO de Docker y CI);
- el mapa de diferencia raster entre vuelos;
- el análisis de barbecho (decisión del equipo del 3 de noviembre);
- la exportación ISO-XML;
- la guía de primer uso y la de estadios fenológicos (propuestas para R5).

Dos ítems que el plan y la presentación ubicaban fuera de R4 sí se hicieron:
- **RFDR-04 (criterio técnico del agrónomo):** `docs/5_Plan_de_Releases.md` lo asigna a R5 y el provisional lo dejaba fuera del alcance. Se implementó en R4 dentro de HU-R4-15 (migración 0028, [`d31d4ff`][d31d4ff]).
- **Actualizaciones automáticas e instalador publicado en GitHub Releases:** la presentación los pone en "Qué sigue" (R5). Se implementaron el 19 de noviembre, antes del tag (D18 a D20, [`9cda5c2`][9cda5c2], PR #184). La publicación se hace con `escritorio/empaquetado/publicar_release.ps1`, y la release `v4.0.0` está publicada en GitHub Releases desde el 19 de noviembre de 2026 a las 21:02 UTC, con `AgroNexo-Setup-4.0.0.exe`, su `.blockmap` y `latest.yml` (`gh release view v4.0.0`).

### 1.2 Sprints que la componen

La presentación planifica **3 sprints** de una semana (S14 24 pts, S15 29 pts, S16 31 pts). **Por decisión del equipo, este documento separa en dos el Sprint 16 de la presentación**, para dejar registrado el cambio de enfoque de sitio web a aplicación de escritorio como un sprint propio. El orden (ahorro y diagnóstico en S16, escritorio en S17) es el que respalda git: el ahorro y las preferencias se mergearon el 14 de octubre, el motor de diagnóstico el 23 de octubre y el trabajo de escritorio entre el 29 de octubre y el 19 de noviembre. El total sigue siendo 17 historias y 84 puntos.

| S | Título | Entregable demostrable | Fecha | Historias | RF/RNF |
|---|---|---|---|---|---|
| S14 | Seguridad, trazabilidad y gestión | Aislamiento por usuario, trazabilidad en resultados y PDF, listado y calendario de vuelos, precios, dosis y marcas de referencia, workflow de seguridad y Dependabot | 22–29 sep | HU-R4-01 (3), 02 (3), 03 (2), 04 (5), 05 (3), 14 (3), 16 (5) — 24 pts | RFGL-01, RFGL-02, RFGL-03, RFDR-05, RNF-08, RNF-15 |
| S15 | Comparación, perfil y catálogo | Resumen por vuelo, capas por fecha, comparación de dos vuelos, perfil, interfaz pareja y catálogo con alternativas con marca | 29 sep – 6 oct | HU-R4-07 (3), 08 (5), 09 (8), 10 (3), 13 (5), 17 (5) — 29 pts | RFGL-03, RFGL-04, RFSA-01, RFDR-01 |
| S16 | Ahorro, preferencias y diagnóstico | Ahorro por vuelo y entre campañas, preferencias de uso y motor por estadio con criterio técnico y motor probabilístico | 6–13 oct | HU-R4-11 (8), 12 (2), 15 (8) — 18 pts | RFGL-05, RFDR-01, RFDR-03, RFDR-04 |
| S17 | Cambio de enfoque: de sitio web a aplicación de escritorio | Instalador de Windows que funciona sin servidor y sin conexión para el flujo principal | 13–20 oct | HU-R4-06 (13) — 13 pts | RNF-19 |

Las fechas son las del calendario de planificación (dato del equipo); el trabajo real de cada historia tiene la fecha de git que se cita en su sección. Los RF/RNF son una derivación por contenido a partir de `docs/2_ERS.md` y `docs/5_Plan_de_Releases.md`, que asigna a R4 RFGL-03, RFGL-04, RFGL-06 y RNF-19. RNF-07 (HTTPS) se abordaba en el enfoque web de HU-R4-06 y deja de aplicar con el instalador. RFGL-06 (eliminar lotes, vuelos o análisis propios) no tiene trabajo nuevo: la baja lógica existe desde R1 y R2.

**Velocidad.** La presentación declara 24, 29 y 31 puntos por sprint (84 en 3 sprints, promedio 28). Con la separación del S16, los puntos planificados por sprint son 24, 29, 18 y 13. Según la evaluación de este documento contra el código, 81 de los 84 puntos están completos; la diferencia es HU-R4-01 (Parcial, 3 pts, sección 2).

### 1.3 Duración y fechas clave

| Evento | Fecha |
|---|---|
| Inicio de la Release 4 | 22 de septiembre de 2026 |
| Fin Sprint 14 — Seguridad, trazabilidad y gestión | 29 de septiembre de 2026 |
| Fin Sprint 15 — Comparación, perfil y catálogo | 6 de octubre de 2026 |
| Fin Sprint 16 — Ahorro, preferencias y diagnóstico | 13 de octubre de 2026 |
| Fin Sprint 17 — App de escritorio | 20 de octubre de 2026 |
| Cierre de R4 según la presentación | 22 de octubre de 2026 |
| Decisión D1: el instalador reemplaza el despliegue en servidor (`docs/decisiones-app-escritorio.md`) | 29 de octubre de 2026 |
| Demo y cierre Release 4 | 29 de octubre de 2026 (dato del equipo) |
| Reescritura de HU-R4-06 en Trello ("Aplicación de escritorio y experiencia inicial") | 2 de noviembre de 2026 (según la tarjeta, dato del equipo) |
| Prueba final del instalador en Windows Sandbox, con y sin internet | 2 de noviembre de 2026 (bitácora, PR #156) |
| Tag `v4.0.0` ([`08fc74f`][08fc74f]) | 19 de noviembre de 2026, 17:47 GMT-3 (20:47 UTC) |
| Release `v4.0.0` publicada en GitHub Releases con el instalador | 19 de noviembre de 2026, 21:02 UTC (`gh release view v4.0.0`) |

Las fechas de sprint son nominales (dato del equipo). Según la nota del PR #162, el trabajo posterior al 22 de octubre se imputa al último sprint; el detalle de lo que es posterior a la demo está en la ficha.

### 1.4 Definición de Terminado (DoD)

DoD de la presentación de R4. Una historia se considera terminada cuando cumple todos los criterios siguientes:

- Funciona de punta a punta con `docker compose up` o con el instalador.
- Tiene tests automáticos que pasan.
- No introduce regresiones en el CI.
- Si toca la base de datos, tiene su migración Alembic.
- Fue revisada por otro integrante.
- Está documentada en la bitácora `docs/release-v4.0.0.md`.

`docs/5_Plan_de_Releases.md` agrega para los sprints de construcción que cada funcionalidad debe estar mergeada a `main` y verificada por al menos 2 integrantes.

**Criterio "revisada por otro integrante".**

*Medido en GitHub* (`gh api graphql`, el 21 de noviembre de 2026). Universo: los 76 PR no automáticos mergeados a `main` en el rango de la release, sin los de Dependabot, del PR #20 (27 de septiembre) al #190 (19 de noviembre). Cada número se cuenta por separado:

| Medición | PR | Detalle |
|---|---|---|
| Mergeados por su propio autor | 73 de 76 | — |
| Mergeados por otra cuenta | 3 de 76 | El #164 lo mergeó otra integrante. El #52 y el #54 los mergeó la cuenta dueña de la organización, `universoparalelo`, que no permite saber qué persona lo hizo |
| Con reseña formal de otra persona (aprobación, pedido de cambios o comentario de reseña) | 0 de 76 | — |
| Con comentarios de otra persona, en la conversación o en el código | 0 de 76 | El único comentario ajeno es de un bot (GitGuardian, en el #157) |

*Dato del equipo.* La revisión y el conocimiento compartido se hacían de forma verbal, sobre todo en las reuniones semanales de avance, y no por herramientas de GitHub. Esa revisión verbal y esas reuniones **no quedan registradas en el repositorio**.

**Estado del criterio.** El criterio de la DoD se cumple en la forma de **revisión verbal** que describe el equipo, y **no es verificable en GitHub**: allí no hay reseñas ni comentarios de otra persona, y 73 de los 76 PR los mergeó su autor. La retrospectiva de la presentación registra "cerrar tarjetas sin revisión de otro" como práctica a dejar de hacer (sección 7, compromisos de mejora).

Los criterios de cierre se **derivaron** de los tres objetivos de la presentación, más los transversales de calidad que ya evaluaba el provisional. El criterio "sistema desplegado en un servidor" se reemplazó por "instalador que funciona sin servidor y sin conexión para el flujo principal". Evaluados contra el commit de corte: 5 cumplen, 4 parciales y ninguno no cumple. En historias, la release cierra con 16 completas y 1 parcial (HU-R4-01), y 81 de 84 puntos completos (criterio 9).

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| 1 | Historia y trazabilidad: cada vuelo y análisis registra su origen y el historial del lote se recorre en el tiempo | Cumple | Migración 0021 ([`bc59329`][bc59329], PR #51), calendario de vuelos ([`d080951`][d080951], PR #52), resumen por vuelo ([`4c3d3cf`][4c3d3cf]) y evolución del NDVI ([`af883e3`][af883e3], [`eb85e71`][eb85e71]), mergeados en el PR #122. La brecha con RFGL-03 (análisis y diagnósticos como eventos de la línea de tiempo) queda en deuda |
| 2 | Comparación y cálculo de ahorro | Cumple | Comparación de dos vuelos ([`278845f`][278845f], [`80e3413`][80e3413], [`5c06e3f`][5c06e3f]), capas ([`f13dcab`][f13dcab]) y ahorro con dosis cargadas por la 0029 ([`ec25a5d`][ec25a5d]) y marca recomendada ([`1444295`][1444295]). El mapa de diferencia raster queda pendiente |
| 3 | Instalador que funciona sin servidor y sin conexión para el flujo principal | Cumple | `escritorio/electron/`, `escritorio/empaquetado/` y modo sin conexión ([`d5a94ed`][d5a94ed], PR #154). Prueba final con instalación, análisis, PDF y backup con y sin red en Windows Sandbox el 2 de noviembre, según la bitácora (PR #156) |
| 4 | Aislamiento de datos entre usuarios | Parcial | Los endpoints que cuelgan de un lote validan la pertenencia ([`537f671`][537f671], PR #49). `precios_productos` sigue sin `usuario_id` (`app/diagnostico/models.py::PrecioProducto`) y `test_multi_tenant_indices.py` no corre en CI |
| 5 | Controles de seguridad automatizados | Parcial | `security.yml` en verde en el corte (corrida 44612219666). 5 de sus 6 jobs mantienen `continue-on-error: true` y solo Gitleaks bloquea |
| 6 | Los tests de la funcionalidad nueva corren en CI | Parcial | Se agregaron al CI 6 archivos de Python (almacenamiento en disco, backup, bienvenida, migración del catálogo, copia antes de migrar e importación del almacenamiento), los 37 tests de Vitest y el job `test-lanzador` (38 tests). Quedan fuera, entre otros, ahorro, aislamiento, revisiones, motor probabilístico, importador del catálogo y orden de trabajo: el CI ejecuta 259 de los 591 tests de Python |
| 7 | Las migraciones aplican en una cadena única desde cero | Cumple | 0001 → 0029 lineal por `down_revision`, único head `0029`; el job `test-api` corre `alembic upgrade head` sobre una base nueva y quedó en verde |
| 8 | CI en verde en el commit de corte | Cumple | `gh run list --commit 08fc74f`: CI (corrida 44612219660) y Security (44612219666), ambas `success` |
| 9 | Historias de la release completas | Parcial | 16 completas y 1 parcial (HU-R4-01, 3 pts): 81 de 84 puntos. Por sprint: S14 6 de 7 (21 de 24 pts), S15 6 de 6 (29 pts), S16 3 de 3 (18 pts) y S17 1 de 1 (13 pts). La Review de la presentación declara 17 completas y 84 pts |

---

## 2. Sprint 14 — Seguridad, trazabilidad y gestión

| Sprint | Título | Fechas | Historias | RF/RNF |
|---|---|---|---|---|
| S14 | Seguridad, trazabilidad y gestión | 22–29 sep 2026 | HU-R4-01, 02, 03, 04, 05, 14, 16 | RFGL-01, RFGL-02, RFGL-03, RFDR-05, RNF-08, RNF-15 |

### Objetivo

Asegurar la base antes de construir sobre ella: aislar los datos de cada usuario, automatizar los controles de seguridad y mantener las dependencias al día, registrar de dónde sale cada análisis, ordenar la gestión de lotes y relevar los precios, dosis y marcas que necesitan el ahorro y la orden de trabajo.

### Tareas realizadas

#### Aislamiento multi-tenencia (HU-R4-01)

**Qué se implementó.**
- Una auditoría de aislamiento por usuario sobre todos los routers, según la bitácora. El modelo no tiene `tenant_id`: la pertenencia es `lotes.usuario_id`, y vuelos, cultivos, análisis e índices se aíslan a través del lote.
- La corrección del único IDOR encontrado ([`537f671`][537f671], PR #49, 30 de septiembre) y una suite de 7 tests de acceso cruzado (`tests/test_multi_tenant_indices.py`).

**Detalle técnico.**
- **IDOR corregido:** `GET .../indices/{indice}/estado` y `.../resultado` validaban el lote, pero `obtener_analisis_indice` (`app/ingesta/service.py`) buscaba el análisis solo por `vuelo_id`. Ahora hace `JOIN` con `Vuelo` y filtra por `Vuelo.lote_id == lote_id`; el parámetro se propagó a `obtener_estado_analisis_indice`, `obtener_resultado_geojson_indice` y `app/diagnostico/service.py::generar_diagnostico`.
- **Decisiones** (bitácora):
  - sin dependencia FastAPI centralizada: el patrón `obtener_lote(db, lote_id, usuario_id=...)` → 404 ya es consistente en todos los routers;
  - sin columna `lote_id` en `analisis_indices`, porque el `JOIN` alcanza;
  - URLs de archivos con un único punto de generación con expiración (`app/core/storage.py::presigned_url`; en escritorio, el endpoint de `app/archivos/router.py` con token que vence).
- **Endpoints posteriores al provisional:**
  - los de backup y archivos trabajan sobre el usuario del token (`app/backup/`, `app/archivos/router.py`);
  - `PUT .../vuelos/{vuelo_id}` y los de revisión validan lote y vuelo;
  - `POST /auth/me/bienvenida` solo opera sobre el propio usuario y solo en modo escritorio.

**Hallazgo clave — precios compartidos entre usuarios.** La tabla `precios_productos` (migración 0023) sigue sin `usuario_id` en el corte (`app/diagnostico/models.py::PrecioProducto`). `POST /productos-fitosanitarios/{id}/precios` guarda un precio de tipo `"usuario"` sin dueño y `resolver_precio()` toma el más reciente de menos de 90 días sin filtrar por quién lo cargó. En la app de escritorio hay un solo usuario por instalación y el riesgo desaparece. En una instalación con Docker y varios usuarios, cualquier usuario autenticado altera el ahorro de los demás.

**Pruebas.** `tests/test_multi_tenant_indices.py` (7): `vuelo_id` de otro usuario con `lote_id` propio → 404, `lote_id` ajeno → 404, camino propio → 200, sin auth → 401. **No corre en CI.**

#### Trazabilidad completa del análisis (HU-R4-02)

**Qué se implementó.** Cada vuelo registra quién lo subió y con qué mapeo de bandas y método de umbral se calculó; cada diagnóstico registra la versión del motor ([`bc59329`][bc59329], [`61ba7ad`][61ba7ad], PR #51, 30 de septiembre).

- **Base de datos** (migración `0021_trazabilidad_analisis.py`):

| Columna | Definición |
|---|---|
| `vuelos.subido_por_id` | FK a `usuarios.id` con `SET NULL`; índice `ix_vuelos_subido_por_id` |
| `vuelos.metodo_umbral` | `VARCHAR(20)` |
| `vuelos.mapeo_bandas` | JSONB |
| `diagnosticos.motor_version` | `VARCHAR(20)` |

- **Backfill:** `subido_por_id` con el dueño del lote; `metodo_umbral = 'fijo'` y `mapeo_bandas` según el sensor en los vuelos completados; `motor_version = '1.0.0'`.
- **Captura:** `subido_por_id` en los 3 puntos que crean un `Vuelo`; el worker completa `metodo_umbral` y `mapeo_bandas`; `MOTOR_VERSION` (`app/diagnostico/reglas.py`, 1.3.0 en el corte) se graba en cada diagnóstico.
- **API:** `VueloListItem` suma `archivo_original`, `subido_por`, `metodo_umbral` y `mapeo_bandas`.
- **Dónde se ve al corte:**
  - en el PDF ejecutivo, sección de trazabilidad (`app/reportes/templates/reporte_ejecutivo.html`: subido por, mapeo de bandas, versión del motor e índices usados);
  - en la línea de metadata del diagnóstico.

El 27 de octubre, dentro de los ajustes de diseño (HU-R4-13, PR #119), se quitó de la pantalla de resultados el bloque desplegable "Trazabilidad del análisis". Los datos se siguen guardando y devolviendo por la API. Por decisión del equipo, la historia se considera completa con la trazabilidad en la API y en el PDF.

**Errores corregidos:** `Vuelo.subido_por` devolvía `None` porque `Usuario.id` está mapeado como `str` (`UUID(as_uuid=False)`) y `subido_por_id` como `uuid.UUID`. Se tipó como `as_uuid=False`; el mismo desajuste en `Lote.usuario_id` se corrigió en [`61ba7ad`][61ba7ad].

**Pruebas.** 1 test en `tests/test_diagnostico_api.py` (en CI), 1 en `tests/test_cultivos.py` (fuera del CI) y `test_lote_usuario_carga_via_selectinload` en `tests/test_lotes.py` (en CI).

#### Listado multi-lote (HU-R4-03)

**Qué se implementó.** `GET /api/v1/lotes` filtra y pagina en el backend y trae el último vuelo de cada lote en la misma consulta, lo que elimina las N consultas por lote del frontend ([`38b475f`][38b475f], PR #53, 30 de septiembre).

- **Parámetros:** `q` (nombre), `cultivo`, `campana` (año de siembra del cultivo actual), `estado` (del último análisis), `page` (≥ 1) y `page_size` (1 a 100, 20 por defecto).
- **Respuesta:** `LoteListResponse` suma `page` y `page_size`; `LoteResponse` suma `ultimo_vuelo_fecha` y `ultimo_vuelo_estado`. `app/lotes/service.py::listar_lotes` resuelve el último vuelo y el cultivo actual con `DISTINCT ON`. Sin migración.
- **Frontend:** `Lotes.jsx` con buscador (espera de 350 ms), filtros de cultivo, campaña y estado, y paginación. El rediseño del 27 de octubre (PR #119) reemplazó la foto de las tarjetas por un ícono y quitó el estado de la tarjeta; los filtros se mantienen.

**Hallazgo:** SQLAlchemy 2.1 marca como obsoleto pasar una expresión a `.distinct()` en `listar_lotes` (warning, según la bitácora).

**Pruebas.** `tests/test_lotes.py`, 28 tests en CI (7 nuevos en R4).

#### Línea de tiempo del lote (HU-R4-04)

**Qué se implementó.** El detalle del lote muestra los vuelos en un calendario mensual con la lista de vuelos del día, y la vista de resultados suma un calendario lateral para ubicar el vuelo actual y elegir otro para comparar ([`d080951`][d080951], PR #52, 30 de septiembre).

- `CalendarioMensual.jsx`: grilla mensual con navegación por mes y año, días con vuelos y leyenda.
- `VuelosCalendario.jsx`: calendario de solo lectura con todos los vuelos del lote; desde el PR #122 cada vuelo completado abre su resumen (HU-R4-07).
- `DetalleLote.jsx`: desde el PR #119 los vuelos se listan en una tabla (fecha, sensor, estadio, estado y acciones) con selector lista/calendario; desde el PR #127 ([`f794f80`][f794f80]) los vuelos van primero y la evolución del NDVI se muestra en tarjetas.
- `frontend/src/utils/fechas.js::fechaVuelo()` corrige que la fecha del vuelo se mostraba un día antes en UTC-3 ([`d31d4ff`][d31d4ff]).

**Cambio de estado respecto del provisional.** El provisional la evaluaba como Parcial contra RFGL-03 y el objetivo 1, que piden relacionar vuelos, análisis y diagnósticos como eventos. Este documento la evalúa contra el enunciado de la presentación ("Todos los vuelos ordenados en el tiempo. Un calendario de vuelos."), que el código cumple. El cambio a Completa **se debe al criterio de evaluación, no a un cambio de código** en la línea de tiempo. La brecha con RFGL-03 (análisis por índice y diagnósticos como eventos de la línea de tiempo) queda en deuda (sección 7). En Trello la tarjeta figuraba "en revisión" el 3 de noviembre (bitácora, PR #163); el código está mergeado y se toma el código.

**Pruebas.** `frontend/src/utils/fechas.test.js` (1). Sin tests de los componentes de calendario.

#### Investigación de costos de fitosanitarios (HU-R4-05)

**Qué se implementó.**
- **Precios de referencia:** relevamiento de los 21 productos del catálogo, cargado por la migración `0023_crear_tabla_precios_productos.py` ([`fb945af`][fb945af], PR #89, 13 de octubre).
- **Planilla:** `docs/catalogo_productos_fitosanitarios.xlsx`, versionada el 15 de octubre ([`31db69a`][31db69a], [`db0ef45`][db0ef45], PR #94) y reemplazada el 26 de octubre por la planilla completa de 59 filas con dosis y precio por marca ([`1a82031`][1a82031], PR #112).
- **Precios en una base nueva:** la migración 0029 deja el precio de referencia de los 21 productos originales ([`ec25a5d`][ec25a5d]).

**Detalle técnico.**
- Tabla `precios_productos`: `producto_id` (FK, `CASCADE`), `precio_usd`, `unidad` (`VARCHAR(10)`), `fuente`, `fecha` y `tipo` (`"referencia"` o `"usuario"`), con índices `ix_precios_productos_producto_id` e `ix_precios_productos_tipo_fecha`.
- Fuentes por fila en la 0023: CASAFE Lista 2026-S1, CIAFA 2026-T3, INTA EEA Sáenz Peña, INTA EEA Reconquista, INTA NEA y listas de fabricantes.
- El importador del 26 de octubre aplicó para los 21 productos el precio de la planilla. Pisó 5 precios con fuente CASAFE o INTA (Glifosato 3,50 → 5,50, 2,4-D 3,80 → 4,95, Atrazina 5,20 → 6,50, Cletodim 15 → 6,90, Imazetapir 22 → 5,36), y los nuevos quedan con la fuente `camposimple.com.ar, 10/2026`, que es una tienda y no una fuente oficial (bitácora). Atrazina pasó a precio por kg, la unidad de su dosis.
- **Decisiones** (bitácora): el precio cargado por el usuario con menos de 90 días manda sobre el de referencia; precios por L o kg, no por envase.

**Entregable.** El entregable es la planilla `docs/catalogo_productos_fitosanitarios.xlsx` más las migraciones 0023 y 0029. El documento `docs/precios_fitosanitarios_referencia.md` que citan la bitácora y el docstring de la 0023 **no existe** en el repositorio al corte.

#### Dosis y marcas de referencia de fitosanitarios (HU-R4-14)

**Qué se implementó.** Dosis de referencia, unidad y confiabilidad de la dosis para los productos del catálogo, y marcas con su propia dosis. Con eso funcionan el ahorro en litros y las alternativas de producto. Se completó entre el 26 de octubre y el 3 de noviembre, después de la fecha nominal del sprint.

- **Migración `0026_confiabilidad_dosis_productos.py`** ([`dcfc9a3`][dcfc9a3], PR #112): columna `productos_fitosanitarios.confiabilidad_dosis` (`marbete`, `web` o NULL), el origen de la dosis.
- **Importador** `app/catalogo/importador.py`: lee el Excel, actualiza dosis, unidad, confiabilidad y precio de los productos del motor emparejados por nombre; sin `--aplicar` solo simula y es idempotente. Dependencia nueva `openpyxl==3.1.5`.
- **Migración `0029_cargar_catalogo_fitosanitarios.py`** ([`ec25a5d`][ec25a5d], PR #165, 3 de noviembre): deja la misma carga hecha en cualquier base, porque la app de escritorio no corre el importador. Carga 30 productos con `dosis_referencia` (los 21 originales y 9 herbicidas nuevos), 21 precios de referencia y 59 presentaciones. Es idempotente; `downgrade` a 0028 y `upgrade` de nuevo deja el mismo resultado (bitácora).
- **Decisión** (bitácora): migración con los datos escritos en el código y no el importador dentro del instalador, para no empaquetar `openpyxl` ni el Excel. Actualizar el catálogo exige otra migración o el importador manual.

**Hallazgo.** 19 de las 21 dosis de los productos originales tienen confiabilidad `web` ("habitual según web") y no de marbete. La bitácora recomienda contrastarlas antes de presentarlas como recomendación firme.

**Errores corregidos.**
- `InvalidRequestError: ... expression 'Usuario' failed to locate a name` al usar el modelo fuera de FastAPI: el importador registra `app.auth.models` y `app.lotes.models`.
- `asyncpg.exceptions.DataError: invalid input for query argument $4: '2026-10-01'` en la 0029: las fechas se pasan con `date.fromisoformat(...)`.

**Pruebas.** `tests/test_catalogo_importador.py` (23, fuera del CI) y `tests/test_catalogo_migracion.py` (4, en el job `test-api`).

#### Seguridad y mantenimiento (HU-R4-16)

El provisional documentaba este trabajo como "tarea e" sin historia; la presentación lo asigna a HU-R4-16.

- **Workflow de seguridad** ([`697ca21`][697ca21], [`4f99d2f`][4f99d2f], [`45b03d1`][45b03d1], [`9af8061`][9af8061], [`d648213`][d648213], PR #20; [`b925724`][b925724], [`ed96d29`][ed96d29], PR #48): `.github/workflows/security.yml` con Gitleaks, Semgrep, Bandit, pip-audit, npm audit y Trivy (detalle en la sección 6). Actions fijadas a SHA y `JWT_SECRET_KEY` declarado solo en los jobs que lo usan. Semgrep pasó de 25 hallazgos a 0. En el historial quedan dos tokens de ejemplo ya vencidos de junio; se decidió no reescribirlo ([`7faf3c5`][7faf3c5]).
- **Dependabot:** `.github/dependabot.yml` para pip, npm, docker y github-actions. Desde el 19 de noviembre ([`6678ef6`][6678ef6], PR #185) abre un PR por semana y por ecosistema: menores y parches agrupados, mayores de a una, y la versión de Python de la imagen ignorada. Antes de agruparlo se revisaron 16 PRs abiertos: 15 se mergearon y se cerró el de `python:3.15-slim` (#173), que no compila porque shapely y pydantic-core no tienen ruedas para 3.15.
- **Correcciones por hallazgos de SCA y SAST posteriores al provisional:**
  - `python-jose` reemplazado por `PyJWT==2.15.1` ([`d163ea2`][d163ea2], PR #128, 28 de octubre): `python-jose` (PYSEC-2026-4298) y `ecdsa` (PYSEC-2026-1325) no tenían versión corregida. El algoritmo sigue siendo `HS256`, así que los tokens emitidos siguen siendo válidos;
  - `pillow` 13.0.0 ([`aaf97f8`][aaf97f8], PR #125);
  - `follow-redirects` 1.16.2 ([`8a01d80`][8a01d80], PR #121);
  - `INSERT` parametrizado en la migración 0025 por Semgrep ([`e114889`][e114889], PR #124).
- **Imagen de MinIO** ([`7e7182d`][7e7182d], PR #46): `cgr.dev/chainguard/minio:latest`, porque `minio/minio` se dio de baja de Docker Hub el 11 de septiembre.
- **Actualizaciones de dependencias:** React 19, react-leaflet 5 y react-router 7 ([`e5054d3`][e5054d3], PR #50). Bumps coordinados de SQLAlchemy 2.1 con `greenlet`, geoalchemy2, bcrypt 5 sin `passlib`, GDAL 3.13.3 con rasterio, Vite 8, y `python-jose` y `pillow` (PRs #76 a #81). Tandas de Dependabot de octubre y noviembre (PRs #29 a #72, #85, #97 a #102, #143 a #149, #168 a #183). Versiones al corte en la sección 6.

**Pruebas.** `test_storage_importable.py` (1, en CI) protege la importación de `app.core.storage` en la imagen del worker después del cambio a PyJWT ([`d329602`][d329602], PR #161).

#### Otros cambios del sprint

- **Bitácora de R1** ([`84ccbf6`][84ccbf6], directo a `main`, 30 de septiembre).
- **Etiqueta "Procesando imagen"** del widget "Vista geoespacial" corregida ([`8b5f698`][8b5f698], PR #50).

### Estado de las historias

| Historia | Estado | Evidencia |
|---|---|---|
| HU-R4-01 — Aislamiento multi-tenencia (3) | Parcial | IDOR corregido y `tests/test_multi_tenant_indices.py` ([`537f671`][537f671], PR #49). Faltan el aislamiento de los precios cargados por usuario (`PrecioProducto` sin `usuario_id`) y la suite de aislamiento en CI. La presentación la declara completa |
| HU-R4-02 — Trazabilidad completa del análisis (3) | Completa | Migración 0021 y trazabilidad en la API y en el PDF (`reporte_ejecutivo.html`) ([`bc59329`][bc59329], [`61ba7ad`][61ba7ad], PR #51). El panel se quitó de la pantalla de resultados en el PR #119; por decisión del equipo se considera completa |
| HU-R4-03 — Listado multi-lote (2) | Completa | `GET /lotes` con filtros y paginación, `Lotes.jsx` ([`38b475f`][38b475f], PR #53) |
| HU-R4-04 — Línea de tiempo del lote (5) | Completa | `CalendarioMensual.jsx`, `VuelosCalendario.jsx` ([`d080951`][d080951], PR #52). Pasa de Parcial a Completa por evaluarse contra el enunciado de la presentación, no por un cambio de código; la brecha con RFGL-03 queda en deuda |
| HU-R4-05 — Investigación de costos (3) | Completa | `docs/catalogo_productos_fitosanitarios.xlsx` ([`31db69a`][31db69a], [`1a82031`][1a82031]) y migraciones 0023 ([`fb945af`][fb945af]) y 0029 ([`ec25a5d`][ec25a5d]). `docs/precios_fitosanitarios_referencia.md` no existe |
| HU-R4-14 — Dosis y marcas de referencia (3) | Completa | Migraciones 0026 ([`dcfc9a3`][dcfc9a3]) y 0029 ([`ec25a5d`][ec25a5d]): 30 productos con dosis, unidad y confiabilidad |
| HU-R4-16 — Seguridad y mantenimiento (5) | Completa | `security.yml` y Dependabot ([`697ca21`][697ca21], [`6678ef6`][6678ef6]); CI y Security en verde en el corte. 5 jobs no bloqueantes quedan en deuda |

Totales del sprint: 6 de 7 historias completas y 1 parcial (HU-R4-01); 21 de 24 puntos completos.

### Resultado

El sprint dejó aislados por usuario los lotes, vuelos e índices y sumó controles de seguridad que corren en cada push y que llevaron a reemplazar `python-jose` y a actualizar varias dependencias. Cada análisis registra su origen, y el listado de lotes dejó de hacer una consulta por lote. Precios, dosis y marcas del catálogo quedaron cargados por migración en cualquier base, aunque la carga completa de dosis y marcas se terminó el 3 de noviembre, fuera de la fecha nominal del sprint. Quedan abiertos los precios compartidos entre usuarios y los tests de aislamiento fuera del CI.

---

## 3. Sprint 15 — Comparación, perfil y catálogo

| Sprint | Título | Fechas | Historias | RF/RNF |
|---|---|---|---|---|
| S15 | Comparación, perfil y catálogo | 29 sep – 6 oct 2026 | HU-R4-07, 08, 09, 10, 13, 17 | RFGL-03, RFGL-04, RFSA-01, RFDR-01 |

### Objetivo

Comparar el estado del lote entre dos momentos (vuelo contra vuelo y capas por fecha), dar a cada vuelo una ficha rápida, darle al usuario un perfil propio que se refleje en sus PDF, terminar los detalles de la interfaz y convertir el catálogo de fitosanitarios en recomendaciones con marca y costo por hectárea.

### Tareas realizadas

#### Resumen por vuelo en el historial (HU-R4-07)

**Qué se implementó.** En el historial de vuelos (`VuelosCalendario.jsx`), cada vuelo completado tiene un botón "Resumen" que despliega `ResumenVuelo.jsx` y `useResumenVuelo.js` ([`4c3d3cf`][4c3d3cf], 8 de octubre, mergeado el 27 de octubre en el PR #122). El provisional la registraba como "No implementada" porque la rama no estaba mergeada al corte del 14 de octubre.

- Barra de rango del índice (mínimo, promedio y máximo) y una nota informativa sobre qué índice correspondería según el estadio (V1 a V3 → SAVI; NDVI > 0,75 → GNDVI; resto → NDVI).
- Porcentaje de superficie por severidad (crítica, moderada, leve, normal, vigorosa), sumando `area_ha` de las zonas del diagnóstico.
- Enlaces de descarga a prescripción (Shapefile), orden de trabajo e informe PDF, deshabilitados cuando no corresponden.
- **Decisiones** (bitácora): sin endpoint nuevo (reutiliza `GET .../diagnostico` y los de exportación), diagnóstico pedido solo al desplegar el resumen de ese vuelo, y gráficos en CSS sin librería nueva.

**Relacionado:** el gráfico de evolución del NDVI por lote (`GraficoEvolucionNdvi.jsx`, `useEvolucionNdvi.js`, [`af883e3`][af883e3], 8 de octubre), que el provisional registraba como rama sin merge, entró en el mismo PR #122. Desde [`eb85e71`][eb85e71] (23 de octubre) superpone el NDVI esperado para el estadio de cada vuelo y explica la diferencia (`frontend/src/utils/evolucionNdvi.js::explicarEvolucion`, 5 tests).

#### Superposición de capas por fecha (HU-R4-08)

**Qué se implementó.** En el Dashboard, con al menos 2 vuelos completados, "Comparar capas" abre un mapa que superpone los resultados de varios vuelos del lote, con visibilidad y opacidad por capa, y un panel con la diferencia entre el vuelo más antiguo y el más reciente visibles ([`f13dcab`][f13dcab], PR #90; [`60de671`][60de671], PR #93).

- `MapaCapas.jsx` reclasifica cada zona con `UMBRALES_FIJOS` (NDVI 0,20 / 0,40 / 0,70; GNDVI 0,25 / 0,45 / 0,60; NDRE 0,10 / 0,20 / 0,35; SAVI 0,15 / 0,30 / 0,50; ExG 0,05 / 0,15 / 0,30), en lugar de usar la `clase` del GeoJSON, que puede venir de un umbral adaptativo. Así la misma zona recibe el mismo color en todos los vuelos.
- Sin endpoint nuevo.
- **Hallazgo:** `UMBRALES_FIJOS` duplica `workers/gis/clasificacion.py::_UMBRALES_POR_INDICE`; hoy coinciden.

#### Comparar dos vuelos del mismo lote (HU-R4-09)

**Qué se implementó.** Comparación de un vuelo contra otro del mismo lote, en cuatro entregas:

| Fecha | Commit / PR | Qué agregó |
|---|---|---|
| 30 sep | [`d080951`][d080951], PR #52 | Doble panel: "Seleccionar para comparar" desde el calendario lateral; cada panel con su mapa, zonas y diagnóstico |
| 14 oct | [`278845f`][278845f], PR #91 | `ResumenDiferenciaVuelos.jsx` y `utils/statsZonas.js`: diferencia del índice promedio ponderado por área y del área por clase, siempre como B − A |
| 15 oct | [`80e3413`][80e3413], PR #95 | "Cambio por zona", tendencia del índice contra el NDVI esperado (`TendenciaIndice.jsx`, migración 0025) y mapa del lote "Lado a lado" y "Cortina" (`MapaComparacionLote.jsx`), con un selector único de tres vistas |
| 27 oct | [`5c06e3f`][5c06e3f], PR #123 | Comparar vuelos desde el detalle del lote (`ModalCompararVuelos.jsx`, `SelectorVuelo.jsx`) y rediseño de la comparación |

**Cómo es "Cambio por zona".** `CambioPorZona.jsx` es una **grilla de tarjetas, no un mapa**. Cada tarjeta representa una zona del vuelo A y muestra:
- una mini silueta SVG de 150 × 120 px del lote con esa zona resaltada en rojo o verde;
- la etiqueta "▼ Empeoró", "No empeoró" o "Sin comparar";
- el cambio de NDVI en texto, la superficie y el diagnóstico de esa zona en el vuelo A.

La zona equivalente del vuelo B se busca por posición, porque cada análisis vectoriza sus zonas por separado y no comparten id: se calcula el centroide de la zona de A y se busca el polígono de B que lo contiene (`frontend/src/utils/cambioZonas.js::emparejarZonas`). Diferencias de NDVI menores a 0,01 no se marcan como empeoramiento (`UMBRAL_NDVI`), para no confundir el ruido de la vectorización con un cambio real.

**¿Cubre el faltante del provisional?** En parte. El provisional pedía un mapa de diferencia: el vuelo B menos el vuelo A remuestreados a una grilla común y vectorizados en zonas "mejoró / empeoró / igual". "Cambio por zona" resuelve la pregunta "¿la aplicación tuvo efecto?" zona por zona y con su ubicación en el lote, que es lo que pide la presentación ("Antes y después, lado a lado"). Pero no es el mapa de diferencia:
- no hay remuestreo ni cálculo por píxel;
- se muestra en tarjetas y no en un mapa continuo;
- solo distingue empeoró y no empeoró.

La bitácora del 15 de octubre deja expresamente fuera de alcance el "Mapa de cambio" raster. Como la tarjeta lo marcaba opcional, la historia se considera completa y el mapa de diferencia raster queda en funcionalidades pendientes.

**Decisiones** (bitácora): cálculo en el navegador sin endpoint nuevo; promedio ponderado por área; mini mapas en SVG en lugar de un `MapContainer` de Leaflet por zona; base y actual según la fecha real de cada vuelo.

**Pruebas.** `frontend/src/utils/cambioZonas.test.js` (8) y `estadios.test.js` (4), en CI desde que el job `build-frontend` corre `npm test`.

#### Personalización del perfil (HU-R4-10)

**Qué se implementó.** Página `/perfil` para editar datos personales y de empresa, cambiar la contraseña y subir avatar y logo. El logo entra en el reporte ejecutivo y en la orden de trabajo ([`dcc1811`][dcc1811], PR #75, 8 de octubre).

- **Base de datos** (migración `0022_personalizacion_perfil_usuario.py`): en `usuarios`, `avatar_key`, `descripcion`, `cuit` (`VARCHAR(13)`), `telefono_contacto`, `matricula_aplicador`, `nombre_empresa` y `logo_empresa_key`, todas nullable.
- **API** (solo el propio usuario):
  - `PUT /auth/me` (CUIT validado, 422 si es inválido);
  - `POST /auth/me/password` (400 si la contraseña actual no coincide, 204 si se cambia);
  - `POST /auth/me/avatar` y `/auth/me/logo-empresa` (extensión y *magic bytes* JPG o PNG en `app/auth/validator.py`).
- **Documentos:** `app.auth.service.resolver_datos_aplicador()` pasa el logo en base64 a los dos generadores de PDF.
- Desde el PR #151 la tarjeta "Copia de seguridad" vive en Mi perfil (sección 5).

**Pruebas.** Sin tests automatizados de los endpoints `/auth/me` de perfil (`tests/test_auth.py` mantiene 15). Verificación manual registrada en la bitácora.

#### Ajustes de diseño pendientes (HU-R4-13)

**Qué se implementó.** Cambios de interfaz registrados uno por fila en la bitácora ("Ajustes de diseño (HU-R4-13)"), hechos el 26 y el 27 de octubre ([`872a481`][872a481], [`1de4f91`][1de4f91], PRs #116 y #118; [`8c9ffd4`][8c9ffd4], PR #119; [`92cb9db`][92cb9db], PR #120). Entre ellos:

- avisos de confirmación al guardar (`AvisosProvider.jsx`) e ícono de advertencia en las ventanas de eliminar (`IconoAdvertencia.jsx`);
- logo de la barra lateral que lleva al Dashboard y barra lateral plegable (`useSidebarPlegada.js`);
- tarjetas de lotes con ícono y apertura del detalle, encabezados con el mismo formato en las cuatro pantallas del panel y miga de pan sin "Dashboard";
- resultados del vuelo en vista dividida (mapa a la izquierda y panel con scroll a la derecha), leyenda fija bajo el mapa y mapa ampliable (`ModalMapaAmpliado.jsx`);
- pestaña "Ahorro comparativo" junto a Zonas y Diagnóstico (`TablaAhorroVuelo.jsx`), con la superficie tratada contra la del lote;
- botón "Generar orden de trabajo" visible en las tres pestañas, con ícono de PDF;
- edición de lotes (nombre y tipo de suelo) y de vuelos (fecha, estadio y cultivo, con `PUT /lotes/{id}/vuelos/{id}` nuevo y `tests/test_vuelos_editar.py`, 9 tests).

**Alcance** (bitácora, 27 de octubre): como el sistema se entrega como aplicación de escritorio, se sacó de la tarjeta el criterio "Revisar vista en tablet/celular". La revisión de pantallas se hizo solo en escritorio.

**Decisión de diseño con efecto en otra historia:** se quitó de la pantalla de resultados el bloque "Trazabilidad del análisis" (ver HU-R4-02).

#### Catálogo de fitosanitarios (HU-R4-17)

**Qué se implementó.** El catálogo pasa de un producto por principio activo a productos con sus marcas, dosis y precios, y la recomendación muestra alternativas con marca y costo por hectárea. Se hizo en cuatro tandas el 26 de octubre y se cerró el 3 de noviembre:

| Tanda | Commit / PR | Contenido |
|---|---|---|
| 1 | [`dcfc9a3`][dcfc9a3], PR #112 | Importador desde Excel y confiabilidad de la dosis (compartido con HU-R4-14) |
| 2 | [`baa2fd4`][baa2fd4], PR #113 | Migración `0027_presentaciones_productos.py`: tabla `presentaciones_productos` (marca, concentración y variante con dosis, precio y cultivos propios), clave única `(producto, marca, concentración, variante)` |
| 3 | [`f0e7645`][f0e7645], PR #115 | `app/diagnostico/service.py::armar_catalogo_productos()`: solo se sugieren productos aptos para el cultivo del vuelo. Si ninguno es apto, la causa queda sin producto. Carga de 9 activos herbicidas nuevos (59 de 59 filas del Excel) |
| 4 | [`c77f5af`][c77f5af], PR #116 | `armar_alternativas_marca()`: por activo, las marcas aptas con dosis, precio y `costo_por_ha_usd`, ordenadas de menor a mayor costo, en la clave nueva `alternativas_marca` de la respuesta (`productos_sugeridos` no cambia) |
| Cierre | [`1444295`][1444295], PR #164 | La orden de trabajo agrega las columnas "Activo" y "Producto" (marca recomendada). Dosis, volúmenes, totales y ahorro salen de la marca recomendada, y se listan hasta 3 alternativas por unidad (`MAX_ALTERNATIVAS`), agrupadas cuando se repiten |

La presentación agrega a la planilla observaciones del marbete, restricciones ambientales, instrucciones de seguridad, fecha, fuente y nota del precio, y confiabilidad. En la base, las restricciones y la seguridad siguen viviendo en el activo (0018, 0019 y 0029 para los 9 nuevos) y no en las marcas.

**Decisiones** (bitácora):
- **Entre activos distintos no se ordena por costo por hectárea:** dejaba primero a Cletodim y Haloxyfop, graminicidas selectivos, para cualquier interferencia de vegetación.
- **Entre marcas del mismo activo sí se ordena por costo.**
- **En la orden de trabajo:** desde el PR #164, el activo y la marca recomendados son los de menor costo por hectárea entre los aptos. No se pondera eficacia ni registro del producto; la bitácora lo deja para revisar con el equipo agronómico.
- **Barbecho:** queda fuera de esta release (decisión del equipo del 3 de noviembre). Las marcas de barbecho del Excel no se sugieren porque todo análisis exige un cultivo.

**Pruebas.** `tests/test_catalogo_productos_cultivo.py` (16) y `tests/test_orden_trabajo.py` (28), fuera del CI.

#### Otros cambios del sprint

- **Cierre de R3 mergeado en R4** ([`f01c301`][f01c301], PR #82): mapa por clase en Diagnóstico y en el PDF, "Acción recomendada" como sección propia y corrección de los análisis que quedaban en "Cargando..." en el Dashboard.
- **Documentación formal de R1 a R3** en `docs/releases/` y plantilla `_TEMPLATE-release.md` ([`06afb2a`][06afb2a], [`93451e0`][93451e0], PR #73; [`0928e47`][0928e47], [`463f2da`][463f2da], PR #74).
- **Despliegue web (continuación de la HU-R4-06 original):** merge del PR #54 el 8 de octubre ([`507a2bd`][507a2bd]). El detalle y lo que pasó con ese enfoque están en la sección 5.

### Estado de las historias

| Historia | Estado | Evidencia |
|---|---|---|
| HU-R4-07 — Resumen por vuelo (3) | Completa | `ResumenVuelo.jsx`, `useResumenVuelo.js` ([`4c3d3cf`][4c3d3cf], PR #122) |
| HU-R4-08 — Superposición de capas por fecha (5) | Completa | `MapaCapas.jsx` ([`f13dcab`][f13dcab], PR #90; [`60de671`][60de671], PR #93) |
| HU-R4-09 — Comparar dos vuelos del mismo lote (8) | Completa | Doble panel ([`d080951`][d080951]), diferencias ([`278845f`][278845f]), cambio por zona y vistas del mapa ([`80e3413`][80e3413]) y comparación desde el lote ([`5c06e3f`][5c06e3f]). El mapa de diferencia raster (opcional) no se hizo |
| HU-R4-10 — Personalización del perfil (3) | Completa | Migración 0022, `/auth/me/*`, `PerfilUsuario.jsx`, logo en los PDF ([`dcc1811`][dcc1811], PR #75). Sin tests automatizados |
| HU-R4-13 — Ajustes de diseño (5) | Completa | Tabla de ajustes de la bitácora; PRs #116, #118, #119 y #120 |
| HU-R4-17 — Catálogo de fitosanitarios (5) | Completa | Migración 0027, importador, filtro por cultivo, alternativas con marca ([`baa2fd4`][baa2fd4], [`f0e7645`][f0e7645], [`c77f5af`][c77f5af]) y marca en la orden de trabajo ([`1444295`][1444295]) |

Totales del sprint: 6 de 6 historias completas; 29 de 29 puntos.

### Resultado

La comparación entre momentos del lote quedó resuelta en el navegador: dos vuelos lado a lado o en cortina, las diferencias de índice y superficie, y el cambio zona por zona con su diagnóstico. Cada vuelo tiene su ficha rápida y el usuario ve su logo en los documentos. El catálogo recomienda marcas aptas para el cultivo con su costo por hectárea, y la orden de trabajo usa la marca más barata. Gran parte de este trabajo se mergeó entre el 14 y el 27 de octubre, después de la fecha nominal del sprint. Queda pendiente el mapa de diferencia raster.

---

## 4. Sprint 16 — Ahorro, preferencias y diagnóstico

| Sprint | Título | Fechas | Historias | RF/RNF |
|---|---|---|---|---|
| S16 | Ahorro, preferencias y diagnóstico | 6–13 oct 2026 | HU-R4-11, 12, 15 | RFGL-05, RFDR-01, RFDR-03, RFDR-04 |

### Objetivo

Calcular cuánto producto y dinero ahorra la aplicación selectiva frente a la uniforme, por vuelo y entre campañas; guardar valores por defecto para cada análisis; y hacer que el diagnóstico compare contra lo esperado para el estadio y ofrezca probabilidades por causa, como base para validarlo a campo.

### Tareas realizadas

#### Ahorro comparativo entre campañas y de aplicación (HU-R4-11)

**Qué se implementó.** Módulo `app/ahorro/` que compara la cantidad y el costo de tratar solo las unidades de manejo con problema ("variable") contra tratar todo el lote ("uniforme"), por vuelo y acumulado por campaña, con opción de comparar dos campañas ([`cbf1f69`][cbf1f69], PR #93, 14 de octubre).

- **Cálculo** (`app/ahorro/calculo.py`, puro):
  - `calcular_ahorro_vuelo()` toma la salida de `generar_orden_trabajo()`. La cantidad variable es el `volumen_total` de la orden, la uniforme es `area_total_lote_ha × dosis`, y el ahorro es la diferencia, en porcentaje y en dinero.
  - `acumular_ahorro()` suma los vuelos de una campaña por producto y marca `sin_dosis_referencia` y `sin_precio` sin descartar lo ya calculado.
- **Precios:** `app/diagnostico/precios.py::resolver_precio` prioriza el precio `"usuario"` con menos de 90 días. Desde el PR #164 el siguiente es el precio de la marca recomendada (`precio_tipo = "marca"`) y, si no hay marca, el de referencia.
- **Dosis:** desde el PR #164 variable y uniforme usan la dosis de la marca recomendada, para que sean comparables.
- **Ahorro estimado:** si alguna zona o vuelo es provisorio (motor v1.3.0), el resultado se marca `estimado` y la pantalla lo avisa.

| Endpoint | Validación | Errores |
|---|---|---|
| `GET /api/v1/lotes/{lote_id}/vuelos/{vuelo_id}/ahorro` | Lote del usuario y vuelo dentro del lote | 404 |
| `GET /api/v1/lotes/{lote_id}/ahorro-comparativo?cultivo_a=&cultivo_b=` | Lote del usuario y campañas del lote | 409 si el lote no tiene área; 404 si una campaña no existe |
| `GET` y `POST /api/v1/productos-fitosanitarios/{producto_id}/precios` | Global; `POST` siempre crea tipo `"usuario"`, con `precio_usd > 0` y fecha no futura | 201, 404, 422 |

- **Frontend:**
  - página `/lotes/:loteId/ahorro` (`AhorroComparativo.jsx`), con selector de una o dos campañas y `ModalCargarPrecio.jsx`;
  - desde el PR #119, la pestaña "Ahorro comparativo" en los resultados del vuelo (`TablaAhorroVuelo.jsx`), que muestra superficie tratada contra superficie del lote (`area_tratada_ha`, `area_total_lote_ha`) y, por producto, cantidad, ahorro y ahorro en US$.

**Cambio respecto del provisional.** Al corte provisional el ahorro no daba cifras con datos reales porque ninguna migración cargaba `dosis_referencia`. Al corte final la 0029 carga dosis para los 30 productos ([`ec25a5d`][ec25a5d]) y la pantalla del vuelo muestra la diferencia de áreas que pide RFGL-05. Según la bitácora, con las dosis reales y Glifosato sobre 100 ha de lote y 10 ha tratadas, la cantidad uniforme es 222 L, la variable 22,2 L y el ahorro 90 %.

**Decisiones** (bitácora): variable contra uniforme es sobre el área tratada y no sobre la dosis; "campaña" equivale a `Cultivo`; no se persiste el ahorro y se recalcula como el diagnóstico; un precio faltante no anula el acumulado.

**Errores corregidos.**
- `acumular_ahorro()` descartaba el ahorro real de un vuelo cuando otro vuelo de la misma campaña no tenía precio. Lo detectó `test_acumular_ahorro_vuelo_sin_precio_marca_campana_parcial`.
- `test_ahorro_vuelo_variable_vs_uniforme` fijaba el precio de la 0023 y falló al importar el catálogo; ahora lee el precio de referencia de la base.

**Pruebas.** `tests/test_ahorro_calculo.py` (13) y `tests/test_ahorro_api.py` (14), fuera del CI.

**Discrepancia de nombres:** `ahorro_pesos` y `ahorro_total_pesos` contienen dólares; renombrarlos rompe el contrato y se decidió dejarlos así (bitácora, 3 de noviembre).

#### Preferencias de uso (HU-R4-12)

**Qué se implementó.** El usuario guarda un índice preferido, una unidad de área y un producto habitual desde la tarjeta "Preferencias de uso" de `/perfil` ([`682afd3`][682afd3], PR #92, 14 de octubre).

- **Base de datos** (migración `0024_preferencias_uso_usuario.py`): en `usuarios`, `indice_preferido` (enum `indiceenum`), `unidad_area_preferida` (enum nuevo `unidadareaenum`: `ha`, `acre`) y `producto_habitual_id` (FK a `productos_fitosanitarios`, `SET NULL`), todas nullable.
- **API:** reutiliza `PUT /api/v1/auth/me` (`exclude_unset`); 422 ante un enum inválido.
- **Uso:** el índice preferido preselecciona la pastilla de índice en `ModalCargaGeoTIFF.jsx` (línea 272) y en el Dashboard (`Dashboard.jsx`, línea 387). La unidad de área y el producto habitual se guardan y se editan en `PerfilUsuario.jsx`, pero ningún otro componente los consume. Por decisión del equipo, la historia se considera completa porque el valor por defecto de cada análisis es el índice. El uso de los otros dos valores queda en funcionalidades pendientes.
- **Backup:** el producto habitual viaja en el backup por nombre, tipo y causa, porque los ids del catálogo difieren entre instalaciones (bitácora).

**Pruebas.** Sin tests automatizados; verificación manual en la bitácora (24 migraciones contra una base nueva, `PUT /auth/me` válido e inválido, persistencia en el navegador).

#### Motor de diagnóstico: reglas por estadio y probabilidades por causa (HU-R4-15)

**Qué se implementó.** Revisión del motor de reglas para comparar contra lo esperado para el estadio fenológico, criterio técnico del agrónomo por zona (RFDR-04) y un motor probabilístico en paralelo. El trabajo es del 15 de octubre (curva esperada) y del 23 de octubre (motor), y se mergeó el 27 de octubre en el PR #122.

| Versión | Commit | Cambio |
|---|---|---|
| — | [`80e3413`][80e3413], PR #95 | Migración `0025_crear_tabla_ndvi_esperado.py`: tabla `ndvi_esperado_estadio` (cultivo, estadio normalizado, orden, NDVI esperado, mínimo y máximo) sembrada con una **curva genérica, no validada agronómicamente**, para soja, maíz, algodón y sorgo. Endpoint `GET /estadios-fenologicos/ndvi-esperado?cultivo=` |
| 1.1.0 | [`d31d4ff`][d31d4ff] | `reglas.py::ndvi_bajo()`: "bajo" es por debajo del `ndvi_min` del estadio, y sin curva se usa el corte fijo 0,50. La severidad toma la peor caída entre la del promedio del lote y la de lo esperado. Reglas nuevas R45 (patrón lineal → compactación o falla de siembra) y R80 (vigor bajo para el estadio sin causa puntual). Reorden de R60 y R10, y "focos aislados" = zonas ≤ 3 ha y ≤ 5 % del lote |
| 1.2.x | [`d31d4ff`][d31d4ff] | `engine.py::precisar_con_bayes()`: R80 adopta la causa del motor probabilístico si es clara (≥ 40 % y 15 puntos sobre la segunda) o da un diagnóstico diferencial "X o Y". Al corte del PR #164 el código estaba en 1.2.1 (bitácora) |
| — | [`cb48a5b`][cb48a5b], PR #118 | Firma de datos (`metadata.firma_datos`, `calcular_firma_datos()`): el diagnóstico guardado se recalcula solo al abrirse si cambió algo de lo que usa. Se quita el botón "Recalcular" de la pantalla y el endpoint de recálculo forzado se conserva |
| 1.3.0 | [`1444295`][1444295], PR #164 (3 de noviembre) | Con empate, `causa_indice` toma la causa más probable para que haya productos; la zona y su unidad de manejo llevan `provisorio: true` y la acción pide confirmar a campo antes de aplicar. Campos nuevos con valor por defecto, sin quitar ninguno |

- **Criterio técnico (RFDR-04):** tabla `revisiones_diagnostico` (migración `0028_crear_tabla_revisiones_diagnostico.py`, renumerada desde 0026 al mergear; única por `vuelo_id` y `zona_id`) y endpoints `PUT` y `DELETE /lotes/{id}/vuelos/{id}/diagnostico/zonas/{zona_id}/revision`.
  - El agrónomo acepta, modifica o rechaza cada zona (`RevisionZona.jsx`).
  - La revisión se adjunta al responder y no se guarda en el JSON del diagnóstico, así un recálculo no la borra.
  - Cada revisión guarda la evidencia cruda de la zona.
- **Motor probabilístico** (`app/diagnostico/bayes.py`, `BayesZona.jsx`): P(causa | evidencia) ∝ P(causa | fase) · Π P(evidencia | causa), sobre 12 causas y 5 evidencias discretas (desvío contra lo esperado, patrón, NDVI, NDRE y ExG).
  - Corre en paralelo a las reglas (`props.bayes` por zona).
  - Aprende de las revisiones con una actualización Dirichlet que usa la tabla experta como prior de 20 casos por causa (`PESO_PRIOR_EXPERTO`).
  - **Las tablas son un borrador experto sin validar por un agrónomo:** no hay casos confirmados a campo.
- **Guía de campo:** `ComoConfirmarCampo.jsx`, siempre visible, con los pasos para confirmar cada causa. El PDF suma un resumen ejecutivo ("En pocas palabras") y "Cómo confirmar en campo" por zona ([`eb85e71`][eb85e71]).

**Decisiones** (bitácora):
- Se usa `ndvi_min` y no `ndvi_esperado` como corte, para no disparar alertas con una curva genérica.
- R00 queda inalcanzable mientras `AREA_MINIMA_M2` sea 10.000 m² (`workers/gis/zonas.py`).
- Se aprende de las revisiones de todos los usuarios, porque la evidencia son solo valores numéricos y patrón.
- Aceptar una zona provisoria equivale a confirmarla como caso de entrenamiento de la causa más probable.

**Errores corregidos.**
- Los tests de revisiones dejaban filas en `revisiones_diagnostico` que contaminaban el entrenamiento del motor; ahora las borran en `teardown_module`.
- El suelo desnudo (R01) aparecía como "Sin problema detectado" en el resumen ejecutivo; se agrupa aparte.
- La fecha de vuelo se mostraba un día antes en resultados y calendarios.

**Pruebas.** `test_bayes.py` (15), `test_revisiones_api.py` (6), `test_firma_diagnostico.py` (3), `test_reporte_ejecutivo.py` (7) y `test_reporte_zona.py` (17) están fuera del CI. Sí corren en CI `test_diagnostico_engine.py` (30) y `test_diagnostico_api.py` (16).

En Trello la tarjeta figuraba "en revisión" el 3 de noviembre (bitácora, PR #163); el código está mergeado.

### Estado de las historias

| Historia | Estado | Evidencia |
|---|---|---|
| HU-R4-11 — Ahorro comparativo entre campañas y de aplicación (8) | Completa | `app/ahorro/`, `AhorroComparativo.jsx` ([`cbf1f69`][cbf1f69], PR #93), `TablaAhorroVuelo.jsx` (PR #119), dosis cargadas por la 0029 ([`ec25a5d`][ec25a5d]) y dosis y precio de la marca recomendada ([`1444295`][1444295]) |
| HU-R4-12 — Preferencias de uso (2) | Completa | Migración 0024 y tarjeta en `PerfilUsuario.jsx` ([`682afd3`][682afd3], PR #92). El índice preferido se usa como valor por defecto; la unidad de área y el producto habitual no tienen consumidor (pendiente) |
| HU-R4-15 — Motor de diagnóstico (8) | Completa | Migraciones 0025 y 0028, `reglas.py` (`MOTOR_VERSION` 1.3.0), `bayes.py`, `revisiones.py` ([`80e3413`][80e3413], [`d31d4ff`][d31d4ff], [`cb48a5b`][cb48a5b], [`1444295`][1444295]). Curva esperada y tablas probabilísticas sin validación agronómica |

Totales del sprint: 3 de 3 historias completas; 18 de 18 puntos.

### Resultado

El ahorro da cifras con datos reales, por vuelo y entre campañas, con la dosis y el precio de la marca recomendada, y avisa cuando es estimado. El motor compara contra lo esperado para el estadio, recibe el criterio del agrónomo y ofrece probabilidades por causa. Eso habilita validar el diagnóstico a campo, que es lo que falta: la curva de NDVI esperado y las tablas del motor probabilístico son borradores. El motor se mergeó el 27 de octubre y el v1.3.0 el 3 de noviembre, después de la fecha nominal del sprint.

---

## 5. Sprint 17 — Cambio de enfoque: de sitio web a aplicación de escritorio

| Sprint | Título | Fechas | Historias | RF/RNF |
|---|---|---|---|---|
| S17 | Cambio de enfoque: de sitio web a aplicación de escritorio | 13–20 oct 2026 (nominal; el trabajo en git va del 29 de octubre al 19 de noviembre) | HU-R4-06 (06.1, 06.2, 06.3) | RNF-19 |

### Objetivo

Que cualquier persona pueda instalar AgroNexo en su PC y usarlo sin servidor y sin depender de internet para el flujo principal: cargar el ortomosaico del dron, procesar los índices, ver el diagnóstico y generar la orden de trabajo y los PDF. El sprint registra por separado el cambio de enfoque de HU-R4-06, que nació como despliegue de un sitio web en un servidor.

### Tareas realizadas

#### Contexto que llevó a la decisión (HU-R4-06)

HU-R4-06 nació como "Despliegue en un entorno accesible y seguro" (8 pts, S13 → S14 según la tarjeta de Trello, dato del equipo). Su avance con ese enfoque:

- **Base de producción web, mergeada el 8 de octubre** ([`bc95528`][bc95528], [`9e87cdf`][9e87cdf], [`cbf1e4d`][cbf1e4d], [`465f6b8`][465f6b8]; merge [`507a2bd`][507a2bd], PR #54):
  - `docker-compose.prod.yml`, sin bind mounts, con migraciones al arrancar y `db`, `redis` y `minio` sin puertos publicados;
  - Nginx como único punto de entrada (`docker/Dockerfile.nginx`, `docker/nginx/nginx.conf`), con el bloque HTTPS comentado y Certbot con renovación cada 12 h;
  - `.env.prod.example`;
  - scripts `scripts/backup_postgres.sh` y `scripts/backup_minio.sh`;
  - la sección "Despliegue en producción" del `README.md`.
- **Servidor:** se intentó Oracle Cloud Free Tier (instancia ARM `VM.Standard.A1.Flex`, región `sa-vinhedo-1`) con reintentos automatizados del 17 al 30 de septiembre, sin conseguir capacidad ni con 4 OCPU/24 GB ni con 2 OCPU/12 GB. La elección de otro proveedor quedó pendiente (bitácora).
- **Criterios sin cumplir con ese enfoque:** HTTPS con dominio, firewall, backups programados en un host y prueba con un GeoTIFF de más de 500 MB en producción.

**Cronología del cambio de enfoque** (cada fecha con su fuente):

| Fecha | Hecho | Fuente |
|---|---|---|
| 27 oct | "HU-R4-06 pasa a la release siguiente y cambia de enfoque": el producto se va a empaquetar como aplicación de escritorio y los criterios de servidor dejan de aplicar | Bitácora `docs/release-v4.0.0.md` |
| 29 oct | D1: "El instalador de escritorio reemplaza el despliegue en servidor" | `docs/decisiones-app-escritorio.md` ([`dbf6a29`][dbf6a29], PR #134) |
| 2 nov | La tarjeta pasa de "Despliegue" a "Aplicación de escritorio y experiencia inicial", con el mismo número y 13 pts; el texto original queda en un comentario | Tarjeta de Trello (dato del equipo) |
| 3 nov | Asignación final: HU-R4-06 con 13 pts en el sprint 16 de la presentación | Bitácora, PR #163 ([`89787fc`][89787fc]) |

El cambio lo propusieron Denise Pujalte y Celeste Martín Rodich (dato del equipo). La nota del 27 de octubre decía que la historia pasaba a la release siguiente. Finalmente se implementó dentro de R4: el instalador está en el tag `v4.0.0`.

#### Registro de la decisión (ADR)

**Contexto.** El sistema estaba pensado como sitio web con un servidor. No se consiguió un servidor gratuito y la decisión de proveedor seguía pendiente. Los usuarios objetivo (productores y prestadores de servicio del NEA) trabajan con ortomosaicos de varios GB (la bitácora registra pruebas con uno de 4,98 GB) y muchas veces en el campo y sin conexión estable (dato del equipo).

**Opciones consideradas.**

| Opción | Fuente | Evaluación registrada |
|---|---|---|
| Servidor en la nube con HTTPS (enfoque original) | Bitácora, PR #54 | Implementada la base. Sin servidor por falta de capacidad en Oracle Cloud; proveedores pagos evaluados en una tabla de la bitácora sin decisión |
| Aplicación web progresiva con trabajo sin conexión | — | A confirmar: no hay registro en el repositorio de que se haya evaluado |
| Aplicación de escritorio instalable (camino B) | `docs/decisiones-app-escritorio.md`, spike del 29 de octubre | Spike en Windows 11 y Windows Sandbox: dependencias con ruedas de Windows, Postgres 16.15 + PostGIS 3.6.2 embebidos (28 migraciones en 4,3 s), Celery sobre Postgres con `--pool=solo` y WeasyPrint con GTK |

El documento de decisiones nombra un "estudio de opciones" (`opciones-app-escritorio.md`) y un informe del spike (`spike-escritorio/INFORME.md`) que están fuera del repositorio. Las opciones y criterios que no surgen de esas fuentes quedan a confirmar.

**Criterios.** Los que surgen de las fuentes:
- funcionar con y sin internet (D8);
- no depender de un servidor ni de su costo (D1);
- no subir GeoTIFF de varios GB por una conexión rural;
- simplicidad del lanzador para el equipo (D13: JavaScript frente a Rust);
- tamaño y madurez del empaquetado (D13).

**Decisión.** Aplicación de escritorio para Windows con Electron como ventana, lanzador e instalador (D1, 29 de octubre; D13, 30 de octubre). Docker se mantiene para desarrollo y CI.

**Consecuencias positivas.**
- El flujo principal funciona sin servidor y sin internet.
- No hay costo ni mantenimiento de servidor.
- Los datos del productor quedan en su equipo (`%APPDATA%\AgroNexo\`).
- Los ortomosaicos no se suben a ningún lado: se procesan donde están.

**Consecuencias negativas.**
- Solo Windows, y sin versión para celular ni tablet: el uso en el campo supone llevar una notebook con Windows.
- Instalador de 454.890.941 bytes (unos 455 MB), sin firma de código ("editor desconocido").
- Cada PC procesa con sus propios recursos: el worker procesa un análisis a la vez.
- Hay que actualizar Electron y las DLL de GTK por seguridad.
- Una instalación es de un solo usuario y no hay datos compartidos entre equipos (el backup es manual).
- Mientras no se haga el paso 2 de D3, conviven dos backends de almacenamiento (disco y MinIO).

#### Justificación principal: conectividad en el campo

Los prestadores de servicio que usan AgroNexo (aplicadores, contratistas y asesores que recorren lotes) trabajan muchas veces en zonas sin señal ni acceso a internet (dato del equipo). Una aplicación web les exige conexión para cada paso: subir el ortomosaico, esperar el procesamiento en el servidor y descargar el diagnóstico y los documentos. Con la aplicación instalada, ese flujo corre completo en el equipo:

- cargar el ortomosaico del dron;
- calcular los índices y las zonas;
- ver el diagnóstico;
- generar la orden de trabajo y los PDF.

Ninguno de esos pasos necesita una conexión ni un servidor. Además:
- los GeoTIFF de varios GB (el equipo probó uno de 4,98 GB) no tienen que transferirse por una conexión rural;
- no hay costo ni mantenimiento de un servidor;
- los datos del productor quedan en su propio equipo.

No se incluyen cifras de conectividad rural porque no hay una fuente verificable citada en el repositorio.

#### Qué funciona sin internet

Verificado sobre el código del corte. La detección de conexión combina `navigator.onLine` con una consulta a `https://www.gstatic.com/generate_204`: al abrir, cada 5 minutos con conexión y cada 30 segundos sin ella (`frontend/src/utils/conexion.js`, 10 tests; `hooks/useConexion.js`).

| Funcionalidad | Funciona sin internet | Evidencia |
|---|---|---|
| Arranque (Postgres + PostGIS, API y worker) | Sí | `escritorio/electron/src/postgres.js` ejecuta `initdb` local; la API escucha en `127.0.0.1`; la cola de Celery usa la propia base (`entorno.js`: `CELERY_BROKER_URL` = `sqla+postgresql`) |
| Inicio de sesión | Sí | Sesión automática contra la API local (`src/sesion.js`, D4); la bienvenida no usa internet (D10) |
| Carga y procesamiento de GeoTIFF de dron | Sí | Almacenamiento en disco (`STORAGE_BACKEND=disk`); worker local (`escritorio/worker.py`, `--pool=solo`) |
| Índices, zonas, diagnóstico, motor probabilístico y criterio técnico | Sí | Base y código locales (`app/diagnostico/`) |
| Reporte PDF y orden de trabajo | Sí | WeasyPrint con las DLL de GTK empaquetadas ([`acc95d6`][acc95d6], PR #139); las plantillas no cargan recursos remotos |
| Exportaciones y backup | Sí | Endpoints locales (`app/backup/`, PR #151) |
| Mapa base (OpenStreetMap y Esri) | No: fondo liso | Los 8 componentes de mapa usan `CapaBase.jsx`, que sin conexión no pide mosaicos y deja el color liso con los polígonos |
| Búsqueda de lugares (Nominatim) | No | `MapaDibujoLote.jsx`: la búsqueda por nombre avisa "Sin conexión"; las coordenadas `lat, lng` siguen funcionando |
| Imágenes Sentinel-2 (Earth Search) | No | Opción deshabilitada con aviso (`ModalCargaGeoTIFF.jsx`, línea 815); el backend consulta `earth-search.aws.element84.com` (`workers/gis/satelital_catalogo.py`) |
| Actualizaciones automáticas | No | Sin conexión fallan en silencio y se reintentan en el próximo arranque (`src/actualizaciones.js`) |
| Tipografías | Degradado | `frontend/index.html` carga Google Fonts; sin internet se usa la fuente del sistema |

Las tres funciones que requieren internet y la degradación de tipografías se registran como limitaciones en la sección 7.

#### Motor autónomo (HU-R4-06.1)

- **Almacenamiento en disco en lugar de MinIO** ([`c242763`][c242763], PR #129, 30 de octubre; paso 1 de D3): `app/core/storage_disco.py`, elegido con `STORAGE_BACKEND=disk`. Los archivos se guardan en la carpeta de datos y las URLs firmadas pasan a ser un endpoint de la API (`app/archivos/router.py`) con un token firmado que vence. El backend impide que una clave salga de la carpeta de datos.
- **Arranque autónomo** ([`9d6c15b`][9d6c15b], PR #132): `escritorio/api.py` corre `alembic upgrade head` antes de uvicorn (`app/core/migraciones.py`) y la API sirve el frontend compilado (`app/frontend.py`). `escritorio/worker.py` corre Celery con `--pool=solo`, porque `prefork` no funciona en Windows.
- **Cola y resultados de Celery sobre Postgres:** en modo escritorio el lanzador configura `CELERY_BROKER_URL` como `sqla+postgresql+psycopg2://...` y `CELERY_RESULT_BACKEND` como `db+postgresql+psycopg2://...` (`escritorio/electron/src/entorno.js`). No se empaqueta Redis.
- **Copia de la base antes de actualizar** ([`278baaa`][278baaa], PR #155, D11): `app/core/copia_migracion.py::actualizar_base`.
  - Solo si hay migraciones pendientes sobre una base con datos, guarda un `pg_dump -Fc` en `copias\base-anterior.dump`; es una sola copia, la previa a la última actualización.
  - Si la migración falla, recrea la base, la restaura con `pg_restore`, deja `actualizacion-fallida.json` y el lanzador muestra un aviso (`src/copias.js::describirFallo`).
  - La copia no se restaura con "Importar".
- **GeoTIFF optimizado por franjas y con 2 hilos de compresión** ([`44feb1d`][44feb1d], PR #133). Con un GeoTIFF de 4,98 GB la fase de optimización pasó de 455 s a 149 s, con resultado idéntico píxel a píxel (bitácora). `AGRONEXO_OPTIMIZACION_RAPIDA=0` vuelve al comportamiento anterior.
- **API sin GTK al arrancar** ([`5106b01`][5106b01], PR #131): WeasyPrint se carga solo al generar un PDF.

#### Lanzador e instalador (HU-R4-06.2)

- **Lanzador de Electron 44.10.0** (`escritorio/electron/`, [`71f07cf`][71f07cf], PR #137, 30 de octubre).
  - **Arranque:** al abrir hace `initdb` en el primer arranque, elige puertos libres, levanta Postgres, la API y después el worker, espera `GET /api/v1/health` y muestra el panel; al cerrar detiene todo en orden.
  - **Seguridad:** una sola instancia; ventana con `contextIsolation` y `sandbox`, sin `nodeIntegration`, con navegación restringida a la API local; Postgres con `scram-sha-256`.
- **Secretos por instalación:** en el primer arranque `src/entorno.js` genera al azar la contraseña de Postgres, `JWT_SECRET_KEY` y la contraseña de la cuenta local (`crypto.randomBytes`) y los guarda en `secretos.json` de la carpeta de datos, con permisos `0o600`. El usuario no los ve. El lanzador también pasa a la API `MODO_ESCRITORIO=true`, `STORAGE_BACKEND=disk` y `STORAGE_PATH`.
- **Sesión automática sin contraseña** ([`4775e04`][4775e04], PR #150, D4): `src/sesion.js` inicia sesión con la cuenta local, deja los tokens en el `localStorage` de la ventana y los renueva cada 20 minutos.
- **PDF en el paquete** ([`acc95d6`][acc95d6], PR #139): las 26 DLL de GTK 3.24.31 (enero de 2022) van en `gtk\` junto al ejecutable y `app/core/gtk.py` las registra con `os.add_dll_directory`. Para el mapa del reporte se buscan fuentes de Windows.
- **Instalador** ([`c43db9d`][c43db9d], PR #142, 31 de octubre):
  - NSIS con electron-builder 26.18.0, por usuario (`perMachine: false`) y sin administrador, con carpeta de instalación elegible;
  - trae adentro el motor: Postgres recortado a 384 MB y la API y el worker empaquetados con PyInstaller;
  - el desinstalador pregunta si borrar los datos, con la casilla desmarcada por defecto (`instalador/installer.nsh`, D7);
  - ícono propio ([`58274b8`][58274b8], PR #153).
- **Scripts de armado** (`escritorio/empaquetado/`, [`6e9ce56`][6e9ce56], PR #157; [`83d7864`][83d7864], PR #158):
  - `armar_motor.ps1`, `preparar_postgres.ps1`, `preparar_gtk.ps1`, `armar_instalador.ps1` y `requirements-empaquetado.txt`;
  - `preparar_entorno.ps1`, que deja lista una PC desde cero (según la bitácora, unos 39 minutos en Windows Sandbox);
  - README paso a paso.
- **Actualizaciones automáticas** ([`9cda5c2`][9cda5c2], PR #184, 19 de noviembre, D18 a D20):
  - `electron-updater` 6.8.12 consulta GitHub Releases 15 s después de abrir y pregunta antes de descargar, mostrando versión y tamaño;
  - el lanzador apaga el motor antes de instalar, y la migración con copia previa corre al abrir la versión nueva;
  - la app pasa a llamarse "AgroNexo" y la carpeta de datos a `%APPDATA%\AgroNexo\` (`src/carpeta-datos.js` renombra la anterior);
  - cada versión se publica con `escritorio/empaquetado/publicar_release.ps1` (sube instalador, `latest.yml` y `.blockmap` como borrador).
  - Según la bitácora, el ciclo 4.0.2 → 4.0.3 bajó una actualización diferencial de 962 KB.
- **Instalación en curso** ([`08fc74f`][08fc74f], PR #190): si la app se abre mientras se instala una actualización, muestra "AgroNexo se está actualizando" y se cierra (`src/instalacion-en-curso.js`).
- **Prueba final** (bitácora, 2 de noviembre, PR #156): instalador armado desde `main` y probado en Windows Sandbox con red y cortándola a mitad de la prueba. Pasaron todos los pasos: instalación silenciosa, bienvenida, lote con GeoTIFF real (análisis en 7 s, 3 zonas), diagnóstico, PDF de 32.910 bytes con y sin red, backup y reapertura.

**Formato, tamaño y requisitos.**
- **Formato:** `AgroNexo-Setup-4.0.0.exe` (NSIS), solo para Windows.
- **Tamaño:** 454.890.941 bytes, el tamaño del `AgroNexo-Setup-4.0.0.exe` publicado en la release `v4.0.0` de GitHub (`gh release view v4.0.0`). Equivale a unos 455 MB, que es la cifra de la tarjeta, y a unos 434 MiB, que es la de la bitácora: las dos fuentes daban el mismo valor en unidades distintas.
- **Requisitos** (borrador de notas de la release en la bitácora): Windows 10 u 11 de 64 bits, 8 GB de RAM recomendados y unos 2 GB libres.

**Build en CI.** No existe: el instalador se arma en una PC con los scripts de `escritorio/empaquetado/` (D20). El CI suma el job `test-lanzador`, que corre `npm test` en `escritorio/electron` (38 tests).

#### Experiencia (HU-R4-06.3)

- **Bienvenida** ([`a136708`][a136708], PR #152, D10 y D17):
  - en el primer arranque `/bienvenida` pide nombre y correo, sin contraseña ni internet, y no vuelve a aparecer;
  - `POST /auth/me/bienvenida` cambia el usuario sembrado por la 0006 solo en modo escritorio y mientras tenga el correo provisorio (si no, 409);
  - ese correo provisorio queda como alias interno del lanzador.
- **Copia de seguridad** ([`fafccac`][fafccac], PR #151, D5 y D14 a D16): tarjeta en Mi perfil con "Exportar todo" (un `.zip` con `manifiesto.json`, `datos/*.jsonl` y `archivos/`) e "Importar".
  - **Qué viaja:** lotes, cultivos, vuelos, análisis, diagnósticos, revisiones y precios cargados por el usuario. El perfil no viaja ni se toca al importar.
  - **"Reemplazar":** pide confirmación y guarda antes una copia (`copias/antes-de-importar-*.zip`, últimas 2).
  - **"Sumar":** reconoce los registros por id. Si un registro está en los dos lados, gana el más reciente cuando tiene fecha de edición.
  - **Versiones:** un backup de una versión más nueva se importa con aviso.
- **Modo sin conexión** ([`d5a94ed`][d5a94ed], PR #154, D6, D8 y D9): indicador "Modo sin conexión" en la barra superior, mapa base de color liso, y búsqueda de lugares y descarga satelital deshabilitadas con aviso. Análisis, diagnóstico y PDF siguen funcionando (tabla anterior).

#### Qué pasó con el enfoque web

| Artefacto | Estado al corte |
|---|---|
| `docker-compose.prod.yml`, `docker/Dockerfile.nginx`, `docker/nginx/nginx.conf`, Certbot, `.env.prod.example` | Se mantienen sin cambios desde el 8 de octubre y **sin uso**: no hay servidor. Producción sigue con MinIO y Redis |
| `scripts/backup_postgres.sh`, `scripts/backup_minio.sh` | Se mantienen sin uso. En escritorio el backup es "Exportar todo" y la copia antes de actualizar |
| Sección "Despliegue en producción" del `README.md` | Se mantiene, aunque describe un despliegue que no se hace |
| MinIO en Docker y CI (D3, paso 2) | No se hizo. MinIO sigue en `docker-compose.yml`, en `minio==7.2.20` de los requirements y en `app/core/storage.py`, junto al backend de disco |
| `docker-compose.yml` para desarrollo | Se mantiene como entorno de desarrollo y de CI |

Estos ítems quedan como deuda en la sección 7.

**Aislamiento multi-tenencia (HU-R4-01) en una instalación de un solo usuario.** En escritorio cada instalación tiene una sola cuenta local y los datos viven en el equipo de esa persona, así que el aislamiento entre usuarios deja de ser un control relevante: no hay otro usuario en la misma base. El aislamiento sigue siendo necesario en el entorno Docker, que admite varios usuarios, y para cualquier despliegue compartido futuro. Por eso los precios compartidos se mantienen como defecto abierto. El backup reasigna al usuario de la instalación todo lo importado: reescribe `usuario_id`, `subido_por_id` y el primer tramo de las claves de archivo.

### Estado de las historias

| Historia | Estado | Evidencia |
|---|---|---|
| HU-R4-06 — App instalable y experiencia inicial (13) | Completa | Contra el enunciado redefinido ("AgroNexo como programa de escritorio. Instalador que funciona sin servidor"): `escritorio/electron/`, `escritorio/empaquetado/`, almacenamiento en disco ([`c242763`][c242763]), instalador ([`c43db9d`][c43db9d]), sesión automática ([`4775e04`][4775e04]), bienvenida ([`a136708`][a136708]), backup ([`fafccac`][fafccac]), modo sin conexión ([`d5a94ed`][d5a94ed]), copia antes de actualizar ([`278baaa`][278baaa]) y actualizaciones automáticas ([`9cda5c2`][9cda5c2]). En el provisional figuraba como "Despliegue" (8 pts, Parcial). Solo Windows |

Totales del sprint: 1 de 1 historia completa; 13 de 13 puntos. Totales de la release: 16 completas y 1 parcial, 81 de 84 puntos.

### Resultado

AgroNexo se entrega como un instalador de Windows que lleva adentro la base, la API y el worker, entra sin login, pide nombre y correo la primera vez, y corre el flujo principal sin servidor y sin internet. Con conexión suma mapas base, búsqueda de lugares, imágenes satelitales y actualizaciones automáticas. El enfoque web quedó en el repositorio sin uso, y el instalador no está firmado ni se arma en CI. Todo el trabajo de este sprint se hizo entre el 29 de octubre y el 19 de noviembre, después de la fecha nominal y en su mayor parte después de la demo.

---

## 6. Calidad y estado al cierre

En el corte hay 591 funciones de test de Python, contra 329 en el provisional y 291 en R3, y 75 tests de JavaScript, contra 9: 37 del frontend con Vitest y 38 del lanzador con `node:test`. Los conteos se tomaron leyendo `def test_`, `it(` y `test(` en el snapshot del tag, sin ejecutarlos.

**CI de pruebas** (`.github/workflows/ci.yml`), con 4 jobs:
- `test-api`, `test-gis` y `build-frontend`, que ahora también corre `npm test`;
- `test-lanzador`, nuevo.

**Workflow de seguridad** (`security.yml`): 6 jobs.

**Resultado en el commit de corte:** CI (corrida 44612219660) y Security (corrida 44612219666) terminaron en `success`, consultado con `gh run list --commit 08fc74f`.

**Alcance del CI:** ejecuta 259 de los 591 tests de Python y los 75 de JavaScript.

### Pruebas automatizadas

| Tipo | Herramienta | Tests | Resultado en el corte |
|---|---|---|---|
| Unitarias GIS (worker) | pytest | 76: `test_ndvi_pipeline` 4, `test_indices_worker` 22, `test_ingesta_worker` 3, `test_clasificacion` 20, `test_cobertura_geotiff` 4, `test_sin_datos` 9, configuración de Celery 2, `test_optimizacion_geotiff` 9, `test_worker_entrada` 3 | Job `test-gis` en verde. Fuera del CI: optimización y entrada del worker (12) |
| Unitarias del motor, salidas, catálogo y ahorro (sin base) | pytest | 238: `test_diagnostico_engine` 30, `test_forma` 12, `test_texto` 32, `test_zonificacion` 22, `test_diagnostico_service` 2, `test_orden_trabajo` 28, `test_absorcion` 12, `test_satelital_catalogo` 6, `test_ahorro_calculo` 13, `test_bayes` 15, `test_catalogo_importador` 23, `test_catalogo_productos_cultivo` 16, `test_reporte_ejecutivo` 7, `test_reporte_zona` 17, `test_firma_diagnostico` 3 | `engine` y `forma` (42) en `test-api`, en verde. Los otros 196 no corren en CI |
| Integración HTTP contra PostGIS | pytest + TestClient | 211: `test_auth` 15, `test_lotes` 28, `test_vuelos_estado` 13, `test_ingesta` 4, `test_diagnostico_api` 16, `test_cultivos` 26, `test_estadios` 5, `test_exportacion_api` 13, `test_reportes_api` 7, `test_orden_trabajo_pdf_api` 8, `test_ahorro_api` 14, `test_multi_tenant_indices` 7, `test_revisiones_api` 6, `test_vuelos_editar` 9, `test_backup` 26, `test_bienvenida` 10, `test_catalogo_migracion` 4 | En `test-api`, en verde: `auth`, `lotes`, `vuelos_estado`, `ingesta`, `diagnostico_api`, `backup`, `bienvenida` y `catalogo_migracion` (116). Los otros 95 no corren en CI |
| Escritorio y worker con base de datos | pytest | 65: `test_almacenamiento_disco` 29, `test_copia_migracion` 7, `test_storage_importable` 1, `test_migraciones_arranque` 4, `test_frontend_estatico` 11, `test_gtk_empaquetado` 8, `test_weasyprint_opcional` 3, `test_lote_limites_worker` 2 | En CI: almacenamiento en disco, copia antes de migrar (con `postgresql-client-16`) e importación del almacenamiento (37), en verde. Los otros 28 no corren en CI |
| End-to-end | pytest (`test_celery_integracion.py::test_ciclo_completo_encolar_y_esperar`) | 1 (de R1) | Solo local |
| Frontend | Vitest (`npm test`) | 37: `geometria` 5, `coordenadas` 4, `cambioZonas` 8, `conexion` 10, `estadios` 4, `evolucionNdvi` 5, `fechas` 1 | Job `build-frontend`, en verde |
| Lanzador de escritorio | `node:test` (`npm test` en `escritorio/electron`) | 38: `sesion` 10, `copias` 8, `carpeta-datos` 5, `actualizaciones` 10, `instalacion-en-curso` 5 | Job `test-lanzador`, en verde |
| Seguridad | Gitleaks, Semgrep, Bandit, pip-audit, npm audit, Trivy | 6 jobs | Workflow `Security` en verde; 5 jobs con `continue-on-error: true` |
| Instalador | — | Sin tests automatizados | Prueba manual en Windows Sandbox (verificaciones manuales) |
| Rendimiento | — | — | Sin tests automatizados; mediciones manuales de la optimización del GeoTIFF |

Las filas de Python suman 591 (76 + 238 + 211 + 65 + 1); en CI corren 259 (64 + 42 + 116 + 37). Los 3 tests de `test_celery_integracion.py` se reparten entre la fila GIS (2 de configuración, en CI) y la de end-to-end (1). La cobertura no se midió: no hay `pytest-cov` ni configuración de cobertura. Algunos conteos de la bitácora difieren de los del código (por ejemplo, 21 tests de `test_bayes.py` según la bitácora y 15 funciones en el código), probablemente por tests parametrizados; este documento usa el conteo de funciones.

**Qué no corre en CI.** Quedan fuera 332 tests de Python. Los grupos más relevantes:
- ahorro (`test_ahorro_*`, 27);
- aislamiento (`test_multi_tenant_indices`, 7);
- revisiones y motor probabilístico (`test_revisiones_api`, `test_bayes`, 21);
- catálogo (`test_catalogo_importador`, `test_catalogo_productos_cultivo`, 39);
- orden de trabajo y reportes (`test_orden_trabajo`, `test_orden_trabajo_pdf_api`, `test_reportes_api`, `test_reporte_*`, 67);
- los heredados de R3 (`test_texto`, `test_zonificacion`, `test_cultivos`, `test_exportacion_api`, entre otros).

La bitácora registra que la lista de tests de `ci.yml` es fija y recomienda revisarla.

### Workflow de seguridad

| Job | Herramienta | Qué analiza | Bloquea |
|---|---|---|---|
| Secretos | Gitleaks | Historial completo del push o PR | **Sí** |
| SAST | Semgrep (`p/security-audit`, `p/owasp-top-ten`, `p/secrets`) | Python y JS/React | No (`continue-on-error: true`) |
| SAST | Bandit | `app/` y `workers/` | No |
| SCA | pip-audit | `docker/requirements.api.txt`, `docker/requirements.worker.txt` | No |
| SCA | npm audit (`--audit-level=high`) | `frontend/` | No |
| Imágenes | Trivy (`api`, `worker`, `frontend`; `--exit-code 0`) | Imágenes construidas con los Dockerfiles | No |

- **Disparadores:** `push` y `pull_request` a `main` y semanal (lunes 06:00 UTC).
- **Hallazgos atendidos después del provisional:** `python-jose` y `ecdsa` eliminados con PyJWT (PR #128), `pillow` 13.0.0 (PR #125), `follow-redirects` 1.16.2 (PR #121) y el `INSERT` de la 0025 (PR #124).
- **Fuera del alcance de los checks:** `escritorio/electron/` (dependencias de npm del lanzador), `docker/Dockerfile.nginx` y las imágenes del despliegue web. Según la bitácora, `npm audit` del lanzador dio 15 avisos moderados de `minimatch` dentro de electron-builder, que no viaja en la app.
- **Escaneo de secretos en los PRs:** además del workflow, el PR #157 pasó por GitGuardian. Un valor fijo de relleno en `armar_motor.ps1` fue un falso positivo; se sacó del historial del PR con `push --force-with-lease`.

### Verificaciones manuales

Registradas en la bitácora `docs/release-v4.0.0.md`, salvo indicación.

| Fecha | Verificación | Resultado |
|---|---|---|
| 22 sep (fecha de la bitácora v3, mergeado en R4) | Mapa por clase y "Acción recomendada" ([`f01c301`][f01c301]) | PNG en modo clase con 4 colores; texto de la acción verificado en el PDF con `pypdf` temporal; 238 tests pasan |
| 27 sep | Semgrep local tras fijar las Actions | "Ran 350 rules on 196 files: 0 findings" (antes, 25) |
| 27 sep | Suite completa tras `pytest` 9.1.1 | 313 tests pasan |
| 28 sep | Stack completo desde cero con `cgr.dev/chainguard/minio` | 6 servicios `healthy`/`running`; `/minio/health/live` → 200; `test_celery_integracion.py` (3, incluido el E2E) pasa |
| 30 sep | Upgrade a React 19, react-leaflet 5 y react-router 7 | `npm run build` y `npm test` sin errores; recorrido manual login → dashboard → lotes → resultados, mapas y dibujo con geoman sin errores de consola |
| 30 sep | HU-R4-02: migración 0021 con `downgrade` y `upgrade` reales; PDF en 3 niveles; panel de trazabilidad en el navegador | Backfill correcto verificado con `psql`; 246 tests pasan; "motor de reglas v1.0.0" visible |
| 30 sep | HU-R4-03: búsqueda y filtro de estado contra datos reales | 253 tests pasan; el modal de carga sigue ofreciendo todos los lotes |
| 30 sep | HU-R4-01: suite completa con los 7 tests de aislamiento | Pasan |
| 8 oct | HU-R4-10 contra el stack | `PUT /auth/me` → 200, CUIT inválido → 422; contraseña incorrecta → 400, correcta → 204; PNG a `/me/logo-empresa` → 200; logo visible en el PDF (confirmado por el usuario) |
| 8 oct | Bumps coordinados de dependencias | 253 tests de `api`, 151 de `worker` y el E2E pasan tras el bump de `geoalchemy2` |
| 14 oct | HU-R4-12 con una base nueva | `alembic upgrade head` aplica las 24 migraciones; `PUT /auth/me` persiste las preferencias; enum inválido → 422 |
| 14 oct | HU-R4-11 contra datos reales y un lote temporal | 275 tests pasan. Con datos reales y sin dosis cargadas: "Uniforme" y "Ahorro" en `—`. Con dosis cargada a mano en un lote temporal: Variable 90,00 L / Uniforme 1.318,27 L / Ahorro 1.228,27 L (93 %) |
| 15 oct | Comparación de vuelos contra datos de desarrollo (lote con vuelos V18 → VT) | Tendencia, lado a lado, cortina (slider al 5, 50 y 95 %) y cambio por zona con diagnóstico, sin errores de consola |
| 23 oct | Motor v1.1.0: barrido cultivo × estadio × patrón × índices contra `evaluar_zona()` y recálculo de 5 vuelos reales | Todas las reglas menos R00 alcanzables con zonas ≥ 1 ha; 4 zonas pasan de R99 a R80; 317 tests de `api` |
| 23 oct | Motor v1.2 y guía de campo en el navegador | Zona de 15,2 ha (soja V6, NDVI 0,26 contra 0,63 esperado) → "estrés hídrico o déficit de nitrógeno"; 323 tests de `api` y 27 de frontend |
| 26 oct | Importador del catálogo con `--aplicar` sobre la base de desarrollo | 21 productos con dosis; segunda corrida sin cambios; Glifosato con 100 ha de lote y 10 ha tratadas: uniforme 222 L, variable 22,2 L (90 %); 289 tests |
| 28 oct | Reemplazo de `python-jose` por PyJWT | Login, `/auth/me` y refresh 200; token inválido 401; 413 tests de `api` |
| 30 oct | Optimización del GeoTIFF con un archivo real de 4,98 GB | Fase de optimización de 455 s a 149 s; 55 franjas idénticas al resultado anterior |
| 30 oct | Lanzador fase 1 en la máquina de desarrollo | Arranque desde cero, GeoTIFF de 3,4 MB analizado de punta a punta, cierre sin procesos huérfanos |
| 1 nov | Backup con un GeoTIFF de 5,3 GB en la app de escritorio | Procesado en 228 s, exportado en 6 s, "reemplazar" lo recuperó en 22 s con `original.tif` idéntico (SHA-1); pico de memoria de la API 199 MB |
| 2 nov | Bienvenida, actualización desde una versión anterior y PC nueva con backup, en Windows Sandbox | Bienvenida una sola vez, alias del lanzador, segunda bienvenida 409, datos conservados |
| 2 nov | Modo sin conexión en Windows Sandbox con los adaptadores de red apagados | Sin mosaicos, polígonos sobre color liso, satelital deshabilitada y búsqueda por coordenadas funcionando |
| 2 nov | Copia antes de actualizar con una migración forzada a fallar, en Windows Sandbox | Copia, falla, base recreada y restaurada (revisión 0027), aviso correcto |
| 2 nov | Prueba final del instalador desde `main`, con y sin red, en Windows Sandbox | Instalación silenciosa, bienvenida, análisis de un GeoTIFF de 3,5 MB en 7 s (3 zonas), PDF de 32.910 bytes con y sin red, backup "sumar" sin duplicados, reapertura directa al panel |
| 3 nov | `preparar_entorno.ps1` desde cero en Windows Sandbox | Entorno completo en unos 39 minutos; segunda corrida en 1 s |
| 3 nov | Worker de Docker con PyJWT | GeoTIFF multibanda de 3,4 GB procesado en unos 4 minutos |
| 3 nov | Motor v1.3.0 y orden de trabajo con marca | 115 tests de `api` en verde; vuelo de prueba de 6,95 ha recomienda Thiamethoxam Genérico con 3 alternativas |
| 19 nov | Ciclo de actualización automática con un repositorio público de prueba | 4.0.0 → 4.0.1 (descarga completa del instalador, unos 434 MiB) y 4.0.2 → 4.0.3 (diferencial de 962 KB, instalación en ~70 s); datos conservados |

Ninguna de estas verificaciones tiene un script reproducible en el repositorio: los scripts del Sandbox (`probar*.ps1`) están fuera del repositorio. Quedaron sin probar:
- instalar la 4.0.0 encima de "AgroNexo (prototipo)";
- el aviso de SmartScreen en una actualización;
- una migración real exitosa dentro del instalador;
- abrir la app durante una instalación con el arreglo del PR #190 (cubierto solo por tests).

### Errores corregidos durante el desarrollo

Ninguno afectó a una versión publicada: el instalador se publicó en GitHub Releases por primera vez con la `v4.0.0`, el 19 de noviembre. A los del provisional (IDOR, tipos de UUID, migraciones con SQLAlchemy 2.1, `passlib`, GDAL 3.13.3, `greenlet`, "Cargando..." en el Dashboard, `acumular_ahorro()`, Semgrep en Nginx, bugs del workflow de seguridad y sidebar) se suman:

- **El worker de Docker no podía procesar GeoTIFF** (`ModuleNotFoundError: No module named 'jwt'`): desde el PR #129, `app/core/storage.py` importa el backend de disco, que usa PyJWT, y `requirements.worker.txt` no lo declaraba. Commit [`d329602`][d329602] (PR #161).
- **El lanzador se colgaba al iniciar Postgres:** `pg_ctl start` lanzado con `execFile` heredaba los canales de salida; se lanza con `spawn`. Commit [`71f07cf`][71f07cf].
- **El PDF fallaba en el programa empaquetado aunque GTK estuviera instalado:** WeasyPrint ignora el `PATH`; se registra la carpeta con `os.add_dll_directory`. Commit [`acc95d6`][acc95d6].
- **El motor no entraba en el instalador** (instalador de 120 MB): `extraResources` con ruta absoluta. Commit [`c43db9d`][c43db9d].
- **Abrir la app durante una actualización** arrancaba con archivos a medio reemplazar o fallaba con `No se encontró el motor empaquetado`. Commit [`08fc74f`][08fc74f] (PR #190).
- **`preparar_entorno.ps1` desde cero:** `404` al bajar PostGIS (OSGeo mueve las versiones viejas a `archive/`). Commit [`08fc74f`][08fc74f].
- **Un 401 de `/auth/login` recargaba el login sin mostrar el error** (interceptor de `frontend/src/api/client.js`). Commit [`4775e04`][4775e04].
- **Fecha de vuelo un día antes** en resultados, calendarios y Dashboard (medianoche UTC mostrada en UTC-3). Commits [`eb85e71`][eb85e71] y [`d31d4ff`][d31d4ff].
- **Tests de revisiones que contaminaban el entrenamiento** del motor probabilístico. Commit [`d31d4ff`][d31d4ff].
- **Fechas como texto con asyncpg** en la migración 0029. Commit [`ec25a5d`][ec25a5d].

### Despliegue de la demo

**Entorno de desarrollo** (`README.md` del corte), sin cambios de procedimiento respecto del provisional:
1. Clonar y hacer checkout del tag `v4.0.0`.
2. Crear `.env` desde `.env.example`.
3. Levantar con `docker compose up -d --build`.
4. Migrar con `docker compose exec api alembic upgrade head`.
5. Verificar con `docker compose ps`, `GET /api/v1/health`, `GET /api/v1/health/db` y Swagger en `/api/docs`.

**Aplicación de escritorio:**
1. Instalar `AgroNexo-Setup-4.0.0.exe`, por usuario y sin administrador. Si Windows muestra "Windows protegió su PC", elegir "Más información" y "Ejecutar de todas formas", porque el instalador no está firmado.
2. Abrir AgroNexo desde el menú Inicio.
3. Completar la bienvenida.

El lanzador crea la base, aplica las migraciones y genera los secretos en el primer arranque. Para armar el instalador desde el repositorio: `escritorio/empaquetado/preparar_entorno.ps1` y luego los pasos del `escritorio/empaquetado/README.md` (`armar_motor.ps1`, `armar_instalador.ps1`). Para publicar una versión: `publicar_release.ps1`.

**Cambios respecto del provisional:**
- **Migraciones:** `upgrade head` aplica además la 0025 (curva esperada, con datos), la 0026, la 0027, la 0028 y la 0029 (carga del catálogo, idempotente).
- **Variables:**
  - `.env.example` suma `STORAGE_BACKEND`;
  - el lanzador define para la API y el worker `MODO_ESCRITORIO`, `STORAGE_BACKEND`, `STORAGE_PATH`, `JWT_SECRET_KEY`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `AGRONEXO_HOST`, `AGRONEXO_PORT`, `AGRONEXO_PG_BIN` y `AGRONEXO_COPIAS_DIR`;
  - `AGRONEXO_OPTIMIZACION_RAPIDA` es un interruptor opcional del worker.
- **Dependencias de la API:** `fastapi` 0.162.2, `pydantic` 2.14.3, `pydantic-settings` 2.16.2, `sqlalchemy` 2.1.8, `geoalchemy2` 0.21.0, `asyncpg` 0.32.0, `alembic` 1.20.1, `PyJWT` 2.15.1 (reemplaza a `python-jose`), `celery` 5.7.0, `pillow` 13.0.0, `openpyxl` 3.1.5 (nueva), `pyshp` 3.1.7, `python-multipart` 0.0.33 y `pytest` 9.2.0. Sin cambios: `uvicorn` 0.54.0, `bcrypt` 5.0.0, `minio` 7.2.20, `weasyprint` 70.0 y `shapely` 2.1.2.
- **Dependencias del worker:** además de las compartidas, `PyJWT` 2.15.1 y `rasterio` 1.5.2.
- **Frontend:** `axios` ^1.21.1, `react-router-dom` ^7.18.5, `@geoman-io/leaflet-geoman-free` ^2.20.6, `vite` ^8.3.8, `@vitejs/plugin-react` ^6.2.1 y `vitest` ^5.1.0.
- **Lanzador:** `electron` 44.10.0, `electron-builder` 26.18.0 y `electron-updater` 6.8.12, con versiones exactas y `package-lock.json`.
- **Paquete de escritorio:** Postgres 16.15 con PostGIS 3.6.2 recortado, Python 3.14 con PyInstaller (`requirements-empaquetado.txt`) y GTK 3.24.31.
- **Imágenes base:** sin cambios respecto del provisional (API `python:3.12-slim`, worker `ghcr.io/osgeo/gdal:ubuntu-small-3.13.3`, frontend `node:26-slim`, MinIO `cgr.dev/chainguard/minio:latest`).

---

## 7. Deuda técnica y trabajo pendiente

R4 cerró 16 de sus 17 historias. La única parcial es HU-R4-01, por los precios cargados por usuario sin dueño. Lo pendiente se agrupa en tres frentes:
- **Calidad:** 332 tests de Python siguen fuera del CI y la cobertura no se mide.
- **Validación agronómica:** la curva de NDVI esperado, las tablas del motor probabilístico y 19 de las 21 dosis originales son borradores o valores "habitual según web".
- **Restos del cambio de enfoque:** el despliegue web quedó sin uso, MinIO convive con el backend de disco, y el instalador no está firmado ni se arma en CI.

La mayoría son correcciones, validaciones y mejoras. Quedan también partes de historias de R4 que se dieron por completas contra el enunciado de la presentación pero no cubren todo el requisito relacionado:
- la unidad de área y el producto habitual de HU-R4-12, sin consumidor;
- los análisis y diagnósticos como eventos de la línea de tiempo (RFGL-03, HU-R4-04);
- el mapa de diferencia raster (opcional en HU-R4-09).

Figuran en "Funcionalidades pendientes".

### Defectos y riesgos conocidos

| Ítem | Descripción | Impacto | Estado |
|---|---|---|---|
| Precios compartidos entre usuarios | `precios_productos` no tiene `usuario_id`; un precio `"usuario"` cargado por cualquiera se aplica al ahorro de todos (`resolver_precio`). La unidad del precio es texto libre. En escritorio hay un solo usuario por instalación | Medio (aislamiento en Docker con varios usuarios; sin efecto en escritorio) | Abierto |
| Tests fuera del CI | 332 de 591 tests de Python, entre ellos ahorro, aislamiento, revisiones, motor probabilístico, catálogo, orden de trabajo y reportes | Alto (regresiones no detectadas) | Abierto |
| Controles de seguridad no bloqueantes | 5 de los 6 jobs de `security.yml` con `continue-on-error: true`; Trivy con `--exit-code 0`. El lanzador (`escritorio/electron/`) no se analiza con npm audit en CI | Medio (seguridad) | Abierto |
| Instalador sin firma de código | Windows muestra "editor desconocido" y SmartScreen puede advertir; no se firma por alcance académico (tarjeta, dato del equipo; bitácora) | Medio (confianza del usuario al instalar y actualizar) | Abierto |
| GTK de 2022 sin actualizar | Las 26 DLL de GTK 3.24.31 (enero de 2022) del PDF no se actualizaron a una compilación más nueva; faltan los avisos de licencia LGPL/MIT en el instalador | Medio (seguridad y licencias) | Abierto |
| Fase 2 del lanzador sin hacer | Sin política de contenido (CSP) ni `fuses` de Electron, sin rotación de logs; el cierre usa `taskkill /T /F` y un análisis en curso se pierde al cerrar | Medio (seguridad y robustez) | Abierto |
| Armado del instalador manual | No hay build del instalador en CI (D20); `preparar_entorno.ps1` descarga versiones fijas sin verificar hash, y GTK y Visual C++ pueden pedir permisos de administrador | Medio (reproducibilidad) | Abierto |
| Tamaño del instalador | 454.890.941 bytes (unos 455 MB); una actualización sin `.blockmap` previo descarga el instalador completo | Bajo (uso real con datos móviles; las actualizaciones preguntan antes de descargar) | Abierto |
| Solo Windows | No hay instalador para Linux ni macOS, ni versión para celular o tablet: el uso en el campo supone una notebook con Windows. La revisión de pantallas de HU-R4-13 se hizo solo para escritorio | Medio (alcance y uso real en el campo) | Abierto |
| Un análisis a la vez en escritorio | El worker corre con `--pool=solo` porque `prefork` no funciona en Windows: varios vuelos se procesan en serie | Bajo (tiempo de espera con varios ortomosaicos) | Abierto |
| Funciones que requieren internet | Mapa base (sin conexión, color liso sin mapa satelital de fondo), búsqueda de lugares por nombre, imágenes Sentinel-2 y actualizaciones automáticas. No hay caché de mosaicos | Medio (uso en el campo) | Abierto (decisiones D6, D8 y D9) |
| Tipografías de Google Fonts sin alternativa local | `frontend/index.html` carga Plus Jakarta Sans y JetBrains Mono desde Google Fonts; sin internet se usa la fuente del sistema y la interfaz cambia de aspecto. También es la única consulta externa no declarada en el modo sin conexión | Bajo (presentación sin conexión) | Abierto |
| Copia antes de actualizar no restaurable con "Importar" | La copia es un `pg_dump`, se guarda una sola (la previa a la última actualización) y una restauración a mano necesita `pg_restore` | Bajo (la restauración automática cubre la falla de migración) | Abierto |
| Backup sin el correo ni el perfil | Un backup no trae el correo ni el perfil: en una PC nueva se hace primero la bienvenida y después se importa. Exportar e importar corren dentro del pedido HTTP sin barra de progreso | Bajo (uso real) | Abierto |
| Correo fijo después de la bienvenida | El correo no se puede cambiar desde Mi perfil | Bajo | Abierto |
| Botón "Salir" sin efecto en escritorio | Cierra la sesión y el lanzador la vuelve a inyectar (bitácora, decisión del 3 de noviembre de dejarlo para la release siguiente) | Bajo | Abierto |
| Escritorio sin probar en algunos caminos | Actualización desde "AgroNexo (prototipo)", aviso de SmartScreen en una actualización, migración real exitosa dentro del instalador | Medio | Abierto |
| MinIO sin quitar (D3, paso 2) | Conviven el backend de disco y MinIO en `app/core/storage.py`, `docker-compose.yml`, CI y requirements; con MinIO, "reemplazar" en el backup no borra los archivos viejos | Medio (mantenimiento: dos backends) | Abierto |
| Enfoque web sin uso | `docker-compose.prod.yml`, Nginx, Certbot, `.env.prod.example`, scripts de backup y la sección "Despliegue en producción" del README describen un despliegue que no se hace | Bajo (documentación y mantenimiento) | Abierto |
| Curva de NDVI esperado genérica | Migración 0025: curva placeholder no validada; condiciona "NDVI bajo" y la severidad desde el motor v1.1.0 | Alto (confiabilidad del diagnóstico) | Abierto |
| Motor probabilístico sin validar | Tablas expertas borrador; aprende de revisiones de todos los usuarios; aceptar una zona provisoria la confirma como caso de entrenamiento | Alto (confiabilidad del diagnóstico) | Abierto (experimental) |
| Dosis "habitual según web" | 19 de las 21 dosis originales no son de marbete; la orden de trabajo elige el activo y la marca por menor costo por hectárea, sin eficacia ni registro | Alto (recomendación agronómica) | Abierto |
| Precios de una tienda | Los precios de la planilla citan `camposimple.com.ar`, una tienda y no una fuente oficial, y pisaron 5 precios con fuente CASAFE o INTA | Medio (cifras de ahorro) | Abierto |
| Campos `ahorro_pesos` en dólares | `ahorro_pesos` y `ahorro_total_pesos` contienen USD; renombrarlos exige versionar la API | Bajo | Abierto (decisión del 3 de noviembre) |
| R00 inalcanzable | `AREA_MINIMA_M2 = 10_000` en `workers/gis/zonas.py` descarta las zonas que R00 evalúa | Bajo | Abierto |
| Umbrales y etiquetas duplicados en el frontend | `MapaCapas.jsx::UMBRALES_FIJOS` copia `_UMBRALES_POR_INDICE`; `CambioPorZona.jsx` repite las etiquetas de causa y severidad de `TablaDiagnostico.jsx` y `MapaZonas.jsx` | Bajo (mantenimiento) | Abierto |
| Certificado de Avast y versiones distintas entre imágenes | `avast-root.crt` en los Dockerfiles de `api`, `worker`, `frontend` y `nginx`; worker en Python 3.14 y API en 3.12; Nginx sobre `node:25-slim` y frontend en `node:26-slim` | Medio (reproducibilidad) | Abierto |
| Uso obsoleto de `.distinct()` | `app/lotes/service.py::listar_lotes` con SQLAlchemy 2.1 (warning) | Bajo | Abierto |
| Endpoints sin tests | `/auth/me/*` de perfil y preferencias; comparación de vuelos y capas sin tests de componentes | Medio | Abierto |

### Funcionalidades pendientes

| Ítem | Descripción | Release destino |
|---|---|---|
| Validación agronómica del motor | Validar con una persona del área la curva de NDVI esperado, las reglas por estadio, las tablas del motor probabilístico y las dosis | Release 5 ("Qué sigue" de la presentación) |
| Fixes pequeños | Entre ellos, el botón "Salir" en escritorio, el aviso de confiabilidad de la dosis y el estilo de opciones deshabilitadas sin conexión | Release 5 ("Qué sigue") |
| Guías de uso | Guía de primer uso y guía de estadios fenológicos dentro de la app; proponer el estadio a partir de la fecha de siembra | Release 5 ("Qué sigue"; bitácora, 3 de noviembre) |
| Build del instalador en GitHub Actions | Workflow en runner de Windows disparado por tag | A definir |
| Línea de tiempo con análisis y diagnósticos (RFGL-03) | La línea de tiempo muestra vuelos; faltan los análisis por índice y los diagnósticos como eventos | A definir |
| Mapa de diferencia raster entre vuelos | Remuestreo a una grilla común y zonas "mejoró / empeoró / igual" (opcional en HU-R4-09) | A definir |
| Uso de la unidad de área y el producto habitual (HU-R4-12) | Guardados sin consumidor | A definir |
| Aislamiento de precios por usuario | `usuario_id` en `precios_productos` y filtro en `resolver_precio` | A definir |
| Quitar MinIO (D3, paso 2) y limpiar el enfoque web | Un solo backend de almacenamiento en Docker, CI y tests; decidir qué hacer con `docker-compose.prod.yml` y su documentación | A definir |
| Análisis de barbecho | Tipo de cultivo `barbecho` y reglas centradas en malezas | A definir (fuera de R4 por decisión del 3 de noviembre) |
| Ahorro como rango por marca | De la marca más barata a la más cara | A definir |
| Carga del catálogo con el importador en el primer arranque | Alternativa a escribir una migración por cada actualización del Excel | A definir |
| Exportación ISO-XML | Integración con maquinaria | A definir |

Las **actualizaciones automáticas**, el **instalador publicado en GitHub Releases** y el **criterio técnico del agrónomo (RFDR-04)** ya no figuran como pendientes. Se implementaron en R4 (secciones 4 y 5), y la release `v4.0.0` quedó publicada el 19 de noviembre con el instalador, su `.blockmap` y `latest.yml`. La presentación ubica las dos primeras en "Qué sigue" (R5) y el plan de releases ubica RFDR-04 en R5.

### Deuda heredada de R3

"Estado al corte" es el del tag `v4.0.0` ([`08fc74f`][08fc74f]). "Estado actual" es el de `origin/main` al 19 de noviembre ([`b638091`][b638091]): sus 12 commits posteriores al tag no cambian ninguno de estos ítems.

| Ítem | Estado al corte de esta release | Estado actual (origin/main) | Evidencia |
|---|---|---|---|
| Orden de trabajo sin dosis | Corregido | Corregido | Migración 0029 ([`ec25a5d`][ec25a5d]); dosis de la marca recomendada ([`1444295`][1444295]) |
| Textos de seguridad incompletos y sin revisión legal | Parcial | Parcial | La 0029 carga restricciones y seguridad de los 9 productos nuevos; `orden_trabajo.html` mantiene la marca "PENDIENTE DE REVISIÓN LEGAL" |
| Tests de R3 fuera del CI (90) | Abierto | Abierto | `test_texto`, `test_zonificacion`, `test_cultivos`, `test_exportacion_api` y otros siguen fuera de `ci.yml` |
| Cambio de contrato sin versionar (migración 0020) | Abierto | Abierto | Decisión aceptada en R3 |
| Downgrade de la 0020 con pérdida de datos | Abierto | Abierto | Sin cambios |
| Caché de exportación sin invalidación | Abierto | Abierto | `app/reportes/router.py` arma la clave `export_{formato}` y no hay borrado al recalcular |
| URLs firmadas como enlaces de portador | Abierto | Abierto | Por diseño; en escritorio, enlace con token que vence (`app/archivos/router.py`, [`c242763`][c242763]) |
| Servicios externos sin SLA ni alternativa | Parcial | Parcial | Modo sin conexión ([`d5a94ed`][d5a94ed]): sin internet se deshabilitan con aviso; con internet siguen sin alternativa |
| Validación de ubicación del GeoTIFF solo en el navegador | Abierto | Abierto | Sin commits que lo aborden en el rango |
| Cortes provisorios de ExG y GNDVI | Abierto | Abierto | Sin commits sobre `clasificacion.py`; `MapaCapas.jsx` replica los cortes |
| Exportación solo de NDVI | Abierto | Abierto | `/zonas/export` mantiene el 501 (`app/reportes/router.py`, línea 177) |
| Geometrías perdidas en la base de desarrollo | Abierto | Abierto | Dato de desarrollo |
| IDOR en índices adicionales | Corregido | Corregido | [`537f671`][537f671] (PR #49) |
| Carga y edición de dosis de referencia | Parcial | Parcial | Carga corregida (0029 e importador); sin edición desde la interfaz |
| Revisión legal y agronómica de la orden de trabajo | Abierto | Abierto | Sin rastro en el repositorio |
| Exportación ISO-XML / integración con maquinaria | Abierto | Abierto | Sin implementación |
| Exportación y diagnóstico multi-índice | Parcial | Parcial | El motor probabilístico usa NDRE y ExG como evidencia ([`d31d4ff`][d31d4ff]); la exportación sigue solo con NDVI |
| Historial y trazabilidad (objetivo 1 de R4) | Parcial | Parcial | Cumple el objetivo de la presentación (criterio 1 de la sección 1.4): trazabilidad, calendario, resumen por vuelo y evolución del NDVI. Para RFGL-03 falta mostrar análisis y diagnósticos como eventos y un historial de diagnósticos por vuelo (ver la fila "Historial de diagnósticos entre vuelos") |
| Comparación entre campañas (objetivo 2 de R4) | Corregido | Corregido | Criterio 2 de la sección 1.4 |
| Gestión centralizada con aislamiento (objetivo 3 de R4) | Parcial | Parcial | Precios compartidos entre usuarios |
| Validación del diagnóstico por el usuario (RFDR-04) | Corregido | Corregido | Migración 0028 y `RevisionZona.jsx` ([`d31d4ff`][d31d4ff]) |
| Worker sin límite de memoria ni concurrencia acotada | Abierto | Abierto | Ni `docker-compose.yml` ni `docker-compose.prod.yml` definen `mem_limit`; en escritorio, `--pool=solo` |
| Certificado raíz de Avast | Abierto | Abierto | Dockerfiles de `api`, `worker`, `frontend` y `nginx` |
| Imagen `minio/minio:latest` | Corregido | Corregido | [`7e7182d`][7e7182d] (PR #46) |
| Tests del motor fuera del CI (texto, zonificación, service) | Abierto | Abierto | Siguen fuera de `ci.yml` |
| Cobertura insuficiente de la API de R2 | Parcial | Parcial | `test_diagnostico_api.py` pasa de 11 a 16 tests; sin tests de `GET /productos-fitosanitarios` ni de `indices/batch` |
| Catálogo sin dosis ni fuente | Parcial | Parcial | Dosis con `confiabilidad_dosis` (0026, 0029); 19 de 21 "habitual según web"; precios de la planilla con fuente de una tienda |
| Atributos del lote sin uso en el motor | Abierto | Abierto | `tipo_suelo` no aparece en `app/diagnostico/` |
| Código muerto `app/diagnostico/productos.py` | Corregido | Corregido | Eliminado en [`796a26a`][796a26a] (PR #130) |
| Downgrades no reversibles (0012, 0013) | Abierto | Abierto | Sin cambios |
| Estadísticas sobre el raster decimado | Abierto | Abierto | Sin cambios |
| Ahorro de insumos (RFGL-05) | Corregido | Corregido | `TablaAhorroVuelo.jsx` muestra superficie tratada contra superficie del lote; cifras con dosis de la 0029 |
| Popup del mapa con confianza y producto | Abierto | Abierto | `MapaZonas.jsx` no muestra confianza ni producto |
| Reglas configurables sin código | Abierto | Abierto | 22 reglas con `condicion=lambda` en `reglas.py` |
| Test E2E del flujo con diagnóstico, en CI | Abierto | Abierto | Sin E2E nuevo |
| Historial de diagnósticos entre vuelos (RFGL-03) | Parcial | Parcial | Un diagnóstico por vuelo; la evolución del NDVI recorre los diagnósticos de los vuelos del lote ([`eb85e71`][eb85e71]) |
| Reporte, exportación y orden de trabajo | Corregido | Corregido | Orden de trabajo con dosis, marca y alternativas ([`1444295`][1444295]); PDF con resumen ejecutivo ([`eb85e71`][eb85e71]) |
| Validación de índices y reglas del motor | Parcial | Parcial | Barrido del motor y v1.1.0 a v1.3.0 ([`d31d4ff`][d31d4ff], [`1444295`][1444295]); sin validación agronómica |
| Registro desde la interfaz | Abierto | Abierto | El botón "Registrarse" de `Login.jsx` sigue sin handler; en escritorio no aplica (bienvenida) |
| Usuario seed con credenciales conocidas | Parcial | Parcial | En escritorio la contraseña es aleatoria por instalación (`entorno.js`); en Docker sin variables vuelve a los valores de desarrollo |
| Archivos grandes en memoria | Mitigado | Mitigado | Optimización por franjas ([`44feb1d`][44feb1d]); backup de 5 GB con pico de 199 MB en la API (bitácora) |
| Dependencias sin fijar (`scipy`, `npm install` con rangos) | Abierto | Abierto | `scipy` sin declarar; el lanzador usa versiones exactas y `npm ci` |
| Migraciones manuales | Parcial | Parcial | Automáticas en escritorio ([`9d6c15b`][9d6c15b]) y en `docker-compose.prod.yml`; manuales en Docker de desarrollo |
| Severidad, zonificación y ahorro de insumos | Corregido | Corregido | Severidad relativa al estadio; ahorro con cifras |
| Roles y permisos | Abierto | Abierto | Sin roles en `app/auth/` |
| Cobertura de tests | Abierto | Abierto | Sin medición |
| Zonas en PostGIS | Abierto | Abierto | La única columna geométrica sigue siendo `lotes.geometry` |

### Compromisos de mejora de la release anterior

| Compromiso | Estado | Evidencia |
|---|---|---|
| Seguir con el manejo de ramas por feature y bugs | Cumplido | Todo el rango entra por PR desde ramas `feat/`, `fix/`, `chore/`, `docs/` y de Dependabot; un solo commit directo a `main` en R4 ([`84ccbf6`][84ccbf6], documentación) |
| Seguir usando Trello | Cumplido | Asignación de historias según etiquetas de Trello (bitácora, PR #163) y tarjeta de HU-R4-06 (dato del equipo) |
| Sprint dedicado a deuda técnica | Parcial | HU-R4-16 atendió seguridad y dependencias, y la 0029 cerró la falta de dosis heredada de R2. Siguen abiertas otras deudas de R3, como los tests fuera del CI y la caché de exportación |
| Bajar el nivel técnico para las exposiciones | No verificable en el repo | — |
| Seguir con la revisión cruzada / no cerrar tarjetas sin revisión de otro | Parcial | En GitHub, 73 de 76 PR los mergeó su propio autor y 3 otra cuenta; ninguno tiene reseñas ni comentarios de otra persona (sección 1.4). Según el equipo, la revisión se hizo de forma verbal en las reuniones semanales de avance; es revisión verbal, no registrada en el repositorio |
| No dejar el testing y la documentación para el último sprint | Parcial | Los tests llegan en el mismo commit que la funcionalidad en la mayoría de las historias, y la bitácora se actualizó por tarea. Pero 332 tests no están en CI, y gran parte del trabajo, incluida la app de escritorio, se mergeó después de la fecha nominal del último sprint y de la demo |
| Test E2E en CI (incumplido en R3) | No cumplido | `ci.yml` no corre ningún E2E |
| Cobertura completa (incumplido en R3) | No cumplido | Sin medición de cobertura |
| Tests dentro del CI (incumplido en R3) | Parcial | Se sumaron 6 archivos de Python, los tests de Vitest y el job `test-lanzador`; siguen fuera 332 tests de Python |

La retrospectiva de la presentación de R4 suma para la release siguiente:
- **Empezar:** validar el contenido agronómico con una persona del área, y probar Docker y el instalador al cerrar cada sprint.
- **Dejar de hacer:** cerrar tarjetas sin revisión de otro. En R4 la revisión fue verbal y no queda registrada en GitHub (estado Parcial en la tabla de compromisos). Para que sea verificable en R5, tendría que quedar registrada como reseña aprobada en el PR.
- **Menos de:** trabajo sin estimar y cambios de alcance sobre la marcha.
- **Más de:** controles de seguridad automáticos y revisión cruzada.

[06afb2a]: https://github.com/universoparalelo/Agronexo/commit/06afb2a
[08fc74f]: https://github.com/universoparalelo/Agronexo/commit/08fc74f
[0928e47]: https://github.com/universoparalelo/Agronexo/commit/0928e47
[1444295]: https://github.com/universoparalelo/Agronexo/commit/1444295
[1a82031]: https://github.com/universoparalelo/Agronexo/commit/1a82031
[1de4f91]: https://github.com/universoparalelo/Agronexo/commit/1de4f91
[278845f]: https://github.com/universoparalelo/Agronexo/commit/278845f
[278baaa]: https://github.com/universoparalelo/Agronexo/commit/278baaa
[31db69a]: https://github.com/universoparalelo/Agronexo/commit/31db69a
[38b475f]: https://github.com/universoparalelo/Agronexo/commit/38b475f
[44feb1d]: https://github.com/universoparalelo/Agronexo/commit/44feb1d
[45b03d1]: https://github.com/universoparalelo/Agronexo/commit/45b03d1
[463f2da]: https://github.com/universoparalelo/Agronexo/commit/463f2da
[465f6b8]: https://github.com/universoparalelo/Agronexo/commit/465f6b8
[4775e04]: https://github.com/universoparalelo/Agronexo/commit/4775e04
[4c3d3cf]: https://github.com/universoparalelo/Agronexo/commit/4c3d3cf
[4f99d2f]: https://github.com/universoparalelo/Agronexo/commit/4f99d2f
[507a2bd]: https://github.com/universoparalelo/Agronexo/commit/507a2bd
[5106b01]: https://github.com/universoparalelo/Agronexo/commit/5106b01
[537f671]: https://github.com/universoparalelo/Agronexo/commit/537f671
[58274b8]: https://github.com/universoparalelo/Agronexo/commit/58274b8
[5c06e3f]: https://github.com/universoparalelo/Agronexo/commit/5c06e3f
[60de671]: https://github.com/universoparalelo/Agronexo/commit/60de671
[61ba7ad]: https://github.com/universoparalelo/Agronexo/commit/61ba7ad
[6678ef6]: https://github.com/universoparalelo/Agronexo/commit/6678ef6
[682afd3]: https://github.com/universoparalelo/Agronexo/commit/682afd3
[697ca21]: https://github.com/universoparalelo/Agronexo/commit/697ca21
[6e9ce56]: https://github.com/universoparalelo/Agronexo/commit/6e9ce56
[71f07cf]: https://github.com/universoparalelo/Agronexo/commit/71f07cf
[796a26a]: https://github.com/universoparalelo/Agronexo/commit/796a26a
[7e7182d]: https://github.com/universoparalelo/Agronexo/commit/7e7182d
[7eadf83]: https://github.com/universoparalelo/Agronexo/commit/7eadf83
[7faf3c5]: https://github.com/universoparalelo/Agronexo/commit/7faf3c5
[80e3413]: https://github.com/universoparalelo/Agronexo/commit/80e3413
[83d7864]: https://github.com/universoparalelo/Agronexo/commit/83d7864
[84ccbf6]: https://github.com/universoparalelo/Agronexo/commit/84ccbf6
[872a481]: https://github.com/universoparalelo/Agronexo/commit/872a481
[89787fc]: https://github.com/universoparalelo/Agronexo/commit/89787fc
[8a01d80]: https://github.com/universoparalelo/Agronexo/commit/8a01d80
[8b5f698]: https://github.com/universoparalelo/Agronexo/commit/8b5f698
[8c9ffd4]: https://github.com/universoparalelo/Agronexo/commit/8c9ffd4
[92cb9db]: https://github.com/universoparalelo/Agronexo/commit/92cb9db
[93451e0]: https://github.com/universoparalelo/Agronexo/commit/93451e0
[9af8061]: https://github.com/universoparalelo/Agronexo/commit/9af8061
[9cda5c2]: https://github.com/universoparalelo/Agronexo/commit/9cda5c2
[9d6c15b]: https://github.com/universoparalelo/Agronexo/commit/9d6c15b
[9e87cdf]: https://github.com/universoparalelo/Agronexo/commit/9e87cdf
[a136708]: https://github.com/universoparalelo/Agronexo/commit/a136708
[aaf97f8]: https://github.com/universoparalelo/Agronexo/commit/aaf97f8
[acc95d6]: https://github.com/universoparalelo/Agronexo/commit/acc95d6
[af883e3]: https://github.com/universoparalelo/Agronexo/commit/af883e3
[b638091]: https://github.com/universoparalelo/Agronexo/commit/b638091
[b925724]: https://github.com/universoparalelo/Agronexo/commit/b925724
[ba39b2a]: https://github.com/universoparalelo/Agronexo/commit/ba39b2a
[baa2fd4]: https://github.com/universoparalelo/Agronexo/commit/baa2fd4
[bc59329]: https://github.com/universoparalelo/Agronexo/commit/bc59329
[bc95528]: https://github.com/universoparalelo/Agronexo/commit/bc95528
[c242763]: https://github.com/universoparalelo/Agronexo/commit/c242763
[c43db9d]: https://github.com/universoparalelo/Agronexo/commit/c43db9d
[c77f5af]: https://github.com/universoparalelo/Agronexo/commit/c77f5af
[cb48a5b]: https://github.com/universoparalelo/Agronexo/commit/cb48a5b
[cbf1e4d]: https://github.com/universoparalelo/Agronexo/commit/cbf1e4d
[cbf1f69]: https://github.com/universoparalelo/Agronexo/commit/cbf1f69
[cd9f6c7]: https://github.com/universoparalelo/Agronexo/commit/cd9f6c7
[d080951]: https://github.com/universoparalelo/Agronexo/commit/d080951
[d163ea2]: https://github.com/universoparalelo/Agronexo/commit/d163ea2
[d31d4ff]: https://github.com/universoparalelo/Agronexo/commit/d31d4ff
[d329602]: https://github.com/universoparalelo/Agronexo/commit/d329602
[d5a94ed]: https://github.com/universoparalelo/Agronexo/commit/d5a94ed
[d648213]: https://github.com/universoparalelo/Agronexo/commit/d648213
[db0ef45]: https://github.com/universoparalelo/Agronexo/commit/db0ef45
[dbf6a29]: https://github.com/universoparalelo/Agronexo/commit/dbf6a29
[dcc1811]: https://github.com/universoparalelo/Agronexo/commit/dcc1811
[dcfc9a3]: https://github.com/universoparalelo/Agronexo/commit/dcfc9a3
[e114889]: https://github.com/universoparalelo/Agronexo/commit/e114889
[e5054d3]: https://github.com/universoparalelo/Agronexo/commit/e5054d3
[eb85e71]: https://github.com/universoparalelo/Agronexo/commit/eb85e71
[ec25a5d]: https://github.com/universoparalelo/Agronexo/commit/ec25a5d
[ed96d29]: https://github.com/universoparalelo/Agronexo/commit/ed96d29
[f01c301]: https://github.com/universoparalelo/Agronexo/commit/f01c301
[f0e7645]: https://github.com/universoparalelo/Agronexo/commit/f0e7645
[f13dcab]: https://github.com/universoparalelo/Agronexo/commit/f13dcab
[f794f80]: https://github.com/universoparalelo/Agronexo/commit/f794f80
[fafccac]: https://github.com/universoparalelo/Agronexo/commit/fafccac
[fb945af]: https://github.com/universoparalelo/Agronexo/commit/fb945af
