# Plantilla de documentación de release — AgroNexo

> **Cómo usar esta plantilla.** Es el formato extraído de la documentación de la Release 1 (v1.0.0). Copiarla a `docs/releases/release-vX.Y.Z.md` y reemplazar todo lo que está entre `[corchetes]`.
> Respetar secciones, orden y columnas de las tablas. Los bloques `<!-- GUÍA: ... -->` son instrucciones para quien redacta: borrarlos en el documento final.
> Lo que no se pueda verificar en el repositorio o en las fuentes se escribe **"a confirmar"**. Nunca se inventa.
> Los elementos marcados **[agregado desde R2]** no estaban en la documentación de R1; se incorporan desde la Release 2.

---

# AgroNexo — Release [N] (v[X.Y.Z])

**[Hito de la release en una frase corta. Ej. R1: "Clasificación visual del lote"]**

Proyecto Final de Ingeniería en Sistemas · UTN FRRe · Equipo 6
Profesores: Acuña, César J · Mendez, Graciela L

---

## Ficha de release

| Campo | Valor |
|---|---|
| Versión | v[X.Y.Z] (tag `v[X.Y.Z]`, commit de corte `[hash]` del [fecha]) |
| Estado | [Completa / En curso] — Demo [fecha] |
| Período | [fecha de inicio] — [fecha de fin] ([N] semanas) |
| Equipo | [Nombres] |
| Metodología | Scrum — sprints de [N] semana(s) |
| Entorno | [Local con Docker Compose. Sin staging ni producción] |
| Repositorio | universoparalelo/Agronexo (privado) |
| Hito de entrega | [Qué puede hacer el usuario al final de la release, en una frase] |

<!-- GUÍA: si no existe el tag, escribir "sin tag; propuesto v[X.Y.Z] sobre [hash]". -->

## Equipo y roles

| Integrante | Rol en la release | Área |
|---|---|---|
| [Nombre] | [Scrum Master / Release Manager, Desarrollo, QA, Investigación GIS...] | [Frontend · API, Backend · GIS · DevOps...] |

<!-- GUÍA: los roles se reutilizan de la release anterior; si cambiaron y no hay fuente, "a confirmar". No inferir roles por el autor de los commits. -->

---

## 1. Planificación de la Release

### 1.1 Objetivo y alcance

[Párrafo de 2 a 4 oraciones: qué se quería construir y cómo lo ve el usuario al final.]

**Incluido en el alcance:**

- **[Capa o tema]:** [Qué se incluyó, con nombres concretos: servicios, endpoints, tablas, índices, pantallas.]
- **[Capa o tema]:** [...]

**Queda fuera del alcance de esta release:** [lista breve de lo que se planificó o se esperaba pero no entra].

<!-- GUÍA: nivel de detalle de R1 en "Incluido": "Docker Compose con 6 servicios (db, redis, minio, api, worker, frontend), FastAPI + SQLAlchemy async + PostGIS, migraciones Alembic 0001 → 0011 y CI en GitHub Actions con 3 jobs." Un ítem por capa (infraestructura, autenticación, datos, pipeline, visualización). No copiar este ejemplo. -->

### 1.2 Sprints que la componen

| S | Título | Entregable demostrable | Fecha | Historias | RF/RNF |
|---|---|---|---|---|---|
| S[n] | [Título del sprint] | [Qué se puede mostrar al terminar] | [dd–dd mmm] | H[n].1–H[n].[k] | [RFxx-01/02, RNFxx...] |

<!-- GUÍA: las fechas de los sprints salen de la presentación o del plan, NO de las fechas de los commits (no son confiables para ubicar sprints). Los RF/RNF salen de docs/2_ERS.md y docs/5_Plan_de_Releases.md. -->

### 1.3 Duración y fechas clave

| Evento | Fecha |
|---|---|
| Inicio de la release [N] | [fecha] |
| Fin Sprint [n] — [título corto] | [fecha] |
| Demo y cierre Release [N] | [fecha] |
| [Receso u otro evento que afectó el calendario] | [fecha] |

