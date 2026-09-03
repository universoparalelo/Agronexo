import json
import uuid
from datetime import datetime, timezone

from geoalchemy2.functions import ST_Area, ST_AsGeoJSON, ST_GeomFromGeoJSON, ST_Transform
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.lotes.models import Cultivo, CultivoEnum, Lote, ProvinciaEnum, Suelo, Ubicacion
from app.lotes.schemas import LoteCreate, LoteUpdate


async def crear_lote(db: AsyncSession, data: LoteCreate, usuario_id: uuid.UUID | None = None) -> Lote:
    """El límite geográfico no se pide al crear — lo deriva el worker del
    bounding box del primer GeoTIFF subido como vuelo. La ubicación
    (departamento/localidad) sí es opcional acá — si no se carga, se puede
    completar después al subir un vuelo."""
    lote = Lote(
        nombre=data.nombre,
        suelo_id=data.suelo_id,
        usuario_id=usuario_id,
    )
    if data.provincia:
        ubicacion = await obtener_o_crear_ubicacion(db, data.provincia, data.departamento, data.localidad)
        lote.ubicacion_id = ubicacion.id

    db.add(lote)
    await db.flush()
    await db.refresh(lote)
    await db.refresh(lote, attribute_names=["suelo", "ubicacion", "cultivos"])
    return lote


async def listar_lotes(db: AsyncSession, usuario_id: uuid.UUID | None = None) -> list[Lote]:
    stmt = select(Lote).where(Lote.deleted_at.is_(None))
    if usuario_id is not None:
        stmt = stmt.where(Lote.usuario_id == usuario_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def obtener_lote(db: AsyncSession, lote_id: uuid.UUID, usuario_id: uuid.UUID | None = None) -> Lote | None:
    stmt = select(Lote).where(Lote.id == lote_id, Lote.deleted_at.is_(None))
    if usuario_id is not None:
        stmt = stmt.where(Lote.usuario_id == usuario_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def actualizar_lote(db: AsyncSession, lote: Lote, data: LoteUpdate) -> Lote:
    if data.nombre is not None:
        lote.nombre = data.nombre
    if data.suelo_id is not None:
        lote.suelo_id = data.suelo_id
    if data.ubicacion_id is not None:
        lote.ubicacion_id = data.ubicacion_id
    if data.geometry is not None:
        geojson_str = json.dumps(data.geometry)
        lote.geometry = ST_GeomFromGeoJSON(geojson_str)
        area_query = select(
            ST_Area(ST_Transform(ST_GeomFromGeoJSON(geojson_str), 32721)) / 10000
        )
        result = await db.execute(area_query)
        lote.area_ha = round(result.scalar(), 4)

    lote.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(lote)
    await db.refresh(lote, attribute_names=["suelo", "ubicacion", "cultivos"])
    return lote


async def eliminar_lote(db: AsyncSession, lote: Lote) -> None:
    """Soft delete — nunca DELETE físico."""
    lote.deleted_at = datetime.now(timezone.utc)
    await db.flush()


# ── Catálogo de suelos ───────────────────────────────────────────────

async def listar_suelos(db: AsyncSession) -> list[Suelo]:
    result = await db.execute(select(Suelo).order_by(Suelo.tipo))
    return list(result.scalars().all())


async def obtener_suelo(db: AsyncSession, suelo_id: uuid.UUID) -> Suelo | None:
    result = await db.execute(select(Suelo).where(Suelo.id == suelo_id))
    return result.scalar_one_or_none()


# ── Ubicación (provincia/departamento/localidad) ───────────────────────

async def obtener_o_crear_ubicacion(
    db: AsyncSession, provincia: ProvinciaEnum, departamento: str | None = None, localidad: str | None = None,
) -> Ubicacion:
    """Busca una ubicación existente por (provincia, departamento, localidad)
    sin distinguir mayúsculas/minúsculas en departamento/localidad; si no
    existe, la crea. Solo provincia es obligatoria — departamento y
    localidad son datos que no todos los usuarios conocen de memoria."""
    stmt = select(Ubicacion).where(Ubicacion.provincia == provincia)
    if departamento:
        stmt = stmt.where(func.lower(Ubicacion.departamento) == departamento.strip().lower())
    else:
        stmt = stmt.where(Ubicacion.departamento.is_(None))
    if localidad:
        stmt = stmt.where(func.lower(Ubicacion.localidad) == localidad.strip().lower())
    else:
        stmt = stmt.where(Ubicacion.localidad.is_(None))
    result = await db.execute(stmt)
    ubicacion = result.scalar_one_or_none()
    if ubicacion is None:
        ubicacion = Ubicacion(
            provincia=provincia,
            departamento=departamento.strip() if departamento else None,
            localidad=localidad.strip() if localidad else None,
        )
        db.add(ubicacion)
        await db.flush()
        await db.refresh(ubicacion)
    return ubicacion


# ── Ciclos de cultivo ──────────────────────────────────────────────────

async def listar_cultivos_lote(db: AsyncSession, lote_id: uuid.UUID) -> list[Cultivo]:
    stmt = (
        select(Cultivo)
        .where(Cultivo.lote_id == lote_id)
        .order_by(Cultivo.fecha_siembra.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def crear_ciclo_cultivo(
    db: AsyncSession,
    lote_id: uuid.UUID,
    cultivo: CultivoEnum,
    fecha_siembra,
    estadio_fenologico: str | None = None,
    fecha_cosecha_estimada=None,
) -> Cultivo:
    """Crea un nuevo ciclo activo para el lote y desactiva cualquier otro
    ciclo que estuviera activo — solo uno vigente a la vez."""
    stmt = select(Cultivo).where(Cultivo.lote_id == lote_id, Cultivo.activo.is_(True))
    result = await db.execute(stmt)
    for anterior in result.scalars().all():
        anterior.activo = False

    nuevo = Cultivo(
        lote_id=lote_id,
        cultivo=cultivo,
        estadio_fenologico=estadio_fenologico,
        fecha_siembra=fecha_siembra,
        fecha_cosecha_estimada=fecha_cosecha_estimada,
        activo=True,
    )
    db.add(nuevo)
    await db.flush()
    await db.refresh(nuevo)
    return nuevo
