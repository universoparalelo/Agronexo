# Arquitectura de Módulos y Responsabilidades — AgroNexo

## 1. Introducción

Este documento define los módulos del sistema AgroNexo, sus responsabilidades, las relaciones entre ellos y su mapeo con los requisitos funcionales de la ERS. Complementa el documento de Stack Tecnológico (que describe *qué tecnologías* se usan y por qué) con la definición de *qué hace cada parte del sistema*.

La arquitectura sigue el patrón de **monolito modular con worker desacoplado**: todos los módulos del backend comparten el mismo proceso y la misma base de datos, pero están organizados internamente con responsabilidades aisladas. El Worker GIS es el único componente que se ejecuta como proceso separado, conectado mediante una cola de tareas.

---

## 2. Capas del sistema

El sistema se organiza en cuatro capas, cada una con un rol definido:

| Capa | Responsabilidad | Comunicación |
|---|---|---|
| **Frontend** | Interfaz de usuario, visualización de mapas y resultados | REST API + GeoJSON hacia el Backend |
| **Backend (Aplicación)** | Lógica de negocio, autenticación, coordinación de procesamiento | HTTP desde Frontend, Celery hacia Worker, SQL hacia Datos |
| **Procesamiento (Worker GIS)** | Cálculo de índices, vectorización, análisis espacial | Recibe tareas de Celery, lee/escribe en la Capa de Datos |
| **Datos** | Persistencia de metadatos, geometrías y archivos binarios | Accedida por Backend y Worker |

---

## 3. Módulos del sistema

### 3.1 Módulo de Autenticación y Seguridad

**Capa:** Backend (FastAPI)

**Responsabilidad:** Gestionar el acceso al sistema, garantizar el aislamiento de datos entre usuarios y proteger las comunicaciones.

**Qué hace:**
- Registro y login de usuarios con JWT
- Validación de tokens en cada request protegida
- Expiración automática de sesiones inactivas (30 minutos)
- Aislamiento de datos por usuario (multi-tenencia)
- Validación y sanitización de entradas contra inyecciones y XSS

**Qué NO hace:**
- No gestiona roles diferenciados (productor vs prestador) en el MVP — todos los usuarios autenticados tienen las mismas capacidades
- No implementa OAuth ni SSO

**Requisitos que cubre:**

| ID | Requisito |
|---|---|
| RNF-05 | Autenticación de usuarios |
| RNF-06 | Control de acceso por usuario |
| RNF-07 | Cifrado de comunicaciones (HTTPS) |
| RNF-08 | Validación de entradas |
| RNF-09 | Gestión de sesiones |
| RFGL-01 | Multi-tenencia de datos |

---

### 3.2 Módulo de Gestión de Lotes

**Capa:** Backend (FastAPI)

**Responsabilidad:** Administrar la información de los lotes agrícolas del usuario, incluyendo sus límites geográficos, historial de vuelos y contexto agronómico.

**Qué hace:**
- CRUD de lotes con límites geográficos (polígonos almacenados en PostGIS)
- Registro de vuelos asociados a cada lote (fecha, condiciones, sensor utilizado)
- Registro de contexto agrológico: tipo de cultivo, estadio fenológico, condiciones climáticas
- Mantenimiento de línea de tiempo de intervenciones (vuelos, análisis, aplicaciones)
- Gestión de hasta 50 lotes por usuario sin degradación

**Qué NO hace:**
- No procesa archivos GeoTIFF — los recibe, los almacena en MinIO y delega el procesamiento al Worker
- No realiza cálculos espaciales complejos — usa PostGIS para almacenamiento y consultas básicas

**Requisitos que cubre:**

| ID | Requisito |
|---|---|
| RFME-03 | Registro de contexto agrológico |
| RFGL-02 | Inventario de lotes con límites geográficos |
| RFGL-03 | Historial de intervenciones |
| RFGL-04 | Gestión de capas (superposición de análisis por fecha) |
| RNF-19 | Procesamiento de múltiples lotes (hasta 50) |

---

### 3.3 Módulo de Ingesta y Validación

**Capa:** Backend (FastAPI)

**Responsabilidad:** Recibir los archivos GeoTIFF del usuario, validar su integridad y metadatos, almacenarlos en MinIO y encolar el procesamiento.

