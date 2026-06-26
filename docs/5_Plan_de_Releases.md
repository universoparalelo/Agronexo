# Plan de Trabajo — Releases de AgroNexo

> Plan de entregas incrementales del sistema **AgroNexo**. Metodología Scrum, sprints
> de **1 semana**. **7 releases**, cada una con varios sprints y una entrega funcional,
> demostrable y desplegada. Equipo de 5 integrantes.

---

## Estructura temporal

- **Release 1:** del **1 de junio** al **7 de julio** → contiene **5 sprints** de 1 semana.
  Se presenta el 7/jul.
- **Releases 2 a 7:** sin fecha ni cantidad de sprints definidas todavía. Único hito firme:
  la **Release 7 (producto terminado) se presenta en diciembre**. Abajo se propone una
  distribución **tentativa** julio→diciembre, ajustable por el equipo.

| Release | Tema | Entrega central |
|:---:|:---|:---|
| R1 | Clasificación visual del lote | Ver el lote clasificado en zonas de vigor sobre un mapa |
| R2 | Diagnóstico interpretativo y ahorro | Explicar qué le pasa a cada zona y cuánto se ahorra |
| R3 | Salidas y prescripción | PDF, exportación estándar y orden de trabajo |
| R4 | Gestión, historial y comparación | Seguimiento del lote en el tiempo |
| R5 | Explicabilidad enriquecida con IA | Capa generativa sobre el diagnóstico |
| R6 | Detección de árboles de copa alta | Caso 2 del Escenario |
| R7 | Cierre, escalabilidad y hardening | Producto final desplegado (diciembre) |

**El proyecto se planifica desde cero.** Todo lo construido hasta ahora (repositorio,
estructura de carpetas, Docker Compose, backend, worker, frontend, pipeline de índices) **es el
resultado esperado de los sprints de las primeras releases**, no un punto de partida previo. La
Release 1 arranca con **dos sprints de investigación y arquitectura** (sin código): se investiga
el dominio técnico (GeoTIFF, índices) y agronómico (criterios, entrevistas), y se define la
arquitectura y la especificación de la API. Recién en el **Sprint 3** se crea el repositorio y
comienza la construcción, que suma una capa funcional por sprint hasta el MVP del 7/jul.

Al construir sobre una arquitectura ya investigada y definida, las buenas prácticas se
incorporan **en el momento de escribir cada parte**, no como correcciones posteriores:
migraciones con Alembic desde el primer sprint de código, mapeo de bandas configurable desde
que se lee el GeoTIFF, zonificación por contigüidad desde que se vectoriza, y tests en paralelo
a cada funcionalidad.

**Definition of Done (DoD).**
Para sprints **de investigación/arquitectura** (1–2): artefacto **documentado** (informe,
diagrama, spec) y **revisado por al menos 2 integrantes**.
Para sprints **de construcción** (3 en adelante), TODA funcionalidad debe estar:
1. **Implementada** según el RF/RNF asociado y mergeada a `main`.
2. **Verificada por al menos 2 integrantes** (revisión de código + prueba funcional), según el DoD de la ERS.
3. **Con tests automatizados** que cubran la lógica nueva (mínimo: funciones puras y caminos críticos).
4. **Desplegada/ejecutable** en el entorno de demo. En R1 el despliegue es **local con Docker
   Compose** (`docker compose up` levanta todo el stack reproducible); el despliegue en
   servidor con HTTPS (Nginx + SSL/TLS) se incorpora en R7.
5. **Documentada** y **demostrable** en la review de fin de sprint.

**Criterios transversales (aplican a toda funcionalidad, en todo sprint de construcción):**
- **Seguridad (RNF-08):** todo dato de entrada se valida y sanitiza (prevención de inyección y XSS).
- **Accesibilidad (RNF-13):** las pantallas son navegables por teclado y cumplen contraste/legibilidad mínimos.
- **Responsivo (RNF-21):** la interfaz se adapta a escritorio y tablet.
Estos no son tareas de una release puntual: son condición de "done" de cada feature de UI/entrada.

**Roles sugeridos (5 integrantes):** Backend/API · Worker GIS · Frontend ·
QA/Testing+DevOps · Product Owner/Documentación. Rotables por sprint.

---

