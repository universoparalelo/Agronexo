import mimetypes

import jwt
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app.core import storage_disco
from app.core.config import settings

router = APIRouter()


# El token ya es la autorización (lo emite storage_disco.presigned_url): las
# imágenes del avatar y del logo se piden desde <img>, que no puede mandar el
# header Authorization.
@router.get("/{token}")
async def descargar_archivo(token: str):
    if settings.storage_backend != "disk":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")
    try:
        ruta = storage_disco.ruta_de(storage_disco.clave_desde_token(token))
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Enlace inválido o vencido")
    if not ruta.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")
    tipo, _ = mimetypes.guess_type(ruta.name)
    return FileResponse(ruta, media_type=tipo or "application/octet-stream")
