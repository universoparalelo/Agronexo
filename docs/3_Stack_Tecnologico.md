# Stack Tecnológico — AgroNexo

## Arquitectura general

El sistema sigue una **arquitectura monolítica modular** organizada en cuatro capas bien diferenciadas: Frontend, Backend (capa de aplicación), Procesamiento y Datos. Toda la infraestructura corre sobre Docker, lo que garantiza portabilidad y reproducibilidad del entorno.

La separación entre el Backend y el Worker GIS es la decisión de diseño más importante: el procesamiento de archivos GeoTIFF (que puede tomar minutos y consumir mucha memoria) ocurre de forma asíncrona en workers independientes, sin bloquear la API principal ni degradar la experiencia del usuario.

---

## Capas y tecnologías

### Frontend

| Tecnología | Rol |
|---|---|
| **React** | Framework principal de UI |
| **Leaflet** | Visualización de mapas y capas GIS |
| **Vite** | Herramienta de build y servidor de desarrollo |
| **Tailwind CSS** | Sistema de estilos y diseño visual (previsto) |

**React** fue elegido por su ecosistema maduro, la facilidad para manejar estado complejo (resultados de análisis, capas de mapa, polling de procesamiento) y la disponibilidad de librerías especializadas para este dominio.

**Leaflet** (vía React-Leaflet) es la solución estándar de código abierto para mapas interactivos en web. Permite renderizar polígonos GeoJSON con estilos por clase, superponer capas raster de índices (NDVI como pseudocolor) y mostrar popups con estadísticas por zona. Es liviano y no requiere API key externa a diferencia de Google Maps o Mapbox.

**Vite** es el bundler y servidor de desarrollo del frontend. Ofrece recarga instantánea (HMR) durante el desarrollo y builds optimizados para producción. Fue elegido sobre Create React App (descontinuado) y Webpack por su velocidad y configuración mínima.

Los estilos se manejan actualmente con **CSS plano** organizado por componentes. Se prevé la incorporación de **Tailwind CSS** a medida que el frontend crezca en cantidad de vistas, para mantener consistencia visual y agilizar el desarrollo sin escribir CSS custom.

El Frontend se comunica con el Backend exclusivamente mediante **REST API + GeoJSON**. El GeoJSON es el formato estándar para intercambiar geometrías georreferenciadas entre backend y mapa, lo que elimina conversiones innecesarias.

---

### Capa de Aplicación — Backend

| Tecnología | Rol |
|---|---|
| **FastAPI** | Framework web y API REST |
| **Pydantic** | Validación de datos y configuración |
| **SQLAlchemy + GeoAlchemy2** | ORM y soporte de geometrías PostGIS |
| **python-jose + bcrypt** | Autenticación JWT y hashing de contraseñas |
| **WeasyPrint** | Generación de reportes PDF |
| **Redis** | Broker de mensajes y caché |
| **Celery** | Cola de tareas asíncronas |

**FastAPI** fue elegido sobre Django REST Framework o Flask por tres razones concretas: generación automática de documentación OpenAPI/Swagger, validación de datos con Pydantic sin configuración extra, y rendimiento asíncrono nativo con async/await. Para un sistema que maneja uploads de archivos grandes y polling frecuente de estado, esto es relevante.

FastAPI concentra: autenticación (JWT), gestión de lotes y vuelos, coordinación de análisis, generación de reportes y el motor de diagnóstico (lógica de reglas agronómicas + integración futura con LLM).

**Pydantic** se usa en dos roles: como motor de validación de datos en los endpoints (schemas de request/response) y como gestor de configuración del sistema (variables de entorno con `pydantic-settings`). Garantiza que los datos que entran a la API cumplan el formato esperado antes de llegar a la lógica de negocio.

**SQLAlchemy** es el ORM (Object-Relational Mapper) que permite interactuar con PostgreSQL usando clases Python en vez de SQL directo. **GeoAlchemy2** extiende SQLAlchemy con soporte para columnas de tipo geometría (polígonos, puntos) y funciones espaciales de PostGIS, permitiendo almacenar y consultar los límites de lotes y las zonas clasificadas como tipos nativos de la base de datos.

