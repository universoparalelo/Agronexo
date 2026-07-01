"""
Tests para workers/gis/clasificacion.py y las mejoras de vectorizar_zonas().
Verifica umbralización dinámica y estadísticas por polígono.
"""
import io
import json
import tempfile

import numpy as np
import pytest
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_bounds

from workers.gis.clasificacion import calcular_umbrales, clasificar_con_umbrales
from workers.gis.ndvi import clasificar_ndvi, vectorizar_zonas


# ── Helpers ─────────────────────────────────────────────────────────────────

def _valores_distribuidos():
    """Array 1-D con valores uniformemente distribuidos en [-0.2, 0.9]."""
    return np.linspace(-0.2, 0.9, 200, dtype=np.float32)


def _meta_sintetica(shape=(100, 100)):
    """Metadatos raster compatibles con rasterio para tests."""
    transform = from_bounds(-60.7, -27.5, -60.6, -27.4, shape[1], shape[0])
    return {"crs": CRS.from_epsg(4326), "transform": transform, "nodata": None, "shape": shape}


# ── Tests calcular_umbrales ──────────────────────────────────────────────────

def test_fijo_retorna_umbrales_agronomicos():
    valores = _valores_distribuidos()
    u = calcular_umbrales(valores, "fijo")
    assert u == [0.20, 0.40, 0.70]


def test_otsu_retorna_tres_umbrales_ordenados():
    valores = _valores_distribuidos()
    u = calcular_umbrales(valores, "otsu")
    assert len(u) == 3
    assert u[0] < u[1] < u[2]
    assert -1.0 <= u[0] and u[2] <= 1.0


def test_percentil_retorna_cuartiles_correctos():
    valores = np.array([0.1, 0.3, 0.5, 0.7] * 50, dtype=np.float32)
    u = calcular_umbrales(valores, "percentil")
    assert len(u) == 3
    assert u[0] < u[1] < u[2]
    # p25 debe estar entre 0.1 y 0.3
    assert 0.1 <= u[0] <= 0.35


def test_otsu_fallback_cuando_imagen_uniforme():
    # Todos los píxeles tienen el mismo valor — Otsu no puede separar 4 clases
    valores = np.full(100, 0.5, dtype=np.float32)
    u = calcular_umbrales(valores, "otsu")
    assert u == [0.20, 0.40, 0.70]


def test_percentil_fallback_cuando_todo_nan():
    valores = np.full(50, np.nan, dtype=np.float32)
    u = calcular_umbrales(valores, "percentil")
    assert u == [0.20, 0.40, 0.70]


def test_metodo_desconocido_lanza_valueerror():
    with pytest.raises(ValueError, match="metodo_umbral desconocido"):
        calcular_umbrales(np.array([0.5], dtype=np.float32), "inventado")


# ── Tests clasificar_con_umbrales ────────────────────────────────────────────

def test_clasificar_con_umbrales_asigna_codigos_correctos():
    valores = np.array([0.10, 0.30, 0.55, 0.80], dtype=np.float32)
    clase = clasificar_con_umbrales(valores, [0.20, 0.40, 0.70])
    assert list(clase) == [1, 2, 3, 4]


def test_clasificar_nan_queda_como_cero():
    valores = np.array([np.nan, 0.5], dtype=np.float32)
    clase = clasificar_con_umbrales(valores, [0.20, 0.40, 0.70])
    assert clase[0] == 0
    assert clase[1] == 3


# ── Tests clasificar_ndvi (backward-compat) ───────────────────────────────────

def test_clasificar_ndvi_fijo_es_identico_al_original():
    ndvi = np.array([0.10, 0.25, 0.55, 0.80], dtype=np.float32)
    clase = clasificar_ndvi(ndvi, metodo="fijo")
    assert list(clase) == [1, 2, 3, 4]


def test_clasificar_ndvi_sin_argumento_usa_fijo():
    ndvi = np.array([0.10, 0.25, 0.55, 0.80], dtype=np.float32)
    assert list(clasificar_ndvi(ndvi)) == list(clasificar_ndvi(ndvi, metodo="fijo"))


