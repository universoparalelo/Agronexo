# AgroNexo — Documentación de la Release 1 (v1.0.0)

> **Conversión a Markdown** del PDF `_Release_1.pdf` (16 páginas). Contenido fiel al original.
> **Qué se omitió o cambió:** se omitieron la portada gráfica (se resume abajo), el índice y los pies de página repetidos. Las tablas que el PDF parte entre páginas se unieron. El diagrama de componentes (página 9) se transcribió a texto. Se normalizaron cortes de línea y palabras partidas dentro de las celdas.
> **Uso:** referencia del nivel de detalle técnico y del tono de la documentación de cada release. La estructura formal está en `_TEMPLATE-release.md`.

---

## Portada

**PROYECTO FINAL — AGRONEXO** · Release 1 · 2026 · UTN

- Profesores: Acuña, César J · Mendez, Graciela L
- Equipo 6: Aguirre, Amilcar · Machado, Matías · Martin Rodich, Celeste · Pujalte, Denise · Rosin, Zaira

---

# AgroNexo — Presentación de Release 1 (v1.0.0)

**Clasificación visual del lote**
Proyecto Final de Ingeniería en Sistemas · UTN FRRe · Equipo 6
Profesores: Acuña, César J · Mendez, Graciela L

## Ficha de release

| Campo | Valor |
|---|---|
| Versión | v1.0.0 (tag v1.0.0, commit de corte f35e422 del 6 de julio de 2026) |
| Estado | Completa — Demo 7 de julio de 2026 |
| Período | 1 de junio — 7 de julio de 2026 (5 semanas) |
| Equipo | Amilcar Aguirre, Matías Machado, Celeste Martín Rodich, Denise Pujalte, Zaira Rosin |
| Metodología | Scrum — sprints de 1 semana |
| Entorno | Local con Docker Compose. Sin staging ni producción |
| Repositorio | universoparalelo/Agronexo (privado) |
| Hito de entrega | Subir un mapa y ver el lote clasificado en zonas de vigor sobre el mapa |

## Equipo y roles

| Integrante | Rol en la release | Área |
|---|---|---|
| Matías Machado | Scrum Master / Release Manager | Frontend · API |
| Celeste Martín Rodich | Desarrollo | Backend · GIS · DevOps |
| Denise Pujalte | QA | Testing · Documentación |
| Zaira Rosin | Investigación | GIS · Análisis espacial |
| Amilcar Aguirre | Desarrollo | Frontend · UI |

---

## 1. Planificación de la Release

### 1.1 Objetivo y alcance

El objetivo fue construir un MVP demostrable de punta a punta: el usuario sube un ortomosaico GeoTIFF desde el navegador, el sistema lo procesa de forma asíncrona y muestra el lote clasificado en zonas de vigor sobre un mapa interactivo, con estadísticas por zona.

**Incluido en el alcance:**

- **Discovery (S1–S2):** investigación técnica y agronómica, arquitectura, stack y especificación OpenAPI. Sin código en el repositorio.
- **Infraestructura:** Docker Compose con 6 servicios (db, redis, minio, api, worker, frontend), FastAPI + SQLAlchemy async + PostGIS, migraciones Alembic 0001 → 0011 y CI en GitHub Actions con 3 jobs.
- **Autenticación JWT:** registro (solo vía API), login, refresh, logout y /me.
- **Gestión de lotes:** alta, baja (soft delete) y modificación, límite cargado desde GeoJSON con vista previa, área calculada en PostGIS y pantalla de lotes con detalle.
- **Ingesta:** inspección previa del GeoTIFF, carga a MinIO sobre un lote existente o creando lote + vuelo en un paso, validación de CRS y bandas por sensor (Sentinel-2 y DJI Mavic 3 Multispectral).
- **Pipeline GIS asíncrono:** índices NDVI, NDRE, SAVI y ExG en paralelo, suavizado gaussiano, umbralización fija / Otsu / percentil, vectorización y zonas atípicas por z-score.
- **Visualización:** barra de progreso en tiempo real, mapa Leaflet coloreado por clase con selector de índice, tabla de estadísticas por zona y acciones de eliminar y reintentar análisis.

**Queda fuera del alcance de esta release:** el motor de diagnóstico interpretativo, la exportación PDF/Shapefile, el historial de campañas y la capa generativa con LLM.

