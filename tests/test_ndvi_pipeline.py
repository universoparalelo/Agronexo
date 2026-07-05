"""
Test del pipeline NDVI completo.
Ejecutar dentro del contenedor worker:
  docker compose exec worker python3 tests/test_ndvi_pipeline.py
"""

import json
import sys
from pathlib import Path

from workers.gis.zonas import calcular_ndvi, clasificar_ndvi, pipeline_ndvi
import numpy as np

_FIXTURES_DIR = Path(__file__).parent / "fixtures"
FIXTURE = str(_FIXTURES_DIR / "sentinel_ndvi_test.tif")
SALIDA  = str(_FIXTURES_DIR / "resultado_ndvi.geojson")


def setup_module(module):
    """Genera los GeoTIFF de fixtures antes de correr los tests con pytest."""
    crear_fixture()


def crear_fixture():
    """Genera el GeoTIFF sintético de prueba con 4 zonas NDVI controladas."""
    import rasterio
    from rasterio.transform import from_bounds
    from rasterio.crs import CRS

    Path(FIXTURE).parent.mkdir(parents=True, exist_ok=True)
    height, width = 200, 200
    transform = from_bounds(-60.68, -27.48, -60.66, -27.46, width, height)
    h2, w2 = height // 2, width // 2

    nir = np.zeros((height, width), dtype=np.float32)
    red = np.zeros((height, width), dtype=np.float32)

    # NDVI = (NIR-RED)/(NIR+RED)
    nir[:h2, :w2] = 0.55;  red[:h2, :w2] = 0.45   # critica    → NDVI 0.10
    nir[:h2, w2:] = 0.65;  red[:h2, w2:] = 0.35   # deficiente → NDVI 0.30
    nir[h2:, :w2] = 0.775; red[h2:, :w2] = 0.225  # normal     → NDVI 0.55
    nir[h2:, w2:] = 0.90;  red[h2:, w2:] = 0.10   # vigorosa   → NDVI 0.80

    with rasterio.open(FIXTURE, "w", driver="GTiff", height=height, width=width,
                       count=2, dtype="float32",
                       crs=CRS.from_epsg(4326), transform=transform) as dst:
        dst.write(nir, 1)
        dst.write(red, 2)
    print(f"  · Fixture generado: {FIXTURE}")


def test_calcular_ndvi():
    nir = np.array([[0.9, 0.3], [0.55, 0.11]], dtype=np.float32)
    red = np.array([[0.1, 0.7], [0.45, 0.89]], dtype=np.float32)
    ndvi = calcular_ndvi(nir, red)

    assert ndvi.shape == (2, 2)
    assert abs(ndvi[0, 0] - 0.80) < 0.01, f"Esperado ~0.80, got {ndvi[0,0]}"
    assert abs(ndvi[0, 1] - (-0.40)) < 0.01
    assert abs(ndvi[1, 0] - 0.10) < 0.01
    print("  ✓ calcular_ndvi OK")


def test_division_por_cero():
    nir = np.array([0.0], dtype=np.float32)
    red = np.array([0.0], dtype=np.float32)
    ndvi = calcular_ndvi(nir, red)
    assert np.isnan(ndvi[0]), "División por cero debe producir NaN"
    print("  ✓ División por cero → NaN OK")


def test_clasificar_ndvi():
    ndvi = np.array([0.10, 0.30, 0.55, 0.80], dtype=np.float32)
    clase = clasificar_ndvi(ndvi)
    assert list(clase) == [1, 2, 3, 4], f"Clasificación incorrecta: {list(clase)}"
    print("  ✓ clasificar_ndvi OK (critica=1, deficiente=2, normal=3, vigorosa=4)")


def test_pipeline_completo():
    stats = pipeline_ndvi(FIXTURE, SALIDA, banda_nir=1, banda_red=2)

    print(f"\n  Estadísticas del pipeline:")
    print(f"    NDVI promedio lote : {stats['ndvi_promedio_lote']}")
    print(f"    NDVI min / max     : {stats['ndvi_min']} / {stats['ndvi_max']}")
    print(f"    Total polígonos    : {stats['total_poligonos']}")
    print()

    for nombre, datos in stats["clases"].items():
        print(f"    [{nombre:>12}]  polígonos={datos['poligonos']}  "
              f"área={datos['area_ha_total']} ha  "
              f"píxeles={datos['porcentaje_px']}%")

    # Verificaciones mínimas
    assert Path(SALIDA).exists(), "GeoJSON no fue creado"
    assert stats["total_poligonos"] >= 4, "Deben existir al menos 4 polígonos (uno por clase)"
    assert set(stats["clases"].keys()) == {"critica", "deficiente", "normal", "vigorosa"}

    # Verificar GeoJSON válido
    with open(SALIDA) as f:
        geojson = json.load(f)
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) >= 4

    # Cada feature debe tener clase, ndvi_promedio y area_ha
    for feat in geojson["features"]:
        props = feat["properties"]
        assert "clase" in props
        assert "ndvi_promedio" in props
        assert "area_ha" in props

    print(f"\n  ✓ GeoJSON creado en {SALIDA}")
    print(f"  ✓ {len(geojson['features'])} features en el GeoJSON")
    print("  ✓ Pipeline completo OK")


if __name__ == "__main__":
    print("=" * 55)
    print("  Test pipeline NDVI — AgroNexo")
    print("=" * 55)
    crear_fixture()

    errores = []
    for nombre, fn in [
        ("calcular_ndvi",    test_calcular_ndvi),
        ("division_por_cero", test_division_por_cero),
        ("clasificar_ndvi",  test_clasificar_ndvi),
        ("pipeline_completo", test_pipeline_completo),
    ]:
        try:
            fn()
        except Exception as e:
            print(f"  ✗ {nombre} FALLÓ: {e}")
            errores.append(nombre)

    print("=" * 55)
    if errores:
        print(f"  FALLOS: {errores}")
        sys.exit(1)
    else:
        print("  Todos los tests pasaron.")
