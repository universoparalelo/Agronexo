# AgroNexo — Release 2 (v2.0.0)

**Diagnóstico interpretativo por zona**

Proyecto Final de Ingeniería en Sistemas · UTN FRRe · Equipo 6
Profesores: Acuña, César J · Mendez, Graciela L

---

## Ficha de release

| Campo | Valor |
|---|---|
| Versión | v2.0.0 (sin tag; propuesto `v2.0.0` sobre [`47994a4`][47994a4], merge del PR #6, fechado en git el 7 de septiembre de 2026) |
| Estado | Completa — Demo: 22 de septiembre de 2026, presentada junto con la Release 3 |
| Período | 7 de julio — 7 de septiembre de 2026 (9 semanas). Inicio: fin de la Release 1 (demo del 7 de julio, dato del equipo); la presentación ubica el inicio del Sprint 6 el 15 de julio. Cierre: fecha del último commit de R2 en git ([`47994a4`][47994a4]); la presentación planificaba el cierre para el 25 de agosto |
| Equipo | Amilcar Aguirre, Matías Machado, Celeste Martín Rodich, Denise Pujalte, Zaira Rosin |
| Metodología | Scrum — sprints de 1 semana planificados (el Sprint 7 duró 2 semanas) |
| Entorno | Local con Docker Compose. Sin staging ni producción |
| Repositorio | universoparalelo/Agronexo (privado) |
| Hito de entrega | Cada zona del lote muestra su causa probable, la confianza, la severidad y el producto fitosanitario sugerido, con un texto explicativo y unidades de manejo sobre el mapa |

**Commit de corte.** El corte de la Release 2 se definió por contenido y por orden de los commits, no por fecha: [`47994a4`][47994a4] es el último commit antes de [`36dc4b9`][36dc4b9] (reporte PDF, PR #7), primer commit con alcance de la Release 3. La fecha de `47994a4` en git (2026-09-07) es posterior al cierre que declara la presentación (25-08): parte del trabajo de R2 se commiteó después del cierre planificado. Todo el estado técnico de este documento es el de `47994a4`, leído con `git show 47994a4:<ruta>`.

**Rango.** De [`f35e422`][f35e422] (tag `v1.0.0`) a [`47994a4`][47994a4]: 23 commits de trabajo y 6 merges (PRs #1 a #6). R2 es la primera release que usa Pull Requests; los cinco primeros commits del rango ([`2b0566e`][2b0566e], [`8644be4`][8644be4], [`c5e41ae`][c5e41ae], [`ecc6fa3`][ecc6fa3] y [`fc9ebb2`][fc9ebb2]) entraron directo a `main`, sin PR.

## Equipo y roles

| Integrante | Rol en la release | Área |
|---|---|---|
| Matías Machado | Scrum Master / Release Manager | Frontend · API |
| Celeste Martín Rodich | Desarrollo | Backend · GIS · DevOps |
| Denise Pujalte | QA | Testing · Documentación |
| Zaira Rosin | Investigación | GIS · Análisis espacial |
| Amilcar Aguirre | Desarrollo | Frontend · UI |

Los roles son los mismos que en la Release 1, según confirmó el equipo.

---

## 1. Planificación de la Release

### 1.1 Objetivo y alcance

El objetivo fue pasar de "ver zonas" a explicar qué le pasa a cada zona: un motor de reglas agronómicas que, a partir de los índices calculados, el cultivo, el estadio fenológico y el patrón espacial de cada zona, infiere la causa probable, estima la severidad respecto del promedio del lote y sugiere el producto fitosanitario correspondiente. Al cierre, el usuario abre un vuelo procesado y ve, en una pestaña "Diagnóstico", una fila por zona con causa, confianza, severidad y producto, un texto en lenguaje simple y las unidades de manejo dibujadas sobre el mapa coloreado por severidad.

**Incluido en el alcance:**

- **Base de conocimiento (S6):** catálogo de 21 productos fitosanitarios sobre 10 causas, esquema de la tabla de productos y mapeo de reglas por cultivo y estadio, llevados a código en `app/diagnostico/productos.py`, `app/diagnostico/reglas.py` y `app/diagnostico/estadios.py`. Los documentos de investigación no están versionados en el repositorio al corte.
- **Datos:** migraciones Alembic 0012 → 0017 (GNDVI en `indiceenum`, `estadio_fenologico` a 30 caracteres, `variedad` / `tipo_suelo` / `fecha_siembra` en `lotes`, tabla `productos_fitosanitarios` con seed de 21 productos, tabla `diagnosticos` y `estadio_fenologico` en `vuelos`). Cadena lineal con único head `0017`.
- **API:** 4 endpoints nuevos con JWT — `GET /api/v1/lotes/{lote_id}/vuelos/{vuelo_id}/diagnostico`, `POST .../diagnostico/recalcular`, `POST .../indices/batch` y `GET /api/v1/productos-fitosanitarios?causa=&tipo=`. Total de endpoints: 25 → 29.
- **Motor de diagnóstico (`app/diagnostico/`):** 20 reglas en cascada (R00 a R99), clasificación de 7 patrones espaciales por métricas de forma, resolución multi-índice por intersección geométrica, severidad en 5 niveles, texto explicativo por zona, resumen general y unidades de manejo por contigüidad. Resultado persistido por vuelo en la tabla `diagnosticos`.
- **Worker GIS:** quinto índice (GNDVI), cálculo de NDVI, NDRE, SAVI y GNDVI en una sola subida, tarea Celery `analizar_indices_batch`, umbrales fijos propios por índice, y optimización para archivos grandes (streaming a MinIO, pre-compresión, lectura decimada por GDAL, caché del GeoTIFF preparado, lock en Redis, reproyección multihilo, BigTIFF).
- **Frontend:** `TablaDiagnostico.jsx` (vista tabla y vista tarjetas, recalcular, unidades de manejo), mapa por severidad en `MapaZonas.jsx`, estadio fenológico y fecha por vuelo en `ModalCargaGeoTIFF.jsx`, atributos del lote en `ModalNuevoLote.jsx`, KPIs con datos reales y acceso a "Diagnósticos" desde el sidebar (`ModalElegirLote.jsx`).
- **Infraestructura:** `uvicorn --http h11` en el servicio `api` y certificado raíz de Avast en las tres imágenes. Sin variables de entorno nuevas ni cambios de dependencias.

**Queda fuera del alcance de esta release:** el cálculo de ahorro de insumos (RFGL-05, asignado a R2 en `docs/5_Plan_de_Releases.md` y no implementado), la validación en campo del diagnóstico por el usuario y el criterio técnico del agrónomo (RFDR-04), el historial multi-vuelo de diagnósticos (RFGL-03, R4), las salidas formales (PDF, Shapefile, orden de trabajo: R3) y el dibujo del lote sobre mapa satelital (R3).

### 1.2 Sprints que la componen

| S | Título | Entregable demostrable | Fecha | Historias | RF/RNF |
|---|---|---|---|---|---|
| S6 | Investigación y base de conocimiento | Catálogo de productos, esquema de la tabla y reglas por cultivo y estadio | 15–22 jul | H6.1–H6.3 | RFDR-01 |
| S7 | Datos maestros e infraestructura | Lote con atributos agronómicos, tabla de productos consultable, 5 índices y archivos de varios GB procesados | 22 jul–5 ago | H7.1–H7.4 | RFME-03, RFMA-01, RFDR-01, RNF-02, RNF-17 |
| S8 | Motor de reglas | `GET .../diagnostico` devuelve causa, confianza, producto y texto por zona | 5–11 ago | H8.1–H8.3 | RFDR-01, RFDR-05 |
| S9 | Severidad y zonificación | Zonas con severidad y unidades de manejo sobre el mapa | 11–13 ago | H9.1 | RFDR-02, RFDR-03 |
| S10 | Integración, QA y cierre | Dashboard con el diagnóstico completo | 13–25 ago | H10.1–H10.3 | RFSA-01, RFGL-05 |

Las fechas y los títulos son los de la presentación. `docs/5_Plan_de_Releases.md` asigna a R2 solo a nivel de release los requisitos RFDR-01, RFDR-02, RFDR-03 y RFGL-05; la columna RF/RNF por sprint es una derivación por contenido, con los textos de `docs/2_ERS.md`.

### 1.3 Duración y fechas clave

| Evento | Fecha |
|---|---|
| Inicio de la release 2 | 7 de julio de 2026 (fin de la Release 1, dato del equipo; la presentación ubica el inicio del Sprint 6 el 15 de julio) |
| Receso invernal (definido en R1) | 20 de julio — 2 de agosto de 2026 |
| Fin Sprint 6 — Investigación | 22 de julio de 2026 |
| Fin Sprint 7 — Datos maestros e infraestructura | 5 de agosto de 2026 |
| Fin Sprint 8 — Motor de reglas | 11 de agosto de 2026 |
| Fin Sprint 9 — Severidad y zonificación | 13 de agosto de 2026 |
| Fin Sprint 10 — Integración, QA y cierre | 25 de agosto de 2026 (planificado, según la presentación) |
| Cierre de la Release 2 según git (último commit de R2, [`47994a4`][47994a4]) | 7 de septiembre de 2026 |
| Demo de la Release 2, junto con la R3 | 22 de septiembre de 2026 |

Criterio de cierre: se toma la fecha del último commit de R2, [`47994a4`][47994a4] (autor y commit: 2026-09-07 09:49), porque el siguiente commit de `main`, [`36dc4b9`][36dc4b9] (2026-09-10), ya es trabajo de la Release 3. Las fechas de los sprints son las de la presentación.

El receso invernal se superpone con el final del S6 y con casi todo el S7, que además duró dos semanas (22-07 a 05-08) en lugar de una.

**Fechas según la bitácora `docs/release-v2.0.0.md` (a confirmar).** La bitácora registra otros períodos, que no coinciden con los de la presentación: S6 del 2026-06-23 al 2026-07-09, S7 del 2026-08-04 al 2026-08-30, S8 del 2026-08-28 al 2026-08-30, S9 el 2026-09-02 y S10 el 2026-09-02 (con una tarea del 2026-09-07). Las fechas de los commits tampoco ubican los sprints: el motor de reglas, planificado para el S8 (5-11 ago), figura en git el 2026-08-28.

### 1.4 Definición de Terminado (DoD)

No se encontró en el repositorio una DoD específica de R2: `docs/5_Plan_de_Releases.md`, que define la DoD de los sprints de construcción, no tiene cambios entre `f35e422` y `47994a4`. Se mantiene la DoD de R1. Una tarea se considera terminada cuando cumple todos los criterios siguientes:

- La funcionalidad es demostrable de punta a punta en el entorno local con `docker compose up`.
- Los endpoints involucrados responden con los códigos HTTP esperados.
- Existe al menos un test automatizado que cubre el caso principal.
- Los tests existentes siguen pasando (sin regresiones en CI).
- Si se modificó la base de datos, existe la migración Alembic correspondiente.
- Si se agregó una tarea Celery nueva, el worker fue reiniciado y verificado.
- La tarea fue documentada en el archivo de seguimiento de la release.

`docs/5_Plan_de_Releases.md` agrega para los sprints de construcción que cada funcionalidad debe estar mergeada a `main` y **verificada por al menos 2 integrantes** (revisión de código y prueba funcional).

La presentación no define criterios de cierre de la release. Los siguientes **se derivaron** del objetivo de la release y de los artefactos declarados para el Sprint 10. Evaluados contra el commit de corte: 5 cumplen, 2 parciales, 1 no cumple y 1 a confirmar.

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| 1 | El pipeline GeoTIFF → índices → diagnóstico → intervención recomendada funciona de punta a punta | Cumple | Camino en el código: `procesar_vuelo` + `analizar_indices_batch` → `GET .../diagnostico` (`app/diagnostico/service.py::generar_diagnostico`). Verificación manual registrada en `docs/release-v1.0.0.md` (2026-08-27): lote de soja + zona circular de NDVI ≈ 0.30 → `R20` con confianza alta y los 5 fungicidas del catálogo. |
| 2 | Cada zona trae causa probable, confianza, severidad y producto sugerido | Cumple | Propiedades `regla_id`, `causa_indice`, `confianza`, `severidad`, `productos_sugeridos` y `texto_explicativo` por feature (`app/diagnostico/service.py::_calcular_diagnostico`). |
| 3 | Las zonas con el mismo problema se agrupan en unidades de manejo | Cumple | `app/diagnostico/zonificacion.py::generar_unidades_manejo` ([`90b4bcd`][90b4bcd]); campo `unidades_manejo` en la respuesta. |
| 4 | El dashboard muestra el diagnóstico completo: colores por severidad y popup con causa, confianza y producto | Parcial | Mapa por severidad y tabla con causa, confianza y producto ([`90b4bcd`][90b4bcd], [`1200a87`][1200a87]). El popup del mapa muestra causa (`regla_nombre`), severidad, NDVI y área, pero no confianza ni producto (`frontend/src/components/MapaZonas.jsx::onEachZonaSeveridad`). |
| 5 | El sistema se testeó de punta a punta sin bugs críticos (reporte de tests E2E) | A confirmar | No hay test E2E nuevo ni reporte en el repositorio. La bitácora v2 deja "Pruebas E2E del flujo completo" como "Manual (usuario)". |
| 6 | La lógica nueva tiene tests automatizados que corren en CI | Parcial | 88 tests nuevos (176 en total). El CI corre `test_forma.py`, `test_diagnostico_engine.py` y `test_diagnostico_api.py` (34 tests), pero no `test_texto.py`, `test_zonificacion.py` ni `test_diagnostico_service.py` (48 tests). Jobs en verde en `47994a4`; el verde no cubre esos 48 tests, que siguen fuera del CI. |
| 7 | Las migraciones aplican en una cadena única desde cero | Cumple | Verificación estática: 0001 → 0017 lineal por `down_revision`, único head `0017`. Verificación estática + job `test-api` en verde en `47994a4` (incluye `alembic upgrade head`). |
| 8 | README actualizado | Cumple | [`b7dae3a`][b7dae3a] y [`89682e1`][89682e1]: flujo de diagnóstico, endpoint de productos y comando de tests del motor. |
| 9 | Cálculo de ahorro de insumos (RFGL-05, asignado a R2 por el plan de releases) | No cumple | Sin implementación. La tarjeta "Ahorro estimado" del dashboard se reemplazó por "Área monitoreada" en [`1200a87`][1200a87]. |

---

## 2. Sprint 6 — Investigación y base de conocimiento

| Sprint | Título | Fechas | Historias | RF/RNF |
|---|---|---|---|---|
| S6 | Investigación y base de conocimiento | 15–22 jul 2026 | H6.1–H6.3 | RFDR-01 |

### Objetivo

Construir la base de conocimiento del motor antes de escribir código: qué productos puede sugerir, cómo se guardan y qué índice y patrón corresponden a cada cultivo y estadio. Es el insumo directo de las reglas del Sprint 8.

### Tareas realizadas

Los artefactos del S6 son documentos que no están versionados en el repositorio al corte. Su contenido se verificó a través de su traducción a código, que entró en [`fc9ebb2`][fc9ebb2] y [`faec54c`][faec54c]. Los docstrings de ese código citan un "documento de referencia" con secciones numeradas (sección 3: estadios; sección 5: reglas y cascada; sección 6: catálogo) que no está en el repositorio.

#### Catálogo de productos fitosanitarios (H6.1)

**Qué se implementó.** Un catálogo de 21 productos agrupados por las 10 causas que puede devolver el motor, primero como diccionario Python y después como seed de la tabla de productos (H7.2). Asignado a H6.1 porque es el catálogo en sí; su carga en base de datos es H7.2.

**Detalle técnico.**
- `app/diagnostico/productos.py` ([`fc9ebb2`][fc9ebb2]): `CATALOGO_PRODUCTOS: dict[str, list[dict]]` con `nombre` y `tipo` por `causa_indice`. El docstring afirma que el total (21 productos sobre 10 causas, 20 reglas, 4 cultivos) se verificó contra el documento de referencia.
- Al corte el diccionario ya no se importa en ningún módulo: el servicio carga el catálogo desde la base (`app/diagnostico/service.py::_cargar_catalogo_productos`). Es código muerto.

| Causa (`causa_indice`) | Tipo | Productos |
|---|---|---|
| `interferencia_vegetacion` | herbicida | Glifosato, 2,4-D, Atrazina, Cletodim, Imazetapir |
| `estres_biotico_fungico` | fungicida | Azoxistrobina, Trifloxistrobina, Mancozeb, Tebuconazol, Carbendazim |
| `estres_biotico_insecto` | insecticida | Clorpirifos, Lambda-cihalotrina, Imidacloprid, Spinosad, Thiamethoxam |
| `estres_nutricional_nitrogeno` | fertilizante | Urea 46% N |
| `estres_nutricional_micro` | fertilizante foliar | Sulfato de Magnesio, Boro foliar 17% |
| `estres_nutricional_fosforo` | fertilizante | Superfosfato Triple 46% |
| `madurez_temprana_diferencial` | acelerador de madurez / defoliante | Ethephon 48%, Tiidiazurón + Diurón |
| `sin_problema_detectado`, `estres_hidrico`, `vigor_excesivo` | — | Sin producto asociado |

**No encontrado en el repo.** La fuente SENASA/INTA de cada producto: no hay referencia a SENASA ni a INTA en `app/` ni en `migrations/` al corte. Tampoco las dosis: la tabla prevé `dosis_referencia` y `unidad`, pero el seed no las carga.

#### Esquema de datos y migración de productos (H6.2)

**Qué se implementó.** El esquema de la tabla de productos, su modelo ORM, los schemas Pydantic y la migración Alembic, en [`faec54c`][faec54c] (PR #1).

**Detalle técnico.**
- **Migración `0015_crear_tabla_productos_fitosanitarios.py`** (revision `0015`, down_revision `0014`): crea los enums `tipoproductoenum` (7 valores: herbicida, fungicida, insecticida, fertilizante, fertilizante_foliar, acelerador_madurez, defoliante) y `causaindiceenum` (10 valores), la tabla `productos_fitosanitarios` (`id UUID`, `nombre VARCHAR(200)`, `tipo`, `causa_indice`, `dosis_referencia FLOAT`, `unidad VARCHAR(50)`) y el índice `ix_productos_causa_indice`. El downgrade borra la tabla y los dos enums.
- **Modelo y schemas:** `app/diagnostico/models.py::ProductoFitosanitario`, enums `TipoProductoEnum` y `CausaIndiceEnum`; `app/diagnostico/schemas.py::ProductoFitosanitarioListResponse` (`total`, `items`).

**Decisiones de diseño** (bitácora `docs/release-v2.0.0.md`, S7): el catálogo pasó de diccionario a tabla para permitir extensión (agregar productos, dosis y filtros por causa y tipo desde la API).

**Errores corregidos.** Ambos en [`faec54c`][faec54c], según la bitácora v2:
- `sa.Enum.create(checkfirst=True)` fallaba con asyncpg porque `migrations/env.py` importa los modelos y registra los enums antes de migrar. Se resolvió creando los enums con SQL directo dentro de `DO $$ BEGIN ... EXCEPTION WHEN duplicate_object THEN NULL; END $$`.
- `op.bulk_insert()` enviaba los valores como `VARCHAR` y PostgreSQL esperaba el enum nativo. Se resolvió con `INSERT` SQL directo y cast explícito (`::tipoproductoenum`).

#### Mapeo de índice y patrón por cultivo y estadio (H6.3)

**Qué se implementó.** El mapeo quedó codificado en dos lugares: la normalización de estadios fenológicos y el filtro de cultivo, estadio e índices que lleva cada regla del motor ([`fc9ebb2`][fc9ebb2]).

**Detalle técnico.**
- `app/diagnostico/estadios.py`: `normalizar_estadio()` lleva el texto libre del usuario ("R3", "Botón floral") a minúsculas, sin acentos y con `_` en lugar de espacios; `estadio_coincide()` compara contra el conjunto de estadios de cada regla (una regla sin estadios aplica a todos; un estadio vacío no matchea reglas con estadio). El docstring indica que los tokens se tomaron de la sección 5 del documento de referencia.
- `app/diagnostico/reglas.py`: cada `Regla` declara `cultivos`, `estadios` y `requiere_indices`.

| Regla | Cultivo | Estadios | Índice requerido |
|---|---|---|---|
| R20 | Soja | R1–R5 | NDVI |
| R21 | Soja | R3–R5 | GNDVI |
| R22 | Maíz | V7–V12, VT | NDVI |
| R23 | Algodón | Botón floral, floración, R1, R2 | NDVI |
| R24 | Sorgo | V6–V9, espigado, floración | NDVI |
| R30 | Soja | V4–V6, R1–R4 | NDVI |
| R31 | Maíz, sorgo | V6–V12, VT | NDVI |
| R32 | Algodón | Botón floral, floración, R1–R3 | NDVI |
| R40 | Soja | V4–V6, R1, R2 | NDRE |
| R41 | Maíz, sorgo | V4–V8 | NDRE |
| R42 | Algodón | V4–V8 | NDRE |
| R44 | Soja, maíz | V1–V6 | NDVI + NDRE |
| R60 | Algodón | R4, R5, apertura de cápsulas | NDVI |
| R70 | Maíz | VT, R1 | NDVI |

Las reglas R00, R01, R10, R43, R50 y R99 aplican a todos los cultivos y estadios.

**No encontrado en el repo.** El documento de investigación con el mapeo: `docs/reglas_diagnostico.md` existe en el repositorio, pero se agregó en [`22d4ee9`][22d4ee9] (21 de septiembre de 2026, posterior al corte). Tampoco hay rastro de la "validación con ingeniero agrónomo", que la presentación deja pendiente, ni de las "4 inconsistencias heredadas de R1" que se dicen corregidas en este sprint (se buscó en mensajes de commit, `docs/`, `README.md`, `CLAUDE.md` y `app/`).

### Estado de las historias

| Historia | Estado | Evidencia |
|---|---|---|
| H6.1 — Catálogo de productos fitosanitarios | Parcial | `app/diagnostico/productos.py` ([`fc9ebb2`][fc9ebb2]) y seed de la 0015 con 21 productos. Falta la fuente SENASA/INTA por producto, y la dosis y la unidad, que quedan NULL. |
| H6.2 — Esquema de datos y migración | Completa | `migrations/versions/0015_crear_tabla_productos_fitosanitarios.py`, `app/diagnostico/models.py`, `app/diagnostico/schemas.py` ([`faec54c`][faec54c]). |
| H6.3 — Mapeo índice y patrón por cultivo y estadio | Parcial | Mapeo en `reglas.py` y `estadios.py` ([`fc9ebb2`][fc9ebb2]). Falta el documento de investigación versionado al corte; la validación con ingeniero agrónomo no es verificable en el repositorio. |

### Resultado

El conocimiento agronómico del sprint quedó en código: 21 productos sobre 10 causas, 20 reglas con su filtro de cultivo, estadio e índice, y un normalizador de estadios. No quedaron en el repositorio los documentos de investigación ni las fuentes de los productos, y el catálogo no tiene dosis. La traducción a código llegó recién con el commit del motor ([`fc9ebb2`][fc9ebb2]).

---

## 3. Sprint 7 — Datos maestros e infraestructura

| Sprint | Título | Fechas | Historias | RF/RNF |
|---|---|---|---|---|
| S7 | Datos maestros e infraestructura | 22 jul–5 ago 2026 | H7.1–H7.4 | RFME-03, RFMA-01, RFDR-01, RNF-02, RNF-17 |

### Objetivo

Preparar los datos que necesita el motor (contexto agronómico del lote y del vuelo, catálogo en base de datos, todos los índices) y saldar la deuda de R1 con archivos grandes, que impedía trabajar con ortomosaicos reales.

### Tareas realizadas

#### Estadio fenológico y contexto agronómico del lote y del vuelo (H7.1)

**Qué se implementó.** El campo `estadio_fenologico` ya existía en `lotes` desde la migración 0002 de R1, con 10 caracteres, y en el formulario "Nuevo lote". En R2 se amplió, se agregaron otros atributos agronómicos al lote, y el estadio pasó a poder cargarse por vuelo, con prioridad sobre el del lote. Asignado a H7.1 porque es el registro del estadio y del contexto que usa el diagnóstico.

**Detalle técnico.**
- **Migración 0013** (`0013_ampliar_estadio_fenologico.py`, [`fc9ebb2`][fc9ebb2]): `lotes.estadio_fenologico` de `VARCHAR(10)` a `VARCHAR(30)`. Según el mensaje del commit, 10 caracteres no alcanzaban para texto libre como "Botón floral". El downgrade vuelve a 10 y puede truncar.
- **Migración 0014** (`0014_add_variedad_tipo_suelo_fecha_siembra.py`, [`34a6d06`][34a6d06], PR #1): agrega a `lotes` `variedad VARCHAR(100)`, `tipo_suelo` (enum `tiposueloenum`: arcilloso, franco, franco_arcilloso, franco_arenoso, arenoso, vertisol, otro) y `fecha_siembra TIMESTAMPTZ`. Expuestos en `app/lotes/schemas.py` y en `frontend/src/components/ModalNuevoLote.jsx`.
- **Migración 0017** (`0017_agregar_estadio_fenologico_a_vuelos.py`, [`0ef03b8`][0ef03b8], PR #6): `vuelos.estadio_fenologico VARCHAR(30)` nullable. `POST /lotes/{id}/vuelos` acepta el campo de formulario `estadio_fenologico` (máx. 30).
- **Resolución del estadio:** `app/diagnostico/service.py::_resolver_estadio` devuelve el estadio del vuelo y, si no hay, el del lote.
- **Frontend:** `ModalCargaGeoTIFF.jsx` agrega los inputs "Estadio fenológico" (precargado con el del lote, editable) y "Fecha del vuelo"; la API ya aceptaba `fecha_vuelo`, pero el frontend nunca la enviaba. [`8cd96b6`][8cd96b6] muestra el estadio y los índices calculados en "Análisis recientes" del dashboard (`VueloListItem` suma esos campos).

**Decisiones de diseño.**
- Según la bitácora v2: `fecha_siembra` reemplazó a las "condiciones climáticas" del ERS (RFME-03) porque el clima no es un atributo fijo del lote y la fecha de siembra permite calcular días desde la siembra.
- `tipo_suelo` se definió como enum de 7 valores relevantes para el NEA.
- El estadio por vuelo es opcional para no romper los vuelos existentes ([`0ef03b8`][0ef03b8]).

**Hallazgo clave:** `variedad`, `tipo_suelo` y `fecha_siembra` se guardan pero ningún módulo del motor los consume al corte (no aparecen en `app/diagnostico/` ni en `workers/`). El estadio sigue siendo texto libre: no se calcula a partir de la fecha de siembra.

**Pruebas.** `tests/test_diagnostico_service.py` (3 tests, [`0ef03b8`][0ef03b8]) cubre la prioridad del estadio del vuelo sobre el del lote. Los atributos de la 0014 no tienen test.

#### Tabla de productos cargada y endpoint de consulta (H7.2)

**Qué se implementó.** El catálogo de H6.1 se cargó en la base dentro de la migración 0015 y se expuso en un endpoint de consulta con filtros, en [`faec54c`][faec54c] (PR #1).

**Detalle técnico.**
- **Seed:** la constante `SEED_PRODUCTOS` de la 0015 inserta los 21 productos (`nombre`, `tipo`, `causa_indice`) con un `INSERT` SQL directo. No hay un script de seeds separado.
- **API:** `GET /api/v1/productos-fitosanitarios` (JWT), con filtros opcionales `causa` (`CausaIndiceEnum`) y `tipo` (`TipoProductoEnum`); responde `{total, items}`. Vive en un router propio (`productos_router` en `app/diagnostico/router.py`, montado en `app/main.py`).
- **Integración con el motor:** `app/diagnostico/service.py::_cargar_catalogo_productos` lee la tabla en cada cálculo de diagnóstico y arma el diccionario por causa que usa `productos_sugeridos`.

**Decisiones de diseño** (bitácora v2): el router de productos no puede colgar de `/api/v1/lotes/` porque FastAPI interpreta el segmento como `{lote_id}` UUID.

**Pruebas.** El endpoint de productos no tiene test (no hay referencias a `productos-fitosanitarios` en `tests/` al corte).

**Diferencia con la presentación:** la ruta declarada es `GET /api/v1/productos`; la real es `/api/v1/productos-fitosanitarios`. Se registra como discrepancia.

#### Cálculo de todos los índices disponibles (H7.3)

**Qué se implementó.** El código de R1 ya calculaba NDVI, NDRE, SAVI y ExG, pero solo NDVI de forma automática al subir; los demás se pedían de a uno. En R2 se agregó un quinto índice (GNDVI), un cálculo en lote que lee el GeoTIFF una sola vez, el precálculo automático de NDVI, NDRE, SAVI y GNDVI en cada subida, y umbrales de clasificación propios por índice.

**Detalle técnico.**
- **GNDVI** ([`fc9ebb2`][fc9ebb2]): migración `0012_add_gndvi_indiceenum.py` (`ALTER TYPE indiceenum ADD VALUE IF NOT EXISTS 'gndvi'`, dentro de `autocommit_block` porque no puede correr en una transacción; el downgrade es `pass` porque PostgreSQL no permite quitar valores de un enum). En `workers/gis/indices.py` y `workers/gis/band_mapping.py`, GNDVI = (NIR − GREEN) / (NIR + GREEN), con bandas `NIR` y `GREEN`. Según la bitácora v1 (2026-08-27), se agregó para la regla R21 (enfermedad tardía en soja).
- **Batch** ([`fc9ebb2`][fc9ebb2]): `POST /api/v1/lotes/{lote_id}/vuelos/{vuelo_id}/indices/batch` (JWT) y la tarea Celery `workers.gis.tasks.analizar_indices_batch` (cola `gis`, `autoretry_for=(ConnectionError, OSError)`, 3 reintentos, 30 s). Recibe un mapa índice → fila de `analisis_indices`, lee cada banda una sola vez y procesa los índices con el núcleo compartido `workers/gis/pipeline.py::_procesar_indice_desde_bandas`. Un índice que falla no aborta los demás.
- **Precálculo automático** ([`1fec6f1`][1fec6f1], PR #4): en `ModalCargaGeoTIFF.jsx`, NDVI, NDRE, SAVI y GNDVI quedan tildados por defecto y se encolan con `analizarIndicesBatch` después de la subida; ExG queda opcional. [`4cb94bf`][4cb94bf] impide destildar NDVI, que el diagnóstico necesita siempre.
- **Umbrales por índice** ([`1fec6f1`][1fec6f1]): `workers/gis/clasificacion.py::_UMBRALES_POR_INDICE` con cortes fijos NDVI y GNDVI `[0.20, 0.40, 0.70]`, NDRE `[0.10, 0.20, 0.35]` y SAVI `[0.15, 0.30, 0.50]`. ExG se clasifica siempre con Otsu.

**Errores corregidos.** Según el mensaje de [`1fec6f1`][1fec6f1], NDRE y SAVI se clasificaban con los umbrales de NDVI y "casi todo el mapa" quedaba como crítico aunque el cultivo estuviera sano. La leyenda y el tooltip de `MapaIndice.jsx` decían siempre "NDVI".

**Pruebas.** `tests/test_indices_worker.py` pasa de 14 a 20 tests ([`fc9ebb2`][fc9ebb2]): `test_gndvi_valor_conocido`, `test_pipeline_multi_indice_bandas_compartidas`, `test_pipeline_multi_indice_error_no_aborta_batch` y tres tests de lectura decimada (H7.4). Los umbrales por índice no tienen test.

**Diferencia con la presentación:** el recap de R1 dice que R1 leía "1 solo índice: NDVI"; el código de `f35e422` ya calculaba cuatro.

#### Pipeline con archivos grandes (H7.4)

**Qué se implementó.** Deuda técnica de R1: el límite de 2 GB con el archivo completo en memoria en la API y en el worker. Se reescribió la entrada y salida de archivos en toda la cadena y se optimizaron la reproyección, la lectura y la vectorización. El trabajo está en [`2b0566e`][2b0566e], [`8644be4`][8644be4], [`c5e41ae`][c5e41ae], [`ecc6fa3`][ecc6fa3] y en la parte de GIS de [`fc9ebb2`][fc9ebb2], todos directo a `main`.

**Detalle técnico por capa.**

| Capa | Cambio | Commit |
|---|---|---|
| Diagnóstico | Logs de cada etapa del pipeline en `workers/gis/pipeline.py` y `tasks.py` | [`2b0566e`][2b0566e] |
| API | Límite de upload subido de 2 GB a 3 GB, como paso temporal: "temporal hasta implementar streaming" | [`8644be4`][8644be4] |
| API | Upload en streaming: `app/core/storage.py::upload_geotiff_stream` (multipart de MinIO, partes de 64 MB, `length=-1`); el router lee solo los primeros 4 bytes para validar | [`c5e41ae`][c5e41ae] |
| API | Sin límite de tamaño: `app/ingesta/validator.py` solo valida extensión y *magic bytes*; su docstring dice que "el límite de tamaño ya no se comprueba aquí" | [`c5e41ae`][c5e41ae] |
| Worker | Descarga a disco en bloques de 8 MB (`download_geotiff_to_file`) en lugar de `response.read()` | [`c5e41ae`][c5e41ae] |
| Worker | Lectura decimada por GDAL para rásters de más de 9 MP (`_UMBRAL_DOWNSAMPLE_PX = 9_000_000`; `_leer_banda` con `out_shape` y `Resampling.average`) | [`c5e41ae`][c5e41ae], [`fc9ebb2`][fc9ebb2] |
| Worker | Estadísticas por polígono con `rasterize` + `np.bincount` en lugar de un `geometry_mask` por polígono | [`c5e41ae`][c5e41ae] |
| Worker | Pre-compresión: `_optimizar_si_necesario` reescribe a DEFLATE con tiles de 512×512 los GeoTIFF sin compresión ni tiles | [`ecc6fa3`][ecc6fa3] |
| Worker | CRS: `_resolver_crs` corrige el `EngineeringCRS` de exportaciones de Pix4D/DJI Terra, y el CRS embebido se corrige en disco antes de reproyectar | [`ecc6fa3`][ecc6fa3] |
| Worker | Salida de la reproyección con `bigtiff="IF_SAFER"`: un raster rotado que se realinea a ejes puede superar los 4 GiB del TIFF clásico | [`ecc6fa3`][ecc6fa3] |
| Worker | Caché del GeoTIFF preparado en MinIO (`{usuario}/{lote}/{vuelo}/preparado_4326.tif`, `_key_preparado`) para no repetir descarga, compresión y reproyección por cada índice | [`fc9ebb2`][fc9ebb2] |
| Worker | Lock distribuido en Redis (`_cliente_redis_lock`, TTL 1800 s, sondeo cada 3 s) para que dos tareas del mismo vuelo no reproyecten en paralelo | [`fc9ebb2`][fc9ebb2] |
| Worker | Reproyección multihilo: `num_threads=4`, `warp_mem_limit=512` MB | [`fc9ebb2`][fc9ebb2] |
| Worker | Simplificación Douglas-Peucker de 0,5 px a 2 px; área mínima por defecto de 1 000 m² a 10 000 m² (1 ha) | [`fc9ebb2`][fc9ebb2] |
| API | `uvicorn --http h11` en `docker-compose.yml` | [`fc9ebb2`][fc9ebb2] |
| API | Cómputo del diagnóstico y descargas de MinIO movidos a threadpool (`run_in_threadpool`) | [`fc9ebb2`][fc9ebb2] |
| Frontend | Barra de progreso con porcentaje durante la subida (`onUploadProgress` en `ModalCargaGeoTIFF.jsx`) | [`a2d6596`][a2d6596] |
| Frontend | `MapaIndice.jsx`: límite de 1 500 features renderizadas (`MAX_FEATURES_RENDER`) y bounds calculados con un bucle en lugar de `Math.min(...array)` | [`c5e41ae`][c5e41ae] |

**Límite de tamaño vigente al corte:** la API no aplica ningún límite de tamaño de archivo. El límite de 3 GB de [`8644be4`][8644be4] fue reemplazado por el streaming de [`c5e41ae`][c5e41ae]. Los "4 GiB" de [`ecc6fa3`][ecc6fa3] no son un límite de upload sino del formato TIFF clásico en el archivo de salida de la reproyección, resuelto con BigTIFF.

**Decisiones de diseño.**
- `--http h11`: el comentario en `docker-compose.yml` y el mensaje de [`fc9ebb2`][fc9ebb2] atribuyen a `httptools`, el parser por defecto de `uvicorn[standard]`, un problema de rendimiento severo con cuerpos de más de 2 GiB.
- Threadpool: según el mismo commit, una zona SAVI de 383 614 vértices bloqueaba el *event loop* de FastAPI durante minutos.
- Estadísticas sobre el raster decimado: la bitácora v1 (2026-08-28) documenta el trade-off de priorizar que el análisis termine sin agotar memoria sobre calcular las estadísticas globales a resolución completa.

**Mediciones (según la bitácora `docs/release-v1.0.0.md` y el mensaje de [`fc9ebb2`][fc9ebb2]):**

| Caso | Antes | Después |
|---|---|---|
| Subida de `ORTOMOSAICO.tif` (2,57 GB) | 42+ min, con 401 final por expiración del JWT | 1 min 27 s |
| Mismo archivo, subida aislada con `--http h11` vs. `httptools` | 40+ min | 12 s |
| Estadísticas por zona, 200 polígonos en un raster de 10k × 10k | ~60 s | < 3 s |
| Reproyección del archivo real de 2,5 GB | ~11–16 min (942 s medidos) | Sin medición posterior registrada |
| Reproyección end-to-end del archivo real de 2,7 GB tras el fix de CRS | — | ~972 s |
| `/health` con el cómputo del diagnóstico al 100 % de CPU | Sin respuesta | ~150 ms |

No hay en el repositorio un script reproducible de estas mediciones. `scripts/descargar_sentinel2_real.py` y `scripts/generar_geotiff_prueba.py`, agregados en [`c5e41ae`][c5e41ae], obtienen y generan datos de prueba pero no miden tiempos. Los archivos medidos no están versionados.

**Errores corregidos** (según la bitácora v1):
- **Pantalla en blanco** con un GeoJSON de 3 567 polígonos (8,7 MB): `RangeError` por `Math.min(...)` sobre cientos de miles de coordenadas ([`c5e41ae`][c5e41ae]).
- **CRS mal resuelto:** `EngineeringCRS` mal clasificado y `reproject()` que ignoraba el `src_crs` explícito ([`ecc6fa3`][ecc6fa3]).
- **Límite de 4 GiB** en la salida de la reproyección ([`ecc6fa3`][ecc6fa3]).
- **Reproyección duplicada** por condición de carrera entre `procesar_vuelo` y `analizar_indices_batch` ([`fc9ebb2`][fc9ebb2]).
- **Worker terminado por falta de memoria** (`SIGKILL`) por leer bandas a resolución completa ([`fc9ebb2`][fc9ebb2]).
- **Bandas enteras:** `TypeError: Cannot convert fill_value nan to dtype uint8` con bandas `uint8` ([`fc9ebb2`][fc9ebb2]).
- **Subida colgada** con `httptools` ([`fc9ebb2`][fc9ebb2]).

**Pruebas.** Tres tests en `tests/test_indices_worker.py` ([`fc9ebb2`][fc9ebb2]): `test_lectura_decimada_raster_grande_no_materializa_resolucion_completa`, `test_lectura_decimada_dtype_entero_no_falla` y `test_pipeline_archivo_grande_completa_sin_cargar_resolucion_completa`. El streaming de la API, la caché y el lock no tienen test.

**Problema abierto al corte:** el worker no tiene `mem_limit` en `docker-compose.yml` ni concurrencia acotada (la bitácora v1 registra 4,4 GiB de 7,4 GiB con dos tareas pesadas concurrentes). Ver sección 8.

#### Otros cambios del sprint

**Certificado raíz de Avast en las imágenes** ([`fc9ebb2`][fc9ebb2]). `docker/certs/avast-root.crt` se agrega al repositorio y se instala en `docker/Dockerfile.api`, `docker/Dockerfile.worker` y `docker/Dockerfile.frontend` (este último con `NODE_EXTRA_CA_CERTS`). Según los comentarios de los Dockerfiles, pip y npm fallaban con `CERTIFICATE_VERIFY_FAILED` en máquinas con Avast interceptando TLS. Sin historia asociada: es un ajuste del entorno de un integrante que quedó en las tres imágenes. Se registra como riesgo en la sección 8.

### Estado de las historias

| Historia | Estado | Evidencia |
|---|---|---|
| H7.1 — Estadio fenológico del cultivo | Completa | Migraciones 0013 ([`fc9ebb2`][fc9ebb2]), 0014 ([`34a6d06`][34a6d06]) y 0017 ([`0ef03b8`][0ef03b8]); `_resolver_estadio`; inputs en `ModalNuevoLote.jsx` y `ModalCargaGeoTIFF.jsx`. El campo existía desde R1 (migración 0002). |
| H7.2 — Tabla de productos cargada | Completa | Seed en la 0015 y `GET /api/v1/productos-fitosanitarios` ([`faec54c`][faec54c]). Ruta distinta de la declarada (ver discrepancias). |
| H7.3 — Cálculo de todos los índices | Completa | GNDVI (0012), `analizar_indices_batch` y `POST .../indices/batch` ([`fc9ebb2`][fc9ebb2]); precálculo y umbrales por índice ([`1fec6f1`][1fec6f1]). |
| H7.4 — Pipeline con archivos grandes | Completa | Streaming, lectura decimada, pre-compresión, caché, lock, BigTIFF y `--http h11` ([`c5e41ae`][c5e41ae], [`ecc6fa3`][ecc6fa3], [`fc9ebb2`][fc9ebb2]). Mediciones según la bitácora, sin script reproducible. |

### Resultado

El lote y el vuelo quedaron con el contexto agronómico que pide el motor, el catálogo quedó consultable desde la API y cada subida calcula cuatro índices con una sola lectura del archivo. El cambio de mayor impacto fue H7.4: la cadena de entrada y salida dejó de cargar el GeoTIFF completo en memoria y, según la bitácora, la subida de un ortomosaico real de 2,57 GB pasó de no completarse a tardar 1 min 27 s. Quedaron sin uso en el motor los atributos `variedad`, `tipo_suelo` y `fecha_siembra`, y sin límite de memoria el worker.

---

## 4. Sprint 8 — Motor de reglas

| Sprint | Título | Fechas | Historias | RF/RNF |
|---|---|---|---|---|
| S8 | Motor de reglas | 5–11 ago 2026 | H8.1–H8.3 | RFDR-01, RFDR-05 |

### Objetivo

Implementar el motor que convierte cada zona vectorizada en un diagnóstico: causa probable, nivel de confianza, acción recomendada, producto sugerido y una explicación en lenguaje simple. Era la historia más incierta de la release (H8.2).

### Tareas realizadas

#### Reglas en un módulo separado del evaluador (H8.1)

**Qué se implementó.** Las 20 reglas del motor viven en `app/diagnostico/reglas.py`, separadas del evaluador en cascada de `app/diagnostico/engine.py` ([`fc9ebb2`][fc9ebb2]). Cada regla es una `dataclass` inmutable (`Regla`) con `id`, `nombre`, `bloque`, `cultivos`, `estadios`, `requiere_indices`, `condicion` (función sobre el contexto de la zona), `confianza`, `causa_indice`, `accion_recomendada`, `como_confirmar_campo` y `excluye_zona`.

**Orden de evaluación.** `REGLAS` fija el orden de la cascada, que el docstring toma de la sección 5 del documento de referencia: exclusiones → malezas → enfermedades fúngicas → insectos → déficit nutricional → estrés hídrico → madurez diferencial del algodón → vigor excesivo → cierre. La primera regla que cumple cultivo, estadio, índices disponibles y condición gana, y las siguientes no se evalúan. R99 no tiene condiciones, así que la cascada siempre termina; si no matchea ninguna, `evaluar_zona()` lanza `AssertionError`.

| Regla | Nombre | Bloque | Condición | Confianza | Causa |
|---|---|---|---|---|---|
| R00 | Copa de árbol u obstáculo físico | exclusiones | NDVI < 0.20, patrón circular y área < 0.05 ha | alta | sin problema (zona excluida) |
| R01 | Suelo desnudo | exclusiones | NDVI < 0.20 | alta | sin problema |
| R10 | Interferencia de malezas | malezas | NDVI < 0.50 y ExG > 0.20 | alta | interferencia de vegetación |
| R20 | Enfermedad fúngica en soja (reproductivo) | fúngicas | NDVI < 0.50, circular | alta | fúngico |
| R21 | Enfermedad tardía en soja (GNDVI) | fúngicas | GNDVI < 0.40, circular o focos aislados | media | fúngico |
| R22 | Enfermedad fúngica en maíz | fúngicas | NDVI < 0.50, circular | media | fúngico |
| R23 | Enfermedad fúngica en algodón | fúngicas | NDVI < 0.50, circular o focos aislados | media | fúngico |
| R24 | Enfermedad fúngica en sorgo | fúngicas | NDVI < 0.50, circular o focos aislados | media | fúngico |
| R30 | Insectos en soja | insectos | NDVI < 0.50, manchas irregulares o focos aislados | media | insectos |
| R31 | Insectos en maíz y sorgo | insectos | NDVI < 0.50, manchas irregulares o bordes del lote | media | insectos |
| R32 | Insectos en algodón | insectos | NDVI < 0.50, manchas irregulares, focos aislados o circular | media | insectos |
| R40 | Déficit de N en soja | nutricional | NDRE < 0.20, difuso homogéneo o por sectores | alta | nitrógeno |
| R41 | Déficit de N en maíz y sorgo | nutricional | NDRE < 0.20, difuso homogéneo o por sectores | alta | nitrógeno |
| R42 | Déficit de N en algodón | nutricional | NDRE < 0.20, difuso homogéneo o por sectores | alta | nitrógeno |
| R43 | Déficit de micronutrientes (Mg, B) | nutricional | NDRE < 0.20, bordes del lote o manchas irregulares | media | micronutrientes |
| R44 | Déficit de fósforo | nutricional | NDVI < 0.50 y NDRE < 0.20, por sectores o difuso homogéneo | media | fósforo |
| R50 | Estrés hídrico generalizado | hídrico | NDVI < 0.50, difuso homogéneo | media | hídrico |
| R60 | Madurez temprana diferencial en algodón | madurez | NDVI < 0.25, NDVI < 0.40 × promedio del lote, focos aislados o manchas irregulares | media | madurez diferencial |
| R70 | Vigor excesivo en maíz | vigor | NDVI > 0.85, difuso homogéneo | baja | vigor excesivo |
| R99 | Sin problema detectado | cierre | Siempre | alta | sin problema |

**Criterio del estado Parcial:** la historia pide las reglas "en un archivo de configuración separado del código para poder modificarlas sin tocar la lógica del motor". Las reglas están separadas del evaluador, pero son código Python con condiciones `lambda`: modificar un umbral o agregar una regla requiere editar un módulo Python y redesplegar la API. No hay un archivo de configuración (YAML, JSON o tabla en la base) editable sin cambiar código.

**Pruebas.** `tests/test_diagnostico_engine.py` (14 funciones de test, una parametrizada; [`fc9ebb2`][fc9ebb2]):
- Unicidad y orden de los IDs de las reglas.
- Prioridades de la cascada: R00 antes que R01, R10 antes que R20.
- Filtros por cultivo y estadio.
- R44 con los dos índices que requiere.
- R60 y su umbral relativo al promedio del lote.
- Caída de una zona sana en R99.
- `normalizar_estadio`.

**Diferencia con la presentación:** los artefactos declarados son `app/diagnostico/rules_config.py` y `app/diagnostico/motor_reglas.py`; los archivos reales son `reglas.py` y `engine.py`. La función `evaluar_zona()` existe con ese nombre, en `engine.py`.

#### Diagnóstico por zona: causa probable, confianza y producto sugerido (H8.2)

**Qué se implementó.** El endpoint de diagnóstico, que toma las zonas NDVI del vuelo, clasifica el patrón espacial de cada una, resuelve los valores de los demás índices por intersección geométrica, corre el motor de reglas y devuelve un GeoJSON enriquecido ([`fc9ebb2`][fc9ebb2]). Desde [`f6644f1`][f6644f1] (PR #5), el resultado se guarda por vuelo y se recalcula solo a pedido. Asignado a H8.2 porque `f6644f1` cambia el comportamiento del mismo endpoint (decisión del equipo).

**Detalle técnico por capa.**
- **API** (`app/diagnostico/router.py`, JWT en ambos):
  - `GET /api/v1/lotes/{lote_id}/vuelos/{vuelo_id}/diagnostico` y `POST .../diagnostico/recalcular` responden 200 con el GeoJSON.
  - 404 si el lote no es del usuario, si el vuelo no pertenece al lote o no está `completado`, o si no hay NDVI.
  - 500 con un mensaje genérico ante cualquier error interno, que se loguea con `logger.exception`.
- **Servicio** (`app/diagnostico/service.py::generar_diagnostico`):
  1. Verifica que el vuelo pertenezca al lote y esté `completado`.
  2. Si no se fuerza el recálculo, devuelve el resultado guardado.
  3. Descarga el GeoJSON de NDVI y los de NDRE, SAVI, ExG y GNDVI que estén `completado`.
  4. Corre el cómputo geométrico en `run_in_threadpool`.
  5. Guarda el resultado con *upsert* (`ON CONFLICT (vuelo_id) DO UPDATE`).
- **Patrón espacial** (`app/diagnostico/forma.py::clasificar_patron_zona`): 7 patrones calculados con Shapely sobre una proyección equirectangular local en metros (error < 0,1 % a escala de lote, según el docstring).

| Patrón | Criterio (constantes en `forma.py`) |
|---|---|
| `bordes_lote` | ≥ 50 % del perímetro de la zona dentro de una franja de 30 m del límite del lote |
| `por_sectores` | La zona ocupa ≥ 15 % del lote y llena ≥ 70 % de su rectángulo mínimo |
| `circular` | Circularidad 4πA/P² ≥ 0.65 y elongación < 3 |
| `lineal` | Elongación (lado mayor / lado menor del rectángulo mínimo) ≥ 3 |
| `focos_aislados` | Focos ≤ 2 000 m², al menos 3 de la misma clase |
| `difuso_homogeneo` | La clase cubre ≥ 30 % del lote en a lo sumo 2 zonas |
| `manchas_irregulares` | Caso por defecto |

- **Multi-índice** (`enriquecer_con_indice`): NDVI es la partición canónica de zonas. El valor de otro índice en cada zona es el promedio ponderado por el área de intersección real contra los polígonos de ese índice. El NDVI promedio del lote es el promedio de las zonas ponderado por área.
- **Respuesta:**
  - Por zona: `patron_espacial`, `zona_id`, `regla_id`, `regla_nombre`, `confianza`, `causa_indice`, `severidad`, `accion_recomendada`, `como_confirmar_campo`, `excluida`, `productos_sugeridos` (desde la tabla de H7.2) y `texto_explicativo`.
  - A nivel raíz: `unidades_manejo` y `metadata` (`lote_id`, `lote_nombre`, `vuelo_id`, `fecha_vuelo`, `calculado_en`, `indices_disponibles`, `n_unidades_manejo`, `resumen_general`), que cubren la trazabilidad vuelo ↔ lote de RFDR-05.
- **Persistencia** (`0016_crear_tabla_diagnosticos.py`, [`f6644f1`][f6644f1]): tabla `diagnosticos` (`id`, `vuelo_id` con FK a `vuelos` y `ON DELETE CASCADE`, `resultado JSONB`, `calculado_en`), índice único `ix_diagnosticos_vuelo_id`. Un vuelo tiene a lo sumo un diagnóstico; recalcular sobrescribe la fila.
- **Frontend:**
  - `frontend/src/pages/ResultadosVuelo.jsx` agrega la pestaña "Diagnóstico", que pide el diagnóstico la primera vez que se abre.
  - `frontend/src/components/TablaDiagnostico.jsx` muestra una tarjeta por zona con causa, confianza, patrón, acción, cómo confirmar en campo y productos ([`fc9ebb2`][fc9ebb2]), y el botón "↻ Recalcular" ([`f6644f1`][f6644f1]).
  - `frontend/src/api/analisis.js` suma `obtenerDiagnostico` y `recalcularDiagnostico`.

**Decisiones de diseño.**
- **Sin GeoPandas en `app/diagnostico/`:** según la bitácora v1 (2026-08-27), el primer intento usó GeoPandas y falló con `ModuleNotFoundError: No module named 'geopandas'` en el contenedor `api`, que a propósito no instala GDAL ni GeoPandas. El motor usa solo Shapely y una proyección local.
- **NDVI como partición canónica:** según la bitácora v1, NDVI siempre existe porque se calcula al subir; las reglas multi-índice (R10, R44) se resuelven por superposición geométrica en lugar de vectorizar de nuevo.
- **Persistencia:** según el docstring de la 0016, solo evita recalcular en cada `GET`; el historial multi-vuelo sigue siendo alcance de R4 (RFGL-03).

**Hallazgo clave:** la bitácora v2 describe el diagnóstico como "sin persistencia (persistencia queda para release 4)", pero al corte existe la tabla `diagnosticos` (migración 0016, [`f6644f1`][f6644f1]) y el endpoint devuelve el resultado guardado. Lo que queda para R4 es el historial: la tabla guarda solo el último cálculo por vuelo.

**Pruebas.**
- `tests/test_forma.py` (12, [`fc9ebb2`][fc9ebb2]): un caso por cada uno de los 7 patrones y los casos sin límite de lote y con lista vacía.
- `tests/test_diagnostico_api.py` (8, [`fc9ebb2`][fc9ebb2]):
  - Cubre solo caminos de error: 404 con el vuelo pendiente, procesando, con error, completado sin GeoJSON, inexistente o de otro lote, y con el lote inexistente.
  - También el acceso sin autenticación.
  - No hay test de una respuesta 200 con zonas, ni del endpoint de recálculo, ni de la persistencia.
- La presentación declara "5 casos de prueba" unitarios: al corte hay 14 en el motor y 12 de forma.

**Errores corregidos relacionados** (según la bitácora v1):
- La API se bloqueaba mientras se calculaba un diagnóstico pesado. Se corrigió moviendo el cómputo a threadpool ([`fc9ebb2`][fc9ebb2]).
- La leyenda del mapa tapaba los modales, porque compartían `z-index: 1000` ([`fc9ebb2`][fc9ebb2]).
- Los nombres de regla largos desbordaban las tarjetas de diagnóstico, por falta de `min-width: 0` ([`fc9ebb2`][fc9ebb2]).

**Diferencia con la presentación:** el endpoint declarado es `GET /analisis/{id}/diagnostico`; el real cuelga del vuelo: `GET /api/v1/lotes/{lote_id}/vuelos/{vuelo_id}/diagnostico`.

#### Diagnóstico en lenguaje simple (H8.3)

**Qué se implementó.** Un módulo puro, sin I/O ni base de datos, que redacta el diagnóstico de cada zona y un resumen del lote en lenguaje para el productor ([`e435402`][e435402], PR #2).

**Detalle técnico.**
- `app/diagnostico/texto.py` define etiquetas legibles para las 10 causas, los 7 patrones y las 3 confianzas: "media" se lee "requiere verificación en campo" y "baja", "orientativo".
- `generar_texto_zona()` arma un párrafo con:
  - el área y el patrón;
  - el NDVI de la zona y su desviación porcentual respecto del promedio del lote;
  - la causa con su confianza;
  - la acción recomendada completa;
  - hasta 3 productos sugeridos, con "y N más" si hay otros.
- `generar_resumen_general()` resume en `metadata.resumen_general` las zonas con y sin problema, el área afectada y las causas agrupadas.
- La acción recomendada y el texto de "cómo confirmar en campo" de cada regla se copiaron literalmente del documento de referencia, según el docstring de `reglas.py`.
- `TablaDiagnostico.jsx` muestra el resumen arriba de la lista y el `texto_explicativo` como párrafo principal de cada tarjeta, junto con "cómo confirmar en campo".

**Decisiones de diseño** (bitácora v2):
- `texto.py` es puro, igual que `engine.py` y `reglas.py`.
- El texto incluye la acción recomendada completa, no un resumen.

**Pruebas.** `tests/test_texto.py` (26 tests) llegó recién en [`1e2f129`][1e2f129], en el S10. Cubre severidad, texto por zona (R99, R00 y zonas con problema), texto de la unidad de manejo y resumen general. No corre en CI.

### Estado de las historias

| Historia | Estado | Evidencia |
|---|---|---|
| H8.1 — Reglas en archivo de configuración | Parcial | 20 reglas en `app/diagnostico/reglas.py`, separadas del evaluador `engine.py` ([`fc9ebb2`][fc9ebb2]). Falta que sean configuración editable sin código: son condiciones `lambda` en Python. |
| H8.2 — Zona con causa, confianza y producto | Completa | `GET .../diagnostico` y `app/diagnostico/service.py` ([`fc9ebb2`][fc9ebb2]); persistencia y recálculo ([`f6644f1`][f6644f1]). Ruta y archivos con otros nombres (ver discrepancias). |
| H8.3 — Diagnóstico en lenguaje simple | Completa | `app/diagnostico/texto.py` y `TablaDiagnostico.jsx` ([`e435402`][e435402]). |

### Resultado

El motor quedó operativo: 20 reglas en cascada, 7 patrones espaciales, resolución multi-índice y un texto explicativo por zona, accesibles desde una pestaña de resultados y guardados por vuelo. La verificación manual registrada (soja con una zona circular de NDVI bajo → R20) confirma el camino principal. Los tests automatizados cubren el evaluador, la forma y los errores del endpoint, pero no una respuesta exitosa del endpoint. Todo el núcleo del sprint entró en un único commit directo a `main` ([`fc9ebb2`][fc9ebb2], 43 archivos), fechado el 28 de agosto.

---

## 5. Sprint 9 — Severidad y zonificación

| Sprint | Título | Fechas | Historias | RF/RNF |
|---|---|---|---|---|
| S9 | Severidad y zonificación | 11–13 ago 2026 | H9.1 | RFDR-02, RFDR-03 |

### Objetivo

Convertir las zonas individuales en información accionable: cuantificar cuánto se aparta cada zona del promedio del lote y agrupar las zonas contiguas con el mismo problema en unidades de manejo.

### Tareas realizadas

#### Severidad por zona y unidades de manejo (H9.1)

**Qué se implementó.**
- **Severidad (RFDR-03):** llegó en [`e435402`][e435402] (PR #2, fechado en git como parte del S8).
- **Unidades de manejo (RFDR-02) y mapa coloreado por severidad:** llegaron en [`90b4bcd`][90b4bcd] (PR #3).

Asignado a H9.1 por contenido: la severidad se calcula en `texto.py`, pero responde a esta historia.

**Detalle técnico.**
- **Severidad** (`app/diagnostico/texto.py::calcular_severidad`): ratio = (NDVI promedio del lote − NDVI de la zona) / NDVI promedio del lote, con 5 niveles:

| Nivel | Condición |
|---|---|
| `critica` | ratio > 0.50 |
| `moderada` | ratio > 0.25 |
| `leve` | ratio > 0.10 |
| `normal` | el resto, las zonas `sin_problema_detectado` y los casos sin NDVI |
| `vigorosa` | causa `vigor_excesivo` (R70) |

- **Unidades de manejo** (`app/diagnostico/zonificacion.py::generar_unidades_manejo`):
  - Excluye las zonas R99, R00 y las de severidad normal.
  - Agrupa por (causa, severidad).
  - Detecta contigüidad con un buffer de 20 m (`BUFFER_CONTIGUIDAD_M`) en proyección local y arma componentes conexos por BFS.
  - Fusiona las geometrías de cada componente con `unary_union`.
  - Calcula el área total, el NDVI promedio ponderado y la cantidad de zonas.
  - Ordena por criticidad (crítica, moderada, leve, vigorosa).
  - `generar_texto_unidad()` redacta la descripción de cada unidad.
  - La respuesta las expone como `unidades_manejo` (Features GeoJSON).
- **Frontend:**
  - `MapaZonas.jsx` recibe la prop `diagnostico`. Con la pestaña "Diagnóstico" activa, colorea las zonas por severidad en lugar de por clase de vigor y dibuja los contornos punteados de las unidades de manejo (`dashArray: '8 4'`). La leyenda cambia según el modo.
  - `TablaDiagnostico.jsx` agrega la sección "Unidades de manejo".

**Decisiones de diseño** (bitácora v2, S9):
- El buffer de 20 m une zonas separadas solo por bordes de vectorización.
- La severidad se calcula sobre NDVI porque es el índice siempre presente.
- El mapa por severidad, planificado para el S10, se adelantó al S9 porque hacía falta para ver las unidades de manejo.

**Pruebas.** `tests/test_zonificacion.py` (19 tests) y los tests de severidad de `tests/test_texto.py` llegaron recién en [`1e2f129`][1e2f129] (S10) y no corren en CI. La bitácora v2 registra 15 tests de zonificación; el archivo al corte tiene 19.

**Diferencia con la presentación:** la presentación declara la severidad con los niveles "crítica / deficiente / normal / vigorosa", que son las clases de vigor de R1. El código usa crítica, moderada, leve, normal y vigorosa.

### Estado de las historias

| Historia | Estado | Evidencia |
|---|---|---|
| H9.1 — Severidad y unidades de manejo | Completa | `calcular_severidad` ([`e435402`][e435402]); `zonificacion.py`, mapa por severidad y contornos de unidades ([`90b4bcd`][90b4bcd]). Niveles distintos de los declarados (ver discrepancias). |

### Resultado

Cada zona diagnosticada tiene un nivel de severidad relativo al promedio del lote, y las zonas contiguas con la misma causa y severidad se presentan como una unidad de manejo con geometría propia. El mapa cambia a colores por severidad al abrir el diagnóstico. Los tests de esta lógica se escribieron dos sprints después y quedaron fuera del CI.

---

## 6. Sprint 10 — Integración, QA y cierre

| Sprint | Título | Fechas | Historias | RF/RNF |
|---|---|---|---|---|
| S10 | Integración, QA y cierre | 13–25 ago 2026 | H10.1–H10.3 | RFSA-01, RFGL-05 |

### Objetivo

Integrar el diagnóstico en la experiencia del dashboard, testear el flujo completo y preparar la demo, sin agregar funcionalidades nuevas.

### Tareas realizadas

#### Diagnóstico completo en el dashboard (H10.1)

**Qué se implementó.** Una vista compacta del diagnóstico, KPIs con datos reales y accesos directos al diagnóstico desde el dashboard y el sidebar ([`1200a87`][1200a87], [`d842ed3`][d842ed3], [`eb5d514`][eb5d514], [`fde502f`][fde502f]). [`fde502f`][fde502f] se asignó a H10.1 por decisión del equipo: viaja en el PR #6 junto con trabajo del S10.

**Detalle técnico.**
- **Tabla del diagnóstico** (`TablaDiagnostico.jsx`, [`1200a87`][1200a87]): vista "tabla" por defecto con las columnas Zona, Área, NDVI, Severidad, Causa, Confianza y Producto (el primero de `productos_sugeridos`); vista "tarjetas" alternativa con el texto completo. Las zonas sin problema (R99) se muestran atenuadas (`.stats-row--ok`).
- **Dashboard** (`frontend/src/pages/Dashboard.jsx`):
  - Las tarjetas "Recomendaciones activas" ("Próximamente") y "Ahorro estimado" ("—") se reemplazaron por "Análisis completados" y "Área monitoreada", con datos reales ([`1200a87`][1200a87]).
  - "Actividad reciente" pasó a armarse con lotes y vuelos reales ([`d842ed3`][d842ed3]).
- **Navegación:**
  - El botón "Ver diagnósticos" se habilita si hay análisis completados.
  - En la pestaña "Zonas" se agregó un link a "Ver diagnóstico agronómico".
  - Mientras carga el diagnóstico se muestra un spinner con mensaje ([`1200a87`][1200a87]).
  - "Diagnósticos" del sidebar abre `ModalElegirLote.jsx` para elegir el lote ([`fde502f`][fde502f]).
  - Se quitó del sidebar "Cargar ortomosaico", que duplicaba el botón de acciones rápidas ([`eb5d514`][eb5d514]).
- **Mapa:** colores por severidad y popups ([`90b4bcd`][90b4bcd]). El popup del modo severidad muestra `regla_nombre` (la causa), la severidad, el NDVI y el área; el popup de una unidad de manejo muestra su número, la regla, la cantidad de zonas y el área total.

**Criterio del estado Parcial:** la historia y su artefacto ("Dashboard con popup por zona (causa + confianza + producto)") piden causa, confianza y producto en el popup del mapa. El popup (`MapaZonas.jsx::onEachZonaSeveridad`) muestra la causa pero no la confianza ni el producto. Ambos datos están en la tabla del diagnóstico, fuera del mapa.

**Pruebas.** No hay tests de frontend al corte.

#### Testing end-to-end (H10.2)

**Qué se implementó.** Tests unitarios puros del texto y de la zonificación, en [`1e2f129`][1e2f129]: `tests/test_texto.py` (26) y `tests/test_zonificacion.py` (19). Se sumó `tests/test_diagnostico_service.py` (3, [`0ef03b8`][0ef03b8]). La bitácora v2 informa "84 tests del motor de diagnóstico pasan". Esa cifra incluye 9 tests de clasificación existentes; `tests/test_clasificacion.py` tiene 16 al corte.

**Criterio del estado Parcial:** la historia pide el sistema "testeado end-to-end" y el artefacto un "reporte de tests E2E sin bugs críticos".
- No hay test E2E nuevo en R2: el único sigue siendo `test_celery_integracion.py::test_ciclo_completo_encolar_y_esperar`, de R1, que no corre en CI.
- No hay reporte de tests en el repositorio, y la bitácora v2 deja "Pruebas E2E del flujo completo" como "Manual (usuario)".
- `test_texto.py`, `test_zonificacion.py` y `test_diagnostico_service.py` no están en `.github/workflows/ci.yml`.

**No encontrado en el repo.** El reporte de tests E2E (se buscó en `docs/`, `tests/` y en los mensajes de commit del rango).

#### Demo preparada (H10.3)

**Qué se implementó.** `README.md` y `CLAUDE.md` se actualizaron con los cambios de R2 en [`b7dae3a`][b7dae3a] (Sprint 7) y [`89682e1`][89682e1] (Sprints 9-10):
- endpoint de diagnóstico y de productos en el flujo de la API;
- comando de tests del motor;
- módulo `diagnostico/` en el árbol del proyecto.

**Demo.** La demo de la Release 2 se presentó el 22 de septiembre de 2026, junto con la de la Release 3 (dato del equipo, no verificable en el repositorio).

**No encontrado en el repo.** La preparación de la demo en sí (guion, datos de prueba seleccionados, ensayo) y la "Documentación de R2 en ClickUp Doc", que no es verificable desde el repositorio.

#### Otros cambios del sprint

- **Favicon** ([`cc5e82a`][cc5e82a], PR #6): `frontend/index.html` usa `logo_hoja.png` en lugar del ícono de Vite.

### Estado de las historias

| Historia | Estado | Evidencia |
|---|---|---|
| H10.1 — Diagnóstico completo en el dashboard | Parcial | Tabla con causa, confianza y producto, KPIs reales y navegación ([`1200a87`][1200a87], [`d842ed3`][d842ed3], [`fde502f`][fde502f]). Falta confianza y producto en el popup del mapa (`MapaZonas.jsx`). |
| H10.2 — Testing end-to-end | Parcial | `test_texto.py` y `test_zonificacion.py` ([`1e2f129`][1e2f129]). Falta el test E2E del flujo con diagnóstico, el reporte y la ejecución de estos tests en CI. |
| H10.3 — Demo preparada | Completa | README actualizado ([`b7dae3a`][b7dae3a], [`89682e1`][89682e1]) y demo presentada el 22 de septiembre de 2026 junto con la Release 3 (dato del equipo, no verificable en el repositorio). |

### Resultado

El diagnóstico quedó integrado al dashboard: tabla compacta con severidad, causa, confianza y producto, KPIs con datos reales y accesos directos desde el dashboard y el sidebar. El testing del sprint fue unitario: no hay prueba automatizada del flujo GeoTIFF → diagnóstico ni reporte E2E, y 48 de los tests nuevos del motor no corren en CI. La tarjeta de ahorro de insumos se eliminó en lugar de implementarse.

---

## 7. Calidad y estado al cierre

Al corte había 176 funciones de test automatizadas, el doble que en R1 (88): 88 nuevas o ampliadas en R2, de las cuales 82 están en 6 archivos nuevos. El CI conserva sus 3 jobs y agrega un step para el motor de diagnóstico. 48 de los tests nuevos no están en el workflow. Los tres jobs (`test-api`, `test-gis` y `build-frontend`) están en verde en el corte, incluido el paso de migraciones del job `test-api`; el resultado se verificó manualmente en GitHub Actions el 4 de octubre de 2026. Ese verde no cubre los 48 tests de `test_texto.py`, `test_zonificacion.py` y `test_diagnostico_service.py`, que siguen fuera del CI. En R1 el job `test-api` había fallado por `test_listar_vuelos_de_lote`; ese test se corrigió en [`fc9ebb2`][fc9ebb2], que pasó a leer `vuelo_id`.

### Pruebas automatizadas

| Tipo | Herramienta | Tests | Resultado en el corte |
|---|---|---|---|
| Unitarias GIS (worker) | pytest | 45: `test_ndvi_pipeline` 4, `test_indices_worker` 20 (+6 en R2), `test_ingesta_worker` 3, `test_clasificacion` 16, configuración de Celery 2 | Job `test-gis` en verde en el corte |
| Unitarias del motor de diagnóstico | pytest | 74: `test_diagnostico_engine` 14, `test_forma` 12, `test_texto` 26, `test_zonificacion` 19, `test_diagnostico_service` 3 | `engine` y `forma` (26): job `test-api` en verde en el corte. `texto`, `zonificacion` y `service` (48) no corren en CI: el verde no los cubre |
| Integración HTTP contra PostGIS | pytest + TestClient | 56: `test_auth` 15, `test_lotes` 16, `test_vuelos_estado` 13, `test_ingesta` 4, `test_diagnostico_api` 8 (nuevo en R2) | Job `test-api` en verde en el corte |
| End-to-end | pytest (`test_celery_integracion.py::test_ciclo_completo_encolar_y_esperar`) | 1 (de R1, sin cambios) | Solo local; no corre en CI. No cubre el diagnóstico |
| Frontend | — | 0 | Job `build-frontend` en verde en el corte; solo verifica que `npm run build` genere `frontend/dist/index.html` |
| Rendimiento y seguridad | — | — | Sin tests automatizados. Las mediciones de rendimiento son manuales (sección 3, H7.4) |

La cobertura no se midió: no hay `pytest-cov` ni configuración de cobertura en el repositorio, ni al corte ni en `origin/main`. Los tests se contaron leyendo las funciones `def test_` del snapshot de `tests/` en `47994a4`, sin ejecutarlos.

La bitácora v2 informa "84 tests del motor de diagnóstico pasan" (engine 14, forma 12, texto 26, zonificación 15, API 8 y 9 de clasificación). Hay dos diferencias con el corte:
- `test_zonificacion.py` tiene 19 tests, no 15.
- `test_clasificacion.py` tiene 16 tests en total, y su conteo no forma parte del motor.

### Verificaciones manuales

| Fecha | Verificación | Resultado |
|---|---|---|
| 4 ago | Reproyección end-to-end de un ortomosaico real de 2,7 GB tras el fix de CRS ([`ecc6fa3`][ecc6fa3]) | Completada en ~972 s, con CRS final EPSG:4326 y bounds válidos; la suite GIS pasa sin cambios |
| 27 ago | Motor de diagnóstico contra el stack Docker: lote de soja (R2) con una zona circular de NDVI ≈ 0.30 | `regla_id = R20` (enfermedad fúngica), confianza alta y los 5 fungicidas del catálogo; la zona sana circundante cae en R99 |
| 27 ago | Botón "Ver resultados" de `DetalleLote.jsx`, en el navegador, antes y después del fix | Fix confirmado; `tests/test_vuelos_estado.py` (13) pasa |
| 28 ago | Caché del GeoTIFF preparado: dos pedidos de GNDVI sobre el mismo vuelo | Primero `cache=False` con optimización y reproyección; segundo `cache=True` sin esos pasos |
| 28 ago | Fixes de interfaz: modal sobre la leyenda del mapa y nombres de regla largos en las tarjetas | Ambos confirmados en el navegador |
| 28 ago | `POST .../indices/batch` con `["ndre","savi","gndvi"]` contra API, worker y MinIO reales | 3 filas con el mismo `task_id`; una sola descarga y una sola reproyección en los logs |
| 28 ago | Lock de preparación: dos tareas simultáneas sobre un archivo de 100 MB en UTM | Antes ambas reproyectaban (6,05 s y 6,19 s); después solo una, y la otra reutilizó la caché |
| 28 ago | Subida de `ORTOMOSAICO.tif` (2,57 GB) con `--http h11` | De 42+ min (con 401 final) a 1 min 27 s |
| 28 ago | `/health` con el cómputo del diagnóstico al 100 % de CPU | Responde en ~150 ms (mensaje de [`fc9ebb2`][fc9ebb2]) |
| 2 sep | Suite del motor de diagnóstico | "84 tests pasan", según la bitácora v2 |

Todas las verificaciones salen de `docs/release-v1.0.0.md` (entradas de agosto, que son trabajo de R2), salvo la del 2 sep, que sale de `docs/release-v2.0.0.md`, y la de `/health`, que sale del mensaje de [`fc9ebb2`][fc9ebb2]. Las fechas son las de las bitácoras, no las de los sprints. No hay registro de una ejecución completa del flujo de demo desde la interfaz con el diagnóstico.

### Errores corregidos durante el desarrollo

Ninguno afectó a una versión publicada. Los más relevantes:

- **"Ver resultados" en el detalle del lote navegaba a `vuelos/undefined`** (deuda de R1): `DetalleLote.jsx` pasa a leer `vuelo_id`, y `test_listar_vuelos_de_lote` se corrigió con el mismo criterio. Commit [`fc9ebb2`][fc9ebb2].
- **Subida de archivos de más de 2 GiB colgada durante 40+ minutos:** por `httptools`. Se corrigió con `uvicorn --http h11`. Commit [`fc9ebb2`][fc9ebb2].
- **Worker terminado por falta de memoria (`SIGKILL`)** al leer bandas a resolución completa; se corrigió con la lectura decimada por GDAL. Commit [`fc9ebb2`][fc9ebb2].
- **Reproyección duplicada** por condición de carrera entre `procesar_vuelo` y `analizar_indices_batch`; se corrigió con un lock en Redis. Commit [`fc9ebb2`][fc9ebb2].
- **`EngineeringCRS` mal resuelto y `reproject()` ignorando el `src_crs` explícito**, más el límite de 4 GiB del TIFF clásico en la salida. Commit [`ecc6fa3`][ecc6fa3].
- **Pantalla en blanco con GeoJSON grande** (3 567 polígonos, 8,7 MB): `RangeError` por `Math.min(...array)`. Commit [`c5e41ae`][c5e41ae].
- **La API dejaba de responder mientras se calculaba un diagnóstico pesado.** Commit [`fc9ebb2`][fc9ebb2].
- **NDRE y SAVI clasificados con los umbrales de NDVI.** Commit [`1fec6f1`][1fec6f1].
- **Migración 0015 con asyncpg:** enum duplicado y `bulk_insert` sin cast al enum nativo. Commit [`faec54c`][faec54c].

### Despliegue de la demo

Los pasos de instalación del `README.md` del corte no cambiaron respecto de R1 (la sección "Instalación" es idéntica entre `f35e422` y `47994a4`):
1. Clonar el repositorio y posicionarse en la versión; el tag `v2.0.0` sobre `47994a4` es una propuesta, todavía no existe.
2. Crear `.env` a partir de `.env.example`.
3. `docker compose up -d --build`.
4. Correr las migraciones a mano: `docker compose exec api alembic upgrade head`.
5. Verificar con `GET /api/v1/health`, `GET /api/v1/health/db` y Swagger en `/api/docs`, donde aparecen las rutas de `diagnostico` y `productos`.

Cambios respecto de R1:
- **Migraciones:** `upgrade head` aplica de la 0012 a la 0017. La 0015 carga el seed de 21 productos fitosanitarios; no hace falta un paso de seed aparte.
- **Variables de entorno:** ninguna nueva; `.env.example` y `app/core/config.py` no cambiaron.
- **Dependencias:** sin cambios en `docker/requirements.api.txt`, `docker/requirements.worker.txt`, `frontend/package.json` ni `package-lock.json`.
- **Contenedores:**
  - El servicio `api` arranca con `--http h11`.
  - La construcción de las tres imágenes instala `docker/certs/avast-root.crt`.
  - MinIO sigue con `minio/minio:latest`, la misma imagen que en R1 (ver sección 8).

---

## 8. Deuda técnica y trabajo pendiente

Al cierre quedaron sin completar dos tipos de trabajo:
- **Funcionalidad comprometida para R2:** el cálculo de ahorro de insumos (RFGL-05), el popup completo del mapa, el test E2E con reporte y la configuración de reglas editable sin código.
- **Riesgos técnicos:** surgieron durante la optimización para archivos grandes y la integración del motor.

Ninguno de estos pendientes impide el flujo principal GeoTIFF → índices → diagnóstico.

### Defectos y riesgos conocidos

| Ítem | Descripción | Impacto | Estado |
|---|---|---|---|
| IDOR en índices adicionales (heredado de R1) | `GET .../indices/{indice}/estado` y `.../resultado` buscan el análisis solo por `vuelo_id` (`app/ingesta/service.py::obtener_estado_analisis_indice` al corte) sin verificar que el vuelo pertenezca al lote validado | Alto (seguridad) | Abierto al corte; corregido después en [`537f671`][537f671] (PR #49, 30 sep 2026) |
| Worker sin límite de memoria ni concurrencia acotada | `docker-compose.yml` no define `mem_limit` y Celery usa la concurrencia por defecto. La bitácora v1 registra 4,4 GiB de 7,4 GiB con dos tareas pesadas concurrentes | Alto (uso real con archivos de varios GB) | Abierto (sigue sin `mem_limit` en `origin/main`) |
| Certificado raíz de Avast en las tres imágenes | `docker/certs/avast-root.crt` se instala como CA de confianza en `api`, `worker` y `frontend` ([`fc9ebb2`][fc9ebb2]). Un certificado raíz de un tercero pasa a ser de confianza para todo el tráfico TLS de los contenedores, y la imagen depende del entorno de un integrante | Medio (seguridad y reproducibilidad) | Abierto (sigue en los tres Dockerfiles de `origin/main`) |
| Imagen `minio/minio:latest` | Sin versión fija. Según el mensaje de [`7e7182d`][7e7182d], la imagen se dio de baja de Docker Hub y `docker compose up` dejó de levantar `api` y `worker` | Alto (reproducibilidad del tag) | Abierto al corte; corregido en `main` después ([`7e7182d`][7e7182d]), no en el commit de corte |
| Tests del motor fuera de CI | `test_texto.py`, `test_zonificacion.py` y `test_diagnostico_service.py` (48 tests) no están en `.github/workflows/ci.yml` | Medio | Abierto (siguen fuera del workflow en `origin/main`) |
| Cobertura insuficiente de la API nueva | `test_diagnostico_api.py` cubre solo caminos de error. No hay test de una respuesta 200 del diagnóstico, de `POST .../recalcular`, de `GET /productos-fitosanitarios` ni de `POST .../indices/batch` | Medio | Abierto |
| Catálogo sin dosis ni fuente | Los 21 productos no tienen `dosis_referencia`, `unidad` ni la fuente SENASA/INTA | Medio | Abierto al corte. En R3, [`a2ec304`][a2ec304] agrega el cálculo de dosis y [`5d28b86`][5d28b86] restricciones para 15 de los 21 productos; el alcance sobre el catálogo está a confirmar |
| Atributos del lote sin uso | `variedad`, `tipo_suelo` y `fecha_siembra` se guardan, pero el motor no los consume; el estadio no se deriva de la fecha de siembra | Bajo | Abierto |
| Código muerto | `app/diagnostico/productos.py` ya no se importa desde [`faec54c`][faec54c] | Bajo | Abierto (sigue en `origin/main` sin importarse) |
| Downgrades no reversibles | La 0012 no puede quitar `gndvi` del enum (`pass`) y la 0013 puede truncar estadios de más de 10 caracteres | Bajo | Abierto |
| Estadísticas sobre el raster decimado | Para rásters de más de 9 MP, min, max y promedio se calculan sobre la lectura decimada, no a resolución completa (trade-off documentado en la bitácora v1, 28 ago) | Bajo | Abierto (decisión aceptada) |

### Funcionalidades pendientes

| Ítem | Descripción | Release destino |
|---|---|---|
| Ahorro de insumos (RFGL-05) | Diferencia entre el área total y el área prescrita. Asignado a R2 por `docs/5_Plan_de_Releases.md`; la tarjeta del dashboard se eliminó en [`1200a87`][1200a87] | A definir (no figura en las presentaciones de R3 ni de R4) |
| Popup del mapa con confianza y producto | El popup de severidad muestra causa, severidad, NDVI y área | A definir |
| Reglas configurables sin código | Las 20 reglas son `lambda` en `reglas.py`; no hay archivo de configuración ni tabla editable | A definir |
| Test E2E del flujo con diagnóstico, en CI y con reporte | El único E2E es el de R1 y corre solo en local | A definir |
| Validación del diagnóstico por el usuario y criterio técnico (RFDR-04) | El plan de releases la menciona en R2 ("validación en campo") y la asigna a R5 (RFDR-04) | Release 5, según `docs/5_Plan_de_Releases.md` |
| Historial de diagnósticos entre vuelos (RFGL-03) | La tabla `diagnosticos` guarda solo el último cálculo por vuelo | Release 4 |
| Reporte ejecutivo PDF, exportación GeoJSON/Shapefile y orden de trabajo | Salidas formales del diagnóstico | Release 3 |
| Dibujo del límite del lote sobre mapa satelital | Carga del lote sin archivo GeoJSON | Release 3 (Sprint 11) |
| Validación de índices y reglas del motor | La presentación de R2 deja pendiente la validación con ingeniero agrónomo; la presentación de R3 declara una validación de índices y reglas (historia 12.3) | Release 3 |

### Deuda heredada de R1

| Ítem | Estado al corte de R2 | Estado actual (origin/main) | Evidencia |
|---|---|---|---|
| "Ver resultados" en el detalle del lote | Corregido | Corregido | [`fc9ebb2`][fc9ebb2]: `DetalleLote.jsx` usa `vuelo_id` |
| Test fallido en CI (`test_listar_vuelos_de_lote`) | Corregido | Corregido | [`fc9ebb2`][fc9ebb2]: el test lee `vuelo_id`; job `test-api` en verde en `47994a4` |
| IDOR en índices adicionales | Abierto | Corregido | Al corte, `obtener_estado_analisis_indice(db, vuelo_id, indice)`; en `origin/main` recibe `lote_id` ([`537f671`][537f671], PR #49, 30 sep 2026) |
| Registro desde la interfaz | Abierto | Abierto | El botón "Registrarse" de `frontend/src/pages/Login.jsx` sigue sin handler ni pantalla de registro |
| Usuario seed con credenciales conocidas | Abierto | Abierto | `migrations/versions/0006_seed_usuario_default.py` sin cambios |
| Archivos grandes en memoria | Mitigado | Mitigado | Streaming y sin límite de tamaño en la API ([`c5e41ae`][c5e41ae]); lectura decimada ([`fc9ebb2`][fc9ebb2]). Riesgo derivado: worker sin `mem_limit` (tabla anterior) |
| Imagen `minio/minio:latest` | Abierto | Corregido | [`7e7182d`][7e7182d] la reemplaza por `cgr.dev/chainguard/minio:latest`; los tags `v1.0.0` y `v2.0.0` (propuesto) conservan la original |
| Dependencias sin fijar (`scipy`, `npm install` con rangos) | Abierto | Abierto | `scipy` no está en `docker/requirements.worker.txt`; `npm install` en `docker/Dockerfile.frontend` y en `ci.yml` |
| Migraciones manuales y downgrades incompletos | Abierto | Abierto | `docker-compose.yml` no corre Alembic; el README mantiene el paso manual |
| Motor de diagnóstico (RFDR-01) | Corregido (implementado) | Corregido (implementado) | `app/diagnostico/` ([`fc9ebb2`][fc9ebb2]) |
| Severidad, zonificación de manejo y ahorro de insumos | Parcial | Parcial | Severidad ([`e435402`][e435402]) y unidades de manejo ([`90b4bcd`][90b4bcd]) implementadas. El ahorro (RFGL-05) no está implementado: la tarjeta se eliminó en [`1200a87`][1200a87] y no hay referencias a "ahorro" en `app/` ni en `frontend/src/` de `origin/main`. Destino: a definir |
| Roles y permisos | Abierto | Abierto | Sin roles en `app/auth/` al corte ni en `origin/main` |
| Testing E2E en CI y cobertura | Abierto | Abierto | `ci.yml` no corre el E2E ni mide cobertura, ni al corte ni en `origin/main` |
| Zonas en PostGIS | Abierto | Abierto | La única columna geométrica sigue siendo `lotes.geometry`. Las zonas siguen como GeoJSON en MinIO, y el diagnóstico se guarda como JSONB (`diagnosticos.resultado`) |
| Exportación PDF, Shapefile e ISO-XML | Abierto | Parcial | En R3: PDF y Shapefile (`app/reportes/`, desde [`36dc4b9`][36dc4b9] y [`706bc15`][706bc15]). Sin ISO-XML en `origin/main` |

### Compromisos de mejora de la release anterior

| Compromiso | Estado | Evidencia |
|---|---|---|
| QA desde el primer sprint de implementación | Parcial | [`fc9ebb2`][fc9ebb2] incluye tests del motor, de forma, de API y 6 de índices, pero `test_texto.py` y `test_zonificacion.py` llegan recién en [`1e2f129`][1e2f129] (S10), después de [`e435402`][e435402] (S8) y [`90b4bcd`][90b4bcd] (S9). Los atributos del lote, el endpoint de productos, los umbrales por índice y el streaming no tienen tests |
| DoD más estricto: no pasar tareas al sprint siguiente sin criterios verificados, con revisión antes de cerrar | Parcial | Desde [`4397d77`][4397d77] (PR #1) el trabajo entra por Pull Request. Pero [`fc9ebb2`][fc9ebb2] reúne trabajo de H6.1, H6.3, H7.1, H7.3, H7.4, H8.1 y H8.2 en un solo commit de 43 archivos directo a `main`, sin PR; 48 tests nuevos no se agregaron al CI. La revisión por al menos 2 integrantes que pide `docs/5_Plan_de_Releases.md` no es verificable sin acceso a los PRs: a confirmar |
| Test E2E en CI | No cumplido | `ci.yml` del corte no corre `test_ciclo_completo_encolar_y_esperar` ni otro E2E. Pasa a: a definir |
| Cobertura completa | No cumplido | Sin medición de cobertura (sin `pytest-cov`). Pasa a: a definir |
| Pendiente R1 → R2: motor de diagnóstico | Cumplido | `app/diagnostico/` ([`fc9ebb2`][fc9ebb2], [`e435402`][e435402], [`f6644f1`][f6644f1]) |
| Pendiente R1 → R2: severidad, zonificación y ahorro de insumos | Parcial | Severidad y zonificación cumplidas; ahorro no implementado (tarjeta eliminada en [`1200a87`][1200a87]). Pasa a: a definir |
| Pendiente R1 → R2: roles y permisos | No cumplido | Sin cambios en `app/auth/`. Pasa a: a definir (no figura en las presentaciones de R3 ni de R4) |
| Pendiente R1 → R2: testing E2E y cobertura | No cumplido | Ver las dos filas de compromisos anteriores. Pasa a: a definir |
| Pendiente R1 → zonas en PostGIS (destino "a definir" en R1) | No cumplido | Sin cambios de modelo para zonas. Pasa a: a definir |

[0ef03b8]: https://github.com/universoparalelo/Agronexo/commit/0ef03b8
[1200a87]: https://github.com/universoparalelo/Agronexo/commit/1200a87
[1e2f129]: https://github.com/universoparalelo/Agronexo/commit/1e2f129
[1fec6f1]: https://github.com/universoparalelo/Agronexo/commit/1fec6f1
[22d4ee9]: https://github.com/universoparalelo/Agronexo/commit/22d4ee9
[2b0566e]: https://github.com/universoparalelo/Agronexo/commit/2b0566e
[34a6d06]: https://github.com/universoparalelo/Agronexo/commit/34a6d06
[36dc4b9]: https://github.com/universoparalelo/Agronexo/commit/36dc4b9
[4397d77]: https://github.com/universoparalelo/Agronexo/commit/4397d77
[47994a4]: https://github.com/universoparalelo/Agronexo/commit/47994a4
[4cb94bf]: https://github.com/universoparalelo/Agronexo/commit/4cb94bf
[537f671]: https://github.com/universoparalelo/Agronexo/commit/537f671
[5d28b86]: https://github.com/universoparalelo/Agronexo/commit/5d28b86
[706bc15]: https://github.com/universoparalelo/Agronexo/commit/706bc15
[7e7182d]: https://github.com/universoparalelo/Agronexo/commit/7e7182d
[8644be4]: https://github.com/universoparalelo/Agronexo/commit/8644be4
[89682e1]: https://github.com/universoparalelo/Agronexo/commit/89682e1
[8cd96b6]: https://github.com/universoparalelo/Agronexo/commit/8cd96b6
[90b4bcd]: https://github.com/universoparalelo/Agronexo/commit/90b4bcd
[9e072d6]: https://github.com/universoparalelo/Agronexo/commit/9e072d6
[a2d6596]: https://github.com/universoparalelo/Agronexo/commit/a2d6596
[a2ec304]: https://github.com/universoparalelo/Agronexo/commit/a2ec304
[b7dae3a]: https://github.com/universoparalelo/Agronexo/commit/b7dae3a
[c5e41ae]: https://github.com/universoparalelo/Agronexo/commit/c5e41ae
[cc5e82a]: https://github.com/universoparalelo/Agronexo/commit/cc5e82a
[d842ed3]: https://github.com/universoparalelo/Agronexo/commit/d842ed3
[e435402]: https://github.com/universoparalelo/Agronexo/commit/e435402
[eb5d514]: https://github.com/universoparalelo/Agronexo/commit/eb5d514
[ecc6fa3]: https://github.com/universoparalelo/Agronexo/commit/ecc6fa3
[f35e422]: https://github.com/universoparalelo/Agronexo/commit/f35e422
[f6644f1]: https://github.com/universoparalelo/Agronexo/commit/f6644f1
[faec54c]: https://github.com/universoparalelo/Agronexo/commit/faec54c
[fc9ebb2]: https://github.com/universoparalelo/Agronexo/commit/fc9ebb2
[fde502f]: https://github.com/universoparalelo/Agronexo/commit/fde502f