### 1.2 Sprints que la componen

| S | Título | Entregable demostrable | Fecha | Historia | RF/RNF |
|---|---|---|---|---|---|
| S1 | Investigación técnica y de índices | Informe con fórmulas y umbrales validados | 1–8 jun | H1.1–H1.4 | RFME-01/02, RFMA-01, RNF-04/05 |
| S2 | Investigación de dominio y arquitectura | Documento de arquitectura + spec OpenAPI | 8–15 jun | H2.1–H2.6 | RFDR-05, RFGL-01, RNF-06/23 |
| S3 | Setup, infraestructura, autenticación y lotes | Stack levantado, el usuario puede crear un lote | 15–22 jun | H3.1–H3.6 | RFGL-01/02, RNF-05/06/23 |
| S4 | Ingesta, pipeline GIS y visualización del índice | Subir GeoTIFF → ver mapa con progreso en tiempo real | 22–29 jun | H4.1–H4.5 | RFME-01–03/05, RFMA-01, RFMP-01, RNF-04/28 |
| S5 | Clasificación, límites, testing y estabilización | MVP completo: lote clasificado en zonas con estadísticas | 29 jun–7 jul | H5.1, H5.2, H5.5–H5.7 | RFMA-02/04, RFMP-02–05, RFGL-02, RNF-10–12 |

### 1.3 Duración y fechas clave

| Evento | Fecha |
|---|---|
| Inicio de la release | 1 de junio de 2026 |
| Fin Sprint 1 — Investigación técnica | 8 de junio de 2026 |
| Fin Sprint 2 — Arquitectura | 15 de junio de 2026 |
| Fin Sprint 3 — Setup e infraestructura | 22 de junio de 2026 |
| Fin Sprint 4 — Pipeline GIS | 29 de junio de 2026 |
| Demo y cierre Release 1 | 7 de julio de 2026 |
| Receso invernal | 20 de julio — 2 de agosto de 2026 |

### 1.4 Definición de Terminado (DoD)

Una tarea se considera terminada cuando cumple todos los criterios siguientes:

- La funcionalidad es demostrable de punta a punta en el entorno local con docker compose up.
- Los endpoints involucrados responden con los códigos HTTP esperados.
- Existe al menos un test automatizado que cubre el caso principal.
- Los tests existentes siguen pasando (sin regresiones en CI).
- Si se modificó la base de datos, existe la migración Alembic correspondiente.
- Si se agregó una tarea Celery nueva, el worker fue reiniciado y verificado.
- La tarea fue documentada en el archivo de seguimiento release-v1.0.0.md.

Criterios de cierre de la release, evaluados contra el commit de corte: 1 cumple, 4 parciales y 2 no cumplen.

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| 1 | Pipeline completo end-to-end con un GeoTIFF de prueba hasta PostGIS | Parcial | Lectura → índices → clasificación → vectorización funciona. Las zonas se guardan como GeoJSON en MinIO, no en PostGIS. |
| 2 | Mapa Leaflet con zonas coloreadas por categoría | Cumple | Clases crítica / deficiente / normal / vigorosa, con zonas atípicas marcadas aparte. |
| 3 | Registro, autenticación JWT y gestión de lotes con PostGIS | Parcial | Todo funciona, pero el registro solo existe vía API: el botón "Registrarse" no está conectado. |
| 4 | API responde a todos los endpoints del OpenAPI | Parcial | 25 endpoints implementados; 15 de los especificados tienen equivalente y 10 quedan para R2+. |
| 5 | Código en main con CI en verde | No cumple | El job test-api falló en test_listar_vuelos_de_lote (1 de 13). No hay CD. |
| 6 | docker compose up levanta el sistema completo | Parcial | Levanta 6 servicios, pero las migraciones requieren un paso manual. |
| 7 | Sin bugs críticos abiertos | No cumple | "Ver resultados" en el detalle del lote navega a vuelos/undefined. |

---

## 2. Sprint 1

**Sprint 1 — Investigación técnica y de índices** · 1–8 jun 2026 · Historias H1.1–H1.4 · RFME-01/02 · RFMA-01 · RNF-04/05

### Objetivo

Antes de escribir el código, el equipo dedicó la primera semana a comprender el procesamiento geoespacial. La meta fue llegar al Sprint 3 con un entendimiento compartido de los conceptos y herramientas del sistema.