**Qué hace:**
- Recepción de archivos GeoTIFF mediante upload HTTP
- Validación de metadatos: presencia de bandas espectrales válidas (RGB/NIR), CRS definido, integridad del archivo
- Almacenamiento del archivo original en MinIO con estructura `usuario/lote/vuelo/`
- Generación de vista previa low-res para confirmación visual antes de procesar
- Encolamiento de la tarea de procesamiento en Redis/Celery
- Soporte para archivos de hasta 1 GB

**Qué NO hace:**
- No procesa el archivo — solo lo valida y lo almacena
- No calcula índices ni genera polígonos

**Requisitos que cubre:**

| ID | Requisito |
|---|---|
| RFME-01 | Carga de archivos ráster (GeoTIFF) |
| RFME-02 | Validación de metadatos (bandas, CRS) |
| RFME-04 | Visualización de integridad (vista previa low-res) |
| RFMP-05 | Persistencia de datos (archivos fuente) |
| RNF-17 | Soporte de archivos de hasta 1 GB |

---

### 3.4 Módulo de Procesamiento Geoespacial (Worker GIS)

**Capa:** Procesamiento (Worker Celery)

**Responsabilidad:** Ejecutar todo el pipeline de análisis geoespacial: lectura de rasters, cálculo de índices de vegetación, clasificación, vectorización y exportación de resultados.

Este es el núcleo técnico del sistema. Se ejecuta como proceso Celery independiente del backend.

**Qué hace:**
- Lectura del GeoTIFF desde MinIO con Rasterio (windowed reading para archivos grandes)
- Reproyección cartográfica al sistema de coordenadas local (UTM) si es necesario
- Cálculo de índices de vegetación: NDVI, NDRE, SAVI, ExG según bandas disponibles
- Umbralización dinámica para clasificar píxeles en categorías de vigor/anomalía
- Soporte para calibración manual y automática de umbrales (método de Otsu)
- Detección de anomalías: áreas con valores atípicos que sugieran estrés o plagas
- Vectorización: conversión de píxeles clasificados en polígonos georeferenciados (gdal_polygonize)
- Simplificación de polígonos con Douglas-Peucker para reducir vértices
- Filtrado de ruido: eliminación de polígonos menores a un área mínima configurable
- Zonificación: agrupación de áreas contiguas con necesidades similares
- Cálculo de estadísticas por zona: área en hectáreas, índice promedio, severidad
- Cálculo de ahorro de insumos (área total vs área prescrita)
- Almacenamiento de resultados: polígonos en PostGIS, archivos generados en MinIO
- Reporte de progreso en Redis para que el frontend muestre avance en tiempo real

**Qué NO hace:**
- No atiende requests HTTP — solo ejecuta tareas encoladas por Celery
- No genera diagnósticos en lenguaje natural — solo produce datos estructurados
- No genera PDFs ni reportes finales — produce los datos que otros módulos consumen

**Requisitos que cubre:**

| ID | Requisito |
|---|---|
| RFMA-01 | Procesamiento de índices de vegetación |
| RFMA-02 | Umbralización dinámica |
| RFMA-03 | Calibración de umbrales (manual y Otsu) |
| RFMA-04 | Detección de anomalías |
| RFMP-01 | Reproyección cartográfica |
| RFMP-02 | Extracción de geometrías (vectorización) |
| RFMP-03 | Generalización / simplificación de polígonos |
| RFMP-04 | Filtrado de ruido (área mínima) |
| RFMP-05 | Persistencia de resultados |
| RFDR-02 | Zonificación de manejo |
| RFDR-03 | Estimación de severidad |
| RFGL-05 | Análisis de eficiencia (ahorro de insumos) |
| RNF-02 | Procesamiento en menos de 5 minutos (hasta 500 MB) |
| RNF-04 | Retroalimentación de progreso cada 10 segundos |
| RNF-15 | Recuperación ante fallos (reintentos Celery) |

---

### 3.5 Módulo de Diagnóstico

**Capa:** Backend (FastAPI)

**Responsabilidad:** Interpretar los resultados del procesamiento geoespacial y generar un diagnóstico comprensible que asocie los datos técnicos con acciones agronómicas concretas.

**Qué hace:**
- Motor de reglas que cruza: índice calculado + tipo de cultivo + estadio fenológico + contexto del lote
- Asociación de niveles de índice con acciones recomendadas (dosis variable por zona)
- Vinculación de cada diagnóstico con el vuelo y lote correspondiente (trazabilidad)
- Permite al profesional adjuntar justificación o comentario técnico al diagnóstico

