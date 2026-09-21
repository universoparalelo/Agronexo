"""
Tests de workers/gis/sin_datos.py::calcular_sin_datos — la parte del lote sin
información REAL (píxeles sin dato + lo que el GeoTIFF no cubre) que el worker
registra al procesar. Requiere rasterio/shapely.

Correr en el contenedor worker:
    docker compose exec worker python3 -m pytest tests/test_sin_datos.py -v
"""
import numpy as np
from rasterio.transform import from_origin
from shapely.geometry import box, mapping, shape

from workers.gis.sin_datos import calcular_sin_datos

# grilla de 100 x 100 píxeles de 0,0001° (≈ 10 m) — 1 píxel ≈ 0,01 ha
PX = 0.0001
X0, Y0 = -59.05, -27.44
N = 100
TRANSFORM = from_origin(X0, Y0, PX, PX)
HUELLA = box(X0, Y0 - N * PX, X0 + N * PX, Y0)


def _valores():
    return np.full((N, N), 0.5, dtype=np.float32)


def _area_px(geojson) -> float:
    return shape(geojson).area / (PX * PX)


def test_raster_completo_no_tiene_sin_datos():
    assert calcular_sin_datos(_valores(), TRANSFORM, mapping(HUELLA)) is None


def test_un_bloque_sin_dato_se_registra_con_su_tamano():
    v = _valores()
    v[20:40, 30:60] = np.nan          # 20 x 30 píxeles
    area = _area_px(calcular_sin_datos(v, TRANSFORM, mapping(HUELLA)))
    assert abs(area - 600) / 600 < 0.05


def test_un_sin_dato_chico_tambien_se_registra():
    # lo que importa: NO se descarta por chico (un solo píxel de 10 m)
    v = _valores()
    v[50:52, 50:52] = np.nan          # 2 x 2 píxeles ≈ 0,04 ha
    resultado = calcular_sin_datos(v, TRANSFORM, mapping(HUELLA))
    assert resultado is not None
    assert 2.5 < _area_px(resultado) < 4.5


def test_un_solo_pixel_sin_dato_tambien_se_registra():
    v = _valores()
    v[50, 50] = np.nan
    resultado = calcular_sin_datos(v, TRANSFORM, mapping(HUELLA))
    assert resultado is not None
    assert 0.5 < _area_px(resultado) < 1.2


def test_lo_que_el_geotiff_no_cubre_del_lote_es_sin_datos():
    lote_mas_grande = box(X0, Y0 - N * PX, X0 + N * PX, Y0 + 40 * PX)   # sobresale 40 px por arriba
    area = _area_px(calcular_sin_datos(_valores(), TRANSFORM, mapping(lote_mas_grande)))
    assert abs(area - 100 * 40) / (100 * 40) < 0.02


def test_el_nodata_fuera_del_lote_no_cuenta():
    # el recorte deja NaN todo lo que está fuera del polígono del lote: no es "sin datos" del lote
    lote = box(X0 + 20 * PX, Y0 - 80 * PX, X0 + 80 * PX, Y0 - 20 * PX)
    v = _valores()
    v[:20, :] = np.nan
    v[80:, :] = np.nan
    v[:, :20] = np.nan
    v[:, 80:] = np.nan
    assert calcular_sin_datos(v, TRANSFORM, mapping(lote)) is None


def test_el_escalon_del_borde_del_lote_no_cuenta():
    # lote en diamante: la máscara por píxeles (centro adentro) queda hasta ~0,5 píxel
    # adentro del contorno; eso es el escalón normal del recorte, no falta de datos
    cx, cy, r = X0 + 50 * PX, Y0 - 50 * PX, 45 * PX
    lote = shape({"type": "Polygon", "coordinates": [[(cx - r, cy), (cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]]})
    v = _valores()
    for fila in range(N):
        for col in range(N):
            if not lote.contains(shape({"type": "Point", "coordinates": (X0 + (col + 0.5) * PX, Y0 - (fila + 0.5) * PX)})):
                v[fila, col] = np.nan
    assert calcular_sin_datos(v, TRANSFORM, mapping(lote)) is None


def test_sin_limite_del_lote_usa_la_huella_del_raster():
    v = _valores()
    v[10:30, 10:30] = np.nan
    area = _area_px(calcular_sin_datos(v, TRANSFORM, None))
    assert abs(area - 400) / 400 < 0.05


def test_todo_el_raster_sin_dato_es_todo_el_lote():
    v = np.full((N, N), np.nan, dtype=np.float32)
    area = _area_px(calcular_sin_datos(v, TRANSFORM, mapping(HUELLA)))
    assert abs(area - N * N) / (N * N) < 0.01