### Tareas realizadas

#### Archivos GeoTIFF multiespectrales (H1.1)

Se estudió la estructura de los GeoTIFF: bandas, valores de reflectancia y metadatos (CRS, resolución espacial, transformación geográfica). Sentinel-2 usa uint16 con factor de escala /10000. Se definió qué bandas necesita cada índice en cada sensor.

**Hallazgo clave:** el DJI Mavic 3 Multispectral captura solo 4 bandas (Green, Red, RedEdge, NIR), sin Blue. Por eso ExG no se puede calcular con ese sensor; la limitación quedó documentada en el código.

#### Rasterio, GDAL y GeoPandas (H1.2)

Se definió el rol de cada herramienta: GDAL como motor base, Rasterio para leer y transformar rásters, GeoPandas para geometrías vectoriales y NumPy para cálculos matriciales. Los índices se calculan sobre arrays completos en una sola instrucción, sin iterar píxel a píxel.

#### Cálculo y validación de índices vegetativos (H1.3)

Se validaron las fórmulas y se establecieron los umbrales agronómicos para el NEA:

| Índice | Fórmula | Cuándo usarlo | Sensor DJI Mavic 3 |
|---|---|---|---|
| NDVI | (NIR − RED) / (NIR + RED) | Crecimiento vegetativo (25–60 días) | NIR = 4, RED = 2 |
| NDRE | (NIR − RE) / (NIR + RE) | Estrés clorófilo temprano, nitrógeno | NIR = 4, RE = 3 |
| SAVI | ((NIR−RED)/(NIR+RED+0.5)) × 1.5 | Primeras 3 semanas, cobertura < 30% | NIR = 4, RED = 2 |
| ExG | 2×Green − Red − Blue | Detección de malezas de hoja ancha | No disponible (sin Blue) |

Para Sentinel-2 el mapeo es BLUE = 2, GREEN = 3, RED = 4, RE = 5, NIR = 8.

#### Interpretación agronómica — Soja en el NEA (H1.4)

El índice óptimo cambia a lo largo del ciclo fenológico de la soja:

- **V1–V3 (emergencia):** SAVI. El suelo descubierto domina la imagen y confunde al NDVI.
- **V4–Vn (crecimiento vegetativo):** NDVI. La cobertura es suficiente para que sea lineal y preciso.
- **R1–R5 (floración y llenado):** GNDVI si NDVI > 0.75, porque el NDVI satura.
- **R7–R8 (maduración):** NDVI en caída hacia 0.20–0.25, estado "listo para cosecha".
- **Umbrales generales de clasificación:** crítica (< 0.20), deficiente (0.20–0.40), normal (0.40–0.70) y vigorosa (≥ 0.70).

### Resultado

Informe técnico interno con fórmulas validadas, tabla de umbrales agronómicos por cultivo y estadio, y prueba de lectura de un GeoTIFF real con Rasterio. Este material sirvió como referencia para todo el desarrollo posterior.

---

## 3. Sprint 2

**Sprint 2 — Investigación de dominio y arquitectura** · 8–15 jun 2026 · Historias H2.1–H2.6 · RFDR-05 · RFGL-01 · RNF-06/23

### Objetivo

Con el dominio GIS incorporado, el Sprint 2 profundizó en el dominio agronómico (qué le pasa a un cultivo y cómo se ve en el mapa) y cerró las decisiones de arquitectura del sistema.

### Tareas realizadas

#### Investigación de dominio: patrones espaciales y causas probables (H2.1)

Las anomalías de un cultivo no son aleatorias: su forma geográfica revela su causa. El motor de diagnóstico de la Release 2 usará esta tabla como base de conocimiento.

| Patrón | Forma típica | Causa probable |
|---|---|---|
| Circular / radial | Mancha con núcleo y gradiente hacia los bordes | Enfermedades fúngicas (Sclerotinia, Rhizoctonia) |
| Lineal / franjas | Bandas del ancho de trabajo de la máquina | Compactación, falla de sembradora |
| Difuso / gradiente | Transición suave sin bordes definidos | Variabilidad edáfica, déficit hídrico, deficiencia N |
| Aleatorio / disperso | Manchas sin estructura geométrica | Plagas móviles (orugas, chinches), granizo |
| Manchones persistentes | Mismas posiciones en campañas distintas | Nemátodos, salinidad, variabilidad edáfica crónica |
| Sigue microtopografía | Coincide con las partes bajas del lote | Anegamiento, Phytophthora (zonas con drenaje impedido) |