# ── Tests vectorizar_zonas — stats por polígono ───────────────────────────────

def _geotiff_cuatro_zonas() -> bytes:
    """
    GeoTIFF 100x100 multibanda (dji_mavic3: 5 bandas, NIR=5, RED=3) con 4 cuadrantes:
      superior-izq: NDVI≈0.10 (crítica)
      superior-der: NDVI≈0.30 (deficiente)
      inferior-izq: NDVI≈0.55 (normal)
      inferior-der: NDVI≈0.80 (vigorosa)
    Valores NIR/RED calculados para que NDVI = (NIR-RED)/(NIR+RED) sea el deseado.
    """
    # NIR y RED tal que (NIR-RED)/(NIR+RED) da el NDVI objetivo
    ndvi_targets = {(slice(None, 50), slice(None, 50)): (1.1, 0.9),    # 0.10
                    (slice(None, 50), slice(50, None)): (1.3, 0.7),     # 0.30
                    (slice(50, None), slice(None, 50)): (1.55, 0.45),   # 0.55
                    (slice(50, None), slice(50, None)): (1.8, 0.2)}     # 0.80

    bands = np.zeros((5, 100, 100), dtype=np.float32)
    for (r, c), (nir, red) in ndvi_targets.items():
        bands[4, r, c] = nir   # banda 5 = NIR (dji_mavic3)
        bands[2, r, c] = red   # banda 3 = RED (dji_mavic3)

    transform = from_bounds(-60.7, -27.5, -60.6, -27.4, 100, 100)
    buf = io.BytesIO()
    with rasterio.open(
        buf, "w", driver="GTiff", height=100, width=100,
        count=5, dtype="float32", crs=CRS.from_epsg(4326), transform=transform,
    ) as dst:
        dst.write(bands)
    buf.seek(0)
    return buf.read()


def test_ndvi_promedio_por_poligono_es_correcto():
    """
    Verifica que cada polígono tiene el ndvi_promedio de SUS píxeles,
    no el promedio global de su clase.
    """
    from workers.gis.ndvi import exportar_geojson
    from workers.gis.pipeline import ejecutar_pipeline

    data = _geotiff_cuatro_zonas()

    with tempfile.NamedTemporaryFile(suffix=".geojson", delete=False) as tmp:
        geojson_path = tmp.name

    ejecutar_pipeline(data=data, sensor="dji_mavic3", indice="ndvi",
                      geojson_destino=geojson_path, metodo_umbral="fijo")

    with open(geojson_path) as f:
        gj = json.load(f)

    features = gj["features"]
    assert len(features) >= 4

    promedios_por_clase = {}
    for feat in features:
        clase = feat["properties"]["clase"]
        prom = feat["properties"]["ndvi_promedio"]
        promedios_por_clase.setdefault(clase, []).append(prom)

    # Cada clase tiene exactamente un polígono con el valor correcto
    assert abs(promedios_por_clase["critica"][0] - 0.10) < 0.02
    assert abs(promedios_por_clase["deficiente"][0] - 0.30) < 0.02
    assert abs(promedios_por_clase["normal"][0] - 0.55) < 0.02
    assert abs(promedios_por_clase["vigorosa"][0] - 0.80) < 0.02


def test_pipeline_otsu_produce_poligonos_validos():
    """Otsu con 4 clases distintas debe producir GeoJSON con features."""
    import tempfile
    from workers.gis.pipeline import ejecutar_pipeline

    data = _geotiff_cuatro_zonas()
    with tempfile.NamedTemporaryFile(suffix=".geojson", delete=False) as tmp:
        geojson_path = tmp.name

    ejecutar_pipeline(data=data, sensor="dji_mavic3", indice="ndvi",
                      geojson_destino=geojson_path, metodo_umbral="otsu")

    with open(geojson_path) as f:
        gj = json.load(f)

    assert gj["type"] == "FeatureCollection"
    assert len(gj["features"]) >= 1
    feat = gj["features"][0]
    assert "clase" in feat["properties"]
    assert "ndvi_promedio" in feat["properties"]
    assert "area_ha" in feat["properties"]