# RELEASE 1 — "Clasificación visual del lote" (1 jun → 7 jul, 5 sprints)

**Objetivo de la release:** investigar el dominio, definir la arquitectura y construir desde
cero un MVP **completo, testeado y ejecutable** que llegue hasta el nivel **descriptivo**:
*subir una imagen de drone y ver el lote clasificado en zonas de vigor sobre un mapa, con
estadísticas básicas por zona.* La **interpretación** de qué le pasa a cada zona (diagnóstico,
acción, ahorro) es el incremento de R2 — no entra acá a propósito, para no comprometer en las
primeras semanas la parte que más criterio agronómico requiere.

**Qué se presenta el 7/jul (incremento demostrable):** un usuario se registra, inicia sesión,
crea un lote con sus límites, sube un GeoTIFF, elige un índice (NDVI/NDRE/SAVI/ExG), y el
sistema le devuelve un **mapa con las zonas del lote clasificadas** (ej. vigor bajo / normal /
alto), cada zona con su **área (ha) e índice promedio**. Todo corriendo en un **entorno local
con Docker Compose**.

**Lo que NO entra en R1 (queda para releases posteriores):** el **diagnóstico interpretativo**
(qué causa probable, qué acción) y el **% de ahorro** (R2); descargas formales —PDF, exportación,
orden de trabajo— (R3); historial y comparación (R4); capa de IA (R5); detección de árboles (R6);
hardening de escalabilidad y HTTPS (R7).

### Sprint 1 — Investigación técnica y de índices *(sin código)*
- **Tareas:** **Investigación GeoTIFF multiespectral** (revisar estructura de bandas,
  analizar metadatos CRS y resolución, testear lectura con GDAL); **Investigación Rasterio y
  GDAL** (instalar/configurar, leer ortomosaico multiespectral, validar reproyección CRS);
  **Cálculo y validación NDVI/GNDVI/SAVI** (implementar fórmulas, verificar umbrales
  agronómicos NEA, comparar resultados con bibliografía); **Interpretación agronómica de
  índices** (bibliografía INTA/AAPRESID, rangos por estadio fenológico, criterios por cultivo).
- **Entregable demostrable:** informe técnico con fórmulas validadas, umbrales por cultivo/estadio
  y prueba de lectura de un GeoTIFF real.

### Sprint 2 — Investigación de dominio y arquitectura *(sin código)*
- **Tareas:** **Patrones espaciales y causas probables** (correlacionar zonas con estrés
  hídrico, indicadores de plagas, deficiencias nutricionales); **Investigación fumigación
  localizada** (técnicas de prescripción diferenciada, normativa vigente, integración GIS);
  **Validación bibliográfica INTA** (publicaciones, umbrales por índice, criterios de
  clasificación); **Entrevistas con productores/prestadores** (guía de entrevista, entrevistas
  en NEA, síntesis de hallazgos); **Arquitectura monolítica modular** (definir módulos y capas,
  asignar responsabilidades, diagramas de arquitectura y componentes); **Especificación APIs
  REST/OpenAPI** (rutas y métodos HTTP, request/response y parámetros, códigos de estado).
- **Entregable demostrable:** documento de arquitectura con diagramas, especificación OpenAPI
  de la API y síntesis de entrevistas/criterios agronómicos.

### Sprint 3 — Setup, infraestructura, autenticación y lotes *(inicio de la construcción)*
- **Tareas:** crear el **repositorio** y la estructura de carpetas (`backend/`, `worker/`,
  `frontend/`, `docs/`); **Docker Compose** con todos los servicios (PostgreSQL+PostGIS,
  Redis, MinIO); variables de entorno (`.env.example`); backend **FastAPI** base + DB con
  **Alembic** (migraciones desde el inicio); **auth JWT** (registro/login) con multi-tenencia;
  modelos de **lote/vuelo** en PostGIS y **CRUD de lotes**; frontend base (Vite + React) con
  **Login** y dashboard inicial; **CI** que corra los tests; **entorno local reproducible**
  (`docker compose up` levanta todo el stack).
- **Incremento demostrable:** un usuario se registra, inicia sesión y crea un lote en el
  sistema corriendo localmente.
- **RF/RNF:** RFGL-01, RNF-05, RNF-06, RNF-23.

