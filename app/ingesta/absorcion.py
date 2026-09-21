"""
Versión "para mirar" de un resultado de índice: lo que tiene datos pero no quedó
con zona se absorbe en la zona vecina.

El worker descarta todo polígono menor a 1 ha (workers/gis/zonas.py) para no
llenar el mapa de ruido, y eso deja parches en blanco dentro del lote. Para el
diagnóstico esas zonas no importan, pero en un mapa de vistazo se ven como "datos
que faltan". Acá se rellenan sin tocar el resultado guardado: el diagnóstico, la
tabla y las exportaciones siguen trabajando sobre las zonas originales.

Qué NO se rellena nunca: la parte "sin datos" real, que el worker registra al
procesar en el miembro `sin_datos` (píxeles sin dato + lo que el GeoTIFF no
cubre, ver workers/gis/sin_datos.py). Todo lo demás —sea del tamaño que sea—
tiene datos y se combina con las celdas que lo rodean. Para análisis viejos que
no registraron `sin_datos` no se puede saber qué es qué: se rellenan solo los
huecos chicos (AREA_MAX_HUECO_M2), por prudencia.
"""

from __future__ import annotations

from collections import defaultdict

from shapely.geometry import mapping, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union
from shapely.validation import make_valid

from app.diagnostico.forma import proyectar_a_metros_locales

# Solo para análisis que no registraron `sin_datos`: un hueco mayor a esto no se
# rellena (podría ser información real que falta). Las zonas descartadas miden
# < 1 ha, pero varias vecinas descartadas forman un solo hueco, de ahí el margen.
AREA_MAX_HUECO_M2 = 30_000.0

_TOL_GRADOS = 1e-6  # ≈ 0,1 m: tolerancia para "comparte borde" entre geometrías en 4326



def _poligonos(geom: BaseGeometry) -> list[BaseGeometry]:
    if geom.is_empty:
        return []
    if geom.geom_type == "Polygon":
        return [geom]
    if hasattr(geom, "geoms"):
        return [p for g in geom.geoms for p in _poligonos(g)]
    return []


def absorber_huecos(geojson: dict, limite_4326: BaseGeometry | None = None) -> dict:
    """
    Devuelve una copia del FeatureCollection con los huecos que tienen datos
    absorbidos por la zona con la que comparten más borde. `limite_4326` (el
    polígono del lote) define dónde buscar huecos; sin él se usa la envolvente
    convexa de las zonas. Los huecos que caen dentro de `sin_datos` no se tocan.
    """
    features = geojson.get("features") or []
    if not features:
        return geojson

    registrado = "sin_datos" in geojson
    sin_datos = make_valid(shape(geojson["sin_datos"])) if geojson.get("sin_datos") else None

    geoms = [make_valid(shape(f["geometry"])) for f in features]
    cobertura = unary_union(geoms)
    region = limite_4326 if limite_4326 is not None else cobertura.convex_hull
    if not region.is_valid:
        region = make_valid(region)

    lon0, lat0 = region.centroid.x, region.centroid.y
    asignadas: dict[int, list[BaseGeometry]] = defaultdict(list)

    huecos = region.difference(cobertura)
    if sin_datos is not None:
        huecos = huecos.difference(sin_datos)
    for hueco in _poligonos(huecos):
        if not registrado and proyectar_a_metros_locales(hueco, lon0, lat0).area > AREA_MAX_HUECO_M2:
            continue
        zona_vecina, borde_compartido = None, 0.0
        zona_cercana = hueco.buffer(_TOL_GRADOS)
        for i, geom in enumerate(geoms):
            if not zona_cercana.intersects(geom):
                continue
            largo = geom.boundary.intersection(zona_cercana).length
            if largo > borde_compartido:
                zona_vecina, borde_compartido = i, largo
        if zona_vecina is not None:
            asignadas[zona_vecina].append(hueco)

    salida = dict(geojson)
    salida["features"] = []
    for i, feature in enumerate(features):
        nueva = dict(feature)
        if i in asignadas:
            geom = make_valid(unary_union([geoms[i], *asignadas[i]]))
            nueva["geometry"] = mapping(geom)
            propiedades = dict(feature.get("properties") or {})
            propiedades["area_ha"] = round(proyectar_a_metros_locales(geom, lon0, lat0).area / 10_000, 4)
            nueva["properties"] = propiedades
        salida["features"].append(nueva)
    return salida

