"""
Tests del pipeline GIS: índices, mapeo de bandas y reproyección.
Correr en el contenedor worker:
    docker compose exec worker env PYTHONPATH=/app python3 tests/test_indices_worker.py
"""

import io

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_bounds


# ── Fixtures ─────────────────────────────────────────────────────────

def _geotiff_multibanda(n_bandas: int, crs: CRS, dtype: str = "float32") -> bytes:
    """GeoTIFF sintético con n bandas, valores secuenciales controlados."""
    buf = io.BytesIO()
    transform = from_bounds(-60.68, -27.48, -60.67, -27.47, 20, 20)
    with rasterio.open(
        buf, "w", driver="GTiff",
        height=20, width=20, count=n_bandas, dtype=dtype,
        crs=crs, transform=transform,
    ) as dst:
        for i in range(1, n_bandas + 1):
            # Valores distintos por banda para poder detectar errores de mapeo
            dst.write(np.full((20, 20), fill_value=0.1 * i, dtype=dtype), i)
    return buf.getvalue()


def _geotiff_utm() -> bytes:
    """GeoTIFF con CRS UTM zona 21 Sur (EPSG:32721) para probar reproyección."""
    buf = io.BytesIO()
    from rasterio.transform import from_origin
    transform = from_origin(3_500_000, 7_000_000, 10, 10)  # metros
    with rasterio.open(
        buf, "w", driver="GTiff",
        height=20, width=20, count=2, dtype="float32",
        crs=CRS.from_epsg(32721), transform=transform,
    ) as dst:
        dst.write(np.full((20, 20), 0.8, dtype="float32"), 1)  # NIR
        dst.write(np.full((20, 20), 0.2, dtype="float32"), 2)  # RED
    return buf.getvalue()


# ── Tests de índices ──────────────────────────────────────────────────

def test_ndvi_valor_conocido():
    from workers.gis.indices import calcular_ndvi

    nir = np.full((5, 5), 0.8, dtype=np.float32)
    red = np.full((5, 5), 0.2, dtype=np.float32)
    resultado = calcular_ndvi(nir, red)
    esperado = (0.8 - 0.2) / (0.8 + 0.2)  # 0.6
    assert np.allclose(resultado, esperado, atol=1e-5), f"NDVI esperado {esperado:.4f}, got {resultado[0,0]:.4f}"
    print(f"✓ NDVI valor conocido → {resultado[0,0]:.4f} (esperado {esperado:.4f})")


def test_ndvi_division_por_cero():
    from workers.gis.indices import calcular_ndvi

    nir = np.zeros((3, 3), dtype=np.float32)
    red = np.zeros((3, 3), dtype=np.float32)
    resultado = calcular_ndvi(nir, red)
    assert np.all(np.isnan(resultado)), "Píxeles nir+red=0 deben ser NaN"
    print("✓ NDVI denominador cero → NaN (sin excepción)")


def test_ndre_rango_valido():
    from workers.gis.indices import calcular_ndre

    nir = np.random.rand(10, 10).astype(np.float32)
    re  = np.random.rand(10, 10).astype(np.float32)
    resultado = calcular_ndre(nir, re)
    validos = resultado[~np.isnan(resultado)]
    assert validos.min() >= -1.0 and validos.max() <= 1.0, "NDRE fuera de rango [-1, 1]"
    print(f"✓ NDRE rango válido → [{validos.min():.3f}, {validos.max():.3f}]")


def test_savi_difiere_de_ndvi():
    """SAVI debe ser diferente a NDVI porque tiene el factor L."""
    from workers.gis.indices import calcular_ndvi, calcular_savi

    nir = np.full((5, 5), 0.6, dtype=np.float32)
    red = np.full((5, 5), 0.2, dtype=np.float32)
    assert not np.allclose(calcular_ndvi(nir, red), calcular_savi(nir, red))
    print("✓ SAVI produce valores distintos a NDVI (factor L aplicado)")


