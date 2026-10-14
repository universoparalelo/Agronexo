"""
Precios de productos fitosanitarios (HU-R4-11, tabla creada en la
migración 0023 de HU-R4-05). Única lógica de negocio: resolver qué precio
usar para un producto — el cargado por el usuario si es reciente, si no
el de referencia del relevamiento inicial.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.diagnostico.models import PrecioProducto

_VIGENCIA_PRECIO_USUARIO_DIAS = 90


async def resolver_precio(db: AsyncSession, producto_id: uuid.UUID) -> PrecioProducto | None:
    """Prioriza el precio tipo 'usuario' más reciente si tiene menos de 90
    días; si no hay uno vigente, cae al 'referencia' más reciente."""
    limite = date.today() - timedelta(days=_VIGENCIA_PRECIO_USUARIO_DIAS)
    stmt_usuario = (
        select(PrecioProducto)
        .where(
            PrecioProducto.producto_id == producto_id,
            PrecioProducto.tipo == "usuario",
            PrecioProducto.fecha >= limite,
        )
        .order_by(PrecioProducto.fecha.desc())
        .limit(1)
    )
    resultado = await db.execute(stmt_usuario)
    precio = resultado.scalar_one_or_none()
    if precio is not None:
        return precio

    stmt_referencia = (
        select(PrecioProducto)
        .where(PrecioProducto.producto_id == producto_id, PrecioProducto.tipo == "referencia")
        .order_by(PrecioProducto.fecha.desc())
        .limit(1)
    )
    resultado = await db.execute(stmt_referencia)
    return resultado.scalar_one_or_none()


async def listar_precios(db: AsyncSession, producto_id: uuid.UUID) -> list[PrecioProducto]:
    stmt = (
        select(PrecioProducto)
        .where(PrecioProducto.producto_id == producto_id)
        .order_by(PrecioProducto.fecha.desc())
    )
    resultado = await db.execute(stmt)
    return list(resultado.scalars().all())


async def crear_precio_usuario(
    db: AsyncSession, producto_id: uuid.UUID, precio_usd: float, unidad: str, fecha: date,
) -> PrecioProducto:
    precio = PrecioProducto(
        producto_id=producto_id, precio_usd=precio_usd, unidad=unidad, fecha=fecha, tipo="usuario",
    )
    db.add(precio)
    await db.commit()
    await db.refresh(precio)
    return precio
