# AgroNexo — Release 3 (v3.0.0)

**Del diagnóstico a la acción en el campo**

Proyecto Final de Ingeniería en Sistemas · UTN FRRe · Equipo 6
Profesores: Acuña, César J · Mendez, Graciela L

---

## Ficha de release

| Campo | Valor |
|---|---|
| Versión | v3.0.0 (tag `v3.0.0` sobre [`ba39b2a`][ba39b2a], merge del PR #18, fechado en git el 22 de septiembre de 2026 a las 11:28) |
| Estado | Completa — Demo: 22 de septiembre de 2026, presentada junto con la Release 2 |
| Período | 7 de septiembre — 22 de septiembre de 2026 (15 días). Inicio: cierre de la Release 2 ([`47994a4`][47994a4], 7 de septiembre en git; dato del equipo: R3 empezó al cerrar R2). Fin: 22 de septiembre (dato del equipo). La presentación ubica el Sprint 11 entre el 25 de agosto y el 1 de septiembre, antes del cierre de R2 en git |
| Equipo | Amilcar Aguirre, Matías Machado, Celeste Martín Rodich, Denise Pujalte, Zaira Rosin |
| Metodología | Scrum — 3 sprints planificados de 1 semana (el Sprint 13 duró 2 semanas, según la presentación) |
| Entorno | Local con Docker Compose. Sin staging ni producción |
| Repositorio | universoparalelo/Agronexo (privado) |
| Hito de entrega | El productor dibuja su lote sobre imagen satelital, analiza un vuelo de dron o una escena Sentinel-2 y descarga el reporte ejecutivo PDF, la exportación de zonas (GeoJSON / Shapefile) y la orden de trabajo |

**Commit de corte.** El corte de la Release 3 se definió por contenido y por orden de los commits: [`ba39b2a`][ba39b2a] es el último commit antes de [`697ca21`][697ca21] (PR #20, 27 de septiembre), que agrega el workflow de seguridad y abre la Release 4 ("iniciar release v4.0.0"). Su fecha en git (22 de septiembre, 11:28) coincide con el cierre de R3 que dio el equipo. Todo el estado técnico de este documento es el de `ba39b2a`, leído con `git show ba39b2a:<ruta>`; el "estado actual" es el de `origin/main`.

**Rango.** De [`47994a4`][47994a4] (tag `v2.0.0`, exclusive) a [`ba39b2a`][ba39b2a]: 13 Pull Requests (#7 a #19) y 5 commits directos a `main` ([`b5600bd`][b5600bd], [`09b4a74`][09b4a74], [`ffea4e2`][ffea4e2], [`e863f45`][e863f45] y [`a8cf16e`][a8cf16e], todos del rediseño visual). El primer commit de R3 en git es [`36dc4b9`][36dc4b9] (reporte PDF, 10 de septiembre), aunque la presentación lo planifica para el Sprint 13; el último commit con contenido es [`22d4ee9`][22d4ee9] (21 de septiembre). Los commits posteriores al corte que podrían parecer de R3 se tratan como R4: [`7e7182d`][7e7182d] (imagen de MinIO, 28 sep), [`537f671`][537f671] (IDOR de índices, PR #49, 30 sep) y [`8b5f698`][8b5f698] (etiqueta del dashboard, dentro del PR #50).

## Equipo y roles

| Integrante | Rol en la release | Área |
|---|---|---|
| Matías Machado | Scrum Master / Release Manager | Frontend · API |
| Celeste Martín Rodich | Desarrollo | Backend · GIS · DevOps |
| Denise Pujalte | QA | Testing · Documentación |
| Zaira Rosin | Investigación | GIS · Análisis espacial |
| Amilcar Aguirre | Desarrollo | Frontend · UI |

Los roles son los mismos que en la Release 2, según confirmó el equipo. La presentación de R3 no lista integrantes ni roles; su Review incluye la nota "Dejar roles anteriores", que no se interpretó como un cambio de roles.

---

## 1. Planificación de la Release

### 1.1 Objetivo y alcance

El objetivo fue cerrar la brecha entre el diagnóstico agronómico y la acción en el campo: que el resultado salga del sistema en documentos que el productor y el operador usan. Al cierre, el usuario define el límite del lote dibujándolo sobre imagen satelital, analiza un vuelo de dron o una escena Sentinel-2 asociada a un cultivo del lote y, desde el dashboard y la vista de resultados, descarga el reporte ejecutivo en PDF, las zonas de diagnóstico en GeoJSON o Shapefile y la orden de trabajo en PDF con el producto, la superficie y las restricciones de seguridad por unidad de manejo.

**Incluido en el alcance:**

- **Datos:** migraciones Alembic 0018 → 0020. Columnas `restricciones_ambientales` e `instrucciones_seguridad` en `productos_fitosanitarios` y su carga para 15 de los 21 productos; tabla `cultivos` y `vuelos.cultivo_id`, con cultivo, variedad, fecha de siembra y estadio fuera de `lotes`. Cadena lineal con único head `0020`.
- **API:** 12 endpoints nuevos con JWT (de 29 a 41):
  - reporte ejecutivo (`GET .../reporte/pdf`);
  - exportación de zonas (`GET .../zonas/geojson`, `.../zonas/shapefile`, `.../zonas/export`);
  - orden de trabajo (`GET .../orden-trabajo/pdf`);
  - satélite (`GET .../vuelos/imagenes-satelitales`, `POST .../vuelos/desde-satelite`);
  - cultivos (`GET`, `POST`, `PUT` y `DELETE /lotes/{id}/cultivos`);
  - catálogo de estadios (`GET /api/v1/estadios-fenologicos`).

  Los 11 endpoints que cuelgan de un lote validan que el lote pertenezca al usuario autenticado; `GET /api/v1/estadios-fenologicos` es un catálogo que no depende de un lote y solo exige JWT.
- **Generación de documentos:** módulos `app/reportes/` (reporte PDF con mapa PNG generado con Pillow, exportación con pyshp) y `app/ordenes_trabajo/` (orden de trabajo PDF); cálculo de dosis y totales en `app/diagnostico/orden_trabajo.py`. Ambos PDF con Jinja2 + WeasyPrint.
- **Worker GIS:** tarea Celery `descargar_satelital` (Sentinel-2 L2A desde Earth Search, recorte al polígono del lote); recorte de las zonas al límite del lote; cobertura real del GeoTIFF como límite inicial; registro de "sin datos"; ExG normalizado; corrección de Otsu y cortes propios para GNDVI y ExG.
- **Frontend:**
  - dibujo del límite con leaflet-geoman sobre Esri World Imagery (`MapaDibujoLote.jsx`) y buscador con Nominatim;
  - modal de análisis en 3 pasos con carga por dron o por satélite y calendario de escenas;
  - descargas y previsualización de PDF (`ModalPreviewPdf.jsx`);
  - navegación unificada (`PanelLayout.jsx`, `TopbarPanel.jsx`);
  - rediseño visual de landing, login y panel.
- **Configuración e infraestructura:** variable `MINIO_PUBLIC_ENDPOINT`; dependencias `jinja2`, `pillow` y `pyshp` en la API; `@geoman-io/leaflet-geoman-free`, `geotiff`, `proj4` y `vitest` en el frontend; librerías de sistema de Pango, Cairo y GDK-Pixbuf, más la fuente DejaVu, en la imagen de la API.

**Queda fuera del alcance de esta release:**
- la exportación ISO-XML y la integración directa con maquinaria (evolución futura según `docs/5_Plan_de_Releases.md`);
- la carga de dosis de referencia del catálogo;
- la revisión legal y agronómica de los textos de seguridad;
- la exportación multi-índice (solo NDVI);
- el historial y la comparación de campañas, y la gestión centralizada de datos (Release 4).

### 1.2 Sprints que la componen

| S | Título | Entregable demostrable | Fecha | Historias | RF/RNF |
|---|---|---|---|---|---|
| S11 | Deuda técnica R2 | Lote dibujado sobre imagen satelital, vuelo cargado desde Sentinel-2 o dron con su cultivo, navegación unificada | 25 ago–1 sep | H11.1–H11.3 | RFGL-02, RFME-01, RFME-03, RFME-04, RFSA-01 |
| S12 | R3 Exportación y PDF | Zonas exportadas en GeoJSON y Shapefile; orden de trabajo en PDF; índices y reglas revisados | 1–8 sep | H12.1–H12.3 | RFSA-02, RFSA-04, RFDR-01 (dosis), RFMA-02 |
| S13 | Integración y cierre | Dashboard con reporte, exportación y orden de trabajo descargables | 8–22 sep | H13.1–H13.3 | RFSA-03, RFSA-01 |

Las fechas y los títulos son los de la presentación. `docs/5_Plan_de_Releases.md` asigna a R3 los requisitos RFSA-02, RFSA-03, RFSA-04 y RFDR-01 (dosis) solo a nivel de release; la columna RF/RNF por sprint es una derivación por contenido, con los textos de `docs/2_ERS.md`.

### 1.3 Duración y fechas clave

| Evento | Fecha |
|---|---|
| Inicio de la Release 3 | 7 de septiembre de 2026 (cierre de R2 en git, dato del equipo; la presentación ubica el inicio del Sprint 11 el 25 de agosto) |
| Fin Sprint 11 — Deuda técnica R2 | 1 de septiembre de 2026 (según la presentación) |
| Fin Sprint 12 — Exportación y PDF | 8 de septiembre de 2026 (según la presentación) |
| Fin Sprint 13 — Integración y cierre | 22 de septiembre de 2026 (según la presentación) |
| Primer commit de R3 en git ([`36dc4b9`][36dc4b9]) | 10 de septiembre de 2026 |
| Cierre de la Release 3 según git (último commit, [`ba39b2a`][ba39b2a]) | 22 de septiembre de 2026, 11:28 |
| Demo de la Release 3, junto con la R2 | 22 de septiembre de 2026 |

Criterio de cierre: se toma la fecha del último commit de R3, [`ba39b2a`][ba39b2a], porque el siguiente commit de `main`, [`697ca21`][697ca21] (27 de septiembre), ya es trabajo de la Release 4. Coincide con el cierre del 22 de septiembre dado por el equipo. Las fechas de los sprints son las de la presentación: los Sprints 11 y 12 quedan, según esas fechas, antes del cierre de R2 en git (7 de septiembre), y todo el código de R3 se commiteó entre el 10 y el 22 de septiembre.

**Fechas según la bitácora `docs/release-v3.0.0.md` (a confirmar).** La bitácora organiza el trabajo en otros sprints, que no coinciden con los de la presentación:
- Sprint 11 "Reporte ejecutivo PDF", período 2026-09-10.
- Sprint 12 "Exportación genérica de zonas + URLs de descarga", período 2026-09-17.
- Sprint 13 "Cultivos por lote y mejoras del flujo de análisis", con entradas del 20 y 21 de septiembre.
- Un "Sprint 14 — Identidad visual unificada", del 21 de septiembre, que la presentación no menciona.

La bitácora de la Release 4 (`docs/release-v4.0.0.md`) vuelve a usar el número 14 para su primer sprint (seguridad, 27 de septiembre).

### 1.4 Definición de Terminado (DoD)

No se encontró en el repositorio una DoD específica de R3: `docs/5_Plan_de_Releases.md` y `docs/2_ERS.md` no tienen cambios entre `47994a4` y `ba39b2a`. Se mantiene la DoD de R1 y R2. Una tarea se considera terminada cuando cumple todos los criterios siguientes:

- La funcionalidad es demostrable de punta a punta en el entorno local con `docker compose up`.
- Los endpoints involucrados responden con los códigos HTTP esperados.
- Existe al menos un test automatizado que cubre el caso principal.
- Los tests existentes siguen pasando (sin regresiones en CI).
- Si se modificó la base de datos, existe la migración Alembic correspondiente.
- Si se agregó una tarea Celery nueva, el worker fue reiniciado y verificado.
- La tarea fue documentada en el archivo de seguimiento de la release.

`docs/5_Plan_de_Releases.md` agrega para los sprints de construcción que cada funcionalidad debe estar mergeada a `main` y **verificada por al menos 2 integrantes** (revisión de código y prueba funcional).

La presentación no define criterios de cierre de la release. Los siguientes **se derivaron** del objetivo de la release y de los artefactos declarados para el Sprint 13. Evaluados contra el commit de corte: 6 cumplen, 2 parciales y 2 no cumplen.

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| 1 | El productor dibuja el límite del lote sobre un mapa satelital y queda guardado | Cumple | `frontend/src/components/MapaDibujoLote.jsx` (leaflet-geoman sobre Esri World Imagery) y `POST`/`PUT /lotes` con validación de área ([`eb16310`][eb16310], PR #8) |
| 2 | El reporte ejecutivo PDF se descarga desde el dashboard | Cumple | `GET .../reporte/pdf` ([`c9d2418`][c9d2418], PR #7) y botón en la tabla de análisis del Dashboard ([`e8f8720`][e8f8720], PR #13) |
| 3 | Las zonas se exportan en GeoJSON y Shapefile con link de descarga | Cumple | `app/reportes/exportacion.py` ([`706bc15`][706bc15]) y `GET .../zonas/export` con URL firmada ([`2079747`][2079747], PR #11) |
| 4 | La orden de trabajo PDF trae dosis por zona, volumen total, restricciones e instrucciones de seguridad | Parcial | Documento y endpoint ([`d7a91e7`][d7a91e7], PR #12). Ninguna migración carga `dosis_referencia`: la dosis y el volumen de cada unidad salen "— (completar a mano)". Restricciones e instrucciones cargadas para 15 de 21 productos ([`5d28b86`][5d28b86]) |
| 5 | Todas las descargas están en un solo lugar, con indicador de estado de carga | Parcial | Reporte y exportación en la tabla del Dashboard; la orden de trabajo, en la pestaña Diagnóstico de Resultados. Solo la orden muestra texto de progreso ("Generando orden...") |
| 6 | Hay tests end-to-end del flujo completo | No cumple | No hay test E2E nuevo; el único sigue siendo `test_celery_integracion.py::test_ciclo_completo_encolar_y_esperar` (R1), fuera del CI |
| 7 | Los tests de la funcionalidad nueva corren en CI | No cumple | De los 116 tests de Python agregados en R3, 90 no están en `.github/workflows/ci.yml`: exportación, reportes, orden de trabajo, cultivos, satélite, estadios y absorción. Los 9 tests de vitest tampoco. Jobs en verde en `ba39b2a`; el verde no cubre los 90 tests de R3 que siguen fuera del CI |
| 8 | Las migraciones aplican en una cadena única desde cero | Cumple | Verificación estática: 0001 → 0020 lineal por `down_revision`, único head `0020`. Job `test-api` en verde en `ba39b2a` (incluye `alembic upgrade head`) |
| 9 | Los endpoints nuevos de descarga, exportación, orden de trabajo y reporte validan que el lote y el vuelo sean del usuario | Cumple | `_resolver_lote_o_404` + `generar_diagnostico` (que busca el vuelo dentro del lote) en `app/reportes/router.py` y `app/ordenes_trabajo/router.py`; tests de "vuelo de otro lote" y "sin auth" en `test_exportacion_api.py`, `test_reportes_api.py` y `test_orden_trabajo_pdf_api.py`, fuera del CI |
| 10 | Documentación de R3 | Cumple | Bitácora `docs/release-v3.0.0.md` actualizada en los mismos commits de cada funcionalidad; `README.md` actualizado en [`5be3b96`][5be3b96] y [`896da6e`][896da6e]. La documentación en herramientas externas no es verificable |

---

## 2. Sprint 11 — Deuda técnica R2

| Sprint | Título | Fechas | Historias | RF/RNF |
|---|---|---|---|---|
| S11 | Deuda técnica R2 | 25 ago–1 sep 2026 | H11.1–H11.3 | RFGL-02, RFME-01, RFME-03, RFME-04, RFSA-01 |

### Objetivo

Mejorar la carga de datos y la navegación antes de construir las salidas: definir el lote dibujándolo sobre imagen satelital, que la carga del lote y del ortomosaico sea confiable y que los datos queden bien guardados, y que la vista de diagnóstico sea fácil de recorrer. Por decisión del equipo, el contenido de este sprint pertenece a R3 aunque su nombre sea "Deuda técnica R2".

### Tareas realizadas

#### Dibujar el límite del lote sobre un mapa satelital (H11.1)

**Qué se implementó.**
- El límite del lote se puede dibujar sobre imagen satelital, tanto al crear el lote como al editar sus límites ([`eb16310`][eb16310], PR #8).
- Un buscador de lugares y coordenadas, y un mapa del NEA como vista inicial ([`5be3b96`][5be3b96], PR #16).
- Un vuelo puede cargarse a partir de una escena Sentinel-2, recortada al límite dibujado, como alternativa al ortomosaico de dron (PR #10).

El vuelo desde imagen Sentinel-2 se asignó a H11.1 por decisión del equipo: es el artefacto "Imágenes satelitales del NEA" y usa el límite dibujado.

**Detalle técnico por capa.**
- **Frontend — dibujo** ([`eb16310`][eb16310]):
  - `frontend/src/components/MapaDibujoLote.jsx` usa `@geoman-io/leaflet-geoman-free` (`map.pm.addControls`, `drawPolygon`, edición del polígono). Un solo polígono activo: una figura nueva reemplaza a la anterior.
  - Fondo **Esri World Imagery** (`server.arcgisonline.com/.../World_Imagery/MapServer/tile/{z}/{y}/{x}`), con la capa de referencia `World_Boundaries_and_Places` (límites y toponimia) y un botón para ocultarla. Atribución visible en el mapa: "Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics". No requiere clave ni variable de entorno.
  - Integrado en `ModalNuevoLote.jsx` y en `ModalLimites.jsx`. La carga de un archivo `.geojson` se mantiene solo en `ModalLimites.jsx`; [`5be3b96`][5be3b96] la quitó del alta de lote.
- **Validación de la geometría dibujada:**
  - Cliente: `frontend/src/utils/geometria.js`.
    - Área geodésica por exceso esférico (`areaGeodesicaM2`), con rango `AREA_MIN_HA = 0.5` a `AREA_MAX_HA = 5000`.
    - Autointersección de aristas no adyacentes (`tieneAutointerseccion`, O(n²)). Bloquea el envío.
  - API:
    - `app/lotes/schemas.py` define el mismo rango (`AREA_MIN_HA`, `AREA_MAX_HA`).
    - `app/lotes/service.py` lo valida contra el área que calcula PostGIS (`ST_Area` sobre EPSG:32721) y devuelve 400 fuera de rango.
    - La geometría inválida (por ejemplo autointersectada) se rechaza con 422 vía Shapely `is_valid`. La validación de la API cubre también las geometrías enviadas directamente.
- **Frontend — búsqueda y mapa inicial** ([`5be3b96`][5be3b96]):
  - Buscador en `MapaDibujoLote.jsx`, que acepta un lugar o coordenadas `lat, lng`. El parser está en `frontend/src/utils/coordenadas.js`.
  - Los lugares se geocodifican con **Nominatim** (`nominatim.openstreetmap.org/search`) desde el navegador, solo al enviar la búsqueda, por la política de uso del servicio. Ante error, muestra un mensaje.
  - `MapaNEA.jsx` muestra Esri World Imagery con las 4 provincias del NEA, a partir de `frontend/src/data/nea-provincias.json` (datos de OpenStreetMap, ODbL, con atribución en el mapa).
- **Vuelo desde imagen Sentinel-2** ([`8304cb2`][8304cb2], [`40c22b5`][40c22b5], [`3df345b`][3df345b], PR #10):
  - **Búsqueda** — `GET /api/v1/lotes/{lote_id}/vuelos/imagenes-satelitales?fecha=&ventana_dias=` (JWT; ventana de 1 a 60 días, por defecto 15):
    - Busca escenas en **Earth Search** (Element84, colección STAC `sentinel-2-l2a`, `workers/gis/satelital_catalogo.py`, con `urllib` y timeout de 30 s, sin clave) y devuelve su nubosidad.
    - Responde 400 si el lote no tiene límite y 404 si no hay escenas en la ventana.
  - **Creación del vuelo** — `POST /api/v1/lotes/{lote_id}/vuelos/desde-satelite` (JWT, 202):
    - Recibe `escena_id`, `fecha_vuelo`, `estadio_fenologico` (obligatorio), `indices` y `cultivo_id` o `cultivo`.
    - Crea el vuelo y encola la tarea Celery **`descargar_satelital`**.
    - `workers/gis/satelital_descarga.py::descargar_y_recortar_geotiff` lee cada banda de la escena remota, la remuestrea a una grilla común de 10 m (`PIXEL_SIZE_OBJETIVO_M`: B05 es de 20 m y las demás de 10 m) y la recorta al polígono del lote (`rasterio.mask`).
    - Después sube el resultado a MinIO con la misma convención que un upload de dron, y desde ahí sigue el pipeline normal.
  - **Frontend:**
    - `ModalCargaGeoTIFF.jsx` suma el selector "dron / satélite".
    - `CalendarioSatelital.jsx` reemplaza el input de fecha y marca los días con escena disponible, diferenciando las limpias de las muy nubladas, según el mensaje de [`3df345b`][3df345b].
    - Cada escena muestra su miniatura (`preview.jpg` de Earth Search).
  - `scripts/poc_satelital_earthsearch.py` contiene la prueba de concepto previa.

**Decisiones de diseño.**
- Según la bitácora v3 (2026-09-10):
  - `leaflet-geoman-free` se eligió sobre `leaflet-draw` por mantenimiento y compatibilidad con React 18 y Leaflet 1.9.
  - El área y la autointersección se calculan sin turf para no sumar dependencias.
  - La lógica geométrica se separó del componente para testearla con Vitest.
- Según el docstring de `satelital_descarga.py`: el remuestreo a una grilla común resuelve un error real del POC, porque las bandas de distinta resolución no se podían apilar.

**Pruebas.**
- `tests/test_lotes.py` pasa de 16 a 21 tests: geometría autointersectada → 422, y área muy chica o muy grande → 400 al crear y al editar.
- `frontend/src/utils/geometria.test.js` (5 tests, la primera suite de Vitest del proyecto) y `frontend/src/utils/coordenadas.test.js` (4).
- `tests/test_satelital_catalogo.py` (6): bbox del polígono, orden por cercanía a la fecha, días de diferencia, sin escenas, nubosidad.
- Los tests de Vitest y `test_satelital_catalogo.py` no corren en CI; `test_lotes.py` sí.

**Diferencia con la presentación.** El artefacto dice "Imágenes satelitales del NEA (Google Earth / Sentinel-2)" y las conclusiones dicen "descargados de Google Earth". En el código no hay Google Earth:
- el mapa de dibujo usa **Esri World Imagery**;
- los vuelos satelitales usan **Sentinel-2 L2A vía Earth Search** (AWS Open Data).

**No encontrado en el repo.** Manejo de errores o proveedor alternativo para las imágenes de Esri: no hay manejador de `tileerror` en los componentes de mapa (se buscó `tileerror`, `onError` y `errorTileUrl` en `frontend/src/`).

#### Carga confiable del lote y del ortomosaico (H11.2)

**Qué se implementó.**
- Se corrigieron dos fallas que hacían perder o no generar datos: el worker sobrescribía la geometría dibujada del lote ([`dff6b83`][dff6b83]), y los índices adicionales no se calculaban en los vuelos satelitales ([`3f61826`][3f61826], PR #15).
- Se reorganizó el modelo para que cada análisis quede asociado al cultivo del lote ([`5be3b96`][5be3b96], PR #16).
- La tabla de análisis del dashboard dejó de quedar congelada en "Pendiente" ([`c3aad69`][c3aad69], PR #18).

[`c3aad69`][c3aad69] se asignó a H11.2 porque la bitácora v3 lo registra como "Fix posterior al cierre de Sprint 12", no como hallazgo del QA de cierre.

**Detalle técnico por capa.**
- **Worker — geometría del lote** ([`dff6b83`][dff6b83]):
  - `workers/gis/tasks.py::_actualizar_lote_geometry` hacía `UPDATE lotes SET geometry = ...` sin condición, con el rectángulo del GeoTIFF; se agregó `AND geometry IS NULL`.
  - Según la bitácora v3, la falla afectaba también al flujo de dron, y dos lotes de la base de desarrollo quedaron con su polígono original perdido sin posibilidad de recuperarlo.
- **Worker — límite inicial y recorte** ([`5be3b96`][5be3b96]):
  - **Límite inicial:** un lote sin límite toma la cobertura real del primer GeoTIFF (`_poligono_cobertura_wkt`: envolvente convexa de los píxeles con dato, con la máscara leída decimada a ~1024 px) y ahora también su `area_ha` (`ST_Area` sobre EPSG:32721).
  - **Recorte:** las zonas vectorizadas se recortan al polígono del lote (`workers/gis/zonas.py::vectorizar_zonas(..., limite=...)`) antes del filtro de área mínima. Según la bitácora, eliminó 5,05 ha de zonas fuera del lote en una prueba con Sentinel-2.
- **API — índices en vuelos satelitales** ([`3f61826`][3f61826]): `POST .../desde-satelite` recibe `indices`, crea las filas de `analisis_indices`, y `descargar_satelital` encola `analizar_indices_batch` al terminar la descarga. Antes, el frontend pedía el batch cuando el archivo todavía no existía, la API respondía 400 y el error se descartaba en silencio.
- **Base de datos y API — cultivos por lote** ([`5be3b96`][5be3b96]): migración 0020 y endpoints `GET`/`POST /api/v1/lotes/{lote_id}/cultivos` y `PUT`/`DELETE .../cultivos/{cultivo_id}` (JWT; validan el lote del usuario y el cultivo del lote; baja lógica con `deleted_at`). Ver el hallazgo clave.
  - **`POST /lotes/{id}/vuelos`:**
    - `estadio_fenologico` pasa a ser **obligatorio**: 422 si falta o está en blanco.
    - Exige `cultivo_id` o `cultivo_tipo` (con `cultivo_variedad`, `cultivo_fecha_siembra` y `cultivo_fecha_cosecha`).
    - Errores: ninguno de los dos o ambos → 400; cultivo de otro lote → 404.
  - **`POST .../desde-satelite`:** las mismas reglas, con `cultivo_id` o un objeto `cultivo`.
  - **`GET /api/v1/estadios-fenologicos`:** devuelve `ESTADIOS_POR_CULTIVO` desde `app/diagnostico/estadios.py`.
  - **Diagnóstico:** toma el cultivo del vuelo y ya no usa el estadio del lote como respaldo. Un vuelo sin cultivo devuelve 409; antes de [`5be3b96`][5be3b96] salía como 500 porque `except Exception` envolvía la `HTTPException`.
- **Frontend:**
  - `ModalCargaGeoTIFF.jsx` pasa a un modal en 3 pasos: Carga → Cultivo → Análisis.
    - El paso Cultivo tiene un selector de cultivos del lote (`CultivoDropdown`), la opción "＋ Nuevo cultivo" y la fecha y el estadio del vuelo, este último como lista según el cultivo.
    - Editar un cultivo existente hace `PUT` antes de crear el análisis.
    - Permite crear un lote nuevo desde el mismo modal.
  - Validación de ubicación del GeoTIFF, solo en el navegador (`frontend/src/utils/geotiffLimites.js`, con `geotiff` + `proj4`): si el archivo queda a más de 1 km del lote se bloquea "Siguiente"; si no se puede leer el CRS, no se bloquea. Según la bitácora, la API no repite esta validación.
  - Componentes adaptados al modelo de cultivos: `ModalNuevoLote`, `ModalCargaGeoTIFF`, `Dashboard`, `Lotes`, `DetalleLote`, `ResultadosVuelo`, `ModalElegirLote`, `TablaDiagnostico` y `utils/cultivos.js`.
- **Frontend — dashboard** ([`c3aad69`][c3aad69]):
  - `Dashboard.jsx` refresca la tabla cada 3 s mientras haya vuelos `pendiente` o `procesando`.
  - El mapa muestra un mensaje explicativo cuando un análisis completado no genera zonas, distinguiendo el caso de un lote de menos de 1 ha (por debajo de `AREA_MINIMA_M2`).

**Hallazgo clave — cambio de modelo y de contrato con la migración 0020** ([`5be3b96`][5be3b96]):

| Aspecto | Antes (R2) | Después (R3) |
|---|---|---|
| Columnas de `lotes` | `cultivo`, `variedad`, `fecha_siembra`, `estadio_fenologico`, `tipo_suelo`, … | Se eliminan `cultivo`, `variedad`, `fecha_siembra` y `estadio_fenologico`; queda `tipo_suelo` |
| Tabla `cultivos` | — | `id`, `lote_id` (FK a `lotes`, `RESTRICT`), `tipo_cultivo` (reutiliza el enum `cultivoenum`), `variedad`, `fecha_siembra`, `fecha_cosecha`, `created_at`, `deleted_at`; índice `ix_cultivos_lote_id` |
| `vuelos` | — | `cultivo_id` (FK a `cultivos`, nullable), índice `ix_vuelos_cultivo_id` |
| `LoteResponse` (`GET /lotes`, `GET /lotes/{id}`) | Incluía `cultivo`, `estadio_fenologico`, `variedad`, `fecha_siembra` | Esos 4 campos desaparecen; se agrega `cultivos[]` |
| `VueloListItem` / `VueloUploadResponse` | — | Se agregan `cultivo_id` y `cultivo` |
| `metadata` del diagnóstico | — | Se agregan `cultivo_id`, `variedad`, `fecha_siembra`, `fecha_cosecha` |

- **Migración de los datos existentes:**
  - Cada lote genera un cultivo con su `cultivo`, `variedad` y `fecha_siembra`.
  - Todos los vuelos del lote quedan asociados a ese cultivo.
  - El `estadio_fenologico` del lote se copia a los vuelos que no tenían el suyo, para que los diagnósticos guardados no cambien de criterio.
  - Según la bitácora, tras migrar la base de desarrollo quedaron 0 vuelos sin cultivo.
- **Downgrade:** restaura en `lotes` solo el cultivo más reciente no eliminado de cada lote y asigna `soja` a los lotes sin cultivos, porque la columna original era `NOT NULL`. Además borra `vuelos.cultivo_id` y la tabla `cultivos`. **Pierde datos:**
  - los demás cultivos de cada lote;
  - todas las `fecha_cosecha`;
  - la asociación entre vuelo y cultivo;
  - el `estadio_fenologico` del lote, que no se restaura.
- **Contrato roto sin versionar:** quitar campos de `LoteResponse` y volver obligatorio el estadio contradice la regla del proyecto de no eliminar campos de respuesta sin versionar (`CLAUDE.md`). Según la bitácora v3, se hizo así porque el único cliente es este frontend.

**Pruebas.**
- `tests/test_cultivos.py` (25): CRUD, fechas incoherentes, cultivo de otro usuario → 404, sin auth, reglas de cultivo y estadio en `POST .../vuelos` y `desde-satelite`, y que un rechazo no deje cultivos huérfanos.
- `tests/test_estadios.py` (5): las 20 reglas pueden matchear con la lista de su cultivo, más el endpoint.
- `tests/test_cobertura_geotiff.py` (4).
- `tests/test_lote_limites_worker.py` (2, requiere base; se saltea sin ella).
- `tests/test_diagnostico_api.py` pasa de 8 a 10 (diagnóstico con cultivo por vuelo y 409).
- `tests/test_diagnostico_service.py` pasa de 3 a 2, porque se eliminó el respaldo al estadio del lote.
- En CI corren solo `test_cobertura_geotiff.py`, `test_diagnostico_api.py` y `test_lotes.py`.

**Errores corregidos relacionados** (según la bitácora v3):
- Geometría del lote sobrescrita ([`dff6b83`][dff6b83]).
- Índices adicionales descartados en vuelos satelitales ([`3f61826`][3f61826]).
- 409 convertido en 500 en el diagnóstico ([`5be3b96`][5be3b96]).
- `ResultadosVuelo.jsx` buscaba el vuelo por `v.id` en lugar de `vuelo_id` ([`5be3b96`][5be3b96]).
- Lote con límite tomado del GeoTIFF pero sin `area_ha` ([`5be3b96`][5be3b96]).
- Tabla de análisis congelada en "Pendiente" y mapa en blanco sin explicación ([`c3aad69`][c3aad69]).

#### Vista de diagnóstico simple (H11.3)

**Qué se implementó.** La pantalla de resultados de un vuelo (con sus pestañas Zonas y Diagnóstico) y la de detalle de lote pasaron a la misma estructura de navegación que el resto del panel, con una ruta clicable ([`a8cf16e`][a8cf16e], directo a `main`). Dentro del rango, la vista de diagnóstico recibió además cambios de contexto y de lectura del mapa.

**Detalle técnico.**
- **Navegación** ([`a8cf16e`][a8cf16e]):
  - `PanelLayout.jsx` (barra lateral + `TopbarPanel`) y `TopbarPanel.jsx`, con una ruta clicable del tipo "Dashboard › Lotes › Lote 1 › Resultados".
  - `DetalleLote.jsx` y `ResultadosVuelo.jsx` reemplazan su propia cabecera oscura y su botón "Volver a…" por esa estructura.
  - Se quitó la campanita sin función, y "Ver todos" de "Análisis recientes" lleva a Lotes.
- **Encabezado del diagnóstico** ([`5be3b96`][5be3b96]): `TablaDiagnostico.jsx` muestra el cultivo y la variedad del vuelo junto al estadio, y `ResultadosVuelo.jsx` muestra la etiqueta del cultivo del vuelo en lugar del cultivo del lote.
- **Botón volver** ([`ffea4e2`][ffea4e2]): `ResultadosVuelo.jsx` usa `BotonVolver` ("Volver a los vuelos").
- **Mapa del diagnóstico** ([`22d4ee9`][22d4ee9]): `MapaZonas` recibe `sinDatos` y dibuja con un rayado (`PatronSinDatos.jsx`) las áreas sin dato real.
- Los botones "Generar orden de trabajo" y la previsualización de PDF, que también tocan `TablaDiagnostico.jsx` y `ResultadosVuelo.jsx` ([`e8f8720`][e8f8720], [`6af36d4`][6af36d4]), se documentan en H13.2.

**Criterio del estado.** El artefacto declarado es "Navegación mejorada en vista 'Ver diagnóstico'", y está en el código. El enunciado ("que la vista de diagnóstico sea simple") no tiene otro criterio verificable.

**Pruebas.** No hay tests de frontend para estas pantallas.

### Estado de las historias

| Historia | Estado | Evidencia |
|---|---|---|
| H11.1 — Dibujar el límite sobre un mapa satelital | Completa | `MapaDibujoLote.jsx`, validación en `geometria.js` y `app/lotes/service.py` ([`eb16310`][eb16310], PR #8); buscador y `MapaNEA.jsx` ([`5be3b96`][5be3b96], PR #16); vuelo desde Sentinel-2 ([`8304cb2`][8304cb2], [`40c22b5`][40c22b5], [`3df345b`][3df345b], PR #10). Fuente de imágenes distinta de la declarada (ver discrepancias) |
| H11.2 — Carga confiable y datos guardados | Completa | [`dff6b83`][dff6b83] (PR #10), [`3f61826`][3f61826] (PR #15), [`5be3b96`][5be3b96] (PR #16, migración 0020), [`c3aad69`][c3aad69] (PR #18) |
| H11.3 — Vista de diagnóstico simple | Completa | Navegación unificada ([`a8cf16e`][a8cf16e]); encabezado con cultivo del vuelo ([`5be3b96`][5be3b96]), `BotonVolver` ([`ffea4e2`][ffea4e2]) y capa "sin datos" ([`22d4ee9`][22d4ee9]). El enunciado no tiene otro criterio verificable |

### Resultado

El lote se define dibujándolo sobre imagen satelital, con la misma validación de área en el navegador y en la API, y un vuelo puede venir de un dron o de una escena Sentinel-2 recortada al lote. La carga quedó más segura: el worker ya no sobrescribe límites dibujados, las zonas se recortan al lote y cada análisis queda asociado a un cultivo. El costo fue la migración 0020, que rompe el contrato de `/lotes` y cuyo downgrade pierde datos. Los tests nuevos de cultivos, estadios y satélite no corren en CI.

---

## 3. Sprint 12 — R3 Exportación y PDF

| Sprint | Título | Fechas | Historias | RF/RNF |
|---|---|---|---|---|
| S12 | R3 Exportación y PDF | 1–8 sep 2026 | H12.1–H12.3 | RFSA-02, RFSA-04, RFDR-01 (dosis), RFMA-02 |

### Objetivo

Construir las salidas que llevan el diagnóstico al campo: la exportación de las zonas en formatos estándar y la orden de trabajo en PDF para el operador, y revisar que los índices y las reglas del motor den resultados correctos antes de integrarlos al dashboard.

### Tareas realizadas

#### Exportar las zonas en formatos estándar (H12.1)

**Qué se implementó.** Las zonas del diagnóstico se exportan en GeoJSON y en Shapefile:
- primero como descarga directa en el cuerpo de la respuesta ([`706bc15`][706bc15], dentro del PR #7);
- después con un endpoint genérico que cachea el archivo en MinIO y devuelve una URL firmada de descarga ([`2079747`][2079747], PR #11).

Las dos variantes exportan el diagnóstico enriquecido (causa y severidad por zona), no el GeoJSON crudo del worker.

**Detalle técnico por capa.**
- **API** (`app/reportes/router.py`, JWT en los tres endpoints):

| Endpoint | Respuesta |
|---|---|
| `GET /api/v1/lotes/{lote_id}/vuelos/{vuelo_id}/zonas/geojson` | Archivo GeoJSON en el cuerpo |
| `GET .../zonas/shapefile` | `.zip` en el cuerpo |
| `GET .../zonas/export?formato=geojson\|shapefile&indice=ndvi` | `{vuelo_id, formato, indice, url, expira_en_segundos}` |

- Códigos de error en los tres:
  - 404 si el lote no es del usuario, o si el vuelo no pertenece al lote o no está completado;
  - 401 sin token;
  - 500 genérico si falla la generación.
- En `/zonas/export`:
  - `indice` distinto de `ndvi` devuelve 501;
  - si falta `formato`, 422.
- **Generación** (`app/reportes/exportacion.py`, [`706bc15`][706bc15]):
  - `generar_geojson_zonas()` y `generar_shapefile_zip()`, con **pyshp 2.3.1**: Python puro, sin GDAL ni Fiona en el proceso de la API.
  - El `.zip` contiene `zonas.shp`, `zonas.shx`, `zonas.dbf` y `zonas.prj`, con geometrías POLYGON.
  - **CRS:** WGS84 (EPSG:4326), declarado con un `.prj` en WKT estilo ESRI (`GCS_WGS_1984`).
  - **Campos del DBF**, limitados a 10 caracteres por el formato clásico (por eso `causa` y no `causa_indice`, `ndvi` y no `ndvi_promedio`): `zona_id` (N 10), `clase` (C 20), `severidad` (C 20), `causa` (C 40), `ndvi` (F 10,4), `area_ha` (F 12,4), `confianza` (C 10), `regla_id` (C 10).
- **Caché y descarga** ([`2079747`][2079747]):
  - El archivo se guarda en MinIO en `{usuario_id}/{lote_id}/{vuelo_id}/export_{formato}.{ext}`. Si ya existe (`object_exists`), no se vuelve a correr el motor.
  - `app/core/storage.py::presigned_url` firma la URL con un cliente apuntado a `MINIO_PUBLIC_ENDPOINT` y con `minio_region` explícito (por defecto `us-east-1`).
  - La URL vence a los `MINIO_PRESIGNED_URL_EXPIRY` segundos (3600 en `.env.example`).
  - El frontend la abre con `window.open(url)` sin enviar el JWT: la firma autentica.
- **Configuración:** `MINIO_PUBLIC_ENDPOINT` se define en `.env.example` (`localhost:9000`) y se lee en `app/core/config.py`. El `README.md` del corte explica que, si falta, la URL se arma con `minio:9000` y ningún cliente externo puede resolverla. `docker-compose.yml` no la nombra: se carga desde `.env` vía `env_file`.

**Decisiones de diseño.**
- **Diagnóstico enriquecido:** según la bitácora v3 (2026-09-17), se exporta el diagnóstico y no el GeoJSON crudo, para que sirva para prescripción diferenciada.
- **Parámetro `indice` reservado** (solo `ndvi`): para no cambiar la URL cuando el motor consuma otros índices.
- **Ownership antes de la caché:** se separó `_resolver_lote_o_404` de `_generar_diagnostico_o_404` para verificar el lote sin correr el motor en cada request.

**Errores corregidos** ([`2079747`][2079747], según la bitácora):
- La URL firmada salía con host `minio:9000`, inaccesible desde fuera de Docker. Se resolvió con `MINIO_PUBLIC_ENDPOINT`.
- Firmar contra `localhost:9000` desde el contenedor fallaba con `MaxRetryError`, porque minio-py consultaba la región por HTTP. Se resolvió con `minio_region` explícito.

**Pruebas.** `tests/test_exportacion_api.py` (13):
- 404 por estado del vuelo, vuelo inexistente, lote inexistente, vuelo de otro lote y lote ajeno.
- Acceso sin autenticación.
- *Cache miss* (genera, sube y firma) y *cache hit* (no regenera).
- 501 para un índice que no es NDVI y 422 sin formato.

No corre en CI.

**Hallazgo clave:** la caché de exportación no se invalida. La clave de MinIO depende solo de usuario, lote, vuelo y formato, y ni `POST .../diagnostico/recalcular` ni ningún otro módulo borra ese objeto (se buscó `remove_object`, `delete_object` y la clave `export_` en `app/`). Después de recalcular un diagnóstico, `/zonas/export` sigue entregando el archivo anterior, mientras que `/zonas/geojson` y `/zonas/shapefile` sí reflejan el cálculo nuevo.

**No encontrado en el repo.** Exportación ISO-XML o ISOBUS (se buscó `iso.?xml|isobus` en `app/` y `workers/`; solo aparece en el texto de `LandingOriginal.jsx`). La presentación tampoco la promete; `docs/5_Plan_de_Releases.md` la deja como evolución futura.

#### Orden de trabajo en PDF (H12.2)

**Qué se implementó.** Un cálculo por unidad de manejo del producto a aplicar, la dosis por hectárea, el volumen total y los totales por producto ([`a2ec304`][a2ec304], PR #9). Los textos de restricciones ambientales e instrucciones de seguridad del catálogo ([`5d28b86`][5d28b86], PR #9). Un documento PDF con su endpoint ([`d7a91e7`][d7a91e7], PR #12), y la corrección de los totales sin dosis ([`b563527`][b563527], PR #13).

**Detalle técnico por capa.**
- **Base de datos:**
  - Migración **0018** (`0018_agregar_restricciones_y_seguridad_a_productos.py`, [`a2ec304`][a2ec304]): agrega `restricciones_ambientales` e `instrucciones_seguridad` (texto, nullable) a `productos_fitosanitarios`. Su downgrade borra las dos columnas.
  - Migración **0019** (`0019_cargar_restricciones_seguridad_productos_confirmados.py`, [`5d28b86`][5d28b86]): carga esos dos campos para 15 de los 21 productos. Su downgrade los vuelve a `NULL`.
  - Quedan sin datos, a propósito, Clorpirifos, Thiamethoxam, Ethephon 48 %, Tiidiazurón + Diurón, Sulfato de Magnesio y Boro foliar 17 %.
- **Cálculo** (`app/diagnostico/orden_trabajo.py::generar_orden_trabajo`, función pura):
  - Recorre las `unidades_manejo` del diagnóstico. Toma como producto el primero de `productos_sugeridos`.
  - Calcula **volumen total = `area_total_ha` × `dosis_referencia`** (redondeo a 3 decimales).
  - Agrupa los totales por producto. Si el producto no tiene dosis o no hay producto, la unidad se incluye igual con `sin_dosis_referencia=True` y `volumen_total=None`.
  - El "volumen total" es la cantidad de producto (dosis × superficie), no un volumen de caldo de aplicación.
- **API:**
  - `GET /api/v1/lotes/{lote_id}/vuelos/{vuelo_id}/orden-trabajo/pdf` (JWT; módulo propio `app/ordenes_trabajo/`).
  - Valida el lote del usuario y resuelve el vuelo dentro del lote vía `generar_diagnostico`.
  - Responde 404 si no hay `unidades_manejo` (todas las zonas en rangos normales) y 401 sin token.
  - `cargar_catalogo_dosis()` lee `dosis_referencia`, `unidad`, restricciones e instrucciones por nombre de producto.
- **Documento** (`app/ordenes_trabajo/templates/orden_trabajo.html`, Jinja2 + WeasyPrint, A4):
  - **Encabezado:** lote y datos del vuelo y del cultivo.
  - **Aviso de dosis pendiente:** si alguna unidad no tiene dosis de referencia, la cantidad "queda pendiente de completar a mano".
  - **"Dosis por unidad de manejo":** tabla con Unidad, Causa, Severidad, Área (ha), Zonas, Producto, Dosis/ha y Volumen total. Sin dosis se muestra "— (completar a mano)".
  - **"Totales por producto":** Producto, Área (ha) y Volumen total. Sin dosis, "— (completar a mano)" desde [`b563527`][b563527].
  - **"Seguridad y restricciones por producto":** los textos cargados, más un aviso con los productos sin ficha de seguridad confirmada.
  - **"Restricciones generales de aplicación — Ley 7032 (Chaco)":** tabla por artículo, marcada "PENDIENTE DE REVISIÓN LEGAL". Fuente: texto de la ley publicado por CASAFE.
- **Frontend:** botón "📋 Generar orden de trabajo" en `TablaDiagnostico.jsx`, visible solo si hay unidades de manejo (ver H13.2).

**Fuente de los datos.**
- `docs/investigacion_seguridad_fitosanitaria.md` ([`5d28b86`][5d28b86]) cita por producto:
  - el marbete SENASA con número de registro (por ejemplo RE-27899, RE-31742) cuando se encontró;
  - fichas técnicas u hojas de seguridad de fabricantes;
  - publicaciones de INTA (EEA Reconquista, EEA Sáenz Peña, INTA NEA);
  - la Ley 7032 de Chaco vía CASAFE.
- Cada dato tiene un nivel de confianza (🟢 / 🟡 / 🔴).
- El documento se declara "borrador para validación profesional".
- **No hay fuente ni carga de dosis**: ninguna migración, script, seed ni endpoint escribe `dosis_referencia` o `unidad`. `GET /api/v1/productos-fitosanitarios` es de solo lectura; se buscó escritura de esos campos en `app/`, `scripts/`, `workers/` y `migrations/`. Completarlos requiere SQL manual sobre la base.

**Decisiones de diseño.**
- Según la migración 0019 y la bitácora v3: no se cargó una estimación para los 6 productos sin fuente confirmada, para no guiar una aplicación real con texto no verificado.
- Según el docstring de `app/ordenes_trabajo/service.py`: el pipeline Jinja2 + WeasyPrint se duplicó a propósito respecto de `app/reportes/`, para mantener RFSA-04 como dominio propio.
- `GET` en lugar del `POST` que pedía la tarjeta, por coherencia con los demás endpoints de descarga (bitácora v3).

**Criterio del estado Parcial:** la historia promete "dosis por zona, volumen total e instrucciones de seguridad". El cálculo existe, pero como `dosis_referencia` no está cargada para ningún producto, al corte todas las unidades y todos los totales salen "— (completar a mano)": la orden no trae ninguna dosis ni volumen calculado. Las instrucciones de seguridad están para 15 de 21 productos.

**Pruebas.**
- `tests/test_orden_trabajo.py` (12): cálculo de volumen, restricciones, producto sin dosis, producto fuera de catálogo, unidad sin producto, totales y área total tratada.
- `tests/test_orden_trabajo_pdf_api.py` (8): genera un PDF real con WeasyPrint, con el diagnóstico y el catálogo simulados; 404 sin unidades, 404 por estado del vuelo y por vuelo de otro lote, 401 sin auth.
- Ninguno de los dos corre en CI.

**Errores corregidos.**
- La "Ley 6.312" se había tomado como ley de agroquímicos de Chaco y es de Santiago del Estero; la vigente en Chaco es la Ley 7032 ([`5d28b86`][5d28b86]).
- Los totales por producto mostraban "0.00" en lugar de "— (completar a mano)" para productos sin dosis, que podía leerse como "no aplicar nada" ([`b563527`][b563527], detectado en el QA de cierre según la bitácora).

#### Validación de índices y reglas del motor (H12.3)

**Qué se implementó.** Correcciones de índices y de clasificación que surgieron de revisar resultados con escenas reales, más la documentación legible de las 20 reglas ([`22d4ee9`][22d4ee9], PR #19). Asignado a H12.3 porque son los cambios que resultan de verificar que índices y reglas den resultados correctos.

**Detalle técnico** (según el código y la bitácora v3, 2026-09-21):
- **Otsu nunca había funcionado.**
  - `workers/gis/clasificacion.py` llamaba `threshold_multiotsu(validos, nclasses=4)`. En scikit-image el parámetro es `classes`, y el `except Exception` caía siempre a los umbrales fijos.
  - Se corrigió a `classes=4`; las demás excepciones ahora se loguean.
  - Según la bitácora, en un vuelo real se pasó de 1 zona a 9 zonas en 4 clases.
- **ExG normalizado:** `workers/gis/indices.py::calcular_exg` pasa de `2G − R − B` a `(2G − R − B) / (R + G + B)`. Así es comparable entre fechas y sensores.
- **Cortes fijos propios** en `_UMBRALES_POR_INDICE`:
  - **ExG:** 0,05 / 0,15 / 0,30, que reemplazan a Otsu.
  - **GNDVI:** 0,25 / 0,45 / 0,60, que reemplazan a los de NDVI.
  - Según la bitácora, ambos son una **calibración provisoria** sobre 3 escenas Sentinel-2. La escala orientativa de ExG "no tiene una fuente citada".
- **Datos guardados en el resultado:** el worker guarda en el GeoJSON los cortes usados (`umbrales`, `metodo_umbral`), y `MapaIndice.jsx` rotula la leyenda con ellos.
- **"Sin datos" medido:** `workers/gis/sin_datos.py` registra los píxeles sin dato y la parte del lote que el GeoTIFF no cubre (`sin_datos` en el resultado).
- **Absorción de huecos:** `app/ingesta/absorcion.py` rellena los huecos con la zona vecina con la que comparten más borde, solo al leer con `?absorber=true` y sin tocar `sin_datos`.
- **Nombres de las clases de valor:** en la interfaz pasan a "Muy bajo / Bajo / Medio / Alto" (`frontend/src/utils/clasesIndice.js`). Los identificadores internos no cambian.
- **`docs/reglas_diagnostico.md`** (284 líneas): tabla de las 20 reglas con orden, cultivo, estadios, índices, condición, confianza y causa, más la acción y la forma de confirmar en campo de cada una. Declara ser "Generado desde `app/diagnostico/reglas.py`", pero **no hay un script generador** en el repositorio (`scripts/` contiene `descargar_sentinel2_real.py`, `generar_geotiff_prueba.py`, `poc_reporte_pdf.py` y `poc_satelital_earthsearch.py`). Es documentación de las reglas, no un reporte de validación.

**Pruebas.**

| Archivo | Cambio | Qué cubre | En CI |
|---|---|---|---|
| `tests/test_clasificacion.py` | 16 → 20 | Regresión de Otsu (`test_otsu_es_adaptativo_y_no_cae_a_los_umbrales_fijos`) y cortes | Sí |
| `tests/test_indices_worker.py` | 20 → 22 | ExG normalizado | Sí |
| `tests/test_sin_datos.py` | 9 (nuevo) | Registro de "sin datos" | Sí |
| `tests/test_absorcion.py` | 12 (nuevo) | Absorción de huecos | **No** |
| `tests/test_estadios.py` | 5 (nuevo, en H11.2) | Que las 20 reglas puedan matchear con los estadios de su cultivo | No |

La bitácora afirma que `test_absorcion.py` corre en el job `test-gis`; en `ci.yml` del corte no figura.

**Criterio del estado Parcial:** la historia promete verificar que índices y reglas "producen resultados correctos", y los artefactos declarados son "Reporte de validación de índices espectrales" y "Reporte de validación de reglas del motor".
- Hay correcciones reales y tests de regresión de los índices.
- No hay reportes de validación: `docs/reglas_diagnostico.md` describe las reglas pero no las valida contra casos de campo.
- Los cortes nuevos de ExG y GNDVI están marcados como provisorios.
- La validación con ingeniero agrónomo que R2 dejó pendiente sigue sin rastro: la bitácora v3 la mantiene como problema abierto ("sin la validación de un ingeniero agrónomo matriculado").

**No encontrado en el repo.** Los reportes de validación de índices y de reglas como documentos (se buscó en `docs/`, `tests/` y en los mensajes de commit del rango).

### Estado de las historias

| Historia | Estado | Evidencia |
|---|---|---|
| H12.1 — Exportar zonas en formatos estándar | Completa | `app/reportes/exportacion.py` ([`706bc15`][706bc15], PR #7); `GET .../zonas/export` con URL firmada ([`2079747`][2079747], PR #11) |
| H12.2 — Orden de trabajo en PDF | Parcial | Cálculo ([`a2ec304`][a2ec304]), restricciones de 15/21 productos ([`5d28b86`][5d28b86], PR #9), documento y endpoint ([`d7a91e7`][d7a91e7], PR #12). Falta la dosis: `dosis_referencia` no está cargada y todas las cantidades salen "completar a mano" |
| H12.3 — Validación de índices y reglas | Parcial | Correcciones de Otsu, ExG y GNDVI, "sin datos" y `docs/reglas_diagnostico.md` ([`22d4ee9`][22d4ee9], PR #19). Faltan los reportes de validación y la validación agronómica; los cortes nuevos son provisorios |

### Resultado

Las zonas del diagnóstico salen del sistema en GeoJSON y Shapefile, con una URL de descarga firmada y cacheada. La orden de trabajo tiene su cálculo y su documento, pero sin dosis cargadas en el catálogo todas las cantidades quedan para completar a mano, y la sección legal está marcada como pendiente de revisión. La revisión de índices encontró que Otsu nunca había sido adaptativo y llevó a nuevos cortes para ExG y GNDVI, marcados como provisorios. Ninguno de los tests nuevos de exportación y orden de trabajo corre en CI.

---

## 4. Sprint 13 — Integración y cierre

| Sprint | Título | Fechas | Historias | RF/RNF |
|---|---|---|---|---|
| S13 | Integración y cierre | 8–22 sep 2026 | H13.1–H13.3 | RFSA-03, RFSA-01 |

### Objetivo

Unificar en la interfaz el diagnóstico y los archivos descargables, y cerrar la release con pruebas finales.

### Tareas realizadas

#### Reporte PDF ejecutivo desde el dashboard (H13.1)

**Qué se implementó.** Un reporte ejecutivo en PDF por vuelo, con el mapa de zonas, las estadísticas y el diagnóstico narrado:
- primero como prueba de concepto ([`36dc4b9`][36dc4b9]);
- después expuesto como endpoint ([`c9d2418`][c9d2418]), ambos en el PR #7;
- finalmente integrado al dashboard (H13.2).

Es el primer commit de R3 en git, aunque la presentación lo planifica para el S13.

**Detalle técnico por capa.**
- **API:**
  - `GET /api/v1/lotes/{lote_id}/vuelos/{vuelo_id}/reporte/pdf` (JWT, `app/reportes/router.py`). Devuelve `application/pdf` con el nombre `reporte_ejecutivo_{vuelo_id}.pdf`.
  - Usa `obtener_lote()` + `generar_diagnostico()`: el lote debe ser del usuario y el vuelo debe pertenecer a ese lote.
  - Responde 404 por estado del vuelo o por vuelo inexistente o ajeno, 401 sin token y 500 genérico si falla WeasyPrint.
  - La generación corre en `run_in_threadpool`.
- **Mapa en el servidor** (`app/reportes/mapa.py::generar_imagen_mapa_zonas`):
  - Dibuja con **Pillow** (`pillow==10.4.0`) los polígonos de las zonas, coloreados por clase o por severidad, como PNG.
  - Usa la misma proyección local de `app/diagnostico/forma.py` para la relación de aspecto, más una leyenda con la fuente DejaVu Sans.
  - No usa mapa base ni tiles: solo las zonas.
- **Documento** (`app/reportes/templates/reporte_ejecutivo.html` y `app/reportes/service.py::generar_pdf_reporte`, Jinja2 + WeasyPrint):
  - **Encabezado:** nombre del lote y fecha de generación.
  - **Mapa:** incrustado en base64.
  - **"Estadísticas por zona":** Zona, Área (ha), NDVI, Severidad, Causa probable, Confianza y Producto sugerido.
  - **"Diagnóstico agronómico por zona":** una subsección por zona con problema.
  - **Pie legal.**
- **Infraestructura:** `docker/Dockerfile.api` instala `libpango-1.0-0`, `libpangocairo-1.0-0`, `libpangoft2-1.0-0`, `libgdk-pixbuf-2.0-0`, `libcairo2` y `fonts-dejavu-core`, que WeasyPrint necesita a nivel de sistema. `weasyprint==63.1` ya figuraba en `docker/requirements.api.txt` desde R1, sin uso hasta ahora; `jinja2==3.1.4` es nueva.
- **Script:** `scripts/poc_reporte_pdf.py` (prueba de concepto standalone).

**Decisiones de diseño** (bitácora v3, 2026-09-10):
- Pillow y no matplotlib, porque matplotlib arrastra NumPy y el proceso de la API no lleva dependencias GIS pesadas.
- `GET` en lugar del `POST` que sugería la tarjeta, por tratarse de una operación de solo lectura.
- Nombre de archivo sin el nombre del lote, para evitar problemas de codificación en `Content-Disposition`.

**Pruebas.** `tests/test_reportes_api.py` (7): 404 por estado del vuelo, sin GeoJSON, lote o vuelo inexistente, vuelo de otro lote, y 401 sin auth. El camino feliz no tiene test automatizado: la bitácora registra una verificación manual con `curl` (200, PDF válido). No corre en CI.

**Errores corregidos** ([`36dc4b9`][36dc4b9], según la bitácora):
- `OSError: cannot load library 'libgobject-2.0-0'`: faltaban las librerías de sistema de WeasyPrint.
- Tildes corruptas en la leyenda del mapa con la fuente por defecto de Pillow.
- `KeyError: 'Usuario'` en el script, por un modelo no registrado.

#### Todas las descargas en un solo lugar (H13.2)

**Qué se implementó.** Los tres endpoints de descarga se conectaron a la interfaz ([`e8f8720`][e8f8720]), se agregó la previsualización de los PDF antes de descargarlos ([`6af36d4`][6af36d4]) y se ajustaron tipografías, íconos y botones ([`1094e0d`][1094e0d]), todo en el PR #13.

**Detalle técnico (frontend).**

| Descarga | Dónde está | Cómo funciona | Indicador mientras genera |
|---|---|---|---|
| Reporte PDF | Tabla "Análisis recientes" del Dashboard (`Dashboard.jsx`), por fila | `descargarReportePdf()` (blob, `frontend/src/api/reportes.js`); abre `ModalPreviewPdf.jsx` con el visor del navegador y un botón "Descargar PDF" que reutiliza el mismo blob | El botón con ícono se deshabilita (`disabled={descargando === ...}`); no hay texto ni spinner |
| GeoJSON / Shapefile | Misma tabla, botón "Exportar zonas" con un menú desplegable | `exportarZonas()` pide la URL firmada y la abre con `window.open` | El menú se cierra al elegir el formato, así que el estado deshabilitado no queda visible |
| Orden de trabajo PDF | Pestaña "Diagnóstico" de Resultados (`TablaDiagnostico.jsx` / `ResultadosVuelo.jsx`), junto a "↻ Recalcular" | `descargarOrdenTrabajoPdf()` → `ModalPreviewPdf.jsx` | Texto "Generando orden..." y botón deshabilitado |

Errores de descarga: `frontend/src/utils/descargarArchivo.js::extraerMensajeErrorBlob` extrae el `detail` de un error devuelto como blob. En el Dashboard se quitó el placeholder deshabilitado "Generar informe PDF" de "Acciones rápidas".

**Decisiones de diseño** (bitácora v3, 2026-09-17):
- Los botones van donde el vuelo ya está en contexto, no en "Acciones rápidas".
- La exportación usa un solo botón con un menú.
- Los PDF se previsualizan antes de descargar, para no ejecutar WeasyPrint dos veces.

**Criterio del estado Parcial:** la historia pide todas las descargas "en un solo lugar" y el artefacto, botones "con indicador de estado de carga".
- El reporte y la exportación están en el Dashboard, y la orden de trabajo en la vista de resultados.
- Solo la orden de trabajo muestra un indicador de progreso visible.

**Pruebas.** No hay tests de frontend para estos componentes.

#### Pruebas finales sin errores críticos (H13.3)

**Qué se implementó.** No hay un test automatizado nuevo del flujo completo.
- La bitácora v3 registra un "QA de cierre" (2026-09-17) sobre el reporte PDF, la exportación y la coherencia de la orden de trabajo (ver sección 5, "Verificaciones manuales").
- Cada funcionalidad de R3 trae su propio archivo de test en el mismo commit.

**Criterio del estado Parcial:** la historia y sus artefactos ("Tests end-to-end del flujo completo") piden pruebas finales del sistema completo.
- **E2E:** no hay un test E2E nuevo; el único sigue siendo el de R1 (`test_celery_integracion.py::test_ciclo_completo_encolar_y_esperar`), fuera del CI.
- **QA de cierre:** según la bitácora, usó un escenario sintético de 4 zonas procesado con las funciones reales, sin el motor de reglas ni la interfaz.
- **CI:** 138 de los 291 tests de Python y los 9 de Vitest no corren en CI, entre ellos los de todas las salidas de R3.
- **"Sin errores críticos":** no es verificable en el repositorio. Al corte siguen abiertos el IDOR de índices heredado de R1 y la orden de trabajo sin dosis (sección 6).

**No encontrado en el repo.** Un reporte de pruebas finales y la "Documentación de R3" fuera de la bitácora `docs/release-v3.0.0.md` (se buscó en `docs/` y en los mensajes de commit del rango).

#### Otros cambios del sprint

**Rediseño visual de landing, login y panel.** La presentación de R3 no lo incluye. La bitácora v3 lo registra como "Sprint 14 — Identidad visual unificada (landing, login y panel)", del 21 de septiembre. El trabajo entró por el PR #14 ([`49ba2d1`][49ba2d1], [`810d1bf`][810d1bf]), el PR #17 ([`8cdc575`][8cdc575], [`5bccebe`][5bccebe], [`c693592`][c693592]) y 4 commits directos a `main` ([`b5600bd`][b5600bd], [`09b4a74`][09b4a74], [`ffea4e2`][ffea4e2] y [`e863f45`][e863f45]).

| Pantalla o componente | Cambio | Commits |
|---|---|---|
| Landing | Queda una sola landing en `/`, `LandingOriginal.jsx` + `LandingOriginal.css`. Se elimina `Landing.jsx`, la variante rediseñada en el PR #14, descartada al resolver el merge según la bitácora. Foto de fondo con degradado, palabra dinámica con efecto de tipeo, barra superior que se achica al hacer scroll; se quitan las secciones de métricas, marquee, preguntas frecuentes, CTA final e impacto agronómico | PR #14, PR #17, [`b5600bd`][b5600bd] |
| Login | Mismo vidrio oscuro y foto que la landing, con barra superior y botón "Volver al inicio" | [`09b4a74`][09b4a74] |
| Panel (tema) | `frontend/src/panel-tema.css`: fondo claro (`#f3f6f3`) con barras lateral y superior oscuras; verde salvia (`#9cc2a8`) en lugar del verde lima; animación de entrada escalonada que respeta `prefers-reduced-motion` | [`ffea4e2`][ffea4e2], [`e863f45`][e863f45] |
| Dashboard (pantalla Resumen) | Portada con foto, saludo según la hora y los tres botones de acción (se elimina la tarjeta "Acciones rápidas"); tarjetas redondeadas; actividad reciente como línea de tiempo | [`ffea4e2`][ffea4e2], [`e863f45`][e863f45] |
| Botones | `BotonVolver.jsx`, con variantes oscura y clara, usado en login, detalle, resultados y el asistente de carga; tamaños y tipografía comunes para primario, secundario y peligro | [`ffea4e2`][ffea4e2] |
| Barra lateral | Usa el mismo `logo.png` que la landing y el login | [`ffea4e2`][ffea4e2] |

Las imágenes de la landing y del panel (por ejemplo `dashboard.jpeg` y `feature_*.jpg`) se agregaron en `frontend/public`, entre otros en [`c693592`][c693592], un commit de 57 archivos. `LandingOriginal.jsx` entra en [`8cdc575`][8cdc575] y `Landing.jsx` se elimina en [`5bccebe`][5bccebe]. La navegación unificada ([`a8cf16e`][a8cf16e]) se documentó en H11.3.

- **Badge de CI en el README** ([`896da6e`][896da6e], PR #7).
- **`.claude/` fuera del tracking de git** ([`76a54ef`][76a54ef], PR #12).

### Estado de las historias

| Historia | Estado | Evidencia |
|---|---|---|
| H13.1 — Reporte PDF ejecutivo desde el dashboard | Completa | `app/reportes/mapa.py`, `service.py` y la plantilla ([`36dc4b9`][36dc4b9]); `GET .../reporte/pdf` ([`c9d2418`][c9d2418]), PR #7; botón en el Dashboard ([`e8f8720`][e8f8720], PR #13) |
| H13.2 — Todas las descargas en un solo lugar | Parcial | [`e8f8720`][e8f8720], [`6af36d4`][6af36d4], [`1094e0d`][1094e0d] (PR #13). La orden de trabajo está en otra vista y solo ella muestra un indicador de carga |
| H13.3 — Pruebas finales sin errores críticos | Parcial | QA de cierre registrado en la bitácora (2026-09-17) y un test por funcionalidad. Falta el E2E del flujo completo y la ejecución en CI de los tests de R3 |

### Resultado

El reporte ejecutivo, la exportación de zonas y la orden de trabajo se pueden previsualizar y descargar desde la interfaz, en dos pantallas distintas. El reporte se genera en el servidor con un mapa propio dibujado con Pillow, sin depender de tiles externos. Las pruebas de cierre fueron manuales y sobre datos sintéticos, sin un E2E automatizado del flujo. El rediseño visual, que la presentación no menciona, se mergeó en los dos días previos al corte, en parte directo a `main`.

---

## 5. Calidad y estado al cierre

Al corte había 291 funciones de test de Python (R2 tenía 176) y 9 tests de frontend con Vitest, la primera suite de frontend del proyecto. R3 agregó 116 tests de Python, y `test_diagnostico_service.py` perdió uno.
- **Qué corre en CI:** el workflow de pruebas conserva sus 3 jobs (`test-api`, `test-gis`, `build-frontend`) y suma solo `test_cobertura_geotiff.py` y `test_sin_datos.py`. Ejecuta 153 de los 291 tests de Python y ninguno de Vitest.
- **Sin workflow de seguridad:** al corte no existe. `.github/workflows/security.yml` (SAST, SCA, secretos e imágenes) entra recién con [`697ca21`][697ca21] (PR #20), ya en R4.
- **Resultado del CI en el corte:** los tres jobs (`test-api`, `test-gis` y `build-frontend`) están en verde en `ba39b2a`, incluido el paso de migraciones de `test-api`; se verificó manualmente en GitHub Actions el 5 de octubre de 2026. Ese verde no cubre los 138 tests de Python ni los 9 de Vitest que no están en el workflow.

### Pruebas automatizadas

| Tipo | Herramienta | Tests | Resultado en el corte |
|---|---|---|---|
| Unitarias GIS (worker) | pytest | 64: `test_ndvi_pipeline` 4, `test_indices_worker` 22, `test_ingesta_worker` 3, `test_clasificacion` 20, `test_cobertura_geotiff` 4, `test_sin_datos` 9, configuración de Celery 2 | Job `test-gis` en verde en el corte |
| Unitarias del motor y de las salidas (sin base de datos) | pytest | 103: `test_diagnostico_engine` 14, `test_forma` 12, `test_texto` 26, `test_zonificacion` 19, `test_diagnostico_service` 2, `test_orden_trabajo` 12, `test_absorcion` 12, `test_satelital_catalogo` 6 | `engine` y `forma` (26): job `test-api` en verde en el corte. Los otros 77 no corren en CI |
| Integración HTTP contra PostGIS | pytest + TestClient | 121: `test_auth` 15, `test_lotes` 21, `test_vuelos_estado` 13, `test_ingesta` 4, `test_diagnostico_api` 10, `test_cultivos` 25, `test_estadios` 5, `test_exportacion_api` 13, `test_reportes_api` 7, `test_orden_trabajo_pdf_api` 8 | Los primeros cinco (63): job `test-api` en verde en el corte. Los de cultivos, estadios, exportación, reportes y orden de trabajo (58) no corren en CI |
| Worker con base de datos | pytest | 2: `test_lote_limites_worker` | No corre en CI; se saltea si no hay base |
| End-to-end | pytest (`test_celery_integracion.py::test_ciclo_completo_encolar_y_esperar`) | 1 (de R1, sin cambios) | Solo local; no corre en CI. No cubre diagnóstico ni salidas |
| Frontend | Vitest (`npm test`) | 9: `geometria.test.js` 5, `coordenadas.test.js` 4 | No corre en CI: el job `build-frontend` (en verde en el corte) solo ejecuta `npm run build` |
| Rendimiento y seguridad | — | — | Sin tests automatizados ni workflow de seguridad al corte |

La cobertura no se midió: no hay `pytest-cov` ni configuración de cobertura en el repositorio. Los tests se contaron leyendo las funciones `def test_` (y `it`/`test` en Vitest) del snapshot de `tests/` y `frontend/src/` en `ba39b2a`, sin ejecutarlos.

**Tests que no corren en CI (138 de Python):**

| Grupo | Archivo | Tests |
|---|---|---|
| Heredados de R2, todavía fuera del CI (47) | `test_texto.py` | 26 |
| | `test_zonificacion.py` | 19 |
| | `test_diagnostico_service.py` | 2 (eran 3 en R2) |
| Nuevos de R3 (90) | `test_cultivos.py` | 25 |
| | `test_exportacion_api.py` | 13 |
| | `test_orden_trabajo.py` | 12 |
| | `test_absorcion.py` | 12 |
| | `test_orden_trabajo_pdf_api.py` | 8 |
| | `test_reportes_api.py` | 7 |
| | `test_satelital_catalogo.py` | 6 |
| | `test_estadios.py` | 5 |
| | `test_lote_limites_worker.py` | 2 |
| E2E de R1 | `test_celery_integracion.py::test_ciclo_completo_encolar_y_esperar` | 1 |

**Autorización.** Los tests nuevos sí cubren la pertenencia de los datos al usuario, pero todos están fuera del CI:
- `test_exportacion_api.py`: vuelo de otro lote, lote ajeno y sin auth.
- `test_reportes_api.py` y `test_orden_trabajo_pdf_api.py`: vuelo de otro lote y sin auth.
- `test_cultivos.py`: cultivo de otro usuario, cultivo de otro lote y sin auth.
- `test_estadios.py`: sin auth.

### Verificaciones manuales

| Fecha | Verificación | Resultado (según la bitácora `docs/release-v3.0.0.md`, salvo indicación) |
|---|---|---|
| 10 sep | Reporte PDF contra dos vuelos reales de un lote | PDF de 2 páginas, con la geometría real, la tabla y el texto de diagnóstico correctos |
| 10 sep | `GET .../reporte/pdf` con `curl` | 200 con `application/pdf`; sin token → 401; lote o vuelo inexistente → 404 |
| 10 sep | Dibujo de lotes en el navegador | `POST /lotes` → 201 y `PUT /lotes/{id}` → 200 con la geometría correcta; envío bloqueado con polígono autointersectado y con área fuera de rango |
| 14 sep | Migración 0019 contra la base, con `psql` | Exactamente 15 de 21 productos con restricciones e instrucciones cargadas |
| 14 sep | Carga satelital de punta a punta en el navegador (mensaje de [`40c22b5`][40c22b5]) | Se eligió una escena con 0 % de nubes en lugar de la más cercana (58 %); vuelo creado y `completado` |
| 14 sep | Calendario satelital con datos reales (mensaje de [`3df345b`][3df345b]) | Días marcados correctamente en agosto y septiembre de 2026; miniaturas cargadas |
| 14 sep | Lote con polígono irregular de 8 vértices y carga satelital completa, tras [`dff6b83`][dff6b83] | La geometría del lote no cambió |
| 17 sep | `GET .../zonas/export` contra el stack real | URL `http://localhost:9000/...` descargable fuera del contenedor; segunda llamada con *cache hit* en ~40 ms |
| 17 sep | Orden de trabajo PDF revisada visualmente contra el stack | Tablas de dosis, severidad, aviso de dosis pendiente, seguridad y recuadro legal correctos en 2 páginas |
| 17 sep | QA de cierre: escenario sintético de 4 zonas procesado con las funciones reales (sin el motor de reglas ni la interfaz) | Reporte con mapa, KPIs, tabla y diagnóstico. Shapefile con WGS84, 4 archivos y los campos esperados (validación estructural, sin abrir QGIS). Dosis y volumen coherentes. Ambos PDF en A4 exacto (210 × 297 mm, leído con `pypdf` instalado solo para la prueba). Se detectó el "0.00" de los totales sin dosis |
| 20 sep | Migración 0020 sobre la base de desarrollo | 0 vuelos sin cultivo |
| 20 sep | Recorte de zonas al lote (escena Sentinel-2) | Zonas fuera del lote: 5,05 ha → 0 ha |
| 20 sep | Límite tomado de un GeoTIFF con una esquina sin dato | 7 vértices y 261 ha (cobertura real) en lugar de 4 vértices y 439 ha (rectángulo) |
| 21 sep | Otsu corregido sobre un vuelo ExG real | Umbrales `[0.0144, 0.0258, 0.0389]`: 9 zonas en 4 clases en lugar de 1 |
| 21 sep | Absorción de huecos | GNDVI: 41 huecos → 0; NDRE: 15 → 1 |
| 21 sep | Tabla "Análisis recientes" con un vuelo satelital | El vuelo llegaba a `completado` en ~21 s y la tabla no se refrescaba; corregido en [`c3aad69`][c3aad69] |

Ninguna de estas verificaciones tiene un script reproducible en el repositorio, salvo los scripts de prueba de concepto (`scripts/poc_reporte_pdf.py`, `scripts/poc_satelital_earthsearch.py`). No hay registro de un recorrido completo de la demo desde la interfaz.

### Errores corregidos durante el desarrollo

Ninguno afectó a una versión publicada. Los más relevantes:

- **El worker sobrescribía la geometría dibujada del lote** con el rectángulo del GeoTIFF, en vuelos de dron y de satélite. Se agregó `AND geometry IS NULL`. Según la bitácora, dos lotes de la base de desarrollo perdieron su polígono sin posibilidad de recuperarlo. Commit [`dff6b83`][dff6b83].
- **Otsu nunca había sido adaptativo:** `threshold_multiotsu(..., nclasses=4)` fallaba en silencio y caía a los umbrales fijos. Commit [`22d4ee9`][22d4ee9].
- **Los índices adicionales no se calculaban en los vuelos satelitales** (400 descartado en silencio por el frontend). Commit [`3f61826`][3f61826].
- **URL firmada inservible fuera de Docker** (host `minio:9000`) y `MaxRetryError` al resolver la región. Commit [`2079747`][2079747].
- **WeasyPrint sin librerías de sistema** (`OSError: cannot load library 'libgobject-2.0-0'`) y tildes corruptas en la leyenda del mapa. Commit [`36dc4b9`][36dc4b9].
- **Ley provincial mal identificada:** la 6.312 es de Santiago del Estero; en Chaco rige la 7032. Commit [`5d28b86`][5d28b86].
- **"0.00" en los totales de productos sin dosis** de la orden de trabajo. Commit [`b563527`][b563527].
- **Vuelo sin cultivo devolvía 500 en lugar de 409**, `ResultadosVuelo.jsx` buscaba el vuelo por `v.id`, y el lote con límite del GeoTIFF quedaba sin `area_ha`. Commit [`5be3b96`][5be3b96].
- **Bandas de Sentinel-2 de distinta resolución no apilables** en un solo GeoTIFF (según el docstring de `satelital_descarga.py`). Commit [`8304cb2`][8304cb2].
- **Tabla de análisis congelada en "Pendiente"** y mapa en blanco sin explicación en lotes de menos de 1 ha. Commit [`c3aad69`][c3aad69].

### Despliegue de la demo

Los pasos de instalación del `README.md` del corte no cambiaron respecto de R2 (la sección "Instalación" es idéntica entre `47994a4` y `ba39b2a`):
1. Clonar el repositorio y posicionarse en la versión: `git checkout v3.0.0` (tag sobre `ba39b2a`).
2. Crear `.env` a partir de `.env.example`, que ahora incluye `MINIO_PUBLIC_ENDPOINT`.
3. `docker compose up -d --build`, que reconstruye las imágenes de `api` y `frontend` por las dependencias nuevas.
4. Correr las migraciones a mano: `docker compose exec api alembic upgrade head`.
5. Verificar con `GET /api/v1/health`, `GET /api/v1/health/db` y Swagger en `/api/docs`, donde aparecen las rutas de reportes, órdenes de trabajo, cultivos y estadios.

El README suma el badge de CI y el comando `cd frontend && npm test` para los tests de Vitest.

Cambios respecto de R2:
- **Migraciones:** `upgrade head` aplica, en orden, la **0018** (columnas de seguridad en el catálogo), la **0019** (textos de 15 productos) y la **0020** (tabla `cultivos`, `vuelos.cultivo_id` y baja de 4 columnas de `lotes`, con backfill). La 0020 cambia el contrato de `/lotes`: un frontend de R2 contra una API de R3 deja de mostrar el cultivo del lote. Su downgrade pierde datos (ver H11.2).
- **Variables de entorno:** `MINIO_PUBLIC_ENDPOINT` (nueva, en `.env.example`); `minio_region` tiene valor por defecto en `app/core/config.py` y no figura en `.env.example`.
- **Dependencias de la API:** `jinja2==3.1.4`, `pillow==10.4.0`, `pyshp==2.3.1`. `weasyprint==63.1` ya estaba desde R1.
- **Dependencias del frontend:** `@geoman-io/leaflet-geoman-free ^2.20.0`, `geotiff ^2.1.3`, `proj4 ^2.12.1` y `vitest ^2.1.8` (desarrollo).
- **Dependencias del worker:** sin cambios; Earth Search se consulta con la biblioteca estándar.
- **Paquetes de sistema** (`docker/Dockerfile.api`): `libpango-1.0-0`, `libpangocairo-1.0-0`, `libpangoft2-1.0-0`, `libgdk-pixbuf-2.0-0`, `libcairo2` y `fonts-dejavu-core`.
- **Imágenes base:** sin cambios. MinIO sigue con `minio/minio:latest` (ver sección 6).
- **Servicios externos que necesita la demo:**
  - Esri World Imagery (tiles del mapa de dibujo y del mapa del NEA);
  - Nominatim (buscador);
  - OpenStreetMap (tiles de los demás mapas);
  - Earth Search y el bucket público de Sentinel-2 en AWS (vuelos satelitales).

  Ninguno requiere clave.

---

## 6. Deuda técnica y trabajo pendiente

Al cierre quedaron sin completar dos frentes:
- **Datos:** las dosis de referencia del catálogo, sin las cuales la orden de trabajo no calcula cantidades; las fichas de seguridad de 6 productos; y la revisión legal y agronómica de los textos.
- **Calidad:** los tests de todas las salidas de R3 fuera del CI, y la ausencia de un E2E.

Además, R3 introdujo un cambio de contrato sin versionar (migración 0020) y nuevas dependencias de servicios externos sin SLA.

### Defectos y riesgos conocidos

| Ítem | Descripción | Impacto | Estado |
|---|---|---|---|
| Orden de trabajo sin dosis | Ninguna migración, script ni endpoint carga `dosis_referencia` ni `unidad`; todas las cantidades y totales salen "— (completar a mano)". Solo se pueden cargar por SQL directo | Alto (funcional) | Abierto (sigue sin carga en `origin/main`) |
| Textos de seguridad incompletos y sin revisión | 6 de 21 productos sin restricciones ni instrucciones; `docs/investigacion_seguridad_fitosanitaria.md` es un "borrador para validación profesional"; la sección de la Ley 7032 del PDF está marcada "PENDIENTE DE REVISIÓN LEGAL" | Alto (legal y de seguridad) | Abierto |
| Tests de R3 fuera del CI | 90 tests nuevos de Python (todas las salidas, cultivos, satélite, estadios, absorción) y los 9 de Vitest no corren en `ci.yml`; los tests de autorización de los endpoints nuevos tampoco | Alto (regresiones no detectadas) | Abierto (siguen fuera de `ci.yml` en `origin/main`) |
| Cambio de contrato sin versionar | La migración 0020 quita `cultivo`, `variedad`, `fecha_siembra` y `estadio_fenologico` de `LoteResponse`, y vuelve obligatorio el estadio en la carga de vuelos, contra la regla de `CLAUDE.md` de no eliminar campos sin versionar | Medio (compatibilidad) | Abierto (decisión aceptada en la bitácora v3: el único cliente es el frontend) |
| Downgrade de la 0020 con pérdida de datos | Restaura solo el cultivo más reciente de cada lote, asigna "soja" a los lotes sin cultivo y pierde `fecha_cosecha`, los demás cultivos, `vuelos.cultivo_id` y el estadio del lote | Medio (reversibilidad) | Abierto |
| Caché de exportación sin invalidación | `/zonas/export` sirve el archivo cacheado en MinIO aunque se haya recalculado el diagnóstico | Medio (datos desactualizados en maquinaria) | Abierto |
| URLs firmadas como enlaces de portador | Quien tiene la URL de `/zonas/export` descarga el archivo sin autenticarse hasta que vence (`MINIO_PRESIGNED_URL_EXPIRY`, 3600 s en `.env.example`). Sin `MINIO_PUBLIC_ENDPOINT`, la URL se arma con `minio:9000` y es inutilizable fuera de Docker | Medio (seguridad / configuración) | Abierto (comportamiento por diseño, documentado en el README) |
| Servicios externos sin SLA ni alternativa | Esri World Imagery (sin manejo de error de tiles), Nominatim (política de uso de ~1 consulta/s), Earth Search (servicio "best effort" según la bitácora v3). Un timeout o error de red en la búsqueda de escenas no se captura y termina en un 500 genérico; solo "sin escenas" devuelve 404. En el worker, el error marca el vuelo como fallido | Medio (disponibilidad de la demo y del uso real) | Abierto |
| Validación de ubicación del GeoTIFF solo en el navegador | El chequeo de distancia de 1 km al lote está en `geotiffLimites.js`; la API acepta un GeoTIFF lejano si se la llama directo | Bajo | Abierto |
| Cortes provisorios de ExG y GNDVI | Calibrados con 3 escenas Sentinel-2; la escala de ExG no tiene fuente citada (bitácora v3). Los análisis ExG y GNDVI anteriores al cambio deben reprocesarse | Medio (interpretación agronómica) | Abierto |
| Exportación solo de NDVI | `/zonas/export` responde 501 para otros índices; el diagnóstico usa NDVI como partición de zonas | Bajo | Abierto |
| Geometrías perdidas en la base de desarrollo | Dos lotes quedaron con un rectángulo en lugar de su polígono, por la falla corregida en [`dff6b83`][dff6b83]; no hay historial de `geometry` | Bajo (datos de desarrollo) | Abierto (hay que redibujarlos) |
| IDOR en índices adicionales (heredado) | Ver la tabla de deuda heredada | Alto (seguridad) | Abierto al corte; corregido después en [`537f671`][537f671] (PR #49, 30 sep 2026) |

### Funcionalidades pendientes

| Ítem | Descripción | Release destino |
|---|---|---|
| Carga y edición de dosis de referencia | Completar `dosis_referencia` y `unidad` del catálogo, con fuente, para que la orden de trabajo calcule cantidades | A definir |
| Revisión legal y agronómica de la orden de trabajo | Validar la sección de la Ley 7032 y los textos de seguridad con un profesional matriculado | A definir |
| Exportación ISO-XML / integración con maquinaria | `docs/5_Plan_de_Releases.md` la deja como evolución futura | A definir |
| Exportación y diagnóstico multi-índice | Hoy la exportación es solo NDVI | A definir |
| Historial y trazabilidad de vuelos, análisis e índices | Objetivo 1 de R4 en la presentación de R3 | Release 4 |
| Comparación entre campañas sobre el mismo lote | Objetivo 2 de R4 en la presentación de R3 | Release 4 |
| Gestión centralizada de lotes, vuelos y análisis, con aislamiento entre usuarios | Objetivo 3 de R4 en la presentación de R3 | Release 4 |
| Validación del diagnóstico por el usuario y criterio técnico (RFDR-04) | Asignado a R5 por el plan de releases | Release 5, según `docs/5_Plan_de_Releases.md` |

### Deuda heredada de R2

| Ítem | Estado al corte de R3 | Estado actual (origin/main) | Evidencia |
|---|---|---|---|
| IDOR en índices adicionales (heredado de R1) | Abierto | Corregido | Al corte, `obtener_estado_analisis_indice(db, vuelo_id, indice)`; en `origin/main` recibe `lote_id` ([`537f671`][537f671], PR #49, 30 sep 2026) |
| Worker sin límite de memoria ni concurrencia acotada | Abierto | Abierto | `docker-compose.yml` sin `mem_limit` ni `--concurrency`, al corte y en `origin/main` |
| Certificado raíz de Avast en las tres imágenes | Abierto | Abierto | `docker/certs/avast-root.crt` copiado en los tres Dockerfiles, al corte y en `origin/main` |
| Imagen `minio/minio:latest` | Abierto | Corregido | Al corte `minio/minio:latest`; [`7e7182d`][7e7182d] (28 sep 2026) la reemplaza por `cgr.dev/chainguard/minio:latest` |
| Tests del motor fuera de CI (texto, zonificación, service) | Abierto | Abierto | Siguen fuera de `ci.yml` (47 tests al corte) |
| Cobertura insuficiente de la API nueva de R2 | Parcial | Parcial | `test_diagnostico_api.py` suma el caso con cultivo y el 409 ([`5be3b96`][5be3b96]); siguen sin test el 200 del diagnóstico, `POST .../recalcular`, `GET /productos-fitosanitarios` y `POST .../indices/batch` |
| Catálogo sin dosis ni fuente | Parcial | Parcial | Fuentes documentadas para restricciones y seguridad (SENASA, INTA, fichas técnicas, Ley 7032) en `docs/investigacion_seguridad_fitosanitaria.md` ([`5d28b86`][5d28b86]) y cargadas para 15/21 productos. `dosis_referencia` y `unidad` siguen vacías |
| Atributos del lote sin uso en el motor | Abierto | Abierto | `variedad` y `fecha_siembra` pasaron a `cultivos` y aparecen en la `metadata` del diagnóstico ([`5be3b96`][5be3b96]), pero ninguna regla las usa; `tipo_suelo` sigue sin uso en `app/diagnostico/` y `workers/` |
| Código muerto `app/diagnostico/productos.py` | Abierto | Abierto | El archivo existe y no se importa, al corte y en `origin/main` |
| Downgrades no reversibles (0012, 0013) | Abierto | Abierto | Sin cambios; se suma la 0020, cuyo downgrade pierde datos |
| Estadísticas sobre el raster decimado | Abierto | Abierto | Sin cambios en `workers/gis/pipeline.py` respecto de este punto |
| Ahorro de insumos (RFGL-05) | Abierto | Abierto | Sin referencias a "ahorro" en `app/` ni en `Dashboard.jsx` |
| Popup del mapa con confianza y producto | Abierto | Abierto | `MapaZonas.jsx::onEachZonaSeveridad` sigue sin confianza ni producto |
| Reglas configurables sin código | Abierto | Abierto | Las 20 reglas siguen como `condicion=lambda` en `app/diagnostico/reglas.py` |
| Test E2E del flujo con diagnóstico, en CI y con reporte | Abierto | Abierto | Sin E2E nuevo; `ci.yml` no corre el E2E de R1 |
| Validación del diagnóstico por el usuario y criterio técnico (RFDR-04) | Abierto | Abierto | Sin endpoint ni modelo de comentario o criterio técnico en `app/` |
| Historial de diagnósticos entre vuelos (RFGL-03) | Abierto | Abierto | `diagnosticos` sigue con índice único por `vuelo_id`. La 0021 de R4 agrega trazabilidad (`subido_por_id`, `motor_version`), no historial |
| Reporte ejecutivo PDF, exportación GeoJSON/Shapefile y orden de trabajo | Parcial | Parcial | Implementados en R3 (secciones 3 y 4); la orden de trabajo sin dosis |
| Dibujo del límite del lote sobre mapa satelital | Corregido (implementado) | Corregido (implementado) | [`eb16310`][eb16310] (PR #8) |
| Validación de índices y reglas del motor | Parcial | Parcial | Correcciones y tests de índices ([`22d4ee9`][22d4ee9]); sin reportes de validación ni validación agronómica |
| Registro desde la interfaz (heredado de R1) | Abierto | Abierto | El botón "Registrarse" de `Login.jsx` sigue sin handler |
| Usuario seed con credenciales conocidas (heredado de R1) | Abierto | Abierto | `migrations/versions/0006_seed_usuario_default.py` sin cambios |
| Archivos grandes en memoria (heredado de R1) | Mitigado | Mitigado | Sin cambios respecto de R2; sigue el riesgo del worker sin `mem_limit` |
| Dependencias sin fijar: `scipy` y `npm install` con rangos (heredado de R1) | Abierto | Abierto | `scipy` no está en `requirements.worker.txt`; `npm install` en `Dockerfile.frontend` y en `ci.yml`. R3 suma 4 dependencias de frontend con rango `^` |
| Migraciones manuales y downgrades incompletos (heredado de R1) | Abierto | Abierto | `docker-compose.yml` no corre Alembic; el README mantiene el paso manual |
| Severidad, zonificación de manejo y ahorro de insumos (heredado de R1) | Parcial | Parcial | Severidad y zonificación implementadas en R2; ahorro sin implementar |
| Roles y permisos (heredado de R1) | Abierto | Abierto | Sin roles en `app/auth/` |
| Testing E2E en CI y cobertura (heredado de R1) | Abierto | Abierto | Sin E2E en CI ni medición de cobertura |
| Zonas en PostGIS (heredado de R1) | Abierto | Abierto | La única columna geométrica sigue siendo `lotes.geometry` |
| Exportación PDF, Shapefile e ISO-XML (heredado de R1) | Parcial | Parcial | PDF y Shapefile implementados en R3; ISO-XML no existe |

### Compromisos de mejora de la release anterior

| Compromiso | Estado | Evidencia |
|---|---|---|
| Seguir documentando las decisiones técnicas antes de implementar | Parcial | La bitácora `docs/release-v3.0.0.md` documenta decisiones, errores y alternativas en los mismos commits de cada funcionalidad (por ejemplo [`eb16310`][eb16310], [`2079747`][2079747], [`5be3b96`][5be3b96]). Que se documentaran *antes* de implementar no es verificable en el repositorio |
| Revisar el trabajo de otros integrantes antes de cerrar una tarea | No verificable en el repo | 13 PRs (#7 a #19); las aprobaciones no se pudieron consultar. 5 commits entraron directo a `main` sin PR ([`b5600bd`][b5600bd], [`09b4a74`][09b4a74], [`ffea4e2`][ffea4e2], [`e863f45`][e863f45], [`a8cf16e`][a8cf16e]) |
| Dejar de postergar testing y documentación para el último sprint | Parcial | Cada funcionalidad de R3 trajo su test en el mismo commit: [`c9d2418`][c9d2418] (reportes), [`706bc15`][706bc15] (exportación), [`a2ec304`][a2ec304] y [`d7a91e7`][d7a91e7] (orden de trabajo), [`8304cb2`][8304cb2] (satélite), [`5be3b96`][5be3b96] (cultivos), [`22d4ee9`][22d4ee9] (absorción, sin datos). Pero 90 de esos tests no se agregaron al CI |
| Acumular menos tareas de cierre en el sprint final | No cumplido | Por orden de commits, los PRs #14 a #19 y los 5 commits directos a `main` entraron en los dos días previos al corte. Incluyen la migración 0020 ([`5be3b96`][5be3b96], 50 archivos), el rediseño visual y las correcciones de índices ([`22d4ee9`][22d4ee9]) |
| Definir criterios de aceptación más detallados antes de cada historia | No verificable en el repo | Las historias viven en Trello; la bitácora cita tarjetas por nombre, pero no sus criterios |
| Practicar la demo con todo el equipo | No verificable en el repo | — |
| Empezar a usar Trello para las historias | Cumplido | La bitácora v3 y `docs/investigacion_seguridad_fitosanitaria.md` citan tarjetas de Trello ("Exportación genérica + URLs de descarga", "Textos legales y de seguridad") |
| Empezar a usar Google Docs y dejar ClickUp | No verificable en el repo | — |
| Más reuniones durante el sprint, carga pareja y responder mensajes | No verificable en el repo | — |
| Test E2E en CI (incumplido en R2) | No cumplido | `ci.yml` del corte no corre ningún E2E |
| Cobertura completa (incumplido en R2) | No cumplido | Sin medición de cobertura |
| Tests del motor dentro del CI (incumplido en R2) | No cumplido | `test_texto.py`, `test_zonificacion.py` y `test_diagnostico_service.py` siguen fuera de `ci.yml` |

[09b4a74]: https://github.com/universoparalelo/Agronexo/commit/09b4a74
[1094e0d]: https://github.com/universoparalelo/Agronexo/commit/1094e0d
[2079747]: https://github.com/universoparalelo/Agronexo/commit/2079747
[22d4ee9]: https://github.com/universoparalelo/Agronexo/commit/22d4ee9
[36dc4b9]: https://github.com/universoparalelo/Agronexo/commit/36dc4b9
[3df345b]: https://github.com/universoparalelo/Agronexo/commit/3df345b
[3f61826]: https://github.com/universoparalelo/Agronexo/commit/3f61826
[40c22b5]: https://github.com/universoparalelo/Agronexo/commit/40c22b5
[47994a4]: https://github.com/universoparalelo/Agronexo/commit/47994a4
[49ba2d1]: https://github.com/universoparalelo/Agronexo/commit/49ba2d1
[537f671]: https://github.com/universoparalelo/Agronexo/commit/537f671
[5bccebe]: https://github.com/universoparalelo/Agronexo/commit/5bccebe
[5be3b96]: https://github.com/universoparalelo/Agronexo/commit/5be3b96
[5d28b86]: https://github.com/universoparalelo/Agronexo/commit/5d28b86
[697ca21]: https://github.com/universoparalelo/Agronexo/commit/697ca21
[6af36d4]: https://github.com/universoparalelo/Agronexo/commit/6af36d4
[706bc15]: https://github.com/universoparalelo/Agronexo/commit/706bc15
[76a54ef]: https://github.com/universoparalelo/Agronexo/commit/76a54ef
[7e7182d]: https://github.com/universoparalelo/Agronexo/commit/7e7182d
[810d1bf]: https://github.com/universoparalelo/Agronexo/commit/810d1bf
[8304cb2]: https://github.com/universoparalelo/Agronexo/commit/8304cb2
[896da6e]: https://github.com/universoparalelo/Agronexo/commit/896da6e
[8b5f698]: https://github.com/universoparalelo/Agronexo/commit/8b5f698
[8cdc575]: https://github.com/universoparalelo/Agronexo/commit/8cdc575
[a2ec304]: https://github.com/universoparalelo/Agronexo/commit/a2ec304
[a8cf16e]: https://github.com/universoparalelo/Agronexo/commit/a8cf16e
[b5600bd]: https://github.com/universoparalelo/Agronexo/commit/b5600bd
[b563527]: https://github.com/universoparalelo/Agronexo/commit/b563527
[ba39b2a]: https://github.com/universoparalelo/Agronexo/commit/ba39b2a
[c3aad69]: https://github.com/universoparalelo/Agronexo/commit/c3aad69
[c693592]: https://github.com/universoparalelo/Agronexo/commit/c693592
[c9d2418]: https://github.com/universoparalelo/Agronexo/commit/c9d2418
[d7a91e7]: https://github.com/universoparalelo/Agronexo/commit/d7a91e7
[dff6b83]: https://github.com/universoparalelo/Agronexo/commit/dff6b83
[e863f45]: https://github.com/universoparalelo/Agronexo/commit/e863f45
[e8f8720]: https://github.com/universoparalelo/Agronexo/commit/e8f8720
[eb16310]: https://github.com/universoparalelo/Agronexo/commit/eb16310
[ffea4e2]: https://github.com/universoparalelo/Agronexo/commit/ffea4e2