def test_exg_no_requiere_nir():
    from workers.gis.indices import calcular_exg

    green = np.full((5, 5), 0.4, dtype=np.float32)
    red   = np.full((5, 5), 0.2, dtype=np.float32)
    blue  = np.full((5, 5), 0.1, dtype=np.float32)
    resultado = calcular_exg(green, red, blue)
    esperado = 2 * 0.4 - 0.2 - 0.1  # 0.5
    assert np.allclose(resultado, esperado, atol=1e-5)
    print(f"✓ ExG = 2G-R-B → {resultado[0,0]:.4f} (esperado {esperado:.4f})")


def test_gndvi_valor_conocido():
    from workers.gis.indices import calcular_gndvi

    nir = np.full((5, 5), 0.8, dtype=np.float32)
    green = np.full((5, 5), 0.3, dtype=np.float32)
    resultado = calcular_gndvi(nir, green)
    esperado = (0.8 - 0.3) / (0.8 + 0.3)
    assert np.allclose(resultado, esperado, atol=1e-5), f"GNDVI esperado {esperado:.4f}, got {resultado[0,0]:.4f}"
    print(f"✓ GNDVI valor conocido → {resultado[0,0]:.4f} (esperado {esperado:.4f})")


def test_msavi_valor_conocido():
    from workers.gis.indices import calcular_msavi

    nir = np.full((5, 5), 0.6, dtype=np.float32)
    red = np.full((5, 5), 0.2, dtype=np.float32)
    resultado = calcular_msavi(nir, red)
    termino = (2 * 0.6 + 1) ** 2 - 8 * (0.6 - 0.2)
    esperado = (2 * 0.6 + 1 - termino ** 0.5) / 2
    assert np.allclose(resultado, esperado, atol=1e-5), f"MSAVI esperado {esperado:.4f}, got {resultado[0,0]:.4f}"
    print(f"✓ MSAVI valor conocido → {resultado[0,0]:.4f} (esperado {esperado:.4f})")


def test_msavi_termino_negativo_no_lanza_excepcion():
    """Con nir-red muy grande el término bajo la raíz puede volverse negativo — no debe lanzar excepción."""
    from workers.gis.indices import calcular_msavi

    nir = np.full((3, 3), 0.1, dtype=np.float32)
    red = np.full((3, 3), 0.9, dtype=np.float32)
    resultado = calcular_msavi(nir, red)
    assert not np.any(np.isnan(resultado)), "MSAVI con término negativo bajo la raíz no debe dar NaN"
    print(f"✓ MSAVI con término negativo bajo la raíz → sin excepción, valor {resultado[0,0]:.4f}")


def test_ndwi_valor_conocido():
    from workers.gis.indices import calcular_ndwi

    green = np.full((5, 5), 0.3, dtype=np.float32)
    nir = np.full((5, 5), 0.6, dtype=np.float32)
    resultado = calcular_ndwi(green, nir)
    esperado = (0.3 - 0.6) / (0.3 + 0.6)
    assert np.allclose(resultado, esperado, atol=1e-5), f"NDWI esperado {esperado:.4f}, got {resultado[0,0]:.4f}"
    print(f"✓ NDWI valor conocido → {resultado[0,0]:.4f} (esperado {esperado:.4f})")


def test_nodata_se_convierte_en_nan():
    from workers.gis.indices import calcular_ndvi

    nir = np.array([[0.8, -9999.0]], dtype=np.float32)
    red = np.array([[0.2, -9999.0]], dtype=np.float32)
    resultado = calcular_ndvi(nir, red, nodata=-9999.0)
    assert not np.isnan(resultado[0, 0]), "Píxel válido no debe ser NaN"
    assert np.isnan(resultado[0, 1]), "Píxel nodata debe ser NaN"
    print("✓ nodata → NaN correctamente")


# ── Tests de mapeo de bandas ──────────────────────────────────────────

