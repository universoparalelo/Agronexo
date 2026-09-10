"""
Exportación de las zonas de diagnóstico a formatos estándar (GeoJSON,
Shapefile) para abrir en software GIS de escritorio (QGIS) o cargar en
maquinaria agrícola.

Deliberadamente con pyshp y no GDAL/Fiona: mismo criterio que
app/diagnostico/service.py y app/reportes/mapa.py — el proceso de FastAPI
no lleva GIS pesado a propósito (esas dependencias quedan reservadas al
worker). pyshp escribe Shapefile en Python puro, sin depender de GDAL a
nivel de sistema operativo.
"""

from __future__ import annotations

import io
import json
import zipfile

import shapefile
from shapely.geometry import shape
from shapely.geometry.polygon import orient

# WKT estilo ESRI (el que esperan los .prj de Shapefile) para EPSG:4326 —
# hardcodeado porque es fijo y conocido, no hace falta pyproj/GDAL para
# generarlo.
_WGS84_ESRI_WKT = (
    'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",'
    'SPHEROID["WGS_1984",6378137.0,298.257223563]],'
    'PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]'
)

# Nombres de campo DBF clásico: máximo 10 caracteres (por eso "causa" y no
# "causa_indice", "ndvi" y no "ndvi_promedio").
_CAMPOS = [
    ("zona_id", "N", 10, 0),
    ("clase", "C", 20, 0),
    ("severidad", "C", 20, 0),
    ("causa", "C", 40, 0),
    ("ndvi", "F", 10, 4),
    ("area_ha", "F", 12, 4),
    ("confianza", "C", 10, 0),
    ("regla_id", "C", 10, 0),
]


def generar_geojson_zonas(diagnostico: dict) -> bytes:
    """
    GeoJSON puro (type + features) para descarga — sin unidades_manejo ni
    metadata, que son extensiones propias del diagnóstico y no forman
    parte del contrato GeoJSON estándar que espera un software GIS externo.
    """
    coleccion = {
        "type": "FeatureCollection",
        "features": diagnostico.get("features", []),
    }
    return json.dumps(coleccion, ensure_ascii=False).encode("utf-8")


def generar_shapefile_zip(diagnostico: dict) -> bytes:
    """
    Empaqueta las zonas del diagnóstico como Shapefile
    (.shp/.shx/.dbf/.prj) dentro de un .zip, listo para cargar en QGIS o
    maquinaria agrícola.
    """
    shp_io, shx_io, dbf_io = io.BytesIO(), io.BytesIO(), io.BytesIO()
    writer = shapefile.Writer(shp=shp_io, shx=shx_io, dbf=dbf_io, shapeType=shapefile.POLYGON)
    for nombre, tipo, longitud, decimales in _CAMPOS:
        writer.field(nombre, tipo, longitud, decimales)

    for feat in diagnostico.get("features", []):
        props = feat.get("properties", {})
        geom = shape(feat["geometry"])
        writer.poly(_partes_shapefile(geom))
        writer.record(
            zona_id=props.get("zona_id"),
            clase=props.get("clase", ""),
            severidad=props.get("severidad", ""),
            causa=props.get("causa_indice", ""),
            ndvi=props.get("ndvi_promedio"),
            area_ha=props.get("area_ha"),
            confianza=props.get("confianza", ""),
            regla_id=props.get("regla_id", ""),
        )
    writer.close()

    zip_io = io.BytesIO()
    with zipfile.ZipFile(zip_io, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("zonas.shp", shp_io.getvalue())
        zf.writestr("zonas.shx", shx_io.getvalue())
        zf.writestr("zonas.dbf", dbf_io.getvalue())
        zf.writestr("zonas.prj", _WGS84_ESRI_WKT)

    return zip_io.getvalue()


def _partes_shapefile(geom) -> list[list[tuple[float, float]]]:
    """
    Shapefile exige anillo exterior en sentido horario y huecos en sentido
    antihorario (shapely.orient(sign=-1.0) da exactamente eso) — sin esa
    orientación, lectores estrictos (QGIS incluido) interpretan mal cuáles
    anillos son huecos.
    """
    poligonos = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
    partes: list[list[tuple[float, float]]] = []
    for poligono in poligonos:
        poligono = orient(poligono, sign=-1.0)
        partes.append(list(poligono.exterior.coords))
        for interior in poligono.interiors:
            partes.append(list(interior.coords))
    return partes