### Sprint 4 — Ingesta, pipeline GIS y visualización del índice
- **Tareas:** **upload de GeoTIFF** a MinIO con **validación de bandas (RGB/NIR) y CRS**;
  andamiaje del **worker Celery** + cola Redis; pipeline del worker: **lectura de bandas con
  mapeo configurable por vuelo/sensor** (no hardcodeado) y cálculo de **NDVI/NDRE/SAVI/ExG**;
  **progreso a Redis** y **polling** en el frontend; mapa **Leaflet** con el resultado del índice.
- **Incremento demostrable:** crear lote → subir GeoTIFF → elegir índice → ver el lote
  procesado en el mapa con barra de progreso en tiempo real.
- **RF/RNF:** RFME-01, RFME-02, RFME-03, RFME-05, RFMA-01, RFMP-01 (reproyección), RNF-04, RNF-28 (multisensor).

### Sprint 5 — Clasificación en zonas, límites del lote, testing y estabilización
- **Tareas:** **clasificación** por umbrales (umbralización dinámica); **vectorización** por
  **contigüidad real** (focos separados, no un bloque por color); **simplificación** de
  geometrías y **filtrado por área mínima**; **estadísticas descriptivas por zona** (área en
  ha e índice promedio); identificación de **zonas atípicas**; **carga de límites del lote** y
  **vista previa** desde la UI; cada análisis queda **vinculado a su vuelo y lote**; pulido de
  UX y mensajes de error; **suite de tests integral** (consolidación + e2e) y **preparación de
  la demo** del 7/jul.
- **Incremento demostrable:** MVP completo — mapa del lote clasificado en zonas, cada una con
  su área e índice promedio; recorrido de punta a punta, testeado y ejecutable en local.
- **RF/RNF:** RFMA-02, RFMA-04, RFMP-02/03/04/05, RFDR-05 (trazabilidad vuelo↔lote), RFGL-02,
  RFME-04, RFSA-01 (dashboard de visualización), RNF-10/11/12.

**DoD de la Release 1:** todos los sprints cumplidos, suite de tests verde en CI, sistema
**corriendo localmente con Docker Compose**, recorrido completo demostrable y documentación
(README + docs) actualizada.

---

# RELEASES 2–7 (jul → dic) — distribución tentativa

> Sin fechas ni cantidad de sprints definidas. Cada release se compone de varios sprints
> semanales y entrega algo funcional, testeado y desplegado (mismo DoD). Reordenar según
> prioridad y feedback.

## R2 — Diagnóstico interpretativo y ahorro
**Valor:** acá **nace el diferenciador**: pasar de "ver zonas" a **explicar qué le pasa a cada
zona en lenguaje accesible** y cuánto se ahorra. Es lo más dependiente del criterio agronómico,
por eso va después de tener las zonas y los umbrales validados.
- **Incremento:** **motor de reglas contextual** (índice + cultivo + estadio + severidad) que
  produce **diagnóstico explicado y acción recomendada** por zona; **estimación de severidad**
  respecto del promedio del lote; **% de ahorro** vs. aplicación general; **validación en campo**
  (el usuario confirma la causa antes de avanzar a prescripción).
- **RF/RNF:** RFDR-01 (motor de reglas), RFDR-02 (zonificación de manejo), RFDR-03 (severidad),
  RFGL-05 (ahorro/eficiencia).

## R3 — Salidas y prescripción
**Valor:** que el resultado **salga del sistema** en documentos que el productor usa.
- **Incremento:** **reporte ejecutivo PDF** (mapa + estadísticas + diagnóstico); **exportación
  en formatos estándar abiertos** (GeoJSON, Shapefile genérico de las zonas); **orden de trabajo**
  con dosis por zona, volumen total y restricciones de seguridad.
- **RF/RNF:** RFSA-03 (PDF), RFSA-02 (exportación estándar), RFSA-04 (orden de trabajo), RFDR-01 (dosis).
- **Nota de alcance:** la exportación es en **formatos estándar abiertos**, sin comprometer
  compatibilidad con una máquina/dron específico. La **integración directa con maquinaria** es
  evolución futura e incierta (ERS 2.6) y requiere investigar primero el equipamiento objetivo.

