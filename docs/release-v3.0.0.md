# Release v3.0.0 — Seguimiento

**Estado:** En desarrollo
**Rama principal:** `main`
**Inicio:** Sprint 11

---

## Sprint 11 — Reporte ejecutivo PDF

**Período:** 2026-09-10

### Tareas completadas

| Tarea | Estado |
|---|---|
| Instalar dependencias (WeasyPrint + Jinja2) y prueba mínima HTML→PDF | Completada |
| Diseñar el layout del reporte ejecutivo (header, mapa, estadísticas, diagnóstico) | Completada |
| Generar imagen estática del mapa de zonas para incrustar en el PDF | Completada |
| Endpoint de reporte ejecutivo PDF (`GET .../reporte/pdf`) | Completada |
| Dibujo de lote sobre mapa satelital → GeoJSON (alta y edición de límites) | Completada |
| Modelo y cálculo de la orden de trabajo (RFSA-04) — sin endpoint/UI todavía | Completada |
| Textos legales y de seguridad — carga parcial (15/21 productos) | Completada |
| POC: cargar vuelo desde imagen satelital (Earth Search, sin cuenta) | Completada |
| Endpoint + tarea Celery: cargar vuelo real desde imagen satelital | Completada |
| Frontend: opción "Imagen satelital" en el modal de carga de ortomosaico | Completada |
| Calendario con fechas marcadas + miniatura real por escena (feedback de usuario) | Completada |
| Fix: worker pisaba la geometry real de un lote con un rectángulo en cada vuelo | Completada |

#### Pipeline de generación de PDF (POC + template + mapa)
**Fecha:** 2026-09-10
**Rama:** `feat/reporte-pdf-poc`

POC del pipeline de reporte ejecutivo PDF: motor de diagnóstico (ya existente) → mapa PNG estático → template Jinja2 → WeasyPrint. Expuesto como script standalone (`scripts/poc_reporte_pdf.py`), sin endpoint HTTP todavía — eso queda para la tarjeta de backlog "Endpoint de reporte ejecutivo PDF".

Nuevo módulo `app/reportes/`:
- `mapa.py` — `generar_imagen_mapa_zonas()` dibuja las zonas del GeoJSON de diagnóstico como PNG, coloreadas por clase/severidad.
- `templates/reporte_ejecutivo.html` — layout Jinja2 con header, mapa embebido (base64), tabla de estadísticas por zona y diagnóstico narrado.
- `service.py` — `generar_pdf_reporte()` arma el contexto y llama a WeasyPrint.

**Decisiones tomadas:**
- Mapa estático generado con **Pillow**, no matplotlib — `app/diagnostico/service.py` y `app/diagnostico/forma.py` documentan que el proceso de FastAPI deliberadamente no lleva NumPy/GeoPandas a propósito (dependencias GIS pesadas reservadas al worker), y matplotlib arrastra NumPy como dependencia dura. Pillow dibuja polígonos rellenos sin esa dependencia.
- Reutiliza `proyectar_a_metros_locales()` de `app/diagnostico/forma.py` para el aspect ratio del mapa (misma proyección equirectangular local que ya usa el motor de diagnóstico, sin pyproj/GDAL).
- Misma paleta de colores que `frontend/src/components/MapaZonas.jsx` (`COLORES_CLASE`/`COLORES_SEVERIDAD`) para que el mapa del PDF sea visualmente consistente con el dashboard.
- `generar_pdf_reporte()` recibe directamente el dict de `generar_diagnostico()` — no vuelve a tocar DB ni MinIO, es una transformación pura de datos ya resueltos.
- POC como script standalone (no endpoint) — decisión explícita para no adelantar trabajo de la tarjeta de backlog siguiente.

**Error encontrado — WeasyPrint no podía importar sus librerías nativas**
```
OSError: cannot load library 'libgobject-2.0-0': libgobject-2.0-0: cannot open shared object file
```
La imagen `python:3.12-slim` de `docker/Dockerfile.api` solo instalaba `libpq-dev`/`gcc`/`ca-certificates` — WeasyPrint necesita Pango/Cairo/GDK-Pixbuf a nivel de sistema operativo, no solo el paquete Python. Se agregaron `libpango-1.0-0`, `libpangocairo-1.0-0`, `libpangoft2-1.0-0`, `libgdk-pixbuf-2.0-0`, `libcairo2` y `fonts-dejavu-core` (para la fuente usada en el template) al Dockerfile y se reconstruyó la imagen. Nota: en Debian trixie (base de la imagen actual) el paquete se llama `libgdk-pixbuf-2.0-0`, no `libgdk-pixbuf2.0-0` como en versiones anteriores de Debian/Ubuntu.

**Error encontrado — leyenda del mapa con tildes corruptas**
La leyenda PNG ("Crítica", etc.) se dibujaba con la fuente bitmap por defecto de Pillow (`ImageFont.load_default()`), que no soporta correctamente caracteres acentuados. Se resolvió cargando la misma fuente DejaVu Sans ya instalada para WeasyPrint (`/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf`) vía `ImageFont.truetype()`, con fallback a la fuente por defecto si el archivo no está presente.

**Error encontrado — `KeyError: 'Usuario'` al consultar Lote desde el script**
El script standalone importaba `app.lotes.service` pero no `app.auth.models`, así que la clase `Usuario` nunca se registraba en el registry declarativo de SQLAlchemy antes de resolver `Lote.usuario = relationship("Usuario", ...)`. En los routers de FastAPI esto nunca pasa porque `app/main.py` importa todos los routers (y transitivamente todos los modelos) al arrancar. Se resolvió agregando `import app.auth.models` al script antes de cualquier query.

Verificado end-to-end contra vuelos reales (`lote_id=1611cafc-f36f-4498-82f7-630ec9fa9657`, dos vuelos distintos) — PDF de 2 páginas, mapa con la geometría real del lote, tabla y texto de diagnóstico correctos.

#### Endpoint de reporte ejecutivo PDF
**Fecha:** 2026-09-10
**Rama:** `feat/reporte-pdf-poc`

`GET /api/v1/lotes/{lote_id}/vuelos/{vuelo_id}/reporte/pdf` — envuelve el pipeline del POC (ya probado con el script standalone) en un endpoint HTTP real. Nuevo `app/reportes/router.py`, montado en `app/main.py` bajo el mismo prefijo `/api/v1/lotes` que diagnóstico/ingesta/lotes.

**Decisiones tomadas:**
- **GET, no POST** — la tarjeta de Trello original sugería `POST /reportes/{ciclo_id}/pdf`, pero se optó por GET para mantener la misma convención que `GET .../diagnostico` (ya existente): es una operación de solo lectura (genera/recupera, no muta estado persistente propio), y un GET permite que el futuro botón del dashboard dispare la descarga con un simple link/`window.open()` en vez de manejar un blob desde una respuesta POST.
- Reutiliza `obtener_lote()` + `generar_diagnostico()` (mismo patrón de ownership y 404 que `app/diagnostico/router.py`) y el `generar_pdf_reporte()` del POC — el router no duplica ninguna lógica, solo orquesta.
- `generar_pdf_reporte()` (Jinja2 + WeasyPrint, CPU-bound y sync) se ejecuta con `run_in_threadpool`, mismo criterio que `_calcular_diagnostico` en `app/diagnostico/service.py`, para no bloquear el event loop de FastAPI.
- Nombre de archivo de descarga simplificado a `reporte_ejecutivo_{vuelo_id}.pdf` (sin el nombre del lote) para evitar problemas de encoding en el header `Content-Disposition` con nombres que tengan tildes/ñ.

**Verificación:**
- `docker compose logs api` confirmó hot-reload del nuevo router sin necesidad de rebuild (`app/` es volumen live).
- Probado manualmente con `curl` autenticado contra un vuelo real: `200 OK`, `content-type: application/pdf`, PDF válido y descargable.
- Casos de error probados: sin token → `401`; lote inexistente → `404`; vuelo inexistente → `404`.
- `tests/test_reportes_api.py` (7 tests, mismo criterio que `test_diagnostico_api.py`: vuelos insertados directo en BD, sin MinIO/Celery) — cubre 404 por estado del vuelo, geojson faltante, lote/vuelo inexistente, ownership (vuelo de otro lote) y 401 sin auth. Los 7 pasan. El camino feliz (PDF real) queda cubierto por la verificación manual de arriba, mismo criterio que `test_diagnostico_api.py` para su propio camino feliz.

#### Dibujo de lote sobre mapa satelital → GeoJSON
**Fecha:** 2026-09-10
**Rama:** `feat/dibujo-lote-mapa`

Reemplaza la carga manual de GeoJSON como único método para definir el límite de un lote: ahora se puede dibujar directamente sobre un mapa satelital (Leaflet + leaflet-geoman, tiles Esri World Imagery + capa de referencia de límites/toponimia con toggle). El upload manual de `.geojson` se mantiene como fallback. Integrado tanto en el alta de lote (`ModalNuevoLote`) como en la edición de límites de un lote existente (`ModalLimites`, con la geometría previa precargada para editar).