def test_mapeo_sentinel2():
    from workers.gis.band_mapping import numero_banda
    assert numero_banda("sentinel2", "NIR") == 8
    assert numero_banda("sentinel2", "RED") == 4
    assert numero_banda("sentinel2", "RE")  == 5
    print("✓ Mapeo Sentinel-2: NIR=8, RED=4, RE=5")


def test_mapeo_dji():
    from workers.gis.band_mapping import numero_banda
    assert numero_banda("dji_mavic3", "NIR") == 4
    assert numero_banda("dji_mavic3", "RED") == 2
    assert numero_banda("dji_mavic3", "RE")  == 3
    print("✓ Mapeo DJI Mavic 3: NIR=4, RED=2, RE=3 (4 bandas, sin Blue)")


def test_sensor_invalido():
    from workers.gis.band_mapping import obtener_mapeo
    try:
        obtener_mapeo("phantom4")
        assert False, "Debería lanzar ValueError"
    except ValueError as e:
        print(f"✓ Sensor inválido → ValueError: {e}")


def test_bandas_insuficientes():
    from workers.gis.band_mapping import validar_bandas_disponibles
    try:
        # sentinel2 necesita banda NIR=8 para NDVI pero el archivo solo tiene 2
        validar_bandas_disponibles("sentinel2", "ndvi", n_bandas_archivo=2)
        assert False, "Debería lanzar ValueError"
    except ValueError as e:
        assert "banda" in str(e).lower()
        print(f"✓ Bandas insuficientes → ValueError: {e}")


def test_gndvi_msavi_ndwi_disponibles_en_dji():
    """A diferencia de ExG (necesita Blue), GNDVI/MSAVI/NDWI no requieren Blue
    y deben estar disponibles también en DJI Mavic 3 (4 bandas, sin Blue)."""
    from workers.gis.band_mapping import validar_bandas_disponibles
    for indice in ("gndvi", "msavi", "ndwi"):
        validar_bandas_disponibles("dji_mavic3", indice, n_bandas_archivo=4)
    print("✓ GNDVI/MSAVI/NDWI disponibles en DJI Mavic 3 sin banda Blue")


# ── Tests de reproyección ─────────────────────────────────────────────

def test_reproyeccion_utm_a_4326():
    from workers.gis.reproyeccion import reproyectar_a_4326

    data_utm = _geotiff_utm()
    data_4326 = reproyectar_a_4326(data_utm)

    with rasterio.open(io.BytesIO(data_4326)) as src:
        assert src.crs == CRS.from_epsg(4326), f"CRS esperado EPSG:4326, got {src.crs}"
        assert src.count == 2
    print("✓ Reproyección UTM→4326 correcta, bandas preservadas")


def test_4326_no_reproyecta():
    from workers.gis.reproyeccion import reproyectar_a_4326

    data = _geotiff_multibanda(2, CRS.from_epsg(4326))
    resultado = reproyectar_a_4326(data)
    assert resultado == data, "GeoTIFF ya en 4326 no debe modificarse"
    print("✓ GeoTIFF ya en EPSG:4326 → devuelve bytes originales sin modificar")


# ── Tests del pipeline completo ───────────────────────────────────────

def test_pipeline_ndvi_dji():
    import tempfile
    from workers.gis.pipeline import ejecutar_pipeline

    # DJI Mavic3 real: 4 bandas, sin Blue — G=1, R=2, RE=3, NIR=4
    data = _geotiff_multibanda(4, CRS.from_epsg(4326))
    with tempfile.NamedTemporaryFile(suffix=".geojson", delete=False) as tmp:
        stats = ejecutar_pipeline(data, sensor="dji_mavic3", indice="ndvi", geojson_destino=tmp.name)

    assert stats["indice"] == "ndvi"
    assert stats["sensor"] == "dji_mavic3"
    assert "ndvi_promedio_lote" in stats
    print(f"✓ Pipeline NDVI DJI → {stats['total_poligonos']} polígonos, NDVI prom={stats['ndvi_promedio_lote']}")