**python-jose** genera y verifica los tokens JWT que autentican cada request del frontend. **bcrypt** hashea las contraseñas de los usuarios antes de almacenarlas, garantizando que nunca se guarden en texto plano. Ambas son librerías estándar de la industria para autenticación segura.

**WeasyPrint** convierte HTML/CSS a PDF para la generación de reportes ejecutivos. Funciona como un motor de renderizado que toma templates HTML con los datos del análisis (mapas, estadísticas, diagnóstico) y los exporta como documentos PDF descargables. Se eligió por su capacidad de generar PDFs con diseño profesional a partir de HTML estándar, sin depender de herramientas externas.

**Redis** cumple un doble rol en el sistema: actúa como broker de mensajes para Celery (comunica el backend con los workers) y como caché de estado temporal (permite que el frontend haga polling del progreso de un análisis sin consultar la base de datos en cada request). Ambos roles conviven en la misma instancia usando bases de datos internas separadas.

**Celery** es el orquestador de tareas asíncronas. Cuando un usuario sube un GeoTIFF y solicita un análisis, FastAPI no lo procesa directamente: encola la tarea en Redis y Celery la distribuye a los workers disponibles. Esto permite paralelizar múltiples análisis, reintentar tareas fallidas automáticamente y no bloquear la API principal durante el procesamiento.

---

### Capa de Procesamiento — Worker GIS

| Tecnología | Rol |
|---|---|
| **GDAL** | Abstracción de datos geoespaciales |
| **Rasterio** | Lectura y escritura de archivos raster |
| **NumPy** | Operaciones matemáticas pixel a pixel |
| **scikit-image** | Algoritmos de procesamiento de imágenes (umbralización Otsu) |
| **GeoPandas** | Manipulación y exportación de datos vectoriales |
| **Shapely** | Operaciones geométricas sobre polígonos |

Este bloque se ejecuta dentro de los **workers Celery**, completamente separado del proceso de FastAPI. Es el núcleo técnico del sistema.

**GDAL** es la librería base de todo el ecosistema geoespacial open source. Rasterio la usa internamente para leer GeoTIFF, reproyectar coordenadas y vectorizar rasters. No se usa directamente en el código de la aplicación, pero es una dependencia fundamental.

**Rasterio** es la interfaz Python estándar para trabajar con archivos raster georreferenciados. Permite leer bandas espectrales individualmente, acceder a metadatos (CRS, resolución, extensión), aplicar enmascaramiento de zonas sin datos y vectorizar el raster clasificado mediante `rasterio.features.shapes()`. Se usa para GeoTIFF de hasta 1 GB mediante windowed reading (lectura por tiles) para no cargar el archivo completo en memoria.

**NumPy** realiza los cálculos de índices de vegetación como operaciones matriciales sobre arrays de píxeles. El cálculo de NDVI, por ejemplo, opera sobre dos matrices (banda NIR y banda RED) simultáneamente, lo que es órdenes de magnitud más rápido que un bucle pixel a pixel. También maneja el enmascaramiento de valores nodata y la división por cero.

**scikit-image** provee algoritmos de procesamiento de imágenes científicas. En el sistema se utiliza principalmente para el **método de Otsu** (`skimage.filters.threshold_otsu`), que calcula automáticamente el umbral óptimo para separar píxeles en categorías a partir del histograma del índice de vegetación (RFMA-03). Es la implementación de referencia de este algoritmo en el ecosistema Python científico.

**GeoPandas** trabaja con los polígonos resultantes de la vectorización: calcula áreas en hectáreas, aplica filtros por área mínima para eliminar ruido, exporta en GeoJSON (para la API) y en Shapefile comprimido en `.zip` (para uso en maquinaria agrícola). Extiende Pandas con soporte geoespacial nativo.

**Shapely** realiza las operaciones geométricas sobre los polígonos: simplificación con el algoritmo Douglas-Peucker (para reducir vértices sin perder la forma de la zona), validación de geometrías y análisis espacial (cálculo de compacidad, circularidad y detección de clusters de zonas afectadas).

---

### Capa de Datos

