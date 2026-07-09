from pathlib import Path

from fastapi import HTTPException, UploadFile, status

_EXTENSIONES_VALIDAS = {".tif", ".tiff"}
_TAMANO_MAXIMO_BYTES = 3 * 1024 * 1024 * 1024  # 3 GB (límite temporal hasta implementar streaming)
# Magic bytes TIFF: little-endian (II) o big-endian (MM)
_TIFF_MAGIC = (b"II", b"MM")


def validar_archivo_geotiff(archivo: UploadFile, contenido: bytes) -> None:
    """Valida extensión, tamaño y magic bytes del archivo en la capa API.

    La validación GIS profunda (CRS, bandas, dtype) ocurre en el worker
    porque requiere rasterio, que no está disponible en el contenedor API.
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
    if len(contenido) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El archivo está vacío.",
        )
    if len(contenido) > _TAMANO_MAXIMO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="El archivo supera el tamaño máximo permitido de 3 GB.",
        )
    if len(contenido) < 4 or contenido[:2] not in _TIFF_MAGIC:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El archivo no es un GeoTIFF válido o está dañado.",
        )
