# AgroNexo — Release 4.1 (v4.1.0)

**Prescripción para maquinaria**

Proyecto Final de Ingeniería en Sistemas · UTN FRRe · Equipo 6
Profesores: Acuña, César J · Mendez, Graciela L

---

## Ficha de release

| Campo | Valor |
|---|---|
| Versión | v4.1.0 (sin tag; en desarrollo) |
| Estado | En curso — Demo a confirmar |
| Período | Inicio 27 de noviembre de 2026 — fin a confirmar |
| Equipo | Amilcar Aguirre, Matías Machado, Celeste Martín Rodich, Denise Pujalte, Zaira Rosin |
| Metodología | Scrum — sprints a confirmar |
| Entorno | Aplicación de escritorio para Windows (instalador de Electron) y Docker Compose para desarrollo y CI |
| Repositorio | universoparalelo/Agronexo (privado) |
| Hito de entrega | El usuario descarga, por vuelo, un paquete de prescripción que una pulverizadora autopropulsada (mosquito) o un dron pulverizador pueden cargar: producto, dosis por zona y recorrido sugerido |

## Equipo y roles

| Integrante | Rol en la release | Área |
|---|---|---|
| Amilcar Aguirre | A confirmar | A confirmar |
| Matías Machado | A confirmar | A confirmar |
| Celeste Martín Rodich | A confirmar | A confirmar |
| Denise Pujalte | A confirmar | A confirmar |
| Zaira Rosin | A confirmar | A confirmar |

---

## 1. Planificación de la Release

### 1.1 Objetivo y alcance

La cátedra pidió un archivo de salida que una máquina de aplicación (dron o mosquito) pueda usar para fumigar, con los productos, sus cantidades y el recorrido. Hasta v4.0.0 la orden de trabajo calculaba producto y dosis por unidad de manejo solo como PDF, y el Shapefile exportado contenía las zonas del diagnóstico sin dosis. Esta release convierte la orden de trabajo en archivos que lee la maquinaria y deja una verificación automatizada que no depende de tener una máquina real.

**Incluido en el alcance:**

- **API:** `GET /api/v1/lotes/{lote_id}/vuelos/{vuelo_id}/prescripcion?maquina=dron|mosquito[&ancho_labor_m=&margen_m=]`, que devuelve un `.zip`. Módulo `app/prescripcion/`.
- **Formatos:** un mapa de prescripción por producto en Shapefile, `TASKDATA/TASKDATA.XML` (ISO 11783-10 v3, una tarea por producto), recorrido sugerido en GeoJSON y KML, `resumen.json` y `LEEME.txt`.
- **Frontend:** botón "Prescripción para maquinaria" con selector de máquina en el resumen del vuelo (`ResumenVuelo.jsx`). El botón anterior pasa a llamarse "Zonas (SHP)".
- **Pruebas:** `tests/test_prescripcion.py` (21 tests puros) y `tests/test_prescripcion_api.py` (8 tests del endpoint), agregados al job `test-api` del CI.

**Queda fuera del alcance de esta release:** la prueba en una máquina o monitor real (no se dispone de equipo), la prescripción ISO-XML en grilla (formato GRD binario) y el envío directo a la máquina o a la nube del fabricante.

### 1.2 Sprints que la componen

| S | Título | Entregable demostrable | Fecha | Historias | RF/RNF |
|---|---|---|---|---|---|
| A confirmar | Prescripción para maquinaria | Descarga del paquete de prescripción desde el resumen del vuelo | A confirmar | A confirmar | RFSA-02, RNF-26 |

### 1.3 Duración y fechas clave

| Evento | Fecha |
|---|---|
| Inicio de la release 4.1 | 27 de noviembre de 2026 |
| Demo y cierre Release 4.1 | A confirmar |

### 1.4 Definición de Terminado (DoD)

Se mantiene la de la Release 4 (`docs/releases/release-v4.0.0.md`, sección 1.4). Los criterios de cierre se evalúan al cortar la release.

---

## 2. Sprint — Prescripción para maquinaria

| Sprint | Título | Fechas | Historias | RF/RNF |
|---|---|---|---|---|
| A confirmar | Prescripción para maquinaria | Desde 27 nov 2026 | A confirmar | RFSA-02, RNF-26 |

### Objetivo

Cerrar el ciclo diagnóstico → receta → máquina: que la dosis por unidad de manejo de la orden de trabajo llegue a la máquina como un archivo estándar, y demostrar que es correcto sin tener la máquina.

### Tareas realizadas

#### Paquete de prescripción para maquinaria (RFSA-02)
**Fecha:** 2026-11-27
**Rama:** `feat/prescripcion-maquinaria` (commit `6aa5971`)

Se agregó el módulo `app/prescripcion/`, puro salvo el router, con cinco piezas:

| Archivo | Qué hace |
|---|---|
| `maquinas.py` | Perfiles de máquina por defecto (ancho de labor, margen, caldo, tanque) |
| `mapa.py` | Cruza la geometría de las unidades de manejo con producto y dosis de `generar_orden_trabajo()`; agrega el margen y recorta al límite del lote |
| `ruta.py` | Recorrido en pasadas paralelas e ida y vuelta sobre el lado más largo del lote, y `simular_cobertura()` |
| `isoxml.py` | `TASKDATA.XML` con zonas de tratamiento poligonales (TZN + PLN) y `validar_taskdata()` |
| `paquete.py` | Shapefile por producto, GeoJSON y KML del recorrido, `resumen.json`, `LEEME.txt` y el `.zip` |

