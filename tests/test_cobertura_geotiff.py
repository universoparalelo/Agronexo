"""
Tests del polígono que se le asigna a un lote sin límite a partir de su
primer GeoTIFF (workers/gis/tasks.py::_poligono_cobertura_wkt) — requiere rasterio.

Correr en el contenedor worker:
    docker compose exec worker python3 -m pytest tests/test_cobertura_geotiff.py -v
"""
import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.io import MemoryFile
from rasterio.transform import from_bounds
from shapely import wkt

from workers.gis.tasks import _poligono_cobertura_wkt

_BOUNDS = (-60.68, -27.48, -60.66, -27.46)


def _raster(datos: np.ndarray, nodata: float | None):
    memfile = MemoryFile()
    with memfile.open(
        driver="GTiff", height=datos.shape[1], width=datos.shape[2], count=datos.shape[0], dtype="float32",
        crs=CRS.from_epsg(4326), transform=from_bounds(*_BOUNDS, datos.shape[2], datos.shape[1]), nodata=nodata,
    ) as dst:
        dst.write(datos)
    return memfile


def test_raster_completo_devuelve_su_rectangulo():
    memfile = _raster(np.ones((1, 50, 60), dtype="float32"), nodata=0)
    with memfile.open() as src:
        poligono = wkt.loads(_poligono_cobertura_wkt(src))
    minx, miny, maxx, maxy = poligono.bounds
    assert poligono.geom_type == "Polygon"
    assert (round(minx, 4), round(miny, 4), round(maxx, 4), round(maxy, 4)) == _BOUNDS
    assert abs(poligono.area - (0.02 * 0.02)) < 1e-7


def test_esquinas_sin_dato_achican_la_cobertura():
    datos = np.ones((1, 100, 100), dtype="float32")
    yy, xx = np.mgrid[0:100, 0:100]
    datos[:, xx + yy < 45] = 0  # esquina superior izquierda sin dato
    memfile = _raster(datos, nodata=0)
    with memfile.open() as src:
        poligono = wkt.loads(_poligono_cobertura_wkt(src))
    rectangulo_area = 0.02 * 0.02
    assert poligono.geom_type == "Polygon"
    assert poligono.area < rectangulo_area * 0.95
    assert poligono.area > rectangulo_area * 0.7


def test_raster_sin_nodata_declarado_usa_el_rectangulo():
    memfile = _raster(np.zeros((1, 40, 40), dtype="float32"), nodata=None)
    with memfile.open() as src:
        poligono = wkt.loads(_poligono_cobertura_wkt(src))
    assert abs(poligono.area - (0.02 * 0.02)) < 1e-7


def test_raster_todo_sin_dato_cae_al_rectangulo():
    memfile = _raster(np.zeros((1, 40, 40), dtype="float32"), nodata=0)
    with memfile.open() as src:
        poligono = wkt.loads(_poligono_cobertura_wkt(src))
    assert poligono.geom_type == "Polygon" and poligono.area > 0
