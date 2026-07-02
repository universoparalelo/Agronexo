import json as _json
import uuid
from datetime import datetime

from celery.result import AsyncResult
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import download_object, upload_geotiff
from app.ingesta.schemas import EstadoVueloResponse
from app.lotes.models import EstadoVueloEnum, SensorEnum, Vuelo
from workers.celery_app import celery_app


async def crear_vuelo_desde_upload(
    db: AsyncSession,
    lote_id: uuid.UUID,
    usuario_id: uuid.UUID,
    sensor: SensorEnum,
    fecha_vuelo: datetime,
    file_data: bytes,
) -> Vuelo:
    vuelo = Vuelo(
        lote_id=lote_id,
        sensor=sensor,
        fecha_vuelo=fecha_vuelo,
        estado=EstadoVueloEnum.pendiente,
    )
    db.add(vuelo)
    await db.flush()
    await db.refresh(vuelo)

    key = upload_geotiff(
        usuario_id=str(usuario_id),
        lote_id=str(lote_id),
        vuelo_id=str(vuelo.id),
        data=file_data,
    )

    task = celery_app.send_task(
        "workers.gis.tasks.procesar_vuelo",
        kwargs={
            "vuelo_id": str(vuelo.id),
            "minio_key": key,
            "sensor": sensor.value,
            "indice": "ndvi",
        },
        queue="gis",
    )

    vuelo.archivo_original = key
    vuelo.task_id = task.id
    await db.flush()
    await db.refresh(vuelo)
    return vuelo


async def obtener_estado_vuelo(
    db: AsyncSession,
    lote_id: uuid.UUID,
    vuelo_id: uuid.UUID,
) -> EstadoVueloResponse | None:
    stmt = select(Vuelo).where(Vuelo.id == vuelo_id, Vuelo.lote_id == lote_id)
    result = await db.execute(stmt)
    vuelo = result.scalar_one_or_none()
    if vuelo is None:
        return None

    progreso: int | None = None
    mensaje: str | None = None

    if vuelo.task_id and vuelo.estado in (EstadoVueloEnum.pendiente, EstadoVueloEnum.procesando):
        ar = AsyncResult(vuelo.task_id, app=celery_app)
        if isinstance(ar.info, dict):
            progreso = ar.info.get("progreso")
            mensaje = ar.info.get("mensaje")

    return EstadoVueloResponse(
        vuelo_id=vuelo.id,
        estado=vuelo.estado,
        task_id=vuelo.task_id,
        progreso=progreso,
        mensaje=mensaje,
        error=vuelo.error_detalle,
    )


async def obtener_zonas_vuelo(
    db: AsyncSession,
    lote_id: uuid.UUID,
    vuelo_id: uuid.UUID,
    usuario_id: uuid.UUID,
) -> dict | None:
    stmt = select(Vuelo).where(Vuelo.id == vuelo_id, Vuelo.lote_id == lote_id)
    result = await db.execute(stmt)
    vuelo = result.scalar_one_or_none()
    if vuelo is None or vuelo.estado != EstadoVueloEnum.completado:
        return None
    key = f"{usuario_id}/{lote_id}/{vuelo_id}/zonas.geojson"
    try:
        data = download_object(key)
        return _json.loads(data)
    except Exception:
        return None