| Parámetro por defecto | Dron | Mosquito |
|---|---|---|
| Ancho de labor | 7 m | 28 m |
| Margen alrededor de cada zona | 3 m | 5 m |
| Caldo | 15 L/ha | 80 L/ha |
| Tanque | 40 L | 3000 L |
| Recorrido | Solo pasadas con aplicación | Lote completo, barra abierta o cerrada |

**Decisiones tomadas:**
- Un mapa por producto (decisión del equipo): la máquina carga un producto por tanque. En ISO-XML es una tarea (TSK) por producto dentro del mismo `TASKDATA.XML`.
- Producto y dosis salen de `generar_orden_trabajo()` y no de un cálculo propio, para que el PDF de la orden y el mapa no puedan dar cantidades distintas. Las unidades sin producto o sin dosis quedan fuera de los mapas y se listan en `resumen.json` y `LEEME.txt`.
- Margen de aplicación según `docs/Arquitectura.md` (3 a 7 m para equipos terrestres). Cuando dos zonas del mismo producto se superponen por el margen, la de mayor dosis se queda con la superposición. Las esquinas del margen son en ángulo (`join_style="mitre"`), no redondeadas, para no generar decenas de vértices por esquina.
- La barra se abre en una pasada cuando cualquier parte de su ancho toca una zona, no solo la línea central: una franja angosta entre dos pasadas no queda sin aplicar, a costa de sobreaplicación en los bordes, que la simulación mide.
- ISO-XML versión 3 con zonas poligonales y no en grilla: lo leen monitores viejos y nuevos y se escribe con `xml.etree`. Escalado de dosis verificado en la base de DDIs de isobus.net: DDI 1 (mm³/m², resolución 0,01; 1 L/ha = 10000) y DDI 6 (mg/m², resolución 1; 1 kg/ha = 100). Si el redondeo al entero del DDI cambia la dosis más de 1 %, se advierte.
- En el Shapefile el resto del lote va como polígono explícito con dosis 0, porque algunos monitores aplican fuera de los polígonos la dosis por defecto que tenga cargada el operador.
- Sin dependencias nuevas (pyshp, Shapely y la librería estándar): no hay que tocar `escritorio/empaquetado/requirements-empaquetado.txt`, y funciona sin internet en la app instalada.

**Verificación sin máquina real** (`tests/test_prescripcion.py`):
- Sin margen, la cantidad por producto del mapa coincide con la orden de trabajo, dentro del redondeo a 3 decimales que hace la orden.
- La simulación del recorrido cubre al menos el 99,9 % de las zonas con los dos perfiles, incluida una franja de 2 m entre dos pasadas.
- `TASKDATA.XML` pasa `validar_taskdata()` y lleva las dosis escaladas (0,2 L/ha → 2000; 0,3 kg/ha → 30), las coordenadas y los huecos de las zonas.
- El Shapefile se vuelve a leer con pyshp: zonas más resto cubren el lote y la suma de cantidades coincide con el mapa.

---

## 3. Calidad y estado al cierre

A completar al cortar la release.

### Pruebas automatizadas

| Tipo | Herramienta | Tests | Resultado |
|---|---|---|---|
| Unitarias | pytest | 21 (`tests/test_prescripcion.py`) | Pasan en el contenedor `api` (27 nov 2026) |
| Integración | pytest + TestClient | 8 (`tests/test_prescripcion_api.py`) | Pasan en el contenedor `api` (27 nov 2026) |
| Frontend | Vitest + build | 37 existentes, sin tests nuevos | Pasan; build sin errores |

### Verificaciones manuales

| Fecha | Verificación | Resultado |
|---|---|---|
| 27 nov | Paquete de ejemplo (lote de 8 ha, 2 productos) para dron y mosquito | Cobertura simulada 100 %; cantidades del mapa con margen mayores que las de la orden, como se espera |
| A confirmar | Abrir Shapefile y KML en QGIS / Google Earth y `TASKDATA.XML` en un visor ISO-XML | A confirmar |

---

## 4. Deuda técnica y trabajo pendiente

### Defectos y riesgos conocidos

| Ítem | Descripción | Impacto | Estado |
|---|---|---|---|
| Sin prueba en equipo real | Los archivos siguen los formatos estándar, pero cada marca de monitor o dron puede pedir ajustes que solo se confirman en la máquina | Medio (uso real) | Abierto |
| Versión de la API desactualizada | `app/main.py` declara `version="1.0.0"` y ese valor se escribe en `TASKDATA.XML` y en `resumen.json` | Bajo (trazabilidad) | Abierto |
| Simulación con barra completa | La simulación supone la barra entera abierta o cerrada; con corte por secciones la sobreaplicación real es menor que la informada | Bajo (informe) | Abierto, documentado en `LEEME.txt` |
| Perfiles de máquina genéricos | Ancho, caldo y tanque son valores típicos; solo ancho y margen se pueden cambiar por parámetro | Bajo | Abierto |

### Funcionalidades pendientes

| Ítem | Descripción | Release destino |
|---|---|---|
| ISO-XML en grilla | Prescripción en grilla (GRD) para monitores que no leen zonas poligonales | A definir |
| Validación contra el XSD oficial | `validar_taskdata()` es un control estructural, no el XSD de la norma | A definir |

### Deuda heredada de la release anterior

A completar al cortar la release, a partir de la sección 7 de `docs/releases/release-v4.0.0.md`. La fila "Exportación ISO-XML / integración con maquinaria" queda cubierta por esta release en la parte de exportación.
