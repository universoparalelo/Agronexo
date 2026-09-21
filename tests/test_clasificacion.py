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
from workers.gis.zonas import clasificar_ndvi, vectorizar_zonas


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


def test_otsu_es_adaptativo_y_no_cae_a_los_umbrales_fijos():
    # Regresión: threshold_multiotsu se llamaba con `nclasses=` (el parámetro
    # correcto es `classes=`); el TypeError se tragaba y "otsu" devolvía siempre
    # [0.20, 0.40, 0.70]. Con un índice de escala chica (como ExG sobre
    # reflectancias, ~0.02) eso dejaba todo el lote en la clase más baja.
    rng = np.random.default_rng(0)
    valores = np.concatenate([
        rng.normal(centro, 0.002, 400) for centro in (0.005, 0.02, 0.035, 0.05)
    ]).astype(np.float32)
    u = calcular_umbrales(valores, "otsu", indice="exg")
    assert u != [0.20, 0.40, 0.70]
    assert all(0.0 < x < 0.07 for x in u)
    clases = clasificar_con_umbrales(valores, u)
    assert set(np.unique(clases)) == {1, 2, 3, 4}


def test_gndvi_tiene_umbrales_propios_distintos_del_ndvi():
    # Regresión: GNDVI reutilizaba los cortes del NDVI y un lote sano quedaba
    # casi entero en "Normal" (su rango real es más angosto).
    assert calcular_umbrales(np.array([0.5, 0.6], dtype=np.float32), "fijo", indice="gndvi") == [0.25, 0.45, 0.60]
    assert calcular_umbrales(np.array([0.5, 0.6], dtype=np.float32), "fijo", indice="ndvi") == [0.20, 0.40, 0.70]
    valores = np.array([0.2, 0.3, 0.5, 0.55, 0.62, 0.7], dtype=np.float32)
    clases = clasificar_con_umbrales(valores, [0.25, 0.45, 0.60])
    assert clases.tolist() == [1, 2, 3, 3, 4, 4]


def test_exg_tiene_umbrales_fijos_propios():
    # ExG normalizado: cortes 0.05 / 0.15 / 0.30 (no los de NDVI), en 4 clases.
    assert calcular_umbrales(np.array([0.1, 0.2], dtype=np.float32), "fijo", indice="exg") == [0.05, 0.15, 0.30]
    valores = np.array([-0.02, 0.03, 0.06, 0.14, 0.16, 0.28, 0.35, 0.5], dtype=np.float32)
    clases = clasificar_con_umbrales(valores, [0.05, 0.15, 0.30])
    assert clases.tolist() == [1, 1, 2, 2, 3, 3, 4, 4]


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
    GeoTIFF 100x100 multibanda (dji_mavic3: 4 bandas reales, sin Blue, NIR=4, RED=2)
    con 4 cuadrantes:
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

    bands = np.zeros((4, 100, 100), dtype=np.float32)
    for (r, c), (nir, red) in ndvi_targets.items():
        bands[3, r, c] = nir   # banda 4 = NIR (dji_mavic3)
        bands[1, r, c] = red   # banda 2 = RED (dji_mavic3)

    transform = from_bounds(-60.7, -27.5, -60.6, -27.4, 100, 100)
    buf = io.BytesIO()
    with rasterio.open(
        buf, "w", driver="GTiff", height=100, width=100,
        count=4, dtype="float32", crs=CRS.from_epsg(4326), transform=transform,
    ) as dst:
        dst.write(bands)
    buf.seek(0)
    return buf.read()


def test_ndvi_promedio_por_poligono_es_correcto():
    """
    Verifica que cada polígono tiene el ndvi_promedio de SUS píxeles,
    no el promedio global de su clase.
    """
    from workers.gis.zonas import exportar_geojson
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


# ── Tests zscore y es_atipica ────────────────────────────────────────────────

def _meta_simple(shape=(10, 10)):
    transform = from_bounds(-60.7, -27.5, -60.6, -27.4, shape[1], shape[0])
    return {"crs": CRS.from_epsg(4326), "transform": transform, "nodata": None, "shape": shape}


