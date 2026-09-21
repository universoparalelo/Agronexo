import json
import uuid
from datetime import datetime, timezone

from celery.result import AsyncResult
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.storage import download_bytes
from app.ingesta.schemas import EstadoVueloResponse, IndiceAnalisisItem, IndiceEstadoResponse, LoteDesdeGeotiffResponse
from app.lotes.models import AnalisisIndice, Cultivo, CultivoEnum, EstadoVueloEnum, IndiceEnum, Lote, SensorEnum, Vuelo
from workers.celery_app import celery_app


async def crear_lote_y_vuelo_desde_geotiff(
    db: AsyncSession,
    usuario_id: uuid.UUID,
    nombre: str,
    cultivo: CultivoEnum,
    sensor: SensorEnum,
    file_stream,
    file_size: int = -1,
    estadio_fenologico: str | None = None,
) -> LoteDesdeGeotiffResponse:
    lote = Lote(
        nombre=nombre,
        usuario_id=usuario_id,
        geometry=None,
    )
    db.add(lote)
    await db.flush()
    await db.refresh(lote)

    cultivo_lote = Cultivo(lote_id=lote.id, tipo_cultivo=cultivo)
    db.add(cultivo_lote)
    await db.flush()

    vuelo = Vuelo(
        lote_id=lote.id,
        cultivo_id=cultivo_lote.id,
        sensor=sensor,
        fecha_vuelo=datetime.now(timezone.utc),
        estadio_fenologico=estadio_fenologico,
        estado=EstadoVueloEnum.pendiente,
    )
    db.add(vuelo)
    await db.flush()
    await db.refresh(vuelo)

    from app.core.storage import upload_geotiff_stream
    key = upload_geotiff_stream(
        usuario_id=str(usuario_id),
        lote_id=str(lote.id),
        vuelo_id=str(vuelo.id),
        stream=file_stream,
        length=file_size,
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
    file_stream,
    file_size: int = -1,
    estadio_fenologico: str | None = None,
    cultivo_id: uuid.UUID | None = None,
) -> Vuelo:
    vuelo = Vuelo(
        lote_id=lote_id,
        cultivo_id=cultivo_id,
        sensor=sensor,
        fecha_vuelo=fecha_vuelo,
        estadio_fenologico=estadio_fenologico,
        estado=EstadoVueloEnum.pendiente,
    )
    db.add(vuelo)
    await db.flush()
    await db.refresh(vuelo)

    from app.core.storage import upload_geotiff_stream
    key = upload_geotiff_stream(
        usuario_id=str(usuario_id),
        lote_id=str(lote_id),
        vuelo_id=str(vuelo.id),
        stream=file_stream,
        length=file_size,
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


async def buscar_imagenes_satelitales(lote: Lote, fecha: str, ventana_dias: int = 15) -> list[dict]:
    """
    Lista escenas Sentinel-2 candidatas para el lote (vía Earth Search, sin
    auth) en una ventana de fechas alrededor de `fecha` — no descarga nada,
    solo consulta el catálogo, así que corre síncrono en threadpool en vez
    de encolarse en Celery (no es "procesamiento de GeoTIFF", es una
    consulta HTTP liviana).
    """
    from geoalchemy2.shape import to_shape
    from shapely.geometry import mapping

    from workers.gis.satelital_catalogo import bbox_de_poligono, buscar_escenas

    poligono = mapping(to_shape(lote.geometry))
    bbox = bbox_de_poligono(poligono)

    features = await run_in_threadpool(buscar_escenas, bbox, fecha, ventana_dias)
    return [
        {
            "escena_id": f["id"],
            "fecha": f["properties"]["datetime"][:10],
            "nubes_pct": f["properties"].get("eo:cloud_cover"),
            "dias_diferencia": f["_dias_de_diferencia"],
            # Preview JPG liviano (no es la banda completa) — deja ver la
            # escena real antes de descargar/recortar nada.
            "thumbnail_url": f.get("assets", {}).get("thumbnail", {}).get("href"),
        }
        for f in features
    ]


async def crear_vuelo_desde_satelite(
    db: AsyncSession,
    lote_id: uuid.UUID,
    usuario_id: uuid.UUID,
    escena_id: str,
    fecha_vuelo: datetime,
    estadio_fenologico: str | None = None,
    indices: list[IndiceEnum] | None = None,
    cultivo_id: uuid.UUID | None = None,
) -> Vuelo:
    """
    Crea el Vuelo y encola workers.gis.tasks.descargar_satelital, que
    descarga+recorta la escena elegida, la sube a MinIO y de ahí encola
    procesar_vuelo — mismo pipeline final que subir un GeoTIFF de dron.
    """
    vuelo = Vuelo(
        lote_id=lote_id,
        cultivo_id=cultivo_id,
        sensor=SensorEnum.sentinel2,
        fecha_vuelo=fecha_vuelo,
        estadio_fenologico=estadio_fenologico,
        estado=EstadoVueloEnum.pendiente,
    )
    db.add(vuelo)
    await db.flush()
    await db.refresh(vuelo)

    # El archivo recién existe cuando el worker termina de descargar, así que
    # el batch de índices adicionales lo encola descargar_satelital, no la API.
    indices_adicionales = [i for i in (indices or []) if i != IndiceEnum.ndvi]
    filas = await _preparar_filas_indices(db, vuelo, indices_adicionales) if indices_adicionales else {}

    task = celery_app.send_task(
        "workers.gis.tasks.descargar_satelital",
        kwargs={
            "analisis_ids": {indice: str(fila.id) for indice, fila in filas.items()},
            "vuelo_id": str(vuelo.id),
            "lote_id": str(lote_id),
            "usuario_id": str(usuario_id),
            "escena_id": escena_id,
            "sensor": "sentinel2",
        },
        queue="gis",
    )
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
        data = await run_in_threadpool(download_bytes, geojson_key)
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


async def _preparar_filas_indices(
    db: AsyncSession, vuelo: Vuelo, indices: list[IndiceEnum],
) -> dict[str, AnalisisIndice]:
    filas: dict[str, AnalisisIndice] = {}
    for indice in indices:
        analisis = await obtener_analisis_indice(db, vuelo.id, indice)
        if analisis is None:
            analisis = AnalisisIndice(vuelo_id=vuelo.id, indice=indice, estado=EstadoVueloEnum.pendiente)
            db.add(analisis)
        else:
            analisis.estado = EstadoVueloEnum.pendiente
            analisis.error_detalle = None
        filas[indice.value] = analisis
    await db.flush()
    for analisis in filas.values():
        await db.refresh(analisis)
    return filas


async def crear_analisis_indices_batch(
    db: AsyncSession, vuelo: Vuelo, indices: list[IndiceEnum], metodo_umbral: str = "fijo",
) -> list[AnalisisIndice]:
    """
    Crea (o reencola) una fila AnalisisIndice por cada índice pedido y
    encola UNA sola task de Celery que los calcula todos en una corrida
    (descarga y lectura de bandas compartida), en lugar de una task por
    índice como hace crear_analisis_indice. Pensada para cuando el usuario
    tilda varios índices a la vez al subir un vuelo.
    """
    filas = await _preparar_filas_indices(db, vuelo, indices)

    task = celery_app.send_task(
        "workers.gis.tasks.analizar_indices_batch",
        kwargs={
            "analisis_ids": {indice: str(fila.id) for indice, fila in filas.items()},
            "minio_key": vuelo.archivo_original,
            "sensor": vuelo.sensor.value,
            "indices": list(filas.keys()),
            "metodo_umbral": metodo_umbral,
        },
        queue="gis",
    )
    for analisis in filas.values():
        analisis.task_id = task.id
    await db.flush()
    for analisis in filas.values():
        await db.refresh(analisis)
    return list(filas.values())


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
        data = await run_in_threadpool(download_bytes, analisis.geojson_key)
        return json.loads(data)
    except Exception:
        return None