## R4 — Gestión, historial y comparación de campañas
**Valor:** de "un análisis suelto" a **gestión del lote en el tiempo**.
- **Incremento:** línea de tiempo por lote; **superposición/comparación de dos vuelos** en
  distintas fechas; gestión multi-lote y eliminación de datos propios.
- **RF/RNF:** RFGL-03, RFGL-04, RFGL-06 (consolida la trazabilidad RFDR-05 en la línea de tiempo), RNF-19.

## R5 — Explicabilidad enriquecida con IA (capa generativa)
**Valor:** potenciar el diferenciador **que ya nació en R2** (diagnóstico explicado por reglas):
la IA enriquece la redacción y el ordenamiento de causas, no estrena la explicabilidad.
- **Incremento:** **capa generativa (LLM)** que reescribe el diagnóstico en lenguaje natural
  más rico, con causas probables ordenadas; calibración manual de umbrales; registro de criterio técnico.
- **RF/RNF:** RFMA-03 (calibración umbrales), RFDR-04 (criterio técnico), evolución previsible (ERS 2.6).
- **Mitigación:** el motor de reglas de R2 es el *fallback* y la versión base; la IA es la capa premium opcional.

## R6 — Detección de árboles de copa alta + robustez agronómica
**Valor:** el **Caso 2** del Escenario (segundo diferenciador) y precisión del producto.
- **Incremento:** detección de árboles dispersos por patrón circular + NDVI elevado y
  prescripción de defoliante solo sobre copas; calibración de umbrales por cultivo/región.
- **RF/RNF:** alcance del Escenario (Caso 2), RFMA-02/03.

## R7 — Cierre, escalabilidad y hardening (producto final, diciembre)
**Valor:** dejar el sistema listo para presentar como producto terminado.
- **Incremento:** **despliegue en servidor con HTTPS** (Nginx + SSL/TLS); **upload directo a
  MinIO con presigned URLs**; **tiled/windowed processing** para no sacrificar precisión en
  archivos grandes; refresh token; limpieza de temporales; pasada final de tests, performance y documentación.
- **RF/RNF:** RNF-07 (HTTPS), RNF-17/18 (escalabilidad), RNF-01/02/03 (tiempos de respuesta:
  interfaz <3s, procesamiento <5min, resultados <2min — se miden y validan acá), RNF-14
  (disponibilidad 95%), cierre de RNF pendientes.

---

## Mapa RF → Release (resumen)

| Release | RF/RNF principales |
|:---:|:---|
| **R1** (5 sprints) | RFME-01/02/03/04/05, RFMA-01/02/04, RFMP-01/02/03/04/05, RFDR-05, RFGL-01/02, RFSA-01, RNF-04/05/06/10-12/23/28 |
| R2 | RFDR-01/02/03, RFGL-05 |
| R3 | RFSA-02/03/04, RFDR-01 (dosis) |
| R4 | RFGL-03/04/06, RNF-19 |
| R5 | RFMA-03, RFDR-04, capa generativa (IA) — ERS 2.6 |
| R6 | Escenario Caso 2, RFMA-02/03 |
| R7 | RNF-01/02/03/07/14/17/18 |

---

## Riesgos y mitigaciones

- **Construcción de R1 comprimida en 3 sprints (3–5):** al dedicar los Sprints 1–2 a
  investigación, la implementación queda en 3 semanas. Se mitiga porque las fórmulas, umbrales,
  arquitectura y la spec OpenAPI ya están resueltos antes de escribir código; y porque R1 llega
  solo al nivel descriptivo (sin el diagnóstico interpretativo, que es lo más pesado).
- **El diferenciador nace en R2, no en R1:** asegurar que R2 llegue temprano en la secuencia
  julio→diciembre para no quedar mucho tiempo mostrando "solo zonas" sin la explicación que
  diferencia al producto.
- **R2–R7 sin fechas:** fijar al menos hitos mensuales hacia diciembre para no acumular todo al final.
- **R5 depende de un servicio externo (LLM):** *fallback* al motor de reglas de R2.
- **Exportación a maquinaria (R3):** incierta y dependiente del equipo objetivo; se entrega solo
  en formatos estándar abiertos y la integración directa se trata como evolución futura (ERS 2.6).
- **Precisión vs. memoria en archivos grandes:** abordar con tiled/windowed processing en R7
  (alto esfuerzo) — priorizar según tiempo disponible.