**Qué NO hace (por ahora):**
- No genera texto en lenguaje natural — produce diagnósticos estructurados basados en reglas
- La integración con LLM para generación de texto está prevista como mejora futura, no como parte del MVP

**Requisitos que cubre:**

| ID | Requisito |
|---|---|
| RFDR-01 | Motor de reglas (índice → acción recomendada) |
| RFDR-04 | Registro de criterio técnico |
| RFDR-05 | Trazabilidad de vuelo |

---

### 3.6 Módulo de Reportes y Exportación

**Capa:** Backend (FastAPI)

**Responsabilidad:** Generar todos los entregables del sistema: reportes PDF, archivos de prescripción para maquinaria y órdenes de trabajo.

**Qué hace:**
- Generación de Reporte Ejecutivo en PDF: mapas, estadísticas de ahorro, diagnóstico
- Exportación de prescripciones en formatos compatibles con maquinaria (Shapefile, GeoJSON)
- Generación de Orden de Trabajo con dosis, restricciones ambientales e instrucciones de seguridad
- Carga y contraste de log de aplicación real vs prescripción original

**Qué NO hace:**
- No calcula los datos — los consume de PostGIS y MinIO, generados por el Worker y el módulo de Diagnóstico
- No envía los reportes por email — los deja disponibles para descarga

**Requisitos que cubre:**

| ID | Requisito |
|---|---|
| RFSA-01 | Exportación de prescripción (Shapefile, ISO-XML) |
| RFSA-02 | Generación de Orden de Trabajo |
| RFSA-03 | Reporte Ejecutivo (PDF) |
| RFSA-04 | Certificación de aplicación (log real vs prescripción) |
| RNF-26 | Formatos de exportación estándar |

---

### 3.7 Frontend

**Capa:** Frontend (React)

**Responsabilidad:** Proveer la interfaz de usuario para todas las operaciones del sistema, incluyendo la visualización de mapas interactivos con los resultados del análisis.

**Qué hace:**
- Dashboards con resumen de lotes, análisis recientes y estado de procesamiento
- Mapas interactivos con Leaflet: polígonos GeoJSON con estilos por clase, capas superpuestas por fecha
- Subida de archivos GeoTIFF con barra de progreso
- Polling de estado de procesamiento con indicadores visuales
- Visualización de diagnósticos y estadísticas por zona
- Descarga de reportes PDF y archivos de prescripción
- Interfaz responsiva para desktop y tablet

**Qué NO hace:**
- No procesa datos geoespaciales en el browser
- No almacena estado persistente — toda la información viene de la API

**Requisitos que cubre:**

| ID | Requisito |
|---|---|
| RNF-01 | Tiempo de carga menor a 3 segundos |
| RNF-04 | Retroalimentación visual del progreso |
| RNF-10 | Curva de aprendizaje baja |
| RNF-11 | Mensajes de error comprensibles |
| RNF-12 | Consistencia de la interfaz |
| RNF-13 | Accesibilidad básica |
| RNF-20 | Compatibilidad con Chrome, Firefox, Edge |
| RNF-21 | Diseño responsivo |

---

## 4. Relaciones entre módulos

### 4.1 Flujo principal: upload → análisis → resultado

```
Usuario sube GeoTIFF
        ↓
[Ingesta y Validación]
  - valida metadatos
  - guarda en MinIO
  - encola tarea
        ↓
[Worker GIS]
  - lee de MinIO
  - calcula índices
  - vectoriza
  - guarda polígonos en PostGIS
  - guarda archivos en MinIO
        ↓
[Diagnóstico]
  - lee polígonos y estadísticas de PostGIS
  - aplica reglas según cultivo y estadio
  - genera diagnóstico estructurado
        ↓
[Reportes y Exportación]
  - genera PDF con mapas y diagnóstico
  - exporta Shapefile para maquinaria
  - genera Orden de Trabajo
        ↓
[Frontend]
  - muestra mapas con polígonos
  - muestra diagnóstico
  - permite descarga de archivos
```

### 4.2 Matriz de dependencias entre módulos

| Módulo | Depende de | Es consumido por |
|---|---|---|
| Autenticación | — | Todos los módulos (middleware) |
| Gestión de Lotes | Autenticación | Ingesta, Diagnóstico, Reportes, Frontend |
| Ingesta y Validación | Autenticación, Gestión de Lotes | Worker GIS |
| Worker GIS | Ingesta (indirectamente, vía cola) | Diagnóstico, Reportes |
| Diagnóstico | Worker GIS (resultados), Gestión de Lotes (contexto) | Reportes, Frontend |
| Reportes y Exportación | Diagnóstico, Worker GIS (datos) | Frontend |
| Frontend | Todos los módulos del Backend (vía API REST) | — |