def test_pipeline_savi_sentinel2():
    import tempfile
    from workers.gis.pipeline import ejecutar_pipeline

    # Sentinel-2 tiene 8+ bandas; usamos 8 para cubrir NIR=8
    data = _geotiff_multibanda(8, CRS.from_epsg(4326))
    with tempfile.NamedTemporaryFile(suffix=".geojson", delete=False) as tmp:
        stats = ejecutar_pipeline(data, sensor="sentinel2", indice="savi", geojson_destino=tmp.name)

    assert stats["indice"] == "savi"
    print(f"✓ Pipeline SAVI Sentinel-2 → {stats['total_poligonos']} polígonos")


def test_pipeline_gndvi_dji():
    import tempfile
    from workers.gis.pipeline import ejecutar_pipeline

    data = _geotiff_multibanda(4, CRS.from_epsg(4326))
    with tempfile.NamedTemporaryFile(suffix=".geojson", delete=False) as tmp:
        stats = ejecutar_pipeline(data, sensor="dji_mavic3", indice="gndvi", geojson_destino=tmp.name)

    assert stats["indice"] == "gndvi"
    assert "gndvi_promedio_lote" in stats
    print(f"✓ Pipeline GNDVI DJI → {stats['total_poligonos']} polígonos, GNDVI prom={stats['gndvi_promedio_lote']}")


def test_pipeline_msavi_sentinel2():
    import tempfile
    from workers.gis.pipeline import ejecutar_pipeline

    data = _geotiff_multibanda(8, CRS.from_epsg(4326))
    with tempfile.NamedTemporaryFile(suffix=".geojson", delete=False) as tmp:
        stats = ejecutar_pipeline(data, sensor="sentinel2", indice="msavi", geojson_destino=tmp.name)

    assert stats["indice"] == "msavi"
    print(f"✓ Pipeline MSAVI Sentinel-2 → {stats['total_poligonos']} polígonos")


def test_pipeline_ndwi_dji():
    import tempfile
    from workers.gis.pipeline import ejecutar_pipeline

    data = _geotiff_multibanda(4, CRS.from_epsg(4326))
    with tempfile.NamedTemporaryFile(suffix=".geojson", delete=False) as tmp:
        stats = ejecutar_pipeline(data, sensor="dji_mavic3", indice="ndwi", geojson_destino=tmp.name)

    assert stats["indice"] == "ndwi"
    print(f"✓ Pipeline NDWI DJI → {stats['total_poligonos']} polígonos")


if __name__ == "__main__":
    print("\n── Índices ──────────────────────────────────────────")
    test_ndvi_valor_conocido()
    test_ndvi_division_por_cero()
    test_ndre_rango_valido()
    test_savi_difiere_de_ndvi()
    test_exg_no_requiere_nir()
    test_gndvi_valor_conocido()
    test_msavi_valor_conocido()
    test_msavi_termino_negativo_no_lanza_excepcion()
    test_ndwi_valor_conocido()
    test_nodata_se_convierte_en_nan()

    print("\n── Mapeo de bandas ──────────────────────────────────")
    test_mapeo_sentinel2()
    test_mapeo_dji()
    test_sensor_invalido()
    test_bandas_insuficientes()
    test_gndvi_msavi_ndwi_disponibles_en_dji()

    print("\n── Reproyección ─────────────────────────────────────")
    test_reproyeccion_utm_a_4326()
    test_4326_no_reproyecta()

    print("\n── Pipeline completo ────────────────────────────────")
    test_pipeline_ndvi_dji()
    test_pipeline_savi_sentinel2()
    test_pipeline_gndvi_dji()
    test_pipeline_msavi_sentinel2()
    test_pipeline_ndwi_dji()

    print("\nTodos los tests pasaron.\n")