**Decisiones tomadas:**
- `leaflet-geoman-free` sobre `leaflet-draw`: mejor mantenido, compatible con React 18 / Leaflet 1.9.x ya usados en el proyecto.
- Esri World Imagery + capa de referencia `World_Boundaries_and_Places` (mismo proveedor, sin API key) para una vista híbrida con límites político-administrativos y nombres de ciudades, con toggle para ocultarla al dibujar de cerca.
- Un solo polígono activo por lote: la figura nueva reemplaza a la anterior en el mapa.
- Área geodésica calculada en el cliente con la fórmula de exceso esférico (la misma que usa `Leaflet.draw`'s `GeometryUtil`) — `geoman-free` no expone un helper de área propio, y esto evita sumar una dependencia como turf solo para esto.
- Rango de área razonable (0.5–5000 ha) validado en frontend (feedback inmediato) y en backend (`app/lotes/service.py`), reutilizando el área que ya calcula PostGIS (`ST_Area` sobre UTM 21S) en vez de duplicar lógica geodésica en Python.
- Autointersección detectada en el cliente con un chequeo O(n²) de cruce de segmentos (`frontend/src/utils/geometria.js`), por la misma razón de no sumar turf. El backend igual la rechaza vía `Polygon.is_valid` de Shapely como red de seguridad ante geometría subida a mano o pegada directo a la API.
- La lógica geométrica pura (área, autointersección) se separó del componente de mapa a `frontend/src/utils/geometria.js` específicamente para poder testearla con Vitest sin necesitar jsdom ni mockear Leaflet.

**Verificación:**
- Backend: 6 tests nuevos en `tests/test_lotes.py` (geometría autointersectada → 422; área muy chica/muy grande → 400 tanto al crear como al editar). 21/21 tests pasan.
- Frontend: primer test suite del proyecto (`vitest`, `npm test` en `frontend/`) — `frontend/src/utils/geometria.test.js`, 5 tests (área geodésica vs. aproximación plana, autointersección en rectángulo/bowtie/triángulo).
- Probado manualmente en el navegador: alta de lote dibujando el polígono (`POST /lotes` → 201 con la geometría correcta), edición de límites de un lote existente con la geometría precargada (`PUT /lotes/{id}` → 200), bloqueo del submit con polígono autointersectado y con área fuera de rango.

#### Modelo y cálculo de la orden de trabajo (RFSA-04)
**Fecha:** 2026-09-14
**Rama:** `feat/orden-trabajo-modelo`

Primera mitad de la tarjeta de Trello "Modelo y cálculo de la orden de trabajo": estructura de datos + lógica pura de cálculo de dosis/volumen por unidad de manejo. Sin endpoint ni UI todavía — eso queda para las tarjetas de backlog "Documento y endpoint de orden de trabajo PDF" e "Integración en el dashboard".

- Migración `0018`: agrega `restricciones_ambientales` e `instrucciones_seguridad` (Text, nullable) a `productos_fitosanitarios` — el catálogo (migración 0015) no tenía estos campos y RFSA-04 los pide explícitamente. Los 21 productos seed quedan con estos campos en `NULL`, a completar manualmente por ficha técnica.
- `app/diagnostico/schemas.py`: nuevos `OrdenTrabajoItem`, `TotalProducto`, `OrdenTrabajoResponse`.
- Nuevo módulo puro `app/diagnostico/orden_trabajo.py::generar_orden_trabajo()` — toma `unidades_manejo` (salida ya existente de `zonificacion.py`) + un catálogo de dosis, y calcula por unidad: producto elegido, dosis/ha, volumen total (`area_total_ha × dosis_referencia`), restricciones e instrucciones de seguridad, más totales agregados por producto para todo el lote.

**Decisiones tomadas:**
- Producto por unidad = el primero de `productos_sugeridos` (ya resuelto por el motor de reglas vía `causa_indice`) — no hay selección múltiple ni UI de por medio en esta tarjeta.
- Unidad sin producto sugerido, o producto sin `dosis_referencia` cargada en BD, no se descarta: se incluye en la orden con `sin_dosis_referencia=True` y `volumen_total=None`, para que la cantidad se complete a mano en vez de perderse silenciosamente.
- Función pura sin DB (mismo criterio que `zonificacion.py`) — no se conectó todavía a `service.py` ni a un endpoint, ya que la tarjeta es explícitamente solo "modelo y cálculo".

**Verificación:**
- `tests/test_orden_trabajo.py` (12 tests, mismo patrón que `test_zonificacion.py`): unidad simple, agrupación de totales por producto, producto fuera de catálogo, producto sin dosis, unidad sin producto sugerido, suma de área total tratada. Los 12 pasan.

#### Textos legales y de seguridad (RFSA-04) — carga parcial
**Fecha:** 2026-09-14
**Rama:** `feat/orden-trabajo-modelo`

Investigación y carga de `restricciones_ambientales`/`instrucciones_seguridad` (campos agregados en `0018`) para el catálogo de 21 productos fitosanitarios.

- `docs/investigacion_seguridad_fitosanitaria.md`: investigación por producto (marbete SENASA cuando había RE disponible, fichas técnicas/SDS de fabricantes, Ley 7032 de Chaco como marco general) con nivel de confianza marcado por fila (🟢/🟡/🔴).
- Migración `0019`: carga los 15 productos con fuente confirmada (🟢/🟡). Los 6 restantes (Clorpirifos, Thiamethoxam, Ethephon 48%, Tiidiazurón + Diurón, Sulfato de Magnesio, Boro foliar 17%) quedan en `NULL` a propósito — no se encontró ficha de seguridad específica que los respalde.

**Decisiones tomadas:**
- No cargar una estimación sin marcar para los 6 productos sin fuente confirmada — mejor dejarlos pendientes y visibles que completar el campo con texto no verificado que termine guiando una aplicación real de agroquímico.
- Las restricciones generales de la Ley provincial (distancias de aplicación, receta agronómica obligatoria, prohibición a menores/embarazadas) no se cargan por producto — aplican a cualquier aplicación, no son un dato específico de cada fila del catálogo. Queda como nota de diseño para cuando se conecte esto al endpoint/dashboard.

**Error encontrado — ley provincial mal identificada**
Se había asumido sin verificar que la Ley 6.312 era la ley de agroquímicos de Chaco. Al bajar el PDF real resultó ser la ley de **Santiago del Estero** (mismo número, provincia distinta — los números de ley no son únicos entre provincias). La ley vigente en Chaco es la **Ley 7032 — Ley de Biocidas** (2012), verificada contra el texto completo publicado por CASAFE. Corregido en el documento de investigación; pendiente corregir también la descripción de la tarjeta de Trello, que todavía cita "Ley 6.312".

**Verificación:**
- Migración `0019` corrida contra la BD (`docker compose exec api alembic upgrade head`) — verificado con `psql` que exactamente 15/21 productos tienen ambos campos poblados y los otros 6 siguen en `NULL`.
- `tests/test_diagnostico_api.py` y `tests/test_orden_trabajo.py` (20 tests) siguen pasando sin cambios.

#### POC: cargar vuelo desde imagen satelital (Earth Search)
**Fecha:** 2026-09-14
**Rama:** `feat/poc-satelital-earthsearch`

Objetivo: evaluar si es viable ofrecer, además de subir un GeoTIFF de dron, la opción de cargar un vuelo a partir de una imagen satelital Sentinel-2, dejando que el usuario elija la fecha y vea la nubosidad antes de confirmar (si está nublado, elige otra fecha).

`scripts/poc_satelital_earthsearch.py` extiende el script existente `scripts/descargar_sentinel2_real.py` (agregado en `c5e41ae`, ago-2026) en dos puntos:
- Búsqueda por **ventana de fechas** alrededor de la fecha elegida por el usuario (no solo "la más reciente") vía el catálogo STAC de [Earth Search (Element84)](https://earth-search.aws.element84.com/v1) — imprime todas las escenas candidatas con su fecha real y % de nubosidad.
- Recorte al **polígono real del lote** (`rasterio.mask`), no solo al bbox rectangular como hacía el script original.

Probado contra el lote real "Lote Nuevisimo" (`a9f9c87d-...`, 1.2645 ha dibujado a mano con leaflet-geoman) pidiendo la fecha `2026-08-03`.

**Decisiones tomadas:**
- **Earth Search (AWS Open Data) en vez de Copernicus Data Space Ecosystem** — no requiere cuenta, OAuth2 ni credenciales de ningún tipo; el bucket de datos (`e84-earth-search-sentinel-data`) es público, `RequesterPays: False`, sin costo. Copernicus queda documentado como plan B (ver "Problemas abiertos") si la disponibilidad de Earth Search se vuelve un problema.
- El GeoTIFF de salida usa el mismo mapeo de bandas que `sensor="sentinel2"` en `workers/gis/band_mapping.py` (ya existente, no hubo que tocarlo) — el pipeline completo de procesamiento (`procesar_vuelo`, cálculo de índices) no necesita ningún cambio, solo el paso previo de conseguir el archivo.

**Error encontrado — bandas de Sentinel-2 a distinta resolución nativa**
```
ValueError: could not broadcast input array from shape (9,9) into shape (17,17)
```
Blue/Green/Red/NIR son 10 m/px pero RedEdge (B05) es 20 m/px — leer cada banda a su resolución nativa produce arrays de distinto tamaño para la misma área geográfica, que no se pueden apilar en un único GeoTIFF multibanda. Se resolvió pasando `out_shape` explícito (calculado desde el bbox en metros / 10 m) a cada `src.read()`, forzando remuestreo bilineal de todas las bandas a una grilla común de 10 m sin importar su resolución nativa.

**Verificación:**
- Búsqueda por fecha: con fecha elegida `2026-08-03` (ventana ±15 días) se encontraron 8 escenas; la más cercana (2026-08-01) tenía 58% de nubes y quedó marcada por sobre el umbral, mostrando como alternativa la del 2026-08-06 con 0.004% de nubes — confirma que el flujo "elegir otra fecha si está nublado" funciona con datos reales.
- Recorte al polígono: el GeoTIFF de salida tiene 126 píxeles con datos de 256 en la ventana total — 126 × 100 m² = 1.26 ha, coincide con el área real del lote (1.2645 ha) casi exacto.
- Sanity check agronómico: NDVI promedio ~0.005 (suelo prácticamente desnudo) para una escena de agosto (invierno) — coherente con que los cultivos de verano del NEA (soja/maíz/algodón/sorgo) todavía no están sembrados en esa fecha.

**Pendiente (no es parte de este POC):** conectar esto a un endpoint real (`GET` de escenas disponibles + tarea Celery que descargue, suba a MinIO y encole `procesar_vuelo`) y al frontend (mapa autocentrado en el lote + selector de fecha). Ver desglose completo de tareas en la conversación de esta sesión — no repetido acá para no duplicar.

#### Endpoint + tarea Celery: cargar vuelo real desde imagen satelital
**Fecha:** 2026-09-14
**Rama:** `feat/poc-satelital-earthsearch`

Conecta el POC (ver tarea anterior) a la aplicación real: dos endpoints nuevos en `app/ingesta/router.py` bajo el mismo prefijo `/lotes` que el resto de ingesta, y una tarea Celery nueva — sin tocar el pipeline de procesamiento existente.

- `GET /lotes/{lote_id}/vuelos/imagenes-satelitales?fecha=...&ventana_dias=...` — corre **síncrono en FastAPI** (no en Celery): solo consulta el catálogo STAC de Earth Search (HTTP + JSON, sin rasterio), no es "procesamiento de GeoTIFF". Devuelve las escenas candidatas con su nubosidad para que el usuario elija.
- `POST /lotes/{lote_id}/vuelos/desde-satelite` (`{escena_id, fecha_vuelo, estadio_fenologico?}`) — crea el `Vuelo` (sensor=`sentinel2`) y encola `workers.gis.tasks.descargar_satelital`.
- Nuevo `workers/gis/tasks.py::descargar_satelital` — descarga+recorta la escena elegida (reconsultando el item por id para tener URLs de assets frescas), la sube a MinIO con la misma convención de key que un upload de dron, actualiza `vuelo.task_id` a la tarea de procesamiento que encola después (si no, el polling de `/estado` se queda mirando una tarea ya terminada) y llama a `procesar_vuelo` — de ahí en más, mismo pipeline sin cambios.
- Módulos nuevos en `workers/gis/`: `satelital_catalogo.py` (solo `urllib`/`json`/`datetime`, sin rasterio — importable también desde FastAPI) y `satelital_descarga.py` (rasterio/numpy, worker-only). Reusan `band_mapping.py::MAPEO_SENSORES["sentinel2"]` como única fuente de verdad del orden de bandas, en vez de duplicar el mapeo como hacía el script del POC.

**Decisiones tomadas:**
- Separar el módulo de catálogo (liviano) del de descarga (pesado) — el proceso FastAPI deliberadamente no tiene rasterio/numpy instalado (mismo criterio que `app/diagnostico/service.py`/`forma.py`), así que un solo archivo con `import rasterio` a nivel de módulo habría roto el import del endpoint de búsqueda.
- La búsqueda de escenas no se encolá en Celery — es una consulta HTTP liviana, no viola la regla "el procesamiento de GeoTIFF nunca ocurre en FastAPI" del CLAUDE.md porque no hay GeoTIFF de por medio en ese paso.
- `descargar_satelital` reconsulta la escena por id en vez de recibir las URLs de los assets por parámetro — evita pasar URLs largas por la cola de Celery y son válidas más tiempo cerca del momento de descarga real.

**Error encontrado — validación de "imagen vacía" rechazaba cualquier GeoTIFF Sentinel-2 real**
```
ValueError: La imagen no tiene píxeles con datos válidos — el archivo está vacío.
```
`_validar_geotiff_gis_desde_src()` en `workers/gis/tasks.py` siempre muestreaba la **banda 1** para detectar archivos vacíos. Pero el mapeo `sentinel2` de `band_mapping.py` deja la banda 1 sin usar a propósito (BLUE arranca en la posición 2, replicando la numeración real de Sentinel-2 donde la banda 1 es Coastal Aerosol) — cualquier GeoTIFF generado con esa convención se rechazaba como "vacío" aunque el resto de las bandas tuviera datos reales. Bug preexistente (afectaba también a `scripts/descargar_sentinel2_real.py`, nunca ejercitado antes end-to-end), no introducido por esta tarea, pero la bloqueaba por completo. Se corrigió recorriendo todas las bandas hasta encontrar la primera con datos válidos, en vez de asumir que siempre es la banda 1.

**Verificación (end-to-end, contra la app real corriendo, no mocks):**
- `GET .../imagenes-satelitales?fecha=2026-08-03&ventana_dias=15` contra el lote real "Lote Nuevisimo" → 200, mismas 8 escenas que el POC, con la del 2026-08-01 marcada con 58% de nubes.
- `POST .../desde-satelite` con la escena del 2026-08-06 (0.004% nubes) → 202, `Vuelo` creado.
- Polling de `GET .../estado` → `descargar_satelital` completa en ~12s, encola `procesar_vuelo`, que completa sin error tras el fix de validación. Estado final: `completado`.
- `GET .../resultado` → GeoJSON real con 1 zona, `area_ha=1.71`, `ndvi_promedio=0.59` ("normal") — confirma que el NDVI se calculó de verdad sobre la imagen satelital descargada, no es un mock.
- **Nota operativa:** el worker Celery no tiene hot-reload — una tarea `@celery_app.task` nueva no se registra hasta reiniciar el proceso (`docker compose restart worker`). El primer intento falló con `KeyError` / "Received unregistered task" hasta reiniciar.
- `tests/test_satelital_catalogo.py` (6 tests, mockeando la llamada HTTP) + suite existente de ingesta/diagnóstico/lotes (51 tests) + `tests/test_ingesta_worker.py` y `tests/test_ndvi_pipeline.py` (worker) — todos pasan, sin regresiones por el fix de validación.

**Pendiente:** frontend (selector "Dron / Satélite" en el modal, mapa autocentrado en el lote, selector de fecha con las escenas devueltas) — el backend ya está completo y probado.

#### Frontend: opción "Imagen satelital" en el modal de carga
**Fecha:** 2026-09-14
**Rama:** `feat/poc-satelital-earthsearch`

Cierra la feature de punta a punta: `ModalCargaGeoTIFF.jsx` ahora tiene un selector "🚁 Subir archivo (dron)" / "🛰️ Imagen satelital" (mismo patrón visual que el toggle "Dibujar / Subir GeoJSON" de `ModalLimites.jsx`). En el modo satelital:

- Mapa autocentrado en la geometría real del lote (reusa el patrón `FitBounds`/`boundsDesdePoligono` ya duplicado en `ModalLimites.jsx`/`ModalNuevoLote.jsx`/`MapaDibujoLote.jsx` — cuarta vez que se repite, sin extraerlo a un módulo compartido todavía) — es justo el pedido original: "que aparezca automáticamente un mapa ya con el campo en vista".
- Selector de fecha + botón "Buscar imágenes" → `GET .../imagenes-satelitales`, muestra las escenas encontradas como tarjetas con fecha, % de nubosidad y distancia en días a la fecha pedida, para que el usuario elija otra si la más cercana está nublada (igual que se probó por API en la tarea anterior).
- El botón "🛰️ Imagen satelital" se deshabilita (con tooltip explicativo) si el lote elegido no tiene `geometry` cargada — no se puede buscar ni recortar sin un polígono.
- Paso 2 (configuración de análisis): mismo selector de índices que para dron (Sentinel-2 tiene las mismas bandas disponibles), la fecha del vuelo se autocompleta con la fecha real de la escena y queda no editable (evita que quede una fecha inventada distinta a la captura real).
- `handleSubmit` llama a `POST .../desde-satelite` en vez de subir un archivo — sin barra de progreso de bytes (no hay upload del lado del cliente), directo a "Descargando y recortando la imagen satelital...".

**Decisiones tomadas:**
- Sensor forzado a `sentinel2` en modo satelital (sin selector manual) — es lo único que este flujo puede producir.
- No se armó un componente de mapa reutilizable nuevo — se siguió el patrón ya establecido en el proyecto de duplicar el pequeño `FitBounds` local en cada modal en vez de crear una abstracción compartida prematura.

**Verificación:**
- `npm run build` (Vite) sin errores.
- Probado manualmente en el navegador contra la app real: seleccioné "Lote Nuevisimo", el botón satelital estaba habilitado (tiene geometry) y deshabilitado para lotes sin límite (ej. "Lote Sur"); mapa mostró el polígono real sobre imagen Esri World Imagery; busqué escenas para `2026-08-03` y aparecieron las mismas 8 escenas ya validadas por API; elegí la del `2026-08-06` (0% nubes) en vez de la más cercana (58% nubes); completé el wizard → vuelo creado, visible en el dashboard como "Pendiente" y confirmado luego como `completado` vía API, con `fecha_vuelo` igual a la fecha real de la escena elegida.

#### Calendario con fechas marcadas + miniatura real por escena
**Fecha:** 2026-09-14
**Rama:** `feat/poc-satelital-earthsearch`

Feedback directo tras probar la tarea anterior: el `<input type="date">` nativo no daba ninguna pista de qué fechas tenían imagen disponible, y el mapa de referencia (basemap Esri genérico) no reflejaba la escena elegida — parecía "no actualizarse", pero en realidad nunca estuvo conectado a la escena puntual.

- Nuevo componente `frontend/src/components/CalendarioSatelital.jsx` — reemplaza el input nativo. Al abrirse (o cambiar de mes) busca escenas en una ventana de ~20 días centrada en el día 15 del mes visible y pinta los días: verde si hay imagen con ≤30% de nubes, ámbar si hay imagen pero muy nublada, sin marca si no hay escena ese día. Clic en un día marcado dispara la búsqueda real (±15 días) igual que antes, poblando la lista de tarjetas debajo.
- `EscenaSatelitalItem` (`app/ingesta/schemas.py`) suma `thumbnail_url` — Earth Search expone un asset `thumbnail` (JPG chico, `preview.jpg`) por escena además de las bandas individuales; no hace falta descargar ni procesar nada para mostrarlo. Cada tarjeta de escena en el modal ahora muestra esa miniatura real junto a la fecha y el % de nubes — se ve literalmente si está nublado o no, no solo el número.

**Decisiones tomadas:**
- Calendario propio en vez de sumar una librería de datepicker — ningún navegador permite marcar días dentro de su calendario nativo (`<input type="date">`), así que de cualquier forma había que reemplazarlo por un componente propio; dado eso, no se justificaba sumar una dependencia nueva de UI (primera de este tipo en el frontend) para algo que se resuelve con un grid de mes simple.
- Fechas calculadas con año/mes/día locales a mano (`fechaISOLocal()`), no `Date#toISOString()` — ese método normaliza a UTC y puede correr la fecha un día para atrás en husos horarios positivos.
- El basemap del mapa de referencia se mantiene genérico (Esri, sin fecha) — mostrar la imagen real de la escena elegida como capa del mapa (no solo como miniatura chica) queda pendiente, requiere renderizar el raster Sentinel-2 real como overlay en vez de una URL de tile fija.

**Verificación:**
- Probado en el navegador: mes actual (septiembre 2026) marcó los días 2, 5 y 10 en verde; al navegar a agosto 2026 marcó el día 1 en ámbar (58% nubes, confirmado con `curl` contra el endpoint) y varios días en verde (6, 11, 13, 16, 21, 26); clic en un día disparó la búsqueda automática y mostró la lista con miniaturas reales — la escena de 99.9% de nubes se ve directamente blanca, la de 0% se ve el campo verde.
- Verificado con JS en consola del navegador que las miniaturas cargan (`complete: true`, `naturalWidth: 343`) pese a que el listado de network requests del panel no las mostraba (limitación de esa herramienta con cargas de `<img>`, no señal de un problema real).
- `npm run build` sin errores; suite de tests backend (`test_ingesta.py`, `test_satelital_catalogo.py`, `test_diagnostico_api.py`, 18 tests) sigue pasando sin cambios.

#### Fix: el worker pisaba la geometry real de un lote con un rectángulo
**Fecha:** 2026-09-14
**Rama:** `feat/poc-satelital-earthsearch`

Bug detectado por reporte del usuario: "Lote de cele" perdió su forma real dibujada a mano y quedó como un cuadrado, después de probar la carga satelital sobre ese lote. Investigado y confirmado con datos reales — **afecta también al flujo existente de subida de GeoTIFF por dron**, no es exclusivo de esta feature nueva.

**Causa raíz:** `workers/gis/tasks.py::_actualizar_lote_geometry()` — llamada desde `procesar_vuelo()` cada vez que se procesa un vuelo con `lote_id` — hacía `UPDATE lotes SET geometry = ...` **sin condición**, usando el bounding box rectangular del GeoTIFF procesado. Tenía sentido cuando el único flujo de alta era `/lotes/desde-geotiff` (lote creado con `geometry=NULL`, se completaba recién al procesar el primer vuelo — documentado en migración `0005`). Pero desde que existe `ModalNuevoLote` (el lote se crea primero con el polígono real dibujado a mano, y los vuelos se suben después a un lote ya existente), esta misma función sigue ejecutándose en **cada** vuelo nuevo — dron o satelital — y reemplaza el polígono real por un rectángulo, silenciosamente, sin ningún error ni aviso.

**Impacto real confirmado en esta sesión:** dos lotes quedaron con la geometry pisada — "Lote de cele" (probado por el usuario) y "Lote Nuevisimo" (pisado por las pruebas propias de esta sesión, incluida la primera versión de este mismo trabajo antes de encontrar el bug). En ambos casos el polígono original **no es recuperable** — no hay historial de versiones de `geometry` en la tabla `lotes`, y el `UPDATE` es directo por SQL crudo, sin trigger de auditoría.

**Fix:** se agregó `AND geometry IS NULL` a la cláusula `WHERE` del `UPDATE` — la función ahora solo rellena la geometry si todavía no existe, preservando el flujo legacy de `/lotes/desde-geotiff` intacto, pero sin volver a tocar un polígono ya dibujado.

**Verificación:**
- Reprocesado un vuelo de "Lote de cele" (ya con la geometry rota) tras el fix → geometry no cambió (correcto, ya no se toca, aunque sigue siendo el rectángulo incorrecto).
- Creado un lote de prueba nuevo con un polígono real (8 vértices, irregular) → corrida una carga satelital completa de punta a punta → geometry se mantuvo exactamente igual después de `completado`. Confirma que el bug está resuelto para el caso real.
- Suite completa (`test_ingesta.py`, `test_satelital_catalogo.py`, `test_lotes.py`, `test_ingesta_worker.py`) sigue pasando sin cambios.

**Pendiente / no resuelto:** el polígono original de "Lote de cele" y "Lote Nuevisimo" quedó perdido — hay que redibujarlo a mano con "Límites" si se necesita la forma real de vuelta. Movido a "Problemas abiertos".

### Problemas abiertos

- **"Lote de cele" y "Lote Nuevisimo" tienen la geometry incorrecta** (quedó como rectángulo por el bug de arriba, ya corregido para el futuro pero sin poder revertir el dato ya pisado) — hay que redibujar el límite real a mano vía el botón "Límites" en cada uno.
- 6 productos del catálogo (Clorpirifos, Thiamethoxam, Ethephon 48%, Tiidiazurón + Diurón, Sulfato de Magnesio, Boro foliar 17%) no tienen `restricciones_ambientales`/`instrucciones_seguridad` cargados — falta ficha de seguridad específica confirmada. Ver `docs/investigacion_seguridad_fitosanitaria.md` sección 3 (marcados 🔴).
- Todo el catálogo de productos fitosanitarios (incluida esta carga) sigue sin la validación de un ingeniero agrónomo matriculado — pendiente desde `esq_datos_prod_fito.md` (Sprint 6, Release 2).
- El mapa de referencia del modal satelital sigue mostrando un basemap genérico (Esri, sin fecha), no la imagen real de la escena elegida como capa — solo se ve como miniatura chica en la tarjeta. Mostrarla como overlay del mapa requeriría renderizar el raster Sentinel-2 real en vez de un tile fijo.
- Earth Search (Element84) es un servicio "best effort" sin SLA ni garantía de disponibilidad publicada (textual en su propio README: "This public API does not come with any guaranteed service") — los datos en sí (bucket AWS Open Data) son sólidos, pero el catálogo de búsqueda podría estar caído o lento sin aviso. Si la disponibilidad se vuelve un problema para el uso real, evaluar sumar Copernicus Data Space Ecosystem (requiere cuenta OAuth2, pero es infraestructura oficial con más garantías) como fuente alternativa o de respaldo.
- **Diagnóstico multi-índice:** el motor de diagnóstico (`app/diagnostico/service.py` + `reglas.py`, RFDR-01) es 1:1 con `vuelo_id` y solo consume las zonas NDVI de ese vuelo — nunca mira `analisis_indices` (NDRE/SAVI/ExG). Un análisis completo de lote con múltiples índices en paralelo (ya soportado para cálculo, ver tabla de estado en CLAUDE.md) no se refleja hoy en el diagnóstico ni en ningún reporte derivado (PDF, geojson, shapefile) — todos quedan acotados a NDVI. Extender el motor de reglas para combinar/ponderar varios índices es un cambio de mayor alcance, fuera de la tarjeta de Trello "Exportación genérica + URLs de descarga"; el endpoint de export nuevo deja un query param `indice` reservado (default `ndvi`) para no tener que romper el contrato de la URL el día que esto se resuelva.

### Problemas encontrados

_(ver errores documentados en las tareas de arriba — todos resueltos)_

---

## Sprint 12 — Exportación genérica de zonas + URLs de descarga

**Período:** 2026-09-17

### Tareas completadas

| Tarea | Estado |
|---|---|
| Endpoint genérico `GET .../zonas/export` (geojson/shapefile, caché en MinIO + URL firmada) | Completada |
| Documento y endpoint de orden de trabajo PDF (`GET .../orden-trabajo/pdf`) | Completada |
| Integración en el dashboard (reporte, exportación y orden de trabajo) | Completada |
| QA de cierre: reporte end-to-end, GeoJSON/Shapefile, coherencia de dosis/A4 | Completada |

#### Endpoint genérico de exportación + URLs de descarga firmadas (Trello: "Exportación genérica + URLs de descarga")
**Fecha:** 2026-09-17
**Rama:** `feat/exportacion-zonas`

Nuevo endpoint `GET /lotes/{lote_id}/vuelos/{vuelo_id}/zonas/export?formato=geojson|shapefile` en `app/reportes/router.py`, anidado bajo la misma convención que el resto de la API (no `/zonas/{ciclo_id}/export` plano como decía el ticket textual — "ciclo_id" no existe como entidad en el dominio, ver Problemas abiertos de Sprint 11). Reusa el diagnóstico enriquecido (causa, severidad) igual que `/zonas/geojson` y `/zonas/shapefile` ya existentes, agregando lo que esos dos no tenían: cachea el archivo generado en MinIO (`{usuario_id}/{lote_id}/{vuelo_id}/export_{formato}.{ext}`) y devuelve una URL firmada (`presigned_url()`) en vez de servir el archivo en el body.

**Decisiones tomadas:**
- Fuente de datos: diagnóstico enriquecido (Opción A), no el GeoJSON crudo del worker — para que sirva de verdad para prescripción diferenciada en maquinaria (causa/severidad por zona), que es el objetivo real detrás del ticket.
- Query param `indice` reservado (default `ndvi`, único valor soportado hoy — cualquier otro devuelve `501`) para no romper el contrato de la URL el día que el motor de diagnóstico soporte NDRE/SAVI/ExG (ver Problemas abiertos).
- `_resolver_diagnostico_o_404()` se partió en `_resolver_lote_o_404()` + `_generar_diagnostico_o_404()` para que el endpoint nuevo pueda chequear ownership del lote sin correr el motor de diagnóstico completo en cada request (solo cuando hay cache miss).

**Error encontrado — presigned URL inservible fuera de la red de Docker**
`presigned_url()` ya existía en `app/core/storage.py` pero no la usaba nadie. Al usarla por primera vez acá, la URL que devolvía tenía como host `minio:9000` (el nombre del servicio en la red de Docker) — inaccesible para cualquier cliente externo (navegador, Postman fuera del stack). Se agregó `MINIO_PUBLIC_ENDPOINT` (`.env`/`.env.example`, `localhost:9000` en desarrollo) y `presigned_url()` ahora arma un cliente de MinIO aparte apuntado a ese endpoint público solo para firmar.

Al resolver eso apareció un segundo error:
```
urllib3.exceptions.MaxRetryError: HTTPConnectionPool(host='localhost', port=9000): ...
Failed to establish a new connection: [Errno 111] Connection refused
```
minio-py resuelve el `region` del bucket pegándole por HTTP al propio endpoint del cliente si no se lo pasás explícito — y `localhost:9000` no es alcanzable *desde dentro* del contenedor de la API (ahí "localhost" es el propio contenedor, no MinIO). Se agregó `minio_region: str = "us-east-1"` (default real de un server MinIO sin `MINIO_REGION` configurado) y se lo pasa explícito en ambos clientes de `app/core/storage.py`, así minio-py nunca intenta ese round-trip.

Verificado end-to-end contra el stack real (no solo mockeado): `GET .../zonas/export?formato=geojson` y `?formato=shapefile` devuelven una URL `http://localhost:9000/...` que se descarga correctamente desde fuera del contenedor, con el contenido real (GeoJSON válido / shapefile de 4 archivos). Segunda llamada al mismo vuelo+formato confirma cache hit (no vuelve a llamar a `generar_diagnostico`, responde en ~40ms).

**Resultado:** `app/reportes/router.py`, `app/reportes/schemas.py` (nuevo), `app/core/config.py`, `app/core/storage.py`, `.env`, `.env.example`, `README.md` (sección Problemas comunes), `tests/test_exportacion_api.py` (10 tests nuevos, 28 tests totales del módulo pasando).

#### Documento y endpoint de orden de trabajo PDF (Trello: "Documento y endpoint de orden de trabajo PDF")
**Fecha:** 2026-09-17
**Rama:** `feat/orden-trabajo-pdf`

Nuevo endpoint `GET /lotes/{lote_id}/vuelos/{vuelo_id}/orden-trabajo/pdf`, en un módulo propio y separado `app/ordenes_trabajo/` (router + service + template), no dentro de `app/reportes/` — decisión deliberada de duplicar el pipeline Jinja2+WeasyPrint (mismo patrón que `app/reportes/service.py`) en vez de reusarlo, para mantener RFSA-04 (orden de trabajo/prescripción) como dominio propio. Consume `generar_orden_trabajo()` (`app/diagnostico/orden_trabajo.py`, ya implementado en Sprint 11) sobre `diagnostico["unidades_manejo"]`, con un catálogo de dosis nuevo (`cargar_catalogo_dosis()`, indexado por nombre de producto, distinto del catálogo por causa que ya existía para sugerir productos).

**Decisiones tomadas:**
- Endpoint `GET` (no `POST` como decía el ticket textual) — coherente con el resto de los endpoints de descarga de documentos (`reporte/pdf`, `zonas/export`), que tampoco tienen efectos secundarios. Ver "Problemas abiertos" para la reconsideración a futuro.
- Módulo separado (`app/ordenes_trabajo/`) aunque duplique el setup de Jinja2/WeasyPrint de `app/reportes/service.py` — decisión explícita de priorizar separación de dominio sobre reuso de código.
- 404 explícito cuando `unidades_manejo` está vacío (todas las zonas del lote dentro de rangos normales) — no tiene sentido generar una orden de trabajo sin nada que tratar.
- Sección legal con la tabla de restricciones generales de la Ley 7032 (Chaco), ya investigada en `docs/investigacion_seguridad_fitosanitaria.md`, embebida como HTML estático en el template — marcada explícitamente en el PDF como "PENDIENTE DE REVISIÓN LEGAL" (ver Problemas abiertos, es urgente).
- El template también advierte, por separado, qué productos de la orden no tienen ficha de seguridad específica cargada (los 6 productos 🔴 de Sprint 11) — para no dar una falsa sensación de completitud.

Verificado: 8 tests nuevos en `tests/test_orden_trabajo_pdf_api.py` (404/401 de ownership + happy path con `generar_diagnostico`/`cargar_catalogo_dosis` mockeados, generando un PDF real vía WeasyPrint) + PDF de muestra generado y revisado visualmente contra el stack real (tablas de dosis, badges de severidad, aviso de dosis pendiente, sección de seguridad y recuadro legal se ven correctamente en las 2 páginas). Contra un vuelo real del stack de desarrollo se confirmó el wiring completo (auth + ownership + 404 por "sin unidades de manejo") — ningún vuelo real disponible en la base de desarrollo tiene unidades de manejo (todas sus zonas ya calculadas son "normal"), así que el camino feliz con datos 100% reales queda sin verificar hasta que exista un vuelo real con zonas problemáticas.

**Resultado:** `app/ordenes_trabajo/__init__.py`, `app/ordenes_trabajo/router.py`, `app/ordenes_trabajo/service.py`, `app/ordenes_trabajo/templates/orden_trabajo.html` (todos nuevos), `app/main.py` (registro del router), `tests/test_orden_trabajo_pdf_api.py` (nuevo).

### Problemas abiertos (Sprint 12)

- **Sección legal del PDF de orden de trabajo pendiente de revisión legal — urgente.** La tabla de restricciones generales de la Ley 7032 (Chaco) en `app/ordenes_trabajo/templates/orden_trabajo.html` es una lectura del texto oficial (ver `docs/investigacion_seguridad_fitosanitaria.md`), no una validación de un abogado ni del ingeniero agrónomo matriculado responsable. Está marcada en el propio PDF como "PENDIENTE DE REVISIÓN LEGAL", pero hay que chequearla formalmente antes de que este documento se use para una aplicación real — **no cerrar esto silenciosamente, es lo más urgente de esta tarjeta.**
- **`GET` vs `POST` en `/orden-trabajo/pdf`:** se implementó como `GET` (sin efectos secundarios, coherente con el resto de endpoints de descarga), pero el ticket original pedía `POST`. Si en un release futuro se agregan ajustes manuales de dosis antes de generar el documento (el agrónomo corrige una dosis sugerida antes de imprimir la orden), ahí sí va a hacer falta un body — momento en el que convendría pasar a `POST` o agregar un endpoint `POST` aparte para ese caso, sin romper el `GET` existente para el caso simple.

#### Integración en el dashboard (reporte, exportación y orden de trabajo)
**Fecha:** 2026-09-17
**Rama:** `feat/dashboard-descargas`

Conecta los tres endpoints de descarga (sin UI hasta ahora) al frontend: botón "Descargar reporte PDF" y botón "Exportar zonas" (con menú GeoJSON/Shapefile) por fila en la tabla "Análisis Recientes" del Dashboard, y botón "Generar orden de trabajo" junto a "↻ Recalcular" en `TablaDiagnostico.jsx` (oculto si no hay `unidades_manejo`, mismo criterio que el 404 del backend).

**Decisiones tomadas:**
- Los tres botones de descarga van en la tabla/vista donde el vuelo ya está en contexto (no en "Acciones Rápidas", que no tiene ningún vuelo asociado) — se sacó el placeholder deshabilitado "Generar Informe PDF" que había ahí por quedar redundante.
- Exportar GeoJSON/Shapefile es un solo botón con un popover para elegir formato (no dos botones separados) — mismo patrón de popover que ya usa `CalendarioSatelital.jsx`, con cierre al hacer click afuera (`useRef` + listener de `mousedown` en el documento).
- **Previsualización en vez de descarga directa** para los dos PDF (reporte y orden de trabajo): `ModalPreviewPdf.jsx` nuevo, embebe el PDF con el visor nativo del navegador vía `<iframe src={URL.createObjectURL(blob)}>`. El botón "Descargar PDF" del modal reusa el mismo blob ya traído — WeasyPrint no se ejecuta dos veces por la misma acción del usuario. La exportación de zonas no tiene preview (no es un PDF, es GeoJSON/Shapefile vía URL firmada — se abre directo con `window.open`).
- Se aprovechó para homogeneizar la tipografía de los componentes exclusivos del Dashboard (antes ~15 tamaños de fuente casi-iguales por drift orgánico — 0.62/0.64/0.71/0.72/0.82/0.83/0.84rem, etc. — normalizados a 3: 0.7/0.78/0.85rem) y sacar los íconos decorativos de "Acciones Rápidas"/"Actividad reciente" a pedido del usuario. El logo del sidebar (antes un cuadrado verde placeholder) ahora usa el mismo PNG que el favicon del navegador.

**Resultado:** `frontend/src/api/reportes.js`, `frontend/src/utils/descargarArchivo.js`, `frontend/src/components/ModalPreviewPdf.jsx` (todos nuevos), `frontend/src/pages/Dashboard.jsx`, `frontend/src/pages/ResultadosVuelo.jsx`, `frontend/src/components/TablaDiagnostico.jsx`, `frontend/src/components/SidebarNav.jsx`, `frontend/src/index.css`. Sin cambios de backend.

#### QA de cierre: reporte end-to-end, GeoJSON/Shapefile y coherencia de la orden de trabajo
**Fecha:** 2026-09-17

Verificación de cierre de sprint sobre los tres documentos/exportaciones nuevos, con un escenario sintético de 4 zonas (crítica/estrés hídrico, moderada/hongo, normal/sin problema, vigorosa/vigor excesivo) armado a mano pero procesado con las funciones reales del pipeline (`generar_unidades_manejo()`, `generar_orden_trabajo()`, `generar_pdf_reporte()`, `generar_pdf_orden_trabajo()`, `generar_geojson_zonas()`, `generar_shapefile_zip()`) — no se re-testeó el motor de reglas en sí (`app/diagnostico/engine.py`), que ya tiene su propia suite en `test_diagnostico_engine.py`.

- **Reporte PDF end-to-end:** contenido completo verificado — mapa coloreado por severidad, resumen con KPIs, tabla de 4 zonas, sección de diagnóstico narrado (excluye correctamente la zona "sin problema"), footer legal.
- **GeoJSON/Shapefile:** validación estructural como proxy de abrir en QGIS (no se pudo abrir QGIS real desde acá, sin acceso a GUI de escritorio) — CRS del `.prj` es WGS84 válido, el shapefile tiene los 4 archivos esperados (`.shp/.shx/.dbf/.prj`), los campos coinciden con `_CAMPOS` de `app/reportes/exportacion.py`, tipo de geometría POLYGON, cantidad de registros = cantidad de zonas.
- **Orden de trabajo:** coherencia de dosis/volumen verificada línea por línea (`área × dosis_referencia = volumen_total`, redondeo a 3 decimales) y en los totales agrupados por producto. Tamaño de página confirmado A4 exacto (210.0 × 297.0 mm, leído con `pypdf` instalado temporalmente solo para esta verificación, no es dependencia del proyecto) en las 2 páginas de ambos PDFs (reporte y orden de trabajo).

**Error encontrado — "Totales por producto" mostraba 0.00 en vez de "—" para un producto sin dosis de referencia**
Un producto cuya única unidad tiene `sin_dosis_referencia=True` mostraba `0.00` en la fila de "Totales por producto" del PDF de orden de trabajo (el acumulador de `_totales_por_producto()` en `app/diagnostico/orden_trabajo.py` arranca en `0.0` y nunca suma si `volumen_total` es `None`) — inconsistente con la fila individual de esa misma unidad, que sí mostraba "— (completar a mano)". Riesgo real: alguien podría leer "0.00" como "no aplicar nada" en vez de "dosis pendiente de completar a mano". Se corrigió en el template (`app/ordenes_trabajo/templates/orden_trabajo.html`): la celda de volumen total ahora muestra "— (completar a mano)" cuando `total.unidad_dosis` es vacío (ningún ítem de ese producto tenía dosis cargada). No se tocó el cálculo en Python — sigue siendo correcto y ya está cubierto por `test_orden_trabajo.py`, era puramente un problema de presentación.

### Fixes posteriores al cierre de Sprint 12

#### Fix: tabla "Análisis Recientes" del Dashboard se quedaba en "Pendiente" para siempre
**Fecha:** 2026-09-21

Reporte de usuario: subió un vuelo satelital al lote "Prueba Satelite" y la fila se quedó mostrando "Pendiente" sin ningún indicador de progreso, aunque el procesamiento ya había terminado. Confirmado con datos reales (worker log, `psql`, y `curl` directo a `/estado`/`/resultado`) que el vuelo sí llegó a `completado` en ~21s — el problema era pura UI, no backend.

**Causa raíz:** `handleCargaExitosa()` en `frontend/src/pages/Dashboard.jsx` llama a `cargarDatos()` una sola vez, justo cuando se acepta el upload (202) — antes de que el worker termine — y nada vuelve a refrescar la tabla después. El panel de mapa (`AnalisisMap`, vía `useVueloProgreso`) sí hace polling cada 2s y funciona bien, pero es un componente separado que no actualiza `loteRows`/`vueloRows`.

**Fix:** `cargarDatos()` ahora acepta `{ silencioso: true }` para refrescar sin togglear `loading` (evita que la tabla entera parpadee a "Cargando..." en cada poll). Nuevo `useEffect` (mismo patrón que ya usaba `DetalleLote.jsx`) hace polling cada 3s mientras haya algún vuelo en `pendiente`/`procesando`, y se detiene solo cuando todos terminan.

#### Fix: mapa de zonas se mostraba en blanco sin explicación cuando el análisis no genera zonas
**Fecha:** 2026-09-21

Mismo reporte del usuario: además de la tabla congelada, el mapa no mostraba ninguna marca. Investigado con los datos reales del vuelo: el NDVI del lote "Prueba Satelite" salió con variación real (min 0.29, max 0.84) pero el worker vectorizó **0 polígonos** — no es un bug de cálculo. Causa raíz: `workers/gis/zonas.py::AREA_MINIMA_M2 = 10_000` (1 ha) descarta cualquier fragmento vectorizado más chico que eso, y el lote entero mide solo **0.61 ha** — por debajo del propio umbral. Ninguna zona puede pasar el filtro en un lote así de chico, sin importar el resultado del índice.

Antes de este fix, `MapaIndice.jsx` con `nFeatures === 0` caía al bounds por defecto (`[[-34,-64],[-22,-53]]`, todo Argentina) — el usuario veía un mapa del país en blanco sin ninguna pista de qué pasó.

**Fix (solo frontend, sin cambios de backend):** `AnalisisMap` en `Dashboard.jsx` ahora detecta `geojson.features.length === 0` en estado `completado` y muestra un mensaje explicativo en vez de delegar a `MapaIndice`, distinguiendo dos casos:
- Lote más chico que el área mínima de zonificación (`loteAreaHa < 1`, recibido como prop desde `selectedVueloRow.lote.area_ha`) — explica el umbral real y aclara que ese lote nunca va a poder mostrar zonas mientras sea tan chico.
- Lote de tamaño normal sin zonas — explica que el índice se mantuvo uniforme/sano, sugiere probar otra fecha/escena o cambiar de índice (NDRE) con el selector ya existente.

**Decisión tomada:** no se tocó `AREA_MINIMA_M2` en el backend ni se agregó un parámetro para bajarlo desde la UI — es un cambio de mayor alcance (afecta el filtro "sal y pimienta" para todos los lotes, no solo los de prueba) fuera del pedido puntual del usuario. Si en el futuro se necesita analizar lotes reales de menos de 1 ha, evaluar exponer `area_minima_m2` como parámetro configurable.

**Resultado:** `frontend/src/pages/Dashboard.jsx` (ambos fixes). `npm run build` sin errores.

---

## Sprint 13 — Cultivos por lote y mejoras del flujo de análisis

### Tareas completadas

| Tarea | Estado |
|---|---|
| Fix: los índices adicionales (NDRE/SAVI/GNDVI/ExG) no se calculaban con imagen satelital | Completada |
| Mostrar el límite del lote en el mapa "Vista geoespacial" del dashboard | Completada |
| Modal de análisis dividido en dos (datos + mapa del lote) | Completada |
| Validar que el GeoTIFF subido esté cerca del límite del lote y mostrar su área en el mapa | Completada |
| Recortar las zonas vectorizadas al límite exacto del lote | Completada |
| Nueva entidad `cultivos` y análisis sobre un cultivo existente o nuevo | Completada |

#### Fix: los índices adicionales no se calculaban con imagen satelital
**Fecha:** 2026-09-20
**Rama:** `feature/Nuevo-ingreso-Ortomosaico` (commit `3f61826`)

**Error encontrado — solo se calculaba NDVI aunque se tildaran más índices**
El frontend pedía `POST .../indices/batch` apenas creaba el vuelo, pero en el flujo satelital el archivo todavía no existe (lo descarga el worker después): la API respondía `400 "El vuelo no tiene un archivo original disponible"` y el `catch {}` del frontend lo descartaba en silencio. Se resolvió pasando `indices` en `POST .../vuelos/desde-satelite`: la API crea las filas de `analisis_indices` y `descargar_satelital` encola `analizar_indices_batch` cuando termina de subir el archivo.

Antes de eso, al analizar salía "Error al solicitar la imagen satelital" genérico: la causa real era que la base estaba en la migración 0016 y el código en la 0019 (`column "estadio_fenologico" of relation "vuelos" does not exist`). Se corrigió corriendo `alembic upgrade head` — recordatorio: correrlo después de cada `git pull` con migraciones nuevas.

#### Recortar las zonas vectorizadas al límite exacto del lote
**Fecha:** 2026-09-20

Con imagen satelital, ~5 ha de 107 ha de zonas (5 %) caían fuera del polígono del lote: el enmascarado por píxeles deja un borde de hasta ~1 píxel afuera, y el suavizado + la simplificación de Douglas-Peucker lo agrandan.

**Decisiones tomadas:**
- Se recorta el vector (no el raster) en `vectorizar_zonas(..., limite=...)`, antes del filtro por área mínima y del cálculo de estadísticas por polígono, para que ambos operen sobre el resultado final.
- Se aplica a **todos** los sensores (dron y Sentinel-2) cuando el lote tiene geometry. Trade-off asumido: un ortomosaico que cubre más que el límite guardado pierde esas zonas.
- Los análisis ya hechos no se recortan retroactivamente; hay que repetirlos.

**Resultado:** con `Nueva Prueba`, zonas fuera del lote 5.05 ha → 0 ha.

#### Validar ubicación del GeoTIFF subido
**Fecha:** 2026-09-20

Al elegir un GeoTIFF de dron se lee su ubicación en el navegador (`frontend/src/utils/geotiffLimites.js`, con `geotiff` + `proj4`), se dibuja como área naranja sobre el mapa del modal y, si queda a más de 1 km del lote, se muestra "GeoTIFF subido queda por fuera de los límites guardados del lote." y se bloquea "Siguiente".

**Decisiones tomadas:**
- Comparación por bounding box con 1 km de tolerancia: los ortomosaicos casi nunca coinciden exacto con el límite dibujado, solo se rechaza lo claramente lejano.
- Si no se puede leer el CRS o la georreferencia (CRS no soportado, sin geokeys) **no se bloquea**; la validación completa sigue siendo del worker. CRS soportados: geográficos, UTM WGS84 (326xx/327xx), POSGAR 94/2007 fajas 1–7 y Web Mercator.
- Se hizo en el navegador porque el contenedor `api` no tiene rasterio a propósito.
- Esta validación es solo de frontend: la API sigue aceptando un GeoTIFF lejano si se la llama directo.
- Dependencias npm nuevas: `geotiff`, `proj4` — hay que reconstruir la imagen (`docker compose up -d --build frontend`).

#### Cultivos por lote
**Fecha:** 2026-09-20
**Rama:** `feature/Nuevo-ingreso-Ortomosaico`

`cultivo`, `variedad`, `fecha_siembra` y `estadio_fenologico` salen de `lotes`. Nueva tabla `cultivos` (`lote_id`, `tipo_cultivo`, `variedad`, `fecha_siembra`, `fecha_cosecha`, `created_at`, `deleted_at`) y `vuelos.cultivo_id`. Un lote puede tener varios cultivos (campañas); cada análisis apunta al que estaba en pie.

**Decisiones tomadas:**
- **Estadio fenológico solo en el vuelo** (ya existía `vuelos.estadio_fenologico`): cambia semana a semana, no pertenece ni al lote ni al cultivo. Se eliminó el fallback al estadio del lote en `_resolver_estadio`.
- **Todo análisis exige un cultivo:** existente (`cultivo_id`) o nuevo (`cultivo_tipo`+campos en el upload multipart; `cultivo{…}` en `desde-satelite`). Ni uno ni otro → 400, ambos → 400, `cultivo_id` de otro lote → 404. La resolución ocurre antes de subir a MinIO/encolar: un rechazo no deja cultivos huérfanos (la sesión hace rollback).
- **`POST /lotes/desde-geotiff` (legacy)** sigue aceptando `cultivo` como form field: crea el lote + un cultivo + el vuelo.
- **Soft delete** de cultivos (`deleted_at`), coherente con lotes/vuelos; los vuelos ya analizados conservan la referencia.
- Contrato: `LoteResponse` pierde `cultivo`/`variedad`/`fecha_siembra`/`estadio_fenologico` y gana `cultivos[]` (campos eliminados → cambio de contrato; se hizo sin versionar porque el único cliente es este frontend). `VueloListItem`/`VueloUploadResponse` ganan `cultivo_id` y `cultivo`. `metadata` del diagnóstico gana `cultivo_id`, `variedad`, `fecha_siembra`, `fecha_cosecha` (aditivo).
- El motor de reglas (`app/diagnostico/engine.py`, `reglas.py`) no cambió: sigue recibiendo un `CultivoEnum`, ahora desde `vuelo.cultivo.tipo_cultivo`.
- Migración **0020** con backfill: un cultivo por lote existente (con su cultivo/variedad/fecha_siembra), todos sus vuelos asociados a él, y `lotes.estadio_fenologico` copiado a los vuelos que no tenían el suyo (así los diagnósticos no cambian de criterio). `downgrade()` restaura el cultivo más reciente en `lotes`. Verificado: 0 vuelos sin cultivo tras migrar la base de desarrollo.

**Error encontrado — el 409 de "vuelo sin cultivo" salía como 500**
`_resolver_diagnostico` (`app/diagnostico/router.py`) envolvía todo en `except Exception` → `HTTPException(500)`, y pisaba cualquier `HTTPException` levantada desde el servicio. Se agregó `except HTTPException: raise` antes del genérico.

**Resultado:** backend (`app/lotes/`, `app/ingesta/`, `app/diagnostico/`, migración 0020), frontend (`ModalNuevoLote`, `ModalCargaGeoTIFF` con selector de cultivo existente / "crear cultivo nuevo", `Dashboard`, `Lotes`, `DetalleLote`, `ResultadosVuelo`, `ModalElegirLote`, `TablaDiagnostico`, `utils/cultivos.js`). Tests: 210 pasando (`test_cultivos.py` nuevo con 21; `test_diagnostico_api.py` cubre el diagnóstico con cultivo por vuelo y el 409). Se corrigió de paso `ResultadosVuelo.jsx`, que buscaba el vuelo por `v.id` cuando la API devuelve `vuelo_id`.

#### Modal de análisis en 3 pasos: Carga → Cultivo → Análisis
**Fecha:** 2026-09-20
**Rama:** `feature/Nuevo-ingreso-Ortomosaico`

Se reordenó `ModalCargaGeoTIFF.jsx` a pedido del usuario: (1) **Carga** — lote, dron o satélite, archivo/escena; (2) **Información de cultivo** — lista de cultivos del lote con sus fechas de siembra y cosecha, que al elegirse autocompleta tipo, variedad y las dos fechas; botón "＋ Nuevo cultivo" que deja los campos en blanco; al final, fecha del vuelo y estadio fenológico; (3) **Análisis** — resumen y selección de índices.

**Decisiones tomadas:**
- **Modificar un cultivo existente es posible, con aviso:** si se edita algún campo de un cultivo elegido aparece un cuadro de advertencia, y al continuar el submit hace primero `PUT /lotes/{id}/cultivos/{id}` y después crea el análisis con ese `cultivo_id`. El cambio también se ve en los análisis anteriores de ese cultivo (comparten la fila); para otro cultivo distinto está "Nuevo cultivo".
- **Estadio fenológico obligatorio** en el frontend y en el backend (`POST .../vuelos` y `POST .../vuelos/desde-satelite` devuelven 422 si falta o viene en blanco). Es un cambio de contrato: antes era opcional. `POST /lotes/desde-geotiff` (legacy) no se tocó.
- Se agregó un campo de variedad (opcional) en el paso de cultivo aunque el pedido solo mencionaba tipo y fechas, porque es parte de la entidad y el diagnóstico la devuelve en `metadata`.
- **Ajustes de usabilidad del modal (feedback de uso):** DJI Mavic 3 como sensor por defecto (Sentinel-2 se fuerza solo en modo satélite); todos los índices que el sensor permite arrancan seleccionados — ExG no se ofrece con DJI porque no tiene banda Blue (limitación del sensor, ver `workers/gis/band_mapping.py`), sí con Sentinel-2; NDVI sigue sin poder destildarse (el backend siempre lo calcula) pero ya no dice "Siempre incluido"; la lista de cultivos pasó a un dropdown propio (`CultivoDropdown`) con scroll interno y "＋ Nuevo cultivo" fijo al pie, para lotes con muchos cultivos; se rehízo el ícono del satélite, que se veía como un enchufe.
- **"＋ Nuevo lote" dentro del modal de análisis** (a pedido): botón junto al selector de lote que reemplaza el paso 1 por un formulario (nombre, tipo de suelo, una sección "Límites" con "Dibujar en mapa" y el texto "O al cargar un GeoTIFF se determinarán los límites"). "Dibujar en mapa" reemplaza el mapa de la derecha por `MapaDibujoLote` (el mismo del alta de lote, con la validación de área y de lados que se cruzan); "Guardar" hace `POST /lotes`, selecciona el lote nuevo y vuelve al paso 1. Sin límite dibujado el lote queda con `geometry = null` y el worker lo completa con el bounding box del GeoTIFF al procesar (comportamiento existente). Al pulsar "Nuevo lote" se deselecciona el lote para que el mapa vuelva al estado vacío; "Cancelar" restaura el lote anterior. El modal ya no bloquea cuando no hay lotes (antes mostraba "creá un lote primero"). Prop nueva `onLoteCreado` para que Dashboard y Lotes refresquen su lista. `TIPOS_SUELO` pasó a `utils/suelos.js`, compartido con `ModalNuevoLote`.
- **Estadio fenológico como lista según el cultivo** (a pedido): `ESTADIOS_POR_CULTIVO` en `app/diagnostico/estadios.py`, expuesta en `GET /api/v1/estadios-fenologicos` (soja VE–R8, maíz VE–R6 con V1–V18 y VT, algodón con botón floral/floración/apertura de cápsulas, sorgo con espigado/floración/llenado). El select del paso "Cultivo" se habilita al elegir el tipo y se limpia si el tipo cambia y el estadio ya no pertenece a la escala. Se guarda el texto tal cual y el motor lo normaliza; `tests/test_estadios.py` verifica que las 20 reglas puedan matchear con alguna opción de la lista de su cultivo, para que agregar una regla con un estadio nuevo no la deje inalcanzable. La lista incluye estadios que ninguna regla usa (p. ej. R6–R8 de soja): solo dejan de aplicar las reglas que exigen un estadio puntual.
- Nuevo ícono de dron (cuadricóptero con rotores) para el botón "Subir archivo (dron)" y la tarjeta del paso de análisis; el anterior se veía como un enchufe.

#### Fix: el umbral adaptativo (Otsu) nunca funcionaba — ExG quedaba entero en "crítica"
**Fecha:** 2026-09-21

**Error encontrado — `TypeError: threshold_multiotsu() got an unexpected keyword argument 'nclasses'`**
Detectado al revisar el ExG de un vuelo Sentinel-2 de "Nueva Prueba": todo el lote (104 ha) salía en una sola zona "crítica" con valor 0,023. `workers/gis/clasificacion.py` llamaba `threshold_multiotsu(validos, nclasses=4)`, pero en scikit-image 0.24 el parámetro se llama `classes`. El `except Exception` que envolvía la llamada se tragaba el TypeError y devolvía los umbrales **fijos** `[0.20, 0.40, 0.70]`, así que "otsu" nunca fue adaptativo. Para ExG (que es una diferencia de reflectancias crudas, valores ~0,02, no un índice razón en [-1,1]) los umbrales fijos dejan todo bajo 0,20. El test `test_otsu_retorna_tres_umbrales_ordenados` pasaba igual porque `[0.20, 0.40, 0.70]` también son 3 umbrales ordenados.

Se corrigió el parámetro (`classes=4`), el fallback esperable (`ValueError`, imagen con < 4 valores únicos) sigue siendo silencioso, y cualquier otra excepción ahora se loguea. Test de regresión `test_otsu_es_adaptativo_y_no_cae_a_los_umbrales_fijos`. Con el vuelo real: umbrales `[0.0144, 0.0258, 0.0389]` y 9 zonas en 4 clases en vez de 1.

**Leyenda con valores reales (a pedido):** el worker ahora guarda en el GeoJSON de cada análisis los cortes de clase usados (`umbrales` y `metodo_umbral`, miembros externos de la FeatureCollection) y `MapaIndice.jsx` rotula la leyenda con ellos — p. ej. ExG: "Crítica (< 0.014) / Deficiente (0.014–0.026) / Normal (0.026–0.039) / Vigorosa (> 0.039)" en vez de "umbral adaptativo por vuelo". Sirve para cualquier índice con umbral adaptativo. Los análisis anteriores no tienen `umbrales` y conservan la leyenda anterior hasta reprocesarse. Son los valores reales del índice, **no normalizados**: si se quiere ExG en una escala normalizada hay que definirlo aparte (ver problema abierto de R10).

**Impacto:** afecta a todo análisis ExG ya calculado y a cualquier análisis pedido con `metodo_umbral="otsu"` explícito; hay que reprocesarlos.

**ExG normalizado (a pedido):** `workers/gis/indices.py::calcular_exg` pasó de `2G − R − B` a `2g − r − b` con `g, r, b = banda / (R + G + B)` (equivale a `(2G − R − B) / (R + G + B)`). Al dividir por el brillo total el valor no cambia con la iluminación ni con las unidades de la cámara (reflectancia 0–1 o DN 8-bit), así que es comparable entre fechas, lotes y sensores. Con la escena de Nueva Prueba: rango −0,047 a 0,492 (antes −0,020 a 0,066), promedio 0,133 (antes 0,023). Eso resuelve el problema de **R10**: `ExG > 0.20` ahora es alcanzable (con la escena de prueba solo 1 píxel de 10.451 cumple "NDVI < 0.50 y ExG > 0.20": el lote no tiene firma de malezas, no es un fallo de la regla). Píxeles con R+G+B = 0 quedan como NaN. Tests: `test_exg_no_depende_del_brillo_ni_de_las_unidades` y `test_exg_suma_cero_es_nan_y_respeta_nodata`.
- Se reprocesaron los 7 análisis ExG con datos del usuario de desarrollo y se recalcularon sus diagnósticos guardados. Los ExG de otros usuarios o de bases ya desplegadas hay que reprocesarlos (`POST .../indices {"indice":"exg"}`), porque conservan la escala vieja.
- **ExG con cortes fijos (a pedido):** con el ExG normalizado ya es comparable, así que dejó de clasificarse con Otsu (que daba cortes distintos en cada escena, hasta 0,99 en una, y hacía imposible comparar mapas) y tiene cortes fijos propios en `workers/gis/clasificacion.py::_UMBRALES_POR_INDICE`: **0,05 / 0,15 / 0,30** → Muy bajo (< 0,05), Bajo (0,05–0,15), Medio (0,15–0,30), Alto (> 0,30) (el corte intermedio empezó en 0,20 y se bajó a 0,15 a pedido: con 0,20 el 63 % de Nueva Prueba quedaba en "Bajo" mientras el NDVI la clasificaba casi toda como normal). Se eliminó `_metodo_umbral_efectivo` (forzaba Otsu); Otsu/percentil siguen disponibles si se piden explícitamente. Con cortes absolutos ya no hace falta la brecha mínima entre clases para ExG: un lote homogéneo queda en una sola clase.
  - **Origen de los cortes:** agrupación en 4 clases de una escala orientativa de interpretación propuesta en una revisión externa (< 0 suelo rojizo/agua/oscuro; 0–0,05 suelo desnudo o materiales grises; 0,05–0,10 pasto seco o vegetación muy rala; 0,10–0,20 vegetación rala o parcialmente verde; 0,20–0,30 vegetación verde con buena cobertura; > 0,30 vegetación muy verde y densa). Esa tabla **no tiene una fuente citada**; se cruzó con datos: en las escenas disponibles el ExG cruza los cortes del NDVI (0,40 y 0,70) en ≈ 0,05 y ≈ 0,29, coherente con los extremos elegidos.
  - **Advertencia para no sobreinterpretar:** en esas escenas los píxeles de ExG bajo (0 a 0,10) tienen NDVI mediano ≈ 0,5, es decir **hay vegetación** (seca, rala o con estructura), no suelo desnudo (que tendría NDVI ~0,1–0,25). Por eso la leyenda usa nombres genéricos (Muy bajo … Alto) y no las descripciones de la tabla.
  - **Calibración provisoria:** 3 escenas Sentinel-2, todas con cultivo, casi sin suelo desnudo (31 píxeles bajo NDVI 0,20): el corte de 0,05 no está bien validado y los cortes valen para Sentinel-2. Validar con más lotes o con un agrónomo.
  - Se reprocesaron los 5 ExG vigentes del usuario de desarrollo (el resto eran vuelos borrados o con el NDVI en error).


#### Nombres de las clases de los índices: Muy bajo / Bajo / Medio / Alto
**Fecha:** 2026-09-21

A pedido, las clases de valor de un índice se muestran como **Muy bajo, Bajo, Medio y Alto** en lugar de Crítica, Deficiente, Normal y Vigorosa ("Normal" pasó a "Medio" el 2026-09-21) (leyenda y tooltip de `MapaIndice.jsx`, mapa y tabla de zonas de la pantalla de resultados). Los nombres viven en `frontend/src/utils/clasesIndice.js`.

**Decisiones tomadas:**
- Solo cambia lo visible: los identificadores internos (`critica`, `deficiente`, `normal`, `vigorosa`) se mantienen porque están guardados en los GeoJSON y los consumen el diagnóstico, el reporte y las exportaciones.
- La **severidad** del diagnóstico (Crítica / Moderada / Leve, en la tabla de diagnóstico, el reporte PDF y la orden de trabajo) no se tocó: habla de la gravedad del problema, no del valor del índice.

#### Mapa chico del inicio: los huecos chicos se absorben en la zona vecina
**Fecha:** 2026-09-21

Al cambiar los cortes del GNDVI aparecieron "parches sin datos" en el mapa: no eran píxeles sin dato sino zonas menores a 1 ha, que el worker descarta a propósito (`AREA_MINIMA_M2` en `workers/gis/zonas.py`) — con los cortes nuevos hay más fragmentos (42 zonas, 39 descartadas: 5,6 ha ≈ 5 % del lote sin cubrir; antes 0,4 ha).

**Decisión tomada (a pedido):** en el mapa chico del Dashboard esos huecos se rellenan con la zona vecina; en el mapa de resultados no (se va a rediseñar con escala de colores continua). Se hace **al leer**, no al procesar: `GET .../resultado` y `GET .../indices/{indice}/resultado` aceptan `?absorber=true` (`app/ingesta/absorcion.py`, Shapely). Así el diagnóstico, la tabla de zonas y las exportaciones siguen trabajando sobre las zonas originales y no hay que reprocesar nada.
- Cada hueco va a la zona con la que comparte más borde; su clase y su valor no cambian, sí se recalcula `area_ha`.
- Solo se absorben huecos de hasta 3 ha (`AREA_MAX_HUECO_M2`): uno grande (nube, borde sin dato, parte del lote que el GeoTIFF no cubre) es información real y queda en blanco.
- **"Sin datos" es real, no una deducción (a pedido):** el worker lo mide al procesar (`workers/gis/sin_datos.py`) y lo guarda en el resultado como `sin_datos` = píxeles sin dato del índice (NaN) + la parte del lote que el GeoTIFF no cubre, **de cualquier tamaño** (un solo píxel sin dato se registra). El recorte del lote deja NaN fuera del polígono: eso no cuenta, y las astillas dentadas del borde (< ~0,9 píxel) tampoco. La clave `sin_datos` está siempre en análisis nuevos (con valor `null` si no hay nada) para distinguir "no hay" de "análisis viejo que no lo registró". Los mapas (Dashboard y zonas de resultados) lo dibujan **rayado en gris** con entrada "Sin datos" en la leyenda y tooltip. Un análisis sin ninguna zona (p. ej. el GeoTIFF cae fuera del lote) marca todo el lote "Sin datos".
- **Lo que tiene datos se combina con la vecina, sea del tamaño que sea (a pedido):** `absorber_huecos` rellena todo hueco entre zonas que NO esté en `sin_datos` (zonas < 1 ha descartadas, o fragmentos que no alcanzaron valor definido), sin tope de tamaño. Nunca rellena el `sin_datos`. Solo para análisis viejos, que no registraron `sin_datos` y por tanto no se puede saber qué es qué, se mantiene el tope de 3 ha por prudencia (y no se dibuja rayado: no se afirma lo que no se midió). Reprocesar un análisis viejo lo pasa al modo exacto.
- **Se reemplazó** la primera versión, que deducía el "sin datos" por el tamaño del hueco (> 3 ha): rotulaba mal en ambos sentidos (fragmentos chicos pegados podían dar un falso positivo y una nube chica quedaba sin marcar).
- Resultado en Nueva Prueba: GNDVI 41 huecos → 0 (98,6 → 104,6 ha cubiertas de 104,6); NDRE 15 → 1.
- Tests: `tests/test_absorcion.py` (12, API) y `tests/test_sin_datos.py` (9, worker; corren en el job `test-gis` del CI).

#### GNDVI con cortes propios (todo salía "Normal")
**Fecha:** 2026-09-21

`GNDVI` reutilizaba los cortes del NDVI (0,20 / 0,40 / 0,70) bajo el supuesto de que "se comporta parecido". Medido sobre 3 escenas Sentinel-2 no es así: al usar la banda verde, que refleja bastante en casi cualquier vegetación, varía la mitad que el NDVI (p5–p95 de 0,13–0,22 contra 0,26–0,37) y un canopeo con NDVI 0,70 tiene GNDVI ≈ 0,63. Resultado: 85–99 % del lote en "Normal" y "Alto" (> 0,70) casi inalcanzable (máximo real ≈ 0,75).

Cortes nuevos: **0,25 / 0,45 / 0,60** (Muy bajo < 0,25, Bajo 0,25–0,45, Medio 0,45–0,60, Alto > 0,60). Salen de los valores de GNDVI donde el NDVI cruza sus cortes (≈ 0,25 / 0,45 / 0,63); el último se fijó en 0,60 a pedido. **Calibración provisoria:** 3 escenas de cultivo sano y el corte de 0,25 se apoya en ~40 píxeles. Se reprocesaron los GNDVI del usuario de desarrollo; los de otras bases hay que reprocesarlos (`POST .../indices {"indice":"gndvi"}`).

#### Buscador en el mapa de dibujo de límites
**Fecha:** 2026-09-20

`MapaDibujoLote.jsx` (usado en "Nuevo lote", "Límites" y en el alta de lote del modal de análisis) suma un buscador arriba a la derecha: acepta el nombre de un lugar o coordenadas `lat, lng` (`-27.45, -59.05`, `-27.45 -59.05`, `27.45°S 59.05°O`; siempre latitud primero), centra el mapa, deja un marcador rojo y, si hay varios lugares, muestra la lista para elegir. Botón 📍 para ir a la ubicación del dispositivo. El parser está en `utils/coordenadas.js` (tests con Vitest).

**Decisiones tomadas:**
- Geocodificación con **Nominatim (OpenStreetMap)** llamado directo desde el navegador: gratis y sin clave, pero es un servicio de terceros — el texto buscado sale hacia `nominatim.openstreetmap.org` y su política de uso pide no más de ~1 consulta/segundo y sin autocompletado, por eso solo se consulta al enviar (Enter o botón). Si el uso crece o hace falta SLA, hay que pasar a un proveedor propio o con clave (o a un endpoint del backend que cachee).
- Las coordenadas no hacen ninguna llamada externa.

#### "Nuevo Lote" del dashboard con el mismo formato de dos paneles
**Fecha:** 2026-09-20

`ModalNuevoLote.jsx` (botón "Nuevo Lote" de Acciones Rápidas y de "Mis lotes") adopta el formato del alta de lote del modal de análisis, sin la barra de pasos: "Nuevo lote" como título en la barra superior, formulario a la izquierda (nombre, tipo de suelo, sección "Límites" con "Dibujar en mapa" y el texto "O al cargar un GeoTIFF se determinarán los límites") y mapa a la derecha (mapa del NEA al abrir; mapa de dibujo con buscador al elegir "Dibujar en mapa").

**Decisión tomada (a pedido):** se **quitó la opción "Subir GeoJSON"** de este modal — el límite de un lote nuevo se dibuja o se determina al cargar el primer GeoTIFF. Sigue existiendo la carga de GeoJSON al editar los límites de un lote ya creado (`ModalLimites.jsx`, botón "Límites") y en el endpoint `PUT /lotes/{id}`.

#### Mapa del NEA cuando no hay ubicación que mostrar
**Fecha:** 2026-09-20

En el modal de análisis, el panel derecho mostraba un cuadro gris con un texto cuando no había lote seleccionado o el lote no tenía límite. Ahora muestra `MapaNEA.jsx`: imagen satelital de Esri centrada en Chaco, Formosa, Corrientes y Misiones, con las 4 provincias resaltadas y rotuladas, y un aviso corto según el caso (sin lote / lote sin límite; al crear un lote nuevo no se muestra aviso).

**Decisiones tomadas:**
- Los límites provinciales están **guardados en el repo** (`frontend/src/data/nea-provincias.json`, ~30 KB) en lugar de pedirse a un servicio en cada apertura: se obtuvieron una vez de Nominatim/OpenStreetMap y se simplificaron con Shapely (tolerancia 0.004°, ≈400 m, imperceptible a esta escala). Los datos de OSM son ODbL: la atribución "Límites provinciales © colaboradores de OpenStreetMap" está en el mapa. Para regenerarlos hay que repetir esa consulta (`state=<provincia>&country=Argentina&polygon_geojson=1`).
- Solo las 4 provincias del NEA definidas en el alcance del proyecto; si se amplía la región hay que agregarlas al JSON.

#### Un lote sin límite toma el del primer GeoTIFF
**Fecha:** 2026-09-20
**Rama:** `feature/Nuevo-ingreso-Ortomosaico`

El worker ya rellenaba `lotes.geometry` con el rectángulo del primer GeoTIFF cuando era `NULL`, pero (reproducido subiendo un GeoTIFF a un lote recién creado sin límite):

**Error encontrado — el lote quedaba con límite pero sin superficie**
`_actualizar_lote_geometry` no calculaba `area_ha`, así que el lote seguía figurando "Sin límites" en el listado y sin hectáreas. Además el `except Exception: pass` alrededor de la extracción de bounds escondía cualquier fallo. Se calcula `area_ha` en el mismo `UPDATE` (`ST_Area` sobre EPSG:32721 / 10 000, igual que la API) y ahora se loguea la excepción (sin bloquear el pipeline).

**Decisiones tomadas:**
- El límite es la **cobertura real** del GeoTIFF (`_poligono_cobertura_wkt`: envolvente convexa de los píxeles con dato válido, máscara leída decimada a ~1024 px) y no el rectángulo del raster: un ortomosaico rotado o con bordes sin dato tiene un bounding box bastante más grande que lo que cubre. Sin nodata declarado, o si el cálculo falla, cae al rectángulo. Con un GeoTIFF de prueba con una esquina sin dato: 7 vértices y 261 ha en vez de 4 vértices y 439 ha.
- Sigue valiendo `WHERE geometry IS NULL`: un lote que ya tiene límite nunca se pisa (ver bug del 2026-09-14 arriba).
- Solo se completa desde `procesar_vuelo` (el análisis de NDVI). Los índices adicionales (`analizar_indice(s)`) no tocan la geometría.
- Dashboard: `AnalisisMap` recarga los lotes cuando termina el análisis de un lote sin límite, así el límite y la superficie aparecen sin recargar la página.
- Tests: `tests/test_cobertura_geotiff.py` (puro, en el job `test-gis` del CI) y `tests/test_lote_limites_worker.py` (contra la base; se saltea si no hay DB; correr en el contenedor worker).

**Límite conocido:** el límite tomado de un GeoTIFF es una envolvente convexa, no el contorno exacto del campo — sirve para empezar; para el contorno real hay que dibujarlo o cargarlo desde "Límites".

### Problemas abiertos (Sprint 13)

- **No hay pantalla dedicada para dar de baja un cultivo** — la API (`DELETE /lotes/{id}/cultivos/{id}`) está lista y testeada. Crear y editar cultivos solo se puede desde el paso "Información de cultivo" al iniciar un análisis; no hay vista para cargar la `fecha_cosecha` sin iniciar uno.
- **La validación de ubicación del GeoTIFF no está en el servidor** (ver más arriba).

## Sprint 14 — Identidad visual unificada (landing, login y panel)

#### Landing única, login y panel con el mismo lenguaje visual
**Fecha:** 2026-09-21
**Rama:** `main`

Se unificó el aspecto de la landing, el login y el panel (dashboard, lotes, detalle y resultados).

**Decisiones tomadas:**
- **Una sola landing en `/`**: `LandingOriginal`. Se eliminaron `Landing.jsx` (la versión rediseñada en el PR #14 de `feat/landing-hero`, descartada a propósito al resolver el merge) y `LandingIntermediate`, junto con ~1.660 líneas de estilos `l2nd-*` de `index.css`. Las rutas `/landing-original` y `/landing-intermedia` ya no existen (caen a `/`).
- **Landing**: foto `fondozaira1.jpeg` con degradado oscuro, palabra dinámica con efecto de tipeo y cursor, barra superior que se achica al hacer scroll. Se quitaron las secciones de preguntas frecuentes, CTA final e impacto agronómico (con sus links de la barra y del footer).
- **Login**: mismo vidrio oscuro y foto que la landing, con barra superior y botón "Volver al inicio".
- **Panel**: fondo claro (`#f3f6f3`) con barra lateral y barra superior oscuras, en `frontend/src/panel-tema.css` (se carga después de `index.css`). Se probaron tres variantes con un selector temporal (híbrido, híbrido con barra clara, oscuro completo) y quedó la híbrida con barra oscura; el selector y las otras variantes se eliminaron. La foto de fondo se descartó en el panel porque competía con el contenido de tarjetas y tablas.
- **Animación de entrada** en todas las pantallas del panel (aparece con desenfoque y sube, escalonada como en la landing y el login), en `panel-tema.css`. Usa `animation-fill-mode: backwards` a propósito: al terminar no queda ningún `transform`/`filter` sobre los contenedores, porque eso cambiaría el contenedor de los modales `position: fixed`. Respeta `prefers-reduced-motion`.
- **Dashboard (pantalla Resumen)** rediseñado: portada con la foto de la landing, saludo según la hora y los tres botones de acción (por eso se eliminó la tarjeta "Acciones Rápidas"), tarjetas redondeadas con sombra suave y actividad reciente como línea de tiempo. La tabla y el mapa ocupan las mismas 3 columnas que los KPIs y la actividad la cuarta, de modo que los bordes coinciden. Los estilos van bajo `.dashboard--resumen` para no afectar a Lotes, que comparte clases. Se comparó contra el diseño anterior con un selector temporal y se eligió el nuevo; el selector y el diseño viejo se eliminaron. Se probó también una textura (`textura.jpeg`) como fondo de la portada y se descartó; el archivo sigue en `frontend/public`.
- **Botones unificados**: un solo botón de "volver" (`BotonVolver.jsx`, con versión oscura para las barras y clara para fondos claros) usado en login, detalle, resultados y el asistente de carga; primario, secundario y de peligro comparten tamaño y tipografía.
- **Barra lateral**: usa el mismo `logo.png` que la landing y el login, en una franja de 52 px que alinea su línea inferior con la de la barra superior.
- **Navegación unificada**: Detalle de lote y Resultados de vuelo pasan a usar la misma estructura que Dashboard y Lotes (`PanelLayout`: barra lateral + `TopbarPanel`), en lugar de su propia cabecera oscura con un botón "Volver a…". La barra superior muestra una ruta clicable (`Dashboard › Lotes › Lote 1 › Resultados`), se quitó la campanita (no tenía función) y "Ver todos" de Análisis Recientes lleva a Lotes. En Resultados el mapa pierde ~190 px de ancho por la barra lateral; queda pendiente evaluar una barra lateral que se contraiga. Se comparó con el diseño anterior mediante un selector temporal y se eligió el nuevo.
- **Paleta**: el verde lima fluor (`#b7f473`) se reemplazó por verde salvia (`#9cc2a8`) en las barras del panel, alineado con la landing.

**Problemas a tener en cuenta:**
- El merge con `origin/main` trajo la dependencia `geotiff`; hubo que reconstruir la imagen (`docker compose build frontend`), porque `npm install` dentro del contenedor no ve el `package.json` nuevo (solo `src` está montado).
- Los estilos inline de algunos componentes (mapas, leyendas) no siguen la paleta; quedan con sus colores propios.
