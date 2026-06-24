import json
import uuid
from datetime import datetime, timezone

from geoalchemy2.functions import ST_Area, ST_AsGeoJSON, ST_GeomFromGeoJSON, ST_Transform
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.lotes.models import Lote, Vuelo
from app.lotes.schemas import LoteCreate, LoteUpdate


async def crear_lote(db: AsyncSession, data: LoteCreate, usuario_id: uuid.UUID | None = None) -> Lote:
    geojson_str = json.dumps(data.geometry)

    # Calcular área en hectáreas con PostGIS:
    # ST_Transform a EPSG:32721 (UTM zona 21 Sur, metros) para que ST_Area devuelva m²
    area_query = select(
        ST_Area(ST_Transform(ST_GeomFromGeoJSON(geojson_str), 32721)) / 10000
    )
    result = await db.execute(area_query)
    area_ha = round(result.scalar(), 4)

    lote = Lote(
        nombre=data.nombre,
        cultivo=data.cultivo,
        estadio_fenologico=data.estadio_fenologico,
        geometry=ST_GeomFromGeoJSON(geojson_str),
        area_ha=area_ha,
        usuario_id=usuario_id,
    )
    db.add(lote)
    await db.flush()
    await db.refresh(lote)
    return lote


async def listar_lotes(db: AsyncSession, usuario_id: uuid.UUID | None = None) -> list[Lote]:
    stmt = select(Lote).where(Lote.deleted_at.is_(None))
    if usuario_id is not None:
        stmt = stmt.where(Lote.usuario_id == usuario_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def obtener_lote(db: AsyncSession, lote_id: uuid.UUID) -> Lote | None:
    stmt = select(Lote).where(Lote.id == lote_id, Lote.deleted_at.is_(None))
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def actualizar_lote(db: AsyncSession, lote: Lote, data: LoteUpdate) -> Lote:
    if data.nombre is not None:
        lote.nombre = data.nombre
    if data.cultivo is not None:
        lote.cultivo = data.cultivo
    if data.estadio_fenologico is not None:
        lote.estadio_fenologico = data.estadio_fenologico
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
    return lote


async def eliminar_lote(db: AsyncSession, lote: Lote) -> None:
    """Soft delete — nunca DELETE físico."""
    lote.deleted_at = datetime.now(timezone.utc)
    await db.flush()


async def listar_vuelos(db: AsyncSession, lote_id: uuid.UUID) -> list[Vuelo]:
    stmt = select(Vuelo).where(Vuelo.lote_id == lote_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())