---

## 5. Estructura de carpetas propuesta

```
agronexo/
├── app/
│   ├── main.py                    # Punto de entrada FastAPI
│   ├── config.py                  # Configuración con Pydantic BaseSettings
│   ├── dependencies.py            # Dependencias compartidas (DB, auth)
│   │
│   ├── auth/                      # Módulo de Autenticación
│   │   ├── router.py              # Endpoints: login, register, refresh
│   │   ├── schemas.py             # Pydantic models
│   │   ├── service.py             # Lógica de negocio
│   │   └── security.py            # JWT, hashing
│   │
│   ├── lotes/                     # Módulo de Gestión de Lotes
│   │   ├── router.py              # Endpoints: CRUD lotes, vuelos
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── models.py              # Modelos SQLAlchemy + PostGIS
│   │
│   ├── ingesta/                   # Módulo de Ingesta y Validación
│   │   ├── router.py              # Endpoints: upload, estado, preview
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── validators.py          # Validación de GeoTIFF
│   │
│   ├── diagnostico/               # Módulo de Diagnóstico
│   │   ├── router.py              # Endpoints: consultar diagnóstico
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── reglas.py              # Motor de reglas agronómicas
│   │
│   ├── reportes/                  # Módulo de Reportes y Exportación
│   │   ├── router.py              # Endpoints: generar PDF, exportar shp
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── templates/             # Templates HTML para WeasyPrint
│   │
│   └── models/                    # Modelos compartidos
│       ├── base.py                # Base declarativa SQLAlchemy
│       └── database.py            # Conexión a PostgreSQL
│
├── worker/                        # Worker GIS (proceso Celery separado)
│   ├── celery_app.py              # Configuración Celery
│   ├── tasks.py                   # Definición de tareas
│   ├── pipeline/
│   │   ├── lectura.py             # Lectura de GeoTIFF con Rasterio
│   │   ├── indices.py             # Cálculo de NDVI, NDRE, SAVI, ExG
│   │   ├── clasificacion.py       # Umbralización y detección de anomalías
│   │   ├── vectorizacion.py       # Raster → polígonos con GDAL
│   │   ├── simplificacion.py      # Douglas-Peucker, filtrado de ruido
│   │   └── exportacion.py         # Guardado en PostGIS y MinIO
│   └── utils/
│       ├── progreso.py            # Reporte de progreso a Redis
│       └── crs.py                 # Utilidades de reproyección
│
├── docker-compose.yml
├── Dockerfile
├── Dockerfile.worker
└── requirements.txt
```

---

## 6. Mapeo completo: Requisitos → Módulos

| Grupo ERS | IDs | Módulo responsable |
|---|---|---|
| Entrada y validación | RFME-01 a RFME-04 | Ingesta y Validación |
| Análisis y procesamiento | RFMA-01 a RFMA-04 | Worker GIS |
| Procesamiento geoespacial | RFMP-01 a RFMP-05 | Worker GIS + Ingesta (persistencia) |
| Diagnóstico y prescripción | RFDR-01 a RFDR-05 | Diagnóstico + Worker GIS (zonificación, severidad) |
| Gestión del lote | RFGL-01 a RFGL-05 | Gestión de Lotes + Autenticación (multi-tenencia) + Worker GIS (eficiencia) |
| Salida | RFSA-01 a RFSA-04 | Reportes y Exportación |
| Rendimiento | RNF-01 a RNF-04 | Frontend (carga) + Worker GIS (procesamiento) |
| Seguridad | RNF-05 a RNF-09 | Autenticación |
| Usabilidad | RNF-10 a RNF-13 | Frontend |
| Disponibilidad | RNF-14 a RNF-16 | Infraestructura (Docker) + Worker GIS (reintentos Celery) |
| Escalabilidad | RNF-17 a RNF-19 | Ingesta (archivos grandes) + Worker GIS (concurrencia) + Gestión de Lotes |
| Portabilidad | RNF-20 a RNF-22 | Frontend |
| Mantenibilidad | RNF-23 a RNF-25 | Todos (arquitectura modular, documentación, logs) |
| Interoperabilidad | RNF-26 a RNF-28 | Reportes (formatos) + Worker GIS (CRS, sensores) |
