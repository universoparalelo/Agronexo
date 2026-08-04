from pathlib import Path

from fastapi import HTTPException, UploadFile, status

_EXTENSIONES_VALIDAS = {".tif", ".tiff"}
# Magic bytes TIFF: little-endian (II) o big-endian (MM)
_TIFF_MAGIC = (b"II", b"MM")


def validar_archivo_geotiff(archivo: UploadFile, primeros_bytes: bytes) -> None:
    """Valida extensión y magic bytes sin requerir el archivo completo en memoria.

    primeros_bytes: al menos los primeros 4 bytes del archivo.
    La validación GIS profunda (CRS, bandas, dtype) ocurre en el worker
    porque requiere rasterio, que no está disponible en el contenedor API.
    El límite de tamaño ya no se comprueba aquí — el upload es streaming y
    el backend de almacenamiento (MinIO/disco) acepta cualquier tamaño.
    """
    ext = Path(archivo.filename or "").suffix.lower()
    if ext not in _EXTENSIONES_VALIDAS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Solo se aceptan archivos GeoTIFF (.tif / .tiff). "
                f"Extensión recibida: '{ext or 'sin extensión'}'"
            ),
        )
    if len(primeros_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El archivo está vacío.",
        )
    if len(primeros_bytes) < 4 or primeros_bytes[:2] not in _TIFF_MAGIC:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El archivo no es un GeoTIFF válido o está dañado.",
        )