### 1.4 Definición de Terminado (DoD)

Una tarea se considera terminada cuando cumple todos los criterios siguientes:

- [Criterio verificable. Ej. "La funcionalidad es demostrable de punta a punta en el entorno local con `docker compose up`."]
- [Criterio...]

Criterios de cierre de la release, evaluados contra el commit de corte: [X] cumple, [Y] parciales y [Z] no cumplen.

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| 1 | [Criterio de cierre] | [Cumple / Parcial / No cumple / A confirmar] | [Qué se verificó, con commit, PR o archivo] |

<!-- GUÍA: si la presentación no define criterios de cierre, derivarlos del objetivo y de los artefactos del último sprint, y decirlo explícitamente en el texto. -->

---

## 2. Sprint [S] — [Título]

| Sprint | Título | Fechas | Historias | RF/RNF |
|---|---|---|---|---|
| S[n] | [Título] | [dd–dd mmm aaaa] | H[n].1–H[n].[k] | [RF/RNF] |

### Objetivo

[1 a 3 oraciones: qué se proponía el sprint y por qué en ese momento.]

### Tareas realizadas

#### [Tema de la tarea] (H[n].[m])

[Descripción técnica concreta: qué se hizo, con qué herramientas, con qué parámetros, y por qué se decidió así. Incluir nombres reales de endpoints, tablas, migraciones, tareas de Celery, archivos y componentes.]

- [Detalle en viñeta cuando sean ítems paralelos.]

| [Columna comparable] | [Columna] |
|---|---|
| [Dato] | [Dato] |

**Hallazgo clave:** [Descubrimiento que cambió una decisión o dejó una limitación documentada. Opcional, solo si existe.]

#### [Otro tema] (H[n].[m], H[n].[p])

[...]

<!-- GUÍA: una subsección por tarea, titulada "Tema (H#.#):" con el ID de historia. Usar tablas cuando los datos son comparables (índices, capas, endpoints, patrones) y viñetas para decisiones o flujos. Si hay diagrama de arquitectura, incluirlo como imagen o Mermaid con una explicación breve. Nivel de detalle de R1: "El área del lote se calcula en PostGIS reproyectando a EPSG:32721 (metros) para mayor precisión." No copiar este ejemplo. -->

### Estado de las historias **[agregado desde R2]**

