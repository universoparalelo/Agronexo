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

### Problemas abiertos

- 6 productos del catálogo (Clorpirifos, Thiamethoxam, Ethephon 48%, Tiidiazurón + Diurón, Sulfato de Magnesio, Boro foliar 17%) no tienen `restricciones_ambientales`/`instrucciones_seguridad` cargados — falta ficha de seguridad específica confirmada. Ver `docs/investigacion_seguridad_fitosanitaria.md` sección 3 (marcados 🔴).
- Todo el catálogo de productos fitosanitarios (incluida esta carga) sigue sin la validación de un ingeniero agrónomo matriculado — pendiente desde `esq_datos_prod_fito.md` (Sprint 6, Release 2).
- Earth Search (Element84) es un servicio "best effort" sin SLA ni garantía de disponibilidad publicada (textual en su propio README: "This public API does not come with any guaranteed service") — los datos en sí (bucket AWS Open Data) son sólidos, pero el catálogo de búsqueda podría estar caído o lento sin aviso. Si la disponibilidad se vuelve un problema para el uso real, evaluar sumar Copernicus Data Space Ecosystem (requiere cuenta OAuth2, pero es infraestructura oficial con más garantías) como fuente alternativa o de respaldo.

### Problemas encontrados

_(ver errores documentados en las tareas de arriba — todos resueltos)_
