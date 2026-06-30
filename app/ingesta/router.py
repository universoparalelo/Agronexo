import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import Usuario
from app.core.database import get_db
from app.ingesta import service
from app.ingesta.schemas import EstadoVueloResponse, VueloListItem, VueloUploadResponse
from app.ingesta.validator import validar_archivo_geotiff
from app.lotes.models import SensorEnum
from app.lotes.service import obtener_lote

router = APIRouter()


@router.post(
    "/{lote_id}/vuelos",
    response_model=VueloUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Subir GeoTIFF y encolar procesamiento",
)
async def subir_vuelo(
    lote_id: uuid.UUID,
    archivo: UploadFile = File(..., description="GeoTIFF multiespectral (.tif / .tiff)"),
    sensor: SensorEnum = Form(..., description="Tipo de sensor utilizado"),
    fecha_vuelo: datetime = Form(
        default=None,
        description="Fecha y hora del vuelo (ISO 8601). Por defecto: ahora.",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    lote = await obtener_lote(db, lote_id, usuario_id=uuid.UUID(str(current_user.id)))
    if not lote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado.")

    contenido = await archivo.read()
    validar_archivo_geotiff(archivo, contenido)

    if fecha_vuelo is None:
        fecha_vuelo = datetime.now(timezone.utc)

    vuelo = await service.crear_vuelo_desde_upload(
        db=db,
        lote_id=lote_id,
        usuario_id=uuid.UUID(str(current_user.id)),
        sensor=sensor,
        fecha_vuelo=fecha_vuelo,
        file_data=contenido,
    )
    await db.commit()

    return VueloUploadResponse(
        vuelo_id=vuelo.id,
        lote_id=vuelo.lote_id,
        sensor=vuelo.sensor,
        estado=vuelo.estado,
        task_id=vuelo.task_id,
        created_at=vuelo.created_at,
    )


@router.get(
    "/{lote_id}/vuelos",
    response_model=list[VueloListItem],
    summary="Listar vuelos de un lote",
)
async def listar_vuelos_lote(
    lote_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    lote = await obtener_lote(db, lote_id, usuario_id=uuid.UUID(str(current_user.id)))
    if not lote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado.")
    vuelos = await service.listar_vuelos(db, lote_id)
    return [
        VueloListItem(
            vuelo_id=v.id,
            lote_id=v.lote_id,
            sensor=v.sensor,
            estado=v.estado,
            fecha_vuelo=v.fecha_vuelo,
            task_id=v.task_id,
            created_at=v.created_at,
        )
        for v in vuelos
    ]


@router.get(
    "/{lote_id}/vuelos/{vuelo_id}/resultado",
    summary="Obtener GeoJSON del resultado del índice procesado",
)
async def resultado_vuelo(
    lote_id: uuid.UUID,
    vuelo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    lote = await obtener_lote(db, lote_id, usuario_id=uuid.UUID(str(current_user.id)))
    if not lote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado.")
    geojson = await service.obtener_resultado_geojson(db, lote_id, vuelo_id)
    if geojson is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resultado no disponible. El vuelo debe estar en estado 'completado'.",
        )
    return geojson


@router.get(
    "/{lote_id}/vuelos/{vuelo_id}/estado",
    response_model=EstadoVueloResponse,
    summary="Consultar estado del procesamiento de un vuelo",
)
async def estado_vuelo(
    lote_id: uuid.UUID,
    vuelo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    lote = await obtener_lote(db, lote_id, usuario_id=uuid.UUID(str(current_user.id)))
    if not lote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado.")

    estado = await service.obtener_estado_vuelo(db, lote_id, vuelo_id)
    if not estado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vuelo no encontrado.")
    return estado
