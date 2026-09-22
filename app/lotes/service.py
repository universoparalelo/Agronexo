import json
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from geoalchemy2.functions import ST_Area, ST_AsGeoJSON, ST_GeomFromGeoJSON, ST_Transform
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.lotes.models import Cultivo, Lote
from app.lotes.schemas import AREA_MAX_HA, AREA_MIN_HA, CultivoCreate, CultivoUpdate, LoteCreate, LoteUpdate


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
        tipo_suelo=data.tipo_suelo,
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
    if data.tipo_suelo is not None:
        lote.tipo_suelo = data.tipo_suelo
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


# ── Cultivos ────────────────────────────────────────────────────────

async def crear_cultivo(db: AsyncSession, lote_id: uuid.UUID, data: CultivoCreate) -> Cultivo:
    cultivo = Cultivo(
        lote_id=lote_id,
        tipo_cultivo=data.tipo_cultivo,
        variedad=data.variedad,
        fecha_siembra=data.fecha_siembra,
        fecha_cosecha=data.fecha_cosecha,
    )
    db.add(cultivo)
    await db.flush()
    await db.refresh(cultivo)
    return cultivo


async def listar_cultivos(db: AsyncSession, lote_id: uuid.UUID) -> list[Cultivo]:
    stmt = (
        select(Cultivo)
        .where(Cultivo.lote_id == lote_id, Cultivo.deleted_at.is_(None))
        .order_by(Cultivo.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def obtener_cultivo(db: AsyncSession, lote_id: uuid.UUID, cultivo_id: uuid.UUID) -> Cultivo | None:
    stmt = select(Cultivo).where(
        Cultivo.id == cultivo_id, Cultivo.lote_id == lote_id, Cultivo.deleted_at.is_(None)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def actualizar_cultivo(db: AsyncSession, cultivo: Cultivo, data: CultivoUpdate) -> Cultivo:
    campos = data.model_dump(exclude_unset=True)
    siembra = campos.get("fecha_siembra", cultivo.fecha_siembra)
    cosecha = campos.get("fecha_cosecha", cultivo.fecha_cosecha)
    if siembra and cosecha and cosecha < siembra:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="fecha_cosecha no puede ser anterior a fecha_siembra.",
        )
    for campo, valor in campos.items():
        if campo == "tipo_cultivo" and valor is None:
            continue
        setattr(cultivo, campo, valor)
    await db.flush()
    await db.refresh(cultivo)
    return cultivo


async def eliminar_cultivo(db: AsyncSession, cultivo: Cultivo) -> None:
    """Soft delete — los vuelos ya analizados conservan la referencia."""
    cultivo.deleted_at = datetime.now(timezone.utc)
    await db.flush()


async def resolver_cultivo_para_analisis(
    db: AsyncSession,
    lote_id: uuid.UUID,
    cultivo_id: uuid.UUID | None,
    nuevo: CultivoCreate | None,
) -> Cultivo:
    """
    Un análisis siempre se hace sobre un cultivo: uno ya cargado en el lote
    (cultivo_id) o uno nuevo que se crea en ese momento — exactamente uno de los dos.
    """
    if cultivo_id is not None and nuevo is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Indicá un cultivo existente o los datos de un cultivo nuevo, no ambos.",
        )
    if cultivo_id is not None:
        cultivo = await obtener_cultivo(db, lote_id, cultivo_id)
        if cultivo is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cultivo no encontrado en este lote.")
        return cultivo
    if nuevo is not None:
        return await crear_cultivo(db, lote_id, nuevo)
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Elegí un cultivo del lote o creá uno nuevo para poder analizar.",
    )