| Tecnología | Rol |
|---|---|
| **PostgreSQL + PostGIS** | Base de datos relacional con extensión espacial |
| **MinIO** | Almacenamiento de archivos (S3-compatible) |

**PostgreSQL** es la base de datos relacional principal. Almacena usuarios, permisos, lotes, vuelos, índices calculados, metadatos e historial de análisis. Se eligió sobre MySQL por su mejor soporte de tipos de datos complejos y por la disponibilidad de PostGIS.

**PostGIS** es la extensión espacial de PostgreSQL. Permite almacenar geometrías (polígonos de zonas clasificadas) como tipos de datos nativos, realizar consultas espaciales eficientes (intersección, contención, distancia) y mantener índices GiST que aceleran las búsquedas geoespaciales. Es el estándar de la industria para bases de datos espaciales open source.

La separación de responsabilidades es clara: PostGIS guarda los **metadatos y vectores** (quién, qué lote, qué fecha, qué polígonos, qué estadísticas), mientras que MinIO guarda los **archivos binarios** (ortomosaicos originales, mapas generados, reportes PDF, Shapefiles exportados).

**MinIO** es un servidor de almacenamiento de objetos compatible con la API de Amazon S3, desplegable en infraestructura propia. Se eligió porque los GeoTIFF pueden pesar varios cientos de megabytes y los reportes generados (PDFs, Shapefiles, mapas de prescripción) no deben ocupar espacio en la base de datos relacional. Organiza los archivos en la estructura `usuario/lote/vuelo/` y genera URLs firmadas de acceso temporario para que el frontend pueda descargar archivos directamente sin pasar por el backend.

---

### Infraestructura

| Tecnología | Rol |
|---|---|
| **Docker / Docker Compose** | Contenedores y orquestación local |

**Docker** empaqueta cada componente del sistema (FastAPI, Worker GIS, Redis, PostgreSQL+PostGIS, MinIO) en contenedores independientes con sus dependencias. Esto garantiza que el entorno de desarrollo sea idéntico al de producción, elimina los problemas de "funciona en mi máquina" y simplifica el despliegue.

**Docker Compose** orquesta todos los contenedores localmente, define la red interna entre servicios, gestiona variables de entorno y volúmenes persistentes para la base de datos y el almacenamiento de archivos.

En la etapa de producción (R7) se añadirá **Nginx** como reverse proxy y gateway de entrada, encargándose de SSL/TLS, compresión y ruteo de tráfico hacia los distintos servicios.

---

## Resumen de decisiones de diseño

| Decisión | Alternativa descartada | Razón |
|---|---|---|
| FastAPI sobre Django REST | Django REST Framework | Validación automática con Pydantic, async nativo, documentación OpenAPI sin configuración |
| Celery + Redis para procesamiento | Procesamiento sincrónico en FastAPI | Los GeoTIFF grandes bloquearían la API; necesidad de reintentos y paralelismo |
| PostGIS para vectores | Archivos GeoJSON en disco | Consultas espaciales, índices GiST, historial y trazabilidad de análisis |
| MinIO para archivos | Sistema de archivos local | Escalabilidad, URLs firmadas, separación de responsabilidades con la BD |
| Rasterio sobre GDAL directo | GDAL Python bindings | API más pythónica, mejor manejo de contextos y memoria |
| React sobre Vue/Angular | Vue.js | Ecosistema más amplio, librerías GIS más maduras (React-Leaflet) |
| Vite sobre Webpack/CRA | Create React App, Webpack | CRA descontinuado; Vite ofrece recarga instantánea y configuración mínima |
| CSS plano en el MVP, Tailwind previsto | Tailwind CSS | Suficiente para las pantallas iniciales; Tailwind se incorporará cuando el frontend crezca en vistas |
| WeasyPrint sobre wkhtmltopdf | wkhtmltopdf, Puppeteer | Librería Python nativa, genera PDFs desde HTML/CSS sin depender de un navegador headless |
| SQLAlchemy sobre SQL directo | Queries SQL manuales | ORM tipado, migraciones con Alembic, integración natural con PostGIS vía GeoAlchemy2 |
