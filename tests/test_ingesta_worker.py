"""
Tests de validación GIS (CRS, bandas, dtype) — requiere rasterio.
Correr en el contenedor worker:
    docker compose exec worker python3 tests/test_ingesta_worker.py
"""

import io

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_bounds


# ── Fixtures ─────────────────────────────────────────────────────────

def _tiff_valido() -> bytes:
    buf = io.BytesIO()
    transform = from_bounds(-60.68, -27.48, -60.67, -27.47, 10, 10)
    with rasterio.open(
        buf, "w", driver="GTiff",
        height=10, width=10, count=1, dtype="float32",
        crs=CRS.from_epsg(4326), transform=transform,
    ) as dst:
        dst.write(np.random.rand(1, 10, 10).astype("float32"))
    return buf.getvalue()


def _tiff_sin_crs() -> bytes:
    buf = io.BytesIO()
    with rasterio.open(
        buf, "w", driver="GTiff",
        height=10, width=10, count=1, dtype="float32",
    ) as dst:
        dst.write(np.ones((1, 10, 10), dtype="float32"))
    return buf.getvalue()


def _tiff_dtype_float64() -> bytes:
    buf = io.BytesIO()
    transform = from_bounds(-60.68, -27.48, -60.67, -27.47, 10, 10)
    with rasterio.open(
        buf, "w", driver="GTiff",
        height=10, width=10, count=1, dtype="float64",
        crs=CRS.from_epsg(4326), transform=transform,
    ) as dst:
        dst.write(np.ones((1, 10, 10), dtype="float64"))
    return buf.getvalue()


# ── Tests ────────────────────────────────────────────────────────────

def test_sin_crs():
    from workers.gis.tasks import _validar_geotiff_gis

    try:
        _validar_geotiff_gis(_tiff_sin_crs())
        assert False, "Debería haber lanzado ValueError"
    except ValueError as e:
        assert "CRS" in str(e)
        print(f"✓ GeoTIFF sin CRS → ValueError: {e}")


def test_dtype_invalido():
    from workers.gis.tasks import _validar_geotiff_gis

    try:
        _validar_geotiff_gis(_tiff_dtype_float64())
        assert False, "Debería haber lanzado ValueError"
    except ValueError as e:
        assert "float64" in str(e) or "dato" in str(e)
        print(f"✓ dtype float64 → ValueError: {e}")


def test_geotiff_valido():
    from workers.gis.tasks import _validar_geotiff_gis

    metadata = _validar_geotiff_gis(_tiff_valido())
    assert metadata["bandas"] >= 1
    assert metadata["crs"] != ""
    assert metadata["dtype"] == "float32"
    print(f"✓ GeoTIFF válido → metadata: {metadata}")


if __name__ == "__main__":
    print("\n── Validación GIS (worker) ──────────────────────────")
    test_sin_crs()
    test_dtype_invalido()
    test_geotiff_valido()
    print("\nTodos los tests pasaron.\n")
