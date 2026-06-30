"""
Tests de validación de capa API (extensión, magic bytes, tamaño).
Correr en el contenedor api:
    docker compose exec api python3 tests/test_ingesta.py
"""

# ── Generadores de fixtures ──────────────────────────────────────────
# No usan rasterio — el API container no lo tiene instalado.
# El validador solo cheqeua extensión, magic bytes y tamaño.

def _tiff_valido_minimo() -> bytes:
    """Bytes con magic TIFF little-endian válido (II + versión 42)."""
    return b"II\x2a\x00" + b"\x00" * 100


def _bytes_no_tiff() -> bytes:
    """Archivo que no es TIFF (magic bytes inválidos)."""
    return b"PK\x03\x04" + b"\x00" * 100  # magic bytes de ZIP


# ── Tests de validación API (validator.py) ───────────────────────────

def test_validacion_extension_invalida():
    from fastapi import HTTPException
    from unittest.mock import MagicMock
    from app.ingesta.validator import validar_archivo_geotiff

    archivo = MagicMock()
    archivo.filename = "imagen.png"
    contenido = _tiff_valido_minimo()

    try:
        validar_archivo_geotiff(archivo, contenido)
        assert False, "Debería haber lanzado HTTPException"
    except HTTPException as e:
        assert e.status_code == 422
        assert ".tif" in e.detail or "GeoTIFF" in e.detail
        print(f"✓ extensión inválida → 422: {e.detail}")


def test_validacion_magic_bytes_invalidos():
    from fastapi import HTTPException
    from unittest.mock import MagicMock
    from app.ingesta.validator import validar_archivo_geotiff

    archivo = MagicMock()
    archivo.filename = "trampa.tif"
    contenido = _bytes_no_tiff()

    try:
        validar_archivo_geotiff(archivo, contenido)
        assert False, "Debería haber lanzado HTTPException"
    except HTTPException as e:
        assert e.status_code == 422
        assert "válido" in e.detail or "dañado" in e.detail
        print(f"✓ magic bytes inválidos → 422: {e.detail}")


def test_validacion_archivo_vacio():
    from fastapi import HTTPException
    from unittest.mock import MagicMock
    from app.ingesta.validator import validar_archivo_geotiff

    archivo = MagicMock()
    archivo.filename = "vacio.tif"

    try:
        validar_archivo_geotiff(archivo, b"")
        assert False, "Debería haber lanzado HTTPException"
    except HTTPException as e:
        assert e.status_code == 422
        print(f"✓ archivo vacío → 422: {e.detail}")


def test_validacion_geotiff_valido_pasa():
    from unittest.mock import MagicMock
    from app.ingesta.validator import validar_archivo_geotiff

    archivo = MagicMock()
    archivo.filename = "ndvi.tif"
    contenido = _tiff_valido_minimo()

    validar_archivo_geotiff(archivo, contenido)
    print("✓ GeoTIFF válido pasa la validación de extensión y magic bytes")


# ── Main ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n── Validación API (validator.py) ────────────────────")
    test_validacion_extension_invalida()
    test_validacion_magic_bytes_invalidos()
    test_validacion_archivo_vacio()
    test_validacion_geotiff_valido_pasa()

    print("\nTodos los tests pasaron.\n")