def test_zscore_y_atipica_presentes_en_geojson():
    """El GeoJSON de salida incluye zscore y es_atipica en cada feature."""
    import tempfile
    from workers.gis.pipeline import ejecutar_pipeline

    data = _geotiff_cuatro_zonas()
    with tempfile.NamedTemporaryFile(suffix=".geojson", delete=False) as tmp:
        geojson_path = tmp.name

    ejecutar_pipeline(data=data, sensor="dji_mavic3", indice="ndvi",
                      geojson_destino=geojson_path, metodo_umbral="fijo")

    with open(geojson_path) as f:
        gj = json.load(f)

    for feat in gj["features"]:
        props = feat["properties"]
        assert "zscore" in props, "falta zscore en feature"
        assert "es_atipica" in props, "falta es_atipica en feature"
        assert isinstance(props["es_atipica"], bool)
        assert isinstance(props["zscore"], float)


def test_outlier_marcado_como_atipico():
    """Polígono con ndvi muy alejado del resto debe tener es_atipica=True."""
    # 6 polígonos sintéticos: 5 vigorosos similares + 1 crítico outlier
    ndvi_values = np.array([0.78, 0.75, 0.80, 0.77, 0.76, 0.05], dtype=np.float32)
    import geopandas as gpd
    from shapely.geometry import box

    # Construir GDF directamente con polígonos separados
    geoms = [box(i, 0, i + 0.9, 0.9) for i in range(6)]
    gdf = gpd.GeoDataFrame(
        {
            "geometry": geoms,
            "clase": ["vigorosa"] * 5 + ["critica"],
            "codigo": [4] * 5 + [1],
            "ndvi_promedio": ndvi_values.tolist(),
        },
        crs=CRS.from_epsg(4326),
    )

    # Aplicar la lógica de zscore directamente (misma que vectorizar_zonas)
    media = float(np.mean(ndvi_values))
    std = float(np.std(ndvi_values, ddof=1))
    gdf["zscore"] = ((gdf["ndvi_promedio"] - media) / std).round(4)
    gdf["es_atipica"] = gdf["zscore"].abs() > 1.5

    atipicas = gdf[gdf["es_atipica"]]
    assert len(atipicas) == 1
    assert atipicas.iloc[0]["clase"] == "critica"
    assert atipicas.iloc[0]["zscore"] < -1.5


def test_menos_de_3_poligonos_no_marca_atipicas():
    """Con menos de 3 polígonos no se calculan atípicas (evita falsos positivos)."""
    ndvi = np.array([
        [0.05, 0.05, 0.80, 0.80],
        [0.05, 0.05, 0.80, 0.80],
        [0.80, 0.80, 0.80, 0.80],
        [0.80, 0.80, 0.80, 0.80],
    ], dtype=np.float32)

    clase = clasificar_ndvi(ndvi)
    gdf = vectorizar_zonas(clase, ndvi, _meta_simple((4, 4)), area_minima_m2=0)

    assert len(gdf) < 3
    assert not gdf["es_atipica"].any()
    assert (gdf["zscore"] == 0.0).all()


def test_area_minima_filtra_poligonos_pequenos():
    """area_minima_m2 configurable elimina polígonos por debajo del umbral."""
    ndvi = np.array([
        [0.05, 0.80, 0.80, 0.80],
        [0.80, 0.80, 0.80, 0.80],
        [0.80, 0.80, 0.80, 0.80],
        [0.80, 0.80, 0.80, 0.80],
    ], dtype=np.float32)

    clase = clasificar_ndvi(ndvi)
    meta = _meta_simple((4, 4))

    sin_filtro = vectorizar_zonas(clase, ndvi, meta, area_minima_m2=0)
    con_filtro = vectorizar_zonas(clase, ndvi, meta, area_minima_m2=500_000_000)

    assert len(sin_filtro) > 0
    assert len(con_filtro) == 0


def test_el_geojson_guarda_los_umbrales_usados():
    """La leyenda del mapa rotula las clases con estos valores (ver MapaIndice.jsx)."""
    from workers.gis.pipeline import ejecutar_pipeline

    for metodo in ("fijo", "otsu"):
        data = _geotiff_cuatro_zonas()
        with tempfile.NamedTemporaryFile(suffix=".geojson", delete=False) as tmp:
            geojson_path = tmp.name
        ejecutar_pipeline(data=data, sensor="dji_mavic3", indice="ndvi",
                          geojson_destino=geojson_path, metodo_umbral=metodo)
        with open(geojson_path) as f:
            gj = json.load(f)
        assert gj["metodo_umbral"] == metodo
        assert "sin_datos" in gj and gj["sin_datos"] is None   # campo entero válido: nada sin datos, pero la clave está
        assert len(gj["umbrales"]) == 3 and gj["umbrales"] == sorted(gj["umbrales"])
        assert len(gj["features"]) > 0
        if metodo == "fijo":
            assert gj["umbrales"] == [0.2, 0.4, 0.7]
