import logging
import shutil
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.auth.dependencies import get_current_user
from app.auth.models import Usuario
from app.backup import archivos, exportar as exportacion, importar as importacion
from app.core.config import settings
from app.core.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

TOKEN_TIPO = "backup"
VIGENCIA_DESCARGA = timedelta(minutes=10)
VIDA_TEMPORALES_S = 24 * 3600
COPIAS_PREVIAS_A_CONSERVAR = 2


class ImportarIn(BaseModel):
    modo: str


def _ruta_importacion(importacion_id: str) -> Path:
    try:
        uuid.UUID(importacion_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")
    ruta = archivos.carpeta_copias() / f"importacion-{importacion_id}.zip"
    if not ruta.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La importación venció o no existe. Elegí el archivo de nuevo.")
    return ruta


def _limpiar_temporales() -> None:
    limite = time.time() - VIDA_TEMPORALES_S
    carpeta = archivos.carpeta_copias()
    for patron in ("agronexo-backup-*.zip", "importacion-*.zip"):
        for ruta in carpeta.glob(patron):
            if ruta.stat().st_mtime < limite:
                ruta.unlink(missing_ok=True)
    previas = sorted(carpeta.glob("antes-de-importar-*.zip"), key=lambda r: r.stat().st_mtime, reverse=True)
    for ruta in previas[COPIAS_PREVIAS_A_CONSERVAR:]:
        ruta.unlink(missing_ok=True)


@router.post("/exportar")
async def exportar_todo(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await run_in_threadpool(_limpiar_temporales)
    nombre = f"agronexo-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"
    destino = archivos.carpeta_copias() / nombre
    try:
        manifiesto = await exportacion.exportar(db, current_user, destino)
    except Exception:
        destino.unlink(missing_ok=True)
        logger.exception("No se pudo crear el backup")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No se pudo crear el backup.")
    token = jwt.encode(
        {"n": nombre, "type": TOKEN_TIPO, "exp": datetime.now(timezone.utc) + VIGENCIA_DESCARGA},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return {
        "nombre": nombre,
        "bytes": destino.stat().st_size,
        "url_descarga": f"/api/v1/backup/descargas/{token}",
        "manifiesto": manifiesto,
    }


# El token ya es la autorización: la descarga la hace el navegador con un enlace,
# que no puede mandar el header Authorization.
@router.get("/descargas/{token}")
async def descargar(token: str):
    try:
        carga = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Enlace inválido o vencido")
    nombre = carga.get("n")
    if carga.get("type") != TOKEN_TIPO or not isinstance(nombre, str) or Path(nombre).name != nombre:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Enlace inválido o vencido")
    ruta = archivos.carpeta_copias() / nombre
    if not ruta.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")
    return FileResponse(ruta, media_type="application/zip", filename=nombre)


@router.post("/importar/analizar")
async def analizar_importacion(
    archivo: UploadFile = File(...),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await run_in_threadpool(_limpiar_temporales)
    importacion_id = str(uuid.uuid4())
    ruta = archivos.carpeta_copias() / f"importacion-{importacion_id}.zip"

    def guardar():
        with open(ruta, "wb") as destino:
            shutil.copyfileobj(archivo.file, destino, length=8 * 1024 * 1024)

    await run_in_threadpool(guardar)
    try:
        leido = await run_in_threadpool(importacion.leer, ruta)
        analisis = await importacion.analizar(db, leido)
    except importacion.BackupInvalido as error:
        ruta.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    except Exception:
        ruta.unlink(missing_ok=True)
        logger.exception("No se pudo leer el backup")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No se pudo leer el backup.")
    return {"importacion_id": importacion_id, **analisis}


@router.post("/importar/{importacion_id}")
async def importar_backup(
    importacion_id: str,
    datos: ImportarIn,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if datos.modo not in importacion.MODOS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Modo de importación inválido.")
    ruta = _ruta_importacion(importacion_id)
    copia_previa = None
    try:
        leido = await run_in_threadpool(importacion.leer, ruta)
        if datos.modo == "reemplazar":
            copia_previa = f"antes-de-importar-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"
            await exportacion.exportar(db, current_user, archivos.carpeta_copias() / copia_previa)
        resumen = await importacion.importar(db, current_user, ruta, leido, datos.modo)
        # Los archivos viejos se borran recién con la base ya confirmada: si algo falla antes,
        # no se pierde nada.
        await db.commit()
    except importacion.BackupInvalido as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    except Exception:
        logger.exception("No se pudo importar el backup")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo importar el backup. Tus datos no se modificaron.",
        )
    for clave in resumen.pop("claves_a_borrar"):
        await run_in_threadpool(archivos.borrar, clave)
    ruta.unlink(missing_ok=True)
    await run_in_threadpool(_limpiar_temporales)
    return {**resumen, "copia_previa": copia_previa}


@router.delete("/importar/{importacion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancelar_importacion(importacion_id: str, current_user: Usuario = Depends(get_current_user)):
    _ruta_importacion(importacion_id).unlink(missing_ok=True)