#### Fumigación localizada y formatos de prescripción (H2.5)

También se documentó la fumigación diferenciada y el buffer geométrico requerido: los equipos terrestres necesitan 3–7 metros de margen alrededor del polígono para dar tiempo a la apertura de boquillas. Se relevaron los formatos de prescripción Shapefile e ISO-XML.

#### Validación bibliográfica de umbrales (H2.6)

Los umbrales se validaron con fuentes primarias del INTA y se contextualizaron para el NEA.

#### Stack y arquitectura del sistema (H2.2, H2.3)

Se eligió una arquitectura monolítica modular de cuatro capas. La decisión central: el procesamiento de GeoTIFF nunca ocurre dentro de FastAPI, siempre pasa por una cola Celery hacia un Worker GIS independiente.

| Capa | Componentes y responsabilidad |
|---|---|
| Frontend | Vite + React + React-Leaflet. Interfaz de usuario, mapas GeoJSON, polling de estado del análisis. |
| Backend (API) | FastAPI + SQLAlchemy async. REST API, autenticación JWT, coordinación de tareas. No hace procesamiento GIS. |
| Worker GIS | Celery + Rasterio + NumPy + GeoPandas. Procesamiento asíncrono de GeoTIFF, cálculo de índices, vectorización y exportación GeoJSON. |
| Datos | PostgreSQL + PostGIS (metadatos y vectores) · MinIO (archivos binarios) · Redis (broker + result backend Celery). |

**Diagrama de componentes** (transcripción del diagrama del PDF):

| Capa del diagrama | Componentes | Funciones listadas |
|---|---|---|
| Frontend | React, Leaflet | Dashboards; mapas interactivos; subida de archivos; visualización de resultados; reportes. Leaflet: mapas y visualización GIS. |
| Capa de aplicación — Backend | FastAPI | Autenticación; gestión de lotes; análisis; reportes. |
| | Redis (broker / caché) | Colas de tareas; caché; estado temporal. |
| | Celery (task queue) | Distribuye tareas; paraleliza trabajos; reintentos. |
| Capa de procesamiento | Worker GIS: GDAL, Rasterio, NumPy, GeoPandas, Shapely | Lectura y reproyección de mapas; cálculos; vectorización y análisis espacial; generación de mapas y reportes; exportación de resultados. |
| Capa de datos | PostgreSQL + PostGIS (base de datos espacial) | Usuarios y permisos; lotes; geometrías y polígonos; índices e indicadores; metadatos e historial. |
| | MinIO | Mapas; ortofotos/mosaicos; mapas generados; reportes; archivos exportados; archivos temporales. |
| Infraestructura / despliegue | Docker | — |

Conexiones del diagrama: Frontend ↔ Backend (REST API + GeoJSON); FastAPI ↔ Redis ↔ Celery; Backend ↔ Worker GIS; Backend ↔ Capa de datos; PostgreSQL/PostGIS ↔ MinIO; MinIO ↔ Worker GIS.

*[Nota del conversor: el diagrama es el diseño de arquitectura del Sprint 2. Algunos componentes que dibuja, como la generación de reportes, corresponden a releases posteriores según la sección 8.]*

**Flujo principal de datos**

- El usuario sube un GeoTIFF desde el frontend → FastAPI lo recibe y lo almacena en MinIO.
- FastAPI encola una tarea Celery en Redis y responde 202 Accepted de inmediato (sin bloquear).
- El Worker GIS toma la tarea: lee el GeoTIFF, calcula el índice, vectoriza y sube el GeoJSON resultante a MinIO.
- El frontend consulta el estado cada 2 segundos. Cuando termina, descarga el GeoJSON a través del backend y lo renderiza en Leaflet.

**Decisiones de arquitectura principales**

- **Worker GIS separado:** el procesamiento puede tardar minutos y bloquearía la API. Celery permite procesar en background y reintentar ante fallos.
- **MinIO para archivos binarios:** separa GeoTIFF y PDF de los metadatos y vectores que van a PostgreSQL. URLs firmadas temporarias para acceso desde el frontend.
- **Redis con doble rol:** broker de Celery (db 0) y result backend para polling de estado (db 1). Sin result backend, el polling siempre devolvería PENDING.
- **Soft delete:** deleted_at timestamp en lugar de DELETE físico, para preservar el historial de vuelos y análisis.

