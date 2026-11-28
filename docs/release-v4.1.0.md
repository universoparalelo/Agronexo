# Release v4.1.0 — Seguimiento

**Estado:** En desarrollo
**Rama principal:** `main`
**Inicio:** 2026-11-27

Release corta para la prescripción para maquinaria que pidió la cátedra: un archivo de salida que una pulverizadora autopropulsada (mosquito) o un dron pulverizador puedan usar para aplicar, con los productos, sus cantidades y el recorrido. Sprints e historias: a confirmar por el equipo.

La documentación formal de la release se escribe al cerrarla, en `docs/releases/release-v4.1.0.md`, a partir de `docs/releases/_TEMPLATE-release.md`.

---

## Prescripción para maquinaria

### Tareas completadas

#### Paquete de prescripción para maquinaria (RFSA-02, RNF-26)
**Fecha:** 2026-11-27
**Rama:** `feat/prescripcion-maquinaria` (commit `6aa5971`)

Hasta v4.0.0 la orden de trabajo calculaba producto y dosis por unidad de manejo solo como PDF, y el Shapefile exportado (`app/reportes/exportacion.py`) eran las zonas del diagnóstico sin dosis, aunque el botón del resumen del vuelo decía "Prescripción (SHP)". Se agregó `GET /api/v1/lotes/{lote_id}/vuelos/{vuelo_id}/prescripcion?maquina=dron|mosquito[&ancho_labor_m=&margen_m=]`, que devuelve un `.zip` con:

- un mapa de prescripción por producto en Shapefile (`<producto>/prescripcion.shp`, campo `dosis`; el resto del lote con dosis 0);
- `TASKDATA/TASKDATA.XML` (ISO 11783-10 v3, una tarea por producto, zonas de tratamiento poligonales);
- el recorrido sugerido en GeoJSON y KML (pasadas paralelas al lado más largo del lote, tramos de aplicación y de traslado);
- `resumen.json` (cantidades, recorrido, cargas de tanque y simulación de cobertura) y `LEEME.txt` (cómo usar cada archivo y limitaciones).

Código en `app/prescripcion/` (`maquinas.py`, `mapa.py`, `ruta.py`, `isoxml.py`, `paquete.py`, `router.py`). En el frontend, la página de resultados del vuelo (`PanelResultadoVuelo.jsx`, `/lotes/{id}/vuelos/{id}`) suma debajo de las pestañas la fila "Prescripción para maquinaria", con selector de máquina y descarga del `.zip`.

**Error encontrado — el botón no se veía en la app**
El primer intento puso el botón en `ResumenVuelo.jsx`, que se abre desde `VuelosCalendario.jsx`, pero ninguna página monta `VuelosCalendario` desde el PR #123. Se detectó en la prueba manual y se movió a `PanelResultadoVuelo.jsx`, al lado de "Generar orden de trabajo". `ResumenVuelo` y `VuelosCalendario` quedan como código sin uso.

| Parámetro por defecto | Dron | Mosquito |
|---|---|---|
| Ancho de labor | 7 m | 28 m |
| Margen alrededor de cada zona | 3 m | 5 m |
| Caldo / tanque | 15 L/ha / 40 L | 80 L/ha / 3000 L |
| Recorrido | Solo pasadas con aplicación | Lote completo, barra abierta o cerrada |

Verificación sin máquina real: `tests/test_prescripcion.py` (21 tests) y `tests/test_prescripcion_api.py` (8), los dos en el job `test-api` del CI. Pasan los 29 en el contenedor `api`. Comprueban que:
- sin margen, la cantidad por producto del mapa coincide con la orden de trabajo, dentro del redondeo a 3 decimales de la orden;
- la simulación del recorrido cubre al menos el 99,9 % de las zonas con los dos perfiles, incluida una franja de 2 m entre dos pasadas;
- `TASKDATA.XML` pasa `validar_taskdata()` y lleva las dosis escaladas, las coordenadas y los huecos;
- el Shapefile se vuelve a leer con pyshp y zonas más resto cubren el lote.

**Decisiones tomadas:**
- Un mapa por producto (decisión del equipo), porque la máquina carga un producto por tanque. En ISO-XML es una tarea (TSK) por producto en el mismo `TASKDATA.XML`.
- Producto y dosis salen de `generar_orden_trabajo()` y no de un cálculo propio, para que el PDF de la orden y el mapa no puedan dar cantidades distintas. Las unidades sin producto o sin dosis quedan fuera de los mapas y se listan en `resumen.json` y `LEEME.txt`.
- Margen según `docs/Arquitectura.md` (3 a 7 m para equipos terrestres). Si dos zonas del mismo producto se superponen por el margen, la de mayor dosis se queda con la superposición. Esquinas del margen en ángulo (`join_style="mitre"`): las redondeadas agregaban decenas de vértices por esquina.
- La barra se abre cuando cualquier parte del ancho de labor toca una zona, no solo la línea central, para que una franja angosta entre dos pasadas no quede sin aplicar. La sobreaplicación que esto genera se informa en la simulación.
- ISO-XML versión 3 con zonas poligonales, no en grilla: lo leen monitores viejos y nuevos y se escribe con `xml.etree`. Escalado verificado en la base de DDIs de isobus.net: DDI 1 (mm³/m², resolución 0,01; 1 L/ha = 10000) y DDI 6 (mg/m², resolución 1; 1 kg/ha = 100). Si el redondeo al entero cambia la dosis más de 1 %, se advierte.
- Sin dependencias nuevas (pyshp, Shapely y la librería estándar): no cambia `escritorio/empaquetado/requirements-empaquetado.txt` y funciona sin internet en la app instalada.

### Problemas abiertos

- **Sin prueba en una máquina real:** los archivos siguen los formatos estándar, pero cada marca de monitor o dron puede pedir ajustes que solo se confirman en el equipo. Falta al menos abrir el Shapefile y el KML en QGIS o Google Earth y `TASKDATA.XML` en un visor ISO-XML, y guardar las capturas.
- **Versión de la API desactualizada:** `app/main.py` declara `version="1.0.0"` y ese valor se escribe en `TASKDATA.XML` y en `resumen.json`.
- **Simulación con barra completa:** supone la barra entera abierta o cerrada; con corte por secciones la sobreaplicación real es menor que la informada (aclarado en `LEEME.txt`).
- **`validar_taskdata()` no es el XSD oficial** de la norma: es un control estructural. Pendiente también la prescripción ISO-XML en grilla para monitores que no lean zonas poligonales.
