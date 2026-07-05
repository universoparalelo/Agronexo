import json
import uuid
from datetime import datetime, timezone

from celery.result import AsyncResult
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import download_bytes, upload_geotiff
from app.ingesta.schemas import EstadoVueloResponse, IndiceAnalisisItem, IndiceEstadoResponse, LoteDesdeGeotiffResponse
from app.lotes.models import AnalisisIndice, CultivoEnum, EstadoVueloEnum, IndiceEnum, Lote, SensorEnum, Vuelo
from workers.celery_app import celery_app


async def crear_lote_y_vuelo_desde_geotiff(
    db: AsyncSession,
    usuario_id: uuid.UUID,
    nombre: str,
    cultivo: CultivoEnum,
    sensor: SensorEnum,
    file_data: bytes,
    estadio_fenologico: str | None = None,
) -> LoteDesdeGeotiffResponse:
    lote = Lote(
        nombre=nombre,
        cultivo=cultivo,
        estadio_fenologico=estadio_fenologico,
        usuario_id=usuario_id,
        geometry=None,
    )
    db.add(lote)
    await db.flush()
    await db.refresh(lote)

    vuelo = Vuelo(
        lote_id=lote.id,
        sensor=sensor,
        fecha_vuelo=datetime.now(timezone.utc),
        estado=EstadoVueloEnum.pendiente,
    )
    db.add(vuelo)
    await db.flush()
    await db.refresh(vuelo)

    key = upload_geotiff(
        usuario_id=str(usuario_id),
        lote_id=str(lote.id),
        vuelo_id=str(vuelo.id),
        data=file_data,
    )

    task = celery_app.send_task(
        "workers.gis.tasks.procesar_vuelo",
        kwargs={
            "vuelo_id": str(vuelo.id),
            "lote_id": str(lote.id),
            "minio_key": key,
            "sensor": sensor.value,
            "indice": "ndvi",
        },
        queue="gis",
    )

    vuelo.archivo_original = key
    vuelo.task_id = task.id
    await db.flush()

    return LoteDesdeGeotiffResponse(
        lote_id=lote.id,
        vuelo_id=vuelo.id,
        sensor=vuelo.sensor,
        estado=vuelo.estado,
        task_id=task.id,
        created_at=vuelo.created_at,
    )


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
            "lote_id": str(lote_id),
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


