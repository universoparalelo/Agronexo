"""
Métricas de forma y clasificación de patrón espacial de zonas de
diagnóstico.

Vive en app/diagnostico/ (no en workers/gis/) porque corre DENTRO del
proceso FastAPI, no del worker Celery: el diagnóstico es una evaluación
liviana sobre polígonos ya vectorizados, no reprocesa el GeoTIFF. FastAPI
no tiene GeoPandas/GDAL instalados a propósito (docker/requirements.api.txt
solo trae Shapely, justamente para no cargar el proceso web con las
dependencias GIS pesadas reservadas al worker).

Para medir área/perímetro/distancias en metros a partir de geometrías en
EPSG:4326 (grados) sin depender de pyproj/GDAL, se usa una proyección
equirectangular local centrada en el lote (pura matemática, sin
dependencias nuevas) — error < 0.1% a la escala de un lote agrícola
(unos pocos km de extensión), más que suficiente para una heurística de
clasificación con umbrales ya pensados como ajustables.

Heurística v1 — la separación entre categorías, en particular
"por_sectores" vs "difuso_homogeneo", es inherentemente aproximada: el
paso de umbralización ya convirtió cualquier gradiente continuo en un
borde duro, así que no hay forma de recuperar si la transición original
era abrupta o gradual solo mirando el polígono resultante.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from shapely.geometry.base import BaseGeometry
from shapely.ops import transform as shapely_transform

# Patrón: circular
CIRCULARIDAD_MIN_CIRCULAR = 0.65   # 4πA/P² — 1.0 = círculo perfecto

# Patrón: lineal
ELONGACION_MIN_LINEAL = 3.0        # eje_mayor / eje_menor del minimum_rotated_rectangle

# Patrón: bordes_lote
BUFFER_BORDE_LOTE_M = 30.0         # franja perimetral del lote considerada "borde"
FRACCION_BORDE_MIN = 0.5           # % del perímetro de la zona que cae dentro de esa franja

# Patrón: por_sectores
AREA_RELATIVA_SECTOR_MIN = 0.15    # la zona individual ocupa >= 15% del área del lote
RECTANGULARIDAD_MIN_SECTOR = 0.70  # area_zona / area(minimum_rotated_rectangle) — "llena" su rectángulo

# Patrón: focos_aislados
AREA_MAX_FOCO_M2 = 2000.0          # cada foco es individualmente chico
N_ZONAS_FOCOS_AISLADOS_MIN = 3     # y hay varios de la misma clase dispersos

# Patrón: difuso_homogeneo
AREA_RELATIVA_DIFUSO_MIN = 0.30    # la CLASE completa (todas sus zonas) cubre >= 30% del lote
N_ZONAS_DIFUSO_MAX = 2             # en pocas manchas grandes, no muchas chicas


@dataclass
class ZonaInput:
    id: int
    geometry: BaseGeometry  # EPSG:4326 (lon, lat en grados)
    clase: str
    area_ha: float


def _proyector_local(lon0: float, lat0: float):
    """Closure de reproyección equirectangular local centrada en (lon0, lat0)."""
    cos_lat0 = math.cos(math.radians(lat0))

    def _proyectar(x, y, z=None):
        return ((x - lon0) * 111_320.0 * cos_lat0, (y - lat0) * 110_540.0)

    return _proyectar


def proyectar_a_metros_locales(geom_4326: BaseGeometry, lon0: float, lat0: float) -> BaseGeometry:
    """Reproyecta una geometría EPSG:4326 a metros locales (ver docstring del módulo)."""
    return shapely_transform(_proyector_local(lon0, lat0), geom_4326)


def _circularidad(area_m2: float, perimetro_m: float) -> float:
    """4πA/P². 1.0 = círculo perfecto. Capado a 1.0 por errores de simplificación."""
    if perimetro_m <= 0:
        return 0.0
    return min(1.0, (4 * math.pi * area_m2) / (perimetro_m ** 2))


def _elongacion_y_rectangularidad(geom_local: BaseGeometry, area_m2: float) -> tuple[float, float]:
    """
    elongacion: lado mayor / lado menor del rectángulo mínimo que contiene la
    geometría (alto → forma alargada, típico de franjas de maquinaria).
    rectangularidad: qué tan "lleno" está ese rectángulo (alto → forma
    geométrica/rectilínea, típico de un sector de manejo real).
    """
    mrr = geom_local.minimum_rotated_rectangle
    coords = list(mrr.exterior.coords)
    if len(coords) < 4:
        return 1.0, 1.0
    lado_a = ((coords[0][0] - coords[1][0]) ** 2 + (coords[0][1] - coords[1][1]) ** 2) ** 0.5
    lado_b = ((coords[1][0] - coords[2][0]) ** 2 + (coords[1][1] - coords[2][1]) ** 2) ** 0.5
    mayor, menor = max(lado_a, lado_b), max(min(lado_a, lado_b), 1e-6)
    elongacion = mayor / menor
    rectangularidad = area_m2 / max(mrr.area, 1e-6)
    return elongacion, rectangularidad


def _distancia_y_fraccion_borde(
    geom_local: BaseGeometry, lote_boundary_local: BaseGeometry | None
) -> tuple[float, float]:
    """
    distancia: separación mínima entre la zona y el borde del lote (0 = toca el borde).
    fraccion: qué parte del perímetro de la zona cae dentro de la franja perimetral
    del lote — distingue una zona que apenas roza el borde de una que corre pegada a él.
    """
    if lote_boundary_local is None:
        return float("inf"), 0.0
    distancia = geom_local.distance(lote_boundary_local)
    franja = lote_boundary_local.buffer(BUFFER_BORDE_LOTE_M)
    interseccion = geom_local.boundary.intersection(franja)
    fraccion = interseccion.length / max(geom_local.length, 1e-6)
    return distancia, fraccion


def clasificar_patron_zona(
    geom_local: BaseGeometry,
    area_m2: float,
    lote_boundary_local: BaseGeometry | None,
    lote_area_m2: float,
    n_zonas_misma_clase: int,
    area_total_clase_relativa: float,
) -> str:
    """
    Clasifica UNA zona (geometría ya en metros locales) en una de 7
    categorías de patrón espacial. Orden de evaluación fijo — la primera
    condición que matchea gana (igual criterio que la cascada de reglas
    del motor de diagnóstico).
    """
    circularidad = _circularidad(area_m2, geom_local.length)
    elongacion, rectangularidad = _elongacion_y_rectangularidad(geom_local, area_m2)
    distancia_borde, fraccion_borde = _distancia_y_fraccion_borde(geom_local, lote_boundary_local)
    area_relativa = area_m2 / max(lote_area_m2, 1e-6)

    if distancia_borde <= BUFFER_BORDE_LOTE_M and fraccion_borde >= FRACCION_BORDE_MIN:
        return "bordes_lote"
    if area_relativa >= AREA_RELATIVA_SECTOR_MIN and rectangularidad >= RECTANGULARIDAD_MIN_SECTOR:
        return "por_sectores"
    if circularidad >= CIRCULARIDAD_MIN_CIRCULAR and elongacion < ELONGACION_MIN_LINEAL:
        return "circular"
    if elongacion >= ELONGACION_MIN_LINEAL:
        return "lineal"
    if area_m2 <= AREA_MAX_FOCO_M2 and n_zonas_misma_clase >= N_ZONAS_FOCOS_AISLADOS_MIN:
        return "focos_aislados"
    if area_total_clase_relativa >= AREA_RELATIVA_DIFUSO_MIN and n_zonas_misma_clase <= N_ZONAS_DIFUSO_MAX:
        return "difuso_homogeneo"
    return "manchas_irregulares"  # catch-all: sin forma definida, no encaja en las otras 6


def clasificar_patrones(
    zonas: list[ZonaInput], lote_geom_4326: BaseGeometry | None
) -> dict[int, str]:
    """
    Devuelve {zona.id: patron_espacial} para la lista de zonas dada (todas
    en EPSG:4326, tal como las produce workers/gis/zonas.py). Agrupa por
    'clase' para calcular cuántas zonas de esa misma clase existen y qué
    fracción del lote cubren en conjunto.

    Si lote_geom_4326 es None (lote sin límites cargados), usa el
    centroide promedio de las zonas como referencia de proyección y la
    suma de sus áreas como área de referencia — ninguna zona podrá
    clasificarse como 'bordes_lote' en ese caso (best-effort).
    """
    if not zonas:
        return {}

    if lote_geom_4326 is not None:
        lon0, lat0 = lote_geom_4326.centroid.x, lote_geom_4326.centroid.y
    else:
        lon0 = sum(z.geometry.centroid.x for z in zonas) / len(zonas)
        lat0 = sum(z.geometry.centroid.y for z in zonas) / len(zonas)

    geoms_locales = {z.id: proyectar_a_metros_locales(z.geometry, lon0, lat0) for z in zonas}
    areas_m2 = {zid: g.area for zid, g in geoms_locales.items()}

    if lote_geom_4326 is not None:
        lote_local = proyectar_a_metros_locales(lote_geom_4326, lon0, lat0)
        lote_boundary_local = lote_local.boundary
        lote_area_m2 = lote_local.area
    else:
        lote_boundary_local = None
        lote_area_m2 = sum(areas_m2.values())

    por_clase: dict[str, list[int]] = {}
    for z in zonas:
        por_clase.setdefault(z.clase, []).append(z.id)

    resultado: dict[int, str] = {}
    for z in zonas:
        ids_clase = por_clase[z.clase]
        n_zonas = len(ids_clase)
        area_total_relativa = sum(areas_m2[i] for i in ids_clase) / max(lote_area_m2, 1e-6)
        resultado[z.id] = clasificar_patron_zona(
            geoms_locales[z.id], areas_m2[z.id], lote_boundary_local, lote_area_m2,
            n_zonas, area_total_relativa,
        )
    return resultado
