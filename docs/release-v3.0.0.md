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

### Problemas encontrados

_(ver errores documentados en la tarea de arriba — todos resueltos)_