#### Especificación de la API (OpenAPI) (H2.4)

Se especificó el contrato de la API antes de implementarla. Los endpoints principales acordados:

- POST /auth/register y /auth/login — registro y autenticación.
- POST /lotes — crear lote con límite GeoJSON.
- POST /lotes/{id}/vuelos — subir GeoTIFF a un lote existente.
- GET /lotes/{id}/vuelos/{id}/estado — polling de progreso del análisis.
- GET /lotes/{id}/vuelos/{id}/resultado — GeoJSON con zonas clasificadas.

### Resultado

Documento de arquitectura con diagramas de componentes, síntesis de entrevistas agronómicas y especificación OpenAPI completa. El equipo arrancó el Sprint 3 con el diseño cerrado y sin deudas conceptuales.

---

## 4. Sprint 3

**Sprint 3 — Setup, infraestructura, autenticación y lotes** · 15–22 jun 2026 · Historias H3.1–H3.6 · RFGL-01/02 · RNF-05/06/23

### Objetivo

Levantar el stack completo y construir la base funcional: autenticación JWT, CRUD de lotes con geometría PostGIS, frontend con login y dashboard, e integración continua. Al final del sprint, un usuario puede registrarse, iniciar sesión y crear un lote.

### Tareas realizadas

#### Infraestructura y Docker Compose (H3.1, H3.2)

Se configuró un stack de 6 servicios: PostgreSQL 16 + PostGIS 3.4, Redis 7, MinIO, API FastAPI (Python 3.12), Worker GIS (imagen osgeo/gdal 3.9.0) y frontend (Node 20). api y worker esperan a que db, redis y minio estén saludables antes de arrancar. Las variables se cargan desde un .env creado a partir de .env.example, nunca commiteado.

FastAPI usa SQLAlchemy async y GeoAlchemy2, con Alembic para migraciones. La migración 0001 habilita las extensiones postgis, postgis_topology y uuid-ossp.

#### Modelos y CRUD de lotes (H3.4)

Se implementaron los modelos Lote y Vuelo con geometría PostGIS, schemas Pydantic con validación geométrica (Shapely), una capa de servicios y los endpoints REST. El área del lote se calcula en PostGIS reproyectando a EPSG:32721 (metros) para mayor precisión. La geometría pasó a ser opcional: si un lote se crea sin límite, el worker la completa con el bounding box del GeoTIFF.

#### Autenticación JWT (H3.3)

Modelo Usuario, contraseñas con bcrypt, dependencia get_current_user para proteger endpoints y router con register, login, me, refresh y logout. Access token de 30 minutos y refresh token de 7 días. Cada usuario solo ve sus propios lotes y vuelos. La migración 0006 agrega un usuario seed para desarrollo.

#### Frontend base (H3.5)

Se creó el scaffold Vite + React con cliente HTTP axios, interceptores JWT, hook useAuth, pantalla de Login y Dashboard con lista de lotes y rutas protegidas (PrivateRoute).

#### Integración continua — GitHub Actions (H3.6)

Pipeline CI con 3 jobs paralelos que corren en cada push a main:

- **test-api:** levanta PostGIS y Redis como servicios, corre las migraciones Alembic, verifica /health y ejecuta los tests HTTP.
- **test-gis:** usa la imagen osgeo/gdal, instala las dependencias GIS y corre los tests del pipeline.
- **build-frontend:** Node 20, npm install y npm run build.

### Resultado

Stack corriendo con docker compose up. Un usuario puede registrarse, hacer login, crear un lote con límite GeoJSON y verlo en el dashboard. CI verde en cada push.

---

## 5. Sprint 4

**Sprint 4 — Ingesta, pipeline GIS y visualización del índice** · 22–29 jun 2026 · Historias H4.1–H4.5 · RFME-01–03/05 · RFMA-01 · RFMP-01 · RNF-04/28

### Objetivo

Conectar el frontend con el Worker GIS: el usuario sube un GeoTIFF, el sistema lo procesa de forma asíncrona y muestra el resultado en el mapa con barra de progreso en tiempo real.

### Tareas realizadas

#### Ingesta y validación de GeoTIFF (H4.1)

Se implementó la validación en dos capas:

- **En la API (sin rasterio):** extensión .tif / .tiff, archivo no vacío, tamaño máximo de 2 GB y magic bytes TIFF.
- **En el Worker (con rasterio):** CRS definido, bandas requeridas por el sensor y tipo de dato compatible (float32, uint8, uint16, int16 o int32).

El archivo se guarda primero en MinIO en {usuario_id}/{lote_id}/{vuelo_id}/, lo que permite reencolar el análisis sin volver a subirlo si el procesamiento falla.

#### Worker asíncrono con Celery (H4.2)

Celery usa Redis como broker y result backend, con una cola gis dedicada, TTL de resultados y reintentos automáticos ante errores de red o de MinIO. La tarea procesar_vuelo lee el GeoTIFF de MinIO, ejecuta el pipeline, sube el GeoJSON resultante y actualiza el estado en la base. El worker informa el porcentaje de progreso en cada etapa.

#### Pipeline GIS: índices y mapeo de bandas (H4.3)

El pipeline soporta los cuatro índices con mapeo configurable de bandas por sensor (band_mapping.py). Las funciones operan sobre arrays NumPy completos, manejan nodata y división por cero, y devuelven siempre float32. Si el archivo viene en otro sistema de coordenadas, se reproyecta automáticamente a EPSG:4326.

#### Visualización con Leaflet y polling de progreso (H4.4)

Se implementó en el frontend:

- **useVueloProgreso:** consulta el endpoint de estado cada 2 segundos hasta que el análisis termina.
- **BarraProgreso:** muestra el porcentaje y el paso actual del worker.
- **Mapa de zonas:** capa GeoJSON coloreada por clase, con tooltip de índice promedio y superficie en hectáreas.

Esta historia quedó al 60 % y se completó en el Sprint 5.

#### Flujo de alta desacoplado

Se separó la creación del lote de la carga del GeoTIFF, para poder cargar varios vuelos al mismo lote a lo largo del tiempo:

- **Nuevo lote:** crea el lote con su límite GeoJSON → POST /lotes.
- **Carga de GeoTIFF:** sube un vuelo a un lote existente → POST /lotes/{id}/vuelos.
- **Alta en un paso:** crea lote + vuelo a partir del GeoTIFF → POST /lotes/desde-geotiff.

#### Tests del pipeline GIS (H4.5)

Se crearon fixtures GeoTIFF sintéticos y tests del pipeline NDVI, de los índices y de la validación GIS, incorporados al job test-gis del CI.

### Resultado

Flujo funcional: crear lote → subir GeoTIFF → barra de progreso en tiempo real → mapa clasificado. Verificado con archivos reales del DJI Mavic 3 Multispectral. Con archivos de tamaño real el worker resultó lento, porque procesa el ráster completo en memoria.

---

## 6. Sprint 5

**Sprint 5 — Clasificación, límites, testing y estabilización** · 29 jun–7 jul 2026 · Historias H5.1, H5.2, H5.5–H5.7 · RFMA-02/04 · RFMP-02–05 · RFGL-02 · RNF-10–12

### Objetivo

Completar el MVP: vectorización robusta, estadísticas correctas por zona, multi-índice real, navegación funcional y testing integral. Al final del sprint el sistema debe ser demostrable de punta a punta.

### Tareas realizadas

#### Umbralización dinámica y vectorización robusta

La clasificación admite tres métodos intercambiables: fijo (umbrales 0.20 / 0.40 / 0.70), Otsu (umbral automático según la distribución) y percentil (p25 / p50 / p75). Si la imagen es uniforme, se usa el método fijo.

Se resolvió la fragmentación "sal y pimienta" con un filtro gaussiano (sigma = 1 píxel) antes de clasificar; las estadísticas se calculan sobre el valor original. Además, gdf.explode() se aplica antes del filtro de área mínima, para medir cada fragmento por separado. En un archivo real con gradiente continuo, el resultado pasó de 2 MultiPolygon con 100 y 140 fragmentos a 2 polígonos limpios.

#### Estadísticas por zona y zonas atípicas (H5.1, parcial)

Cada polígono tiene superficie en ha, porcentaje del lote, índice promedio, mínimo y máximo. Las zonas con |z| > 1.5 se marcan como atípicas (es_atipica) en el GeoJSON. La tabla de estadísticas (TablaZonas.jsx) muestra clase, área, % del lote, índice promedio y cantidad de polígonos. La severidad por zona quedó para la Release 2.

