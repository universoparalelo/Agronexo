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

### Problemas encontrados

_(ver errores documentados en las tareas de arriba — todos resueltos)_