async def listar_vuelos(
    db: AsyncSession,
    lote_id: uuid.UUID,
) -> list[Vuelo]:
    stmt = (
        select(Vuelo)
        .where(Vuelo.lote_id == lote_id, Vuelo.deleted_at.is_(None))
        .order_by(Vuelo.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def obtener_vuelo(
    db: AsyncSession,
    lote_id: uuid.UUID,
    vuelo_id: uuid.UUID,
) -> Vuelo | None:
    stmt = select(Vuelo).where(
        Vuelo.id == vuelo_id, Vuelo.lote_id == lote_id, Vuelo.deleted_at.is_(None)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def eliminar_vuelo(db: AsyncSession, vuelo: Vuelo) -> None:
    """Soft delete — nunca DELETE físico."""
    vuelo.deleted_at = datetime.now(timezone.utc)
    await db.flush()


async def reintentar_vuelo(db: AsyncSession, vuelo: Vuelo) -> Vuelo:
    """Reencola el mismo GeoTIFF ya subido a MinIO, sin pedir un nuevo upload."""
    task = celery_app.send_task(
        "workers.gis.tasks.procesar_vuelo",
        kwargs={
            "vuelo_id": str(vuelo.id),
            "lote_id": str(vuelo.lote_id),
            "minio_key": vuelo.archivo_original,
            "sensor": vuelo.sensor.value,
            "indice": "ndvi",
        },
        queue="gis",
    )
    vuelo.estado = EstadoVueloEnum.pendiente
    vuelo.error_detalle = None
    vuelo.task_id = task.id
    await db.flush()
    await db.refresh(vuelo)
    return vuelo


async def obtener_resultado_geojson(
    db: AsyncSession,
    lote_id: uuid.UUID,
    vuelo_id: uuid.UUID,
) -> dict | None:
    stmt = select(Vuelo).where(
        Vuelo.id == vuelo_id, Vuelo.lote_id == lote_id, Vuelo.deleted_at.is_(None)
    )
    result = await db.execute(stmt)
    vuelo = result.scalar_one_or_none()
    if vuelo is None or vuelo.estado != EstadoVueloEnum.completado:
        return None

    # Usar geojson_key guardado por el worker; fallback a derivación legacy
    geojson_key = vuelo.geojson_key
    if geojson_key is None and vuelo.archivo_original:
        partes = vuelo.archivo_original.split("/")
        geojson_key = "/".join(partes[:3]) + "/zonas.geojson"

    if geojson_key is None:
        return None

    try:
        data = download_bytes(geojson_key)
        return json.loads(data)
    except Exception:
        return None


async def obtener_estado_vuelo(
    db: AsyncSession,
    lote_id: uuid.UUID,
    vuelo_id: uuid.UUID,
) -> EstadoVueloResponse | None:
    stmt = select(Vuelo).where(
        Vuelo.id == vuelo_id, Vuelo.lote_id == lote_id, Vuelo.deleted_at.is_(None)
    )
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


# ── Índices adicionales sobre un vuelo (NDRE, SAVI, ExG) ─────────────────────
# El primer índice (NDVI) se calcula siempre al subir el vuelo y su estado
# real vive en Vuelo (estado/task_id/geojson_key) — estas funciones son solo
# para índices adicionales que el usuario pide analizar después.

async def listar_analisis_indices(db: AsyncSession, vuelo: Vuelo) -> list[IndiceAnalisisItem]:
    items = [
        IndiceAnalisisItem(
            indice=IndiceEnum.ndvi,
            estado=vuelo.estado,
            task_id=vuelo.task_id,
            error=vuelo.error_detalle,
            es_primario=True,
        )
    ]
    stmt = (
        select(AnalisisIndice)
        .where(AnalisisIndice.vuelo_id == vuelo.id)
        .order_by(AnalisisIndice.created_at)
    )
    result = await db.execute(stmt)
    for a in result.scalars().all():
        items.append(IndiceAnalisisItem(
            indice=a.indice, estado=a.estado, task_id=a.task_id, error=a.error_detalle, es_primario=False,
        ))
    return items


async def obtener_analisis_indice(
    db: AsyncSession, vuelo_id: uuid.UUID, indice: IndiceEnum,
) -> AnalisisIndice | None:
    stmt = select(AnalisisIndice).where(
        AnalisisIndice.vuelo_id == vuelo_id, AnalisisIndice.indice == indice
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def crear_analisis_indice(
    db: AsyncSession, vuelo: Vuelo, indice: IndiceEnum, metodo_umbral: str = "fijo",
) -> AnalisisIndice:
    """Crea (o reencola si ya se había pedido) el análisis de un índice
    adicional, reusando el mismo GeoTIFF ya subido — sin pedir un nuevo upload."""
    analisis = await obtener_analisis_indice(db, vuelo.id, indice)
    if analisis is None:
        analisis = AnalisisIndice(vuelo_id=vuelo.id, indice=indice, estado=EstadoVueloEnum.pendiente)
        db.add(analisis)
    else:
        analisis.estado = EstadoVueloEnum.pendiente
        analisis.error_detalle = None
    await db.flush()
    await db.refresh(analisis)

    task = celery_app.send_task(
        "workers.gis.tasks.analizar_indice",
        kwargs={
            "analisis_id": str(analisis.id),
            "minio_key": vuelo.archivo_original,
            "sensor": vuelo.sensor.value,
            "indice": indice.value,
            "metodo_umbral": metodo_umbral,
        },
        queue="gis",
    )
    analisis.task_id = task.id
    await db.flush()
    await db.refresh(analisis)
    return analisis


async def obtener_estado_analisis_indice(
    db: AsyncSession, vuelo_id: uuid.UUID, indice: IndiceEnum,
) -> IndiceEstadoResponse | None:
    analisis = await obtener_analisis_indice(db, vuelo_id, indice)
    if analisis is None:
        return None

    progreso: int | None = None
    mensaje: str | None = None
    if analisis.task_id and analisis.estado in (EstadoVueloEnum.pendiente, EstadoVueloEnum.procesando):
        ar = AsyncResult(analisis.task_id, app=celery_app)
        if isinstance(ar.info, dict):
            progreso = ar.info.get("progreso")
            mensaje = ar.info.get("mensaje")

    return IndiceEstadoResponse(
        indice=analisis.indice,
        estado=analisis.estado,
        task_id=analisis.task_id,
        progreso=progreso,
        mensaje=mensaje,
        error=analisis.error_detalle,
    )


async def obtener_resultado_geojson_indice(
    db: AsyncSession, vuelo_id: uuid.UUID, indice: IndiceEnum,
) -> dict | None:
    analisis = await obtener_analisis_indice(db, vuelo_id, indice)
    if analisis is None or analisis.estado != EstadoVueloEnum.completado or analisis.geojson_key is None:
        return None
    try:
        data = download_bytes(analisis.geojson_key)
        return json.loads(data)
    except Exception:
        return None