#### Modal de límites del lote y vista previa (H5.2)

El modal de límites acepta un archivo .geojson por drag & drop, lo muestra en un mapa React-Leaflet y actualiza el lote con PUT /lotes/{id}. Acepta Polygon, Feature con Polygon o FeatureCollection, los formatos más comunes de QGIS. Cada card del dashboard muestra un mini-mapa estático de 110 px con el polígono del lote.

La carga del GeoTIFF pasó a un wizard de 2 pasos. El primero inspecciona el archivo con POST /lotes/inspeccionar-geotiff y muestra bandas, CRS y compatibilidad con el sensor antes de procesar.

#### Multi-índice real y almacenamiento de zonas (H5.5)

Los cuatro índices pasaron a procesarse realmente en paralelo, con la tabla analisis_indices (ciclo de vida propio por índice) y la tarea Celery analizar_indice. El dashboard tiene un selector para cambiar el índice visible. ExG sobre DJI Mavic 3 falla con un mensaje claro sin afectar a los demás índices. Las zonas se guardan como GeoJSON en MinIO, con su referencia en geojson_key.

#### Dashboard y navegación (H5.6, parcial)

Dashboard con KPIs, tabla de análisis recientes y mapa de zonas. El sidebar navega con react-router a Dashboard y Lotes; la pantalla de Lotes muestra una grilla de cards con detalle y eliminación. La tarjeta "Ahorro estimado" muestra "—" hasta que exista el motor de diagnóstico.

#### Tests de integración y acciones sobre análisis (H5.7)

Se implementaron 48 tests HTTP sobre PostGIS real, sin mocks, que cubren auth JWT, gestión de lotes y estados de vuelos. Total al corte: 88 tests (48 de API + 40 de GIS). Se agregaron DELETE /vuelos/{id} (soft delete) y POST /vuelos/{id}/reintentar, que reencola sin pedir un nuevo upload.

### Resultado

MVP demostrable de punta a punta: multi-índice real, estadísticas por zona y navegación conectada. Al corte quedaron abiertos un test fallido en CI y un bug en el detalle del lote (ver sección 8).

---

## 7. Calidad y estado al cierre

Al corte había 88 tests automatizados y 2 de los 3 jobs de CI en verde. El job de API falló por un único test (test_listar_vuelos_de_lote), causado por la misma inconsistencia de vuelo_id que el bug del detalle del lote.

### Pruebas automatizadas

| Tipo | Herramienta | Tests | Resultado en el corte |
|---|---|---|---|
| Unitarias GIS | pytest | 40 (pipeline NDVI, índices, validación, clasificación, configuración Celery) | Job test-gis en verde |
| Integración HTTP contra PostGIS | pytest + TestClient | 48 (auth 15, lotes 16, vuelos 13, ingesta 4) | Job test-api en rojo: 1 fallido, 12 pasan en vuelos |
| End-to-end | pytest (test_ciclo_completo_encolar_y_esperar) | 1 | Pasa solo en local; no corre en CI |
| Frontend | — | 0 | El job build-frontend solo verifica el build |
| Rendimiento y seguridad | — | — | No realizados en esta release |

La cobertura no se midió. La bitácora registra 85 tests porque no cuenta los 3 de test_celery_integracion.py.

### Verificaciones manuales

| Fecha | Verificación | Resultado |
|---|---|---|
| 6 jul | Pantalla Lotes vía API: crear, listar, eliminar | Soft delete confirmado |
| 6 jul | Multi-índice con vuelo DJI Mavic 3: NDVI, SAVI y NDRE en paralelo | Los 3 completados, cada uno con su GeoJSON |
| 5 jul | Archivo real con gradiente continuo tras el fix "sal y pimienta" | 2 polígonos limpios |
| 5 jul | GeoTIFF real de 4 bandas con perfil dji_mavic3 corregido | 2 polígonos, NDVI promedio 0.6053 |
| 5 jul | Inspector de GeoTIFF contra Rasterio con archivos de 4 y 5 bandas | Coincidencia exacta |
| 1 jul | E2E local: GeoTIFF a MinIO → tarea → zonas.geojson | Completado en 2 s |
| 30 jun | Ciclo completo de Celery (upload → cola → procesamiento) | OK tras reiniciar el worker |
| 24 jun | CRUD de lotes vía API, incluido 404 tras borrar | deleted_at seteado, registro preservado |

