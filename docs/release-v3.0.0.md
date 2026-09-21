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
