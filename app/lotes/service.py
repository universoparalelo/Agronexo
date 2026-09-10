import json
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from geoalchemy2.functions import ST_Area, ST_AsGeoJSON, ST_GeomFromGeoJSON, ST_Transform
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.lotes.models import Lote
from app.lotes.schemas import AREA_MAX_HA, AREA_MIN_HA, LoteCreate, LoteUpdate


def _validar_rango_area(area_ha: float) -> None:
    if area_ha < AREA_MIN_HA or area_ha > AREA_MAX_HA:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"El área del polígono ({area_ha:.2f} ha) está fuera del rango "
                f"esperado para un lote agrícola ({AREA_MIN_HA}-{AREA_MAX_HA} ha)."
            ),
        )


async def crear_lote(db: AsyncSession, data: LoteCreate, usuario_id: uuid.UUID | None = None) -> Lote:
    geometry = None
    area_ha = None

    if data.geometry is not None:
        geojson_str = json.dumps(data.geometry)
        # Calcular área en hectáreas con PostGIS:
        # ST_Transform a EPSG:32721 (UTM zona 21 Sur, metros) para que ST_Area devuelva m²
        area_query = select(
            ST_Area(ST_Transform(ST_GeomFromGeoJSON(geojson_str), 32721)) / 10000
        )
        result = await db.execute(area_query)
        area_ha = round(result.scalar(), 4)
        _validar_rango_area(area_ha)
        geometry = ST_GeomFromGeoJSON(geojson_str)

    lote = Lote(
        nombre=data.nombre,
        cultivo=data.cultivo,
        estadio_fenologico=data.estadio_fenologico,
        variedad=data.variedad,
        tipo_suelo=data.tipo_suelo,
        fecha_siembra=data.fecha_siembra,
        geometry=geometry,
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


async def obtener_lote(db: AsyncSession, lote_id: uuid.UUID, usuario_id: uuid.UUID | None = None) -> Lote | None:
    stmt = select(Lote).where(Lote.id == lote_id, Lote.deleted_at.is_(None))
    if usuario_id is not None:
        stmt = stmt.where(Lote.usuario_id == usuario_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def actualizar_lote(db: AsyncSession, lote: Lote, data: LoteUpdate) -> Lote:
    if data.nombre is not None:
        lote.nombre = data.nombre
    if data.cultivo is not None:
        lote.cultivo = data.cultivo
    if data.estadio_fenologico is not None:
        lote.estadio_fenologico = data.estadio_fenologico
    if data.variedad is not None:
        lote.variedad = data.variedad
    if data.tipo_suelo is not None:
        lote.tipo_suelo = data.tipo_suelo
    if data.fecha_siembra is not None:
        lote.fecha_siembra = data.fecha_siembra
    if data.geometry is not None:
        geojson_str = json.dumps(data.geometry)
        area_query = select(
            ST_Area(ST_Transform(ST_GeomFromGeoJSON(geojson_str), 32721)) / 10000
        )
        result = await db.execute(area_query)
        area_ha = round(result.scalar(), 4)
        _validar_rango_area(area_ha)
        lote.geometry = ST_GeomFromGeoJSON(geojson_str)
        lote.area_ha = area_ha

    lote.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(lote)
    return lote


async def eliminar_lote(db: AsyncSession, lote: Lote) -> None:
    """Soft delete — nunca DELETE físico."""
    lote.deleted_at = datetime.now(timezone.utc)
    await db.flush()