### Errores corregidos durante el desarrollo

Ninguno afectó a una versión publicada. Los más relevantes:

- Perfil de bandas del DJI Mavic 3 incorrecto: esperaba 5 bandas con Blue; el sensor real tiene 4.
- El worker no actualizaba la geometría del lote al subir a un lote existente, porque no recibía el lote_id.
- Ruta duplicada GET /{lote_id}/vuelos en dos módulos, que mostraba vuelos eliminados.
- features.shapes() rechazaba float64: el worker ahora castea a float32 antes de vectorizar.
- Problemas de imagen del worker: faltaba copiar app/, conflicto de NumPy con la imagen GDAL y pydantic-settings ausente.

**Tarea Celery no registrada:** se resolvió reiniciando el worker, lo que dio origen al criterio de la DoD.

### Despliegue de la demo

La demo corrió en local. Pasos: clonar y hacer checkout de v1.0.0, crear .env desde .env.example, ejecutar docker compose up -d --build y luego, a mano, docker compose exec api alembic upgrade head. La verificación se hace con GET /api/v1/health, GET /api/v1/health/db y Swagger en /api/docs.

---

## 8. Deuda técnica y trabajo pendiente

Los siguientes ítems estaban planificados para la Release 1 pero no se completaron. Son funcionalidades nuevas, no correcciones de bugs — el MVP entregado es estable.

### Defectos y riesgos conocidos

| Ítem | Descripción | Impacto | Estado |
|---|---|---|---|
| "Ver resultados" en detalle del lote | Navega a vuelos/undefined porque la API devuelve vuelo_id y el frontend lee id. Workaround: entrar desde el Dashboard. | Alto | Corregido en R2 (fc9ebb2) |
| Test fallido en CI | test_listar_vuelos_de_lote falla por la misma causa. | Medio | Corregido en R2 (fc9ebb2) |
| IDOR en índices adicionales | Los endpoints de estado y resultado por índice no verifican que el vuelo pertenezca al lote: un usuario podría leer datos de otro conociendo el vuelo_id. | Alto (seguridad) | Corregido (PR #49, 30 sep 2026) |
| Registro desde la interfaz | El botón "Registrarse" no está conectado; el registro solo funciona vía API. | Medio | Abierto |
| Usuario seed con credenciales conocidas | La migración 0006 incluye la contraseña del usuario de desarrollo y se aplica en cualquier base migrada. | Medio | Abierto |
| Archivos grandes en memoria | Límite de 2 GB y archivo cargado completo en memoria en API y worker; procesamiento lento con archivos reales. | Alto en uso real | Streaming y procesamiento por tiles en R2 |
| Imagen minio/minio:latest | Sin versión fija; la imagen dejó de estar disponible y puede impedir levantar el tag v1.0.0. | Alto (reproducibilidad) | Corregido en main (7e7182d), no en el tag |
| Dependencias sin fijar | scipy llega como dependencia transitiva sin versión; el frontend usa npm install con rangos ^. | Bajo | Abierto |
| Migraciones manuales | Hay que correr alembic upgrade head a mano; los downgrades de 0005 y 0010 están incompletos. | Bajo | Abierto |

### Funcionalidades pendientes

| Ítem | Descripción | Release destino |
|---|---|---|
| Motor de diagnóstico (RFDR-01) | Clasificar cada zona por patrón + índice + contexto y generar causas probables ordenadas por verosimilitud. | Release 2 |
| Severidad, zonificación de manejo y ahorro de insumos | Severidad por zona (RFDR-02/03) y cálculo del "Ahorro estimado" del dashboard; dependen del motor de diagnóstico. | Release 2 |
| Roles y permisos | Admin / Operador / Técnico; hoy hay un único tipo de usuario. | Release 2 |
| Testing E2E en CI y cobertura | El test E2E requiere MinIO + worker levantados; faltan tests de frontend y medición de cobertura. | Release 2 |
| Zonas en PostGIS | Las zonas viven como GeoJSON en MinIO, sin consultas espaciales ni historial sobre ellas. | A definir |
| Exportación PDF, Shapefile e ISO-XML | Reporte ejecutivo PDF (WeasyPrint) y prescripciones para maquinaria. | Release 3 |
