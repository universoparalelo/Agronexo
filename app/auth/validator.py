from pathlib import Path

from fastapi import HTTPException, UploadFile, status

_EXTENSIONES_VALIDAS = {".jpg", ".jpeg", ".png"}


def validar_archivo_imagen(archivo: UploadFile, contenido: bytes) -> None:
    """Valida extensión y magic bytes de una imagen (avatar / logo de empresa).

    Mismo criterio que app/ingesta/validator.py::validar_archivo_geotiff,
    pero sin streaming — avatar y logo son archivos chicos, se leen enteros
    antes de subir a MinIO.
    """
    ext = Path(archivo.filename or "").suffix.lower()
    if ext not in _EXTENSIONES_VALIDAS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Solo se aceptan imágenes JPG o PNG. "
                f"Extensión recibida: '{ext or 'sin extensión'}'"
            ),
        )
    if len(contenido) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El archivo está vacío.",
        )
    es_png = contenido[:8] == b"\x89PNG\r\n\x1a\n"
    es_jpeg = contenido[:3] == b"\xff\xd8\xff"
    if not (es_png or es_jpeg):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El archivo no es una imagen JPG/PNG válida o está dañado.",
        )