| Historia | Estado | Evidencia |
|---|---|---|
| H[n].[m] — [Título] | [Completa / Parcial / No implementada / A confirmar] | [Hash corto con link, PR (#N) o ruta de archivo. Si es Parcial, qué falta] |

<!-- GUÍA: Completa = todo lo que dicen el enunciado de la historia y los artefactos de la presentación está en el código al corte. Parcial = falta parte (decir qué). No implementada = sin evidencia. A confirmar = no verificable en el repositorio. -->

### Resultado

[2 a 4 oraciones: qué quedó funcionando al terminar el sprint, qué quedó abierto y qué se descubrió. Lo que la presentación declara en sus "Conclusiones" solo entra si el código lo respalda; si no, escribir "según la presentación".]

<!-- GUÍA: repetir esta sección completa por cada sprint, numerándolas de forma consecutiva (R1: secciones 2 a 6 para los Sprints 1 a 5). Los sprints de investigación documentan sus artefactos con la ruta en el repo; si no están versionados, "a confirmar". -->

---

## [N+1]. Calidad y estado al cierre

[Párrafo de apertura con el panorama: cuántos tests automatizados había al corte, cuántos jobs de CI estaban en verde y la causa de cualquier falla.]

### Pruebas automatizadas

| Tipo | Herramienta | Tests | Resultado en el corte |
|---|---|---|---|
| Unitarias | [pytest] | [N ([detalle por archivo o tema])] | [Job en verde / en rojo / a confirmar] |
| Integración | [pytest + TestClient] | [N] | [...] |
| End-to-end | [pytest] | [N] | [Pasa solo en local / corre en CI / a confirmar] |
| Frontend | — | [0] | [Qué verifica el job de CI, si existe] |
| Rendimiento y seguridad | — | — | [No realizados / qué se hizo] |

[Nota sobre cobertura: si se midió, el valor; si no, "La cobertura no se midió". Si la bitácora y el código difieren en el conteo de tests, explicar la diferencia.]

<!-- GUÍA: los tests se cuentan leyendo el código (funciones `def test_`) sobre un snapshot del commit de corte, sin ejecutarlos. Si no hay acceso al CI, los resultados van como "a confirmar". -->

### Verificaciones manuales

| Fecha | Verificación | Resultado |
|---|---|---|
| [dd mmm] | [Qué se probó y cómo] | [Resultado concreto, con valores si los hay] |

<!-- GUÍA: solo las verificaciones registradas en bitácoras o documentos. No inventar. -->

### Errores corregidos durante el desarrollo

[Aclaración: si alguno afectó o no a una versión publicada.] Los más relevantes:

- [Error: causa y corrección. Commit `[hash]`.]

### Despliegue de la demo

[Pasos reales según el README en el commit de corte: clonar y hacer checkout del tag, crear `.env` desde `.env.example`, levantar con `docker compose up -d --build`, correr las migraciones, y cómo verificar (`GET /api/v1/health`, `GET /api/v1/health/db`, Swagger en `/api/docs`). Indicar qué cambió respecto de la release anterior: migraciones, seeds, variables nuevas.]

<!-- GUÍA: nunca copiar valores de secretos ni credenciales. Solo nombres de variables. -->

---

## [N+2]. Deuda técnica y trabajo pendiente

[Apertura: qué ítems estaban planificados y no se completaron, y aclaración de si son funcionalidades nuevas o correcciones.]

### Defectos y riesgos conocidos

| Ítem | Descripción | Impacto | Estado |
|---|---|---|---|
| [Nombre corto] | [Qué pasa, por qué y, si existe, workaround] | [Alto / Medio / Bajo, con aclaración entre paréntesis: seguridad, reproducibilidad, uso real] | [Abierto / Corregido en R[n] (`hash`) / Planificado en R[n]] |

### Funcionalidades pendientes

| Ítem | Descripción | Release destino |
|---|---|---|
| [Funcionalidad] | [Qué falta y de qué depende] | [Release N / A definir] |

### Deuda heredada de la release anterior **[agregado desde R2]**

| Ítem | Estado al corte de esta release | Estado actual (origin/main) | Evidencia |
|---|---|---|---|
| [Ítem de la sección de deuda de la release anterior] | [Abierto / Corregido / Parcial / A confirmar] | [Abierto / Corregido / Parcial / A confirmar] | [Hash, PR o archivo] |

<!-- GUÍA: incluir TODOS los ítems de la sección de deuda de la release anterior (defectos y funcionalidades pendientes). Los dos estados pueden diferir: algo corregido después del corte de esta release figura como abierto "al corte" y corregido en "estado actual". -->

### Compromisos de mejora de la release anterior **[agregado desde R2]**

| Compromiso | Estado | Evidencia |
|---|---|---|
| [Acción de mejora acordada en las retrospectivas anteriores] | [Cumplido / Parcial / No cumplido / A confirmar] | [Hash, PR o archivo] |

---

## Convenciones de estilo

<!-- GUÍA (borrar esta sección en el documento final):
- Español formal e impersonal ("se implementó", "se definió"). Sin emojis ni adjetivos de marketing.
- Datos concretos: rutas, endpoints, tablas, parámetros, versiones, conteos. Nada genérico.
- Tablas para lo comparable; viñetas para decisiones y flujos; párrafos cortos.
- Cada afirmación de estado cita evidencia: hash corto con link (https://github.com/universoparalelo/Agronexo/commit/<hash>), PR (#N) o ruta de archivo.
- Vocabulario de estado de historias: Completa / Parcial / No implementada / A confirmar. Vocabulario de criterios de cierre: Cumple / Parcial / No cumple / A confirmar.
- Si el código contradice a una presentación o a una bitácora, manda el código.
- Todo el estado técnico es el del commit de corte (leído con `git show <corte>:ruta`), no el del árbol de trabajo.
-->
