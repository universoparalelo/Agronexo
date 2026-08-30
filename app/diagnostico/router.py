import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import Usuario
from app.core.database import get_db
from app.diagnostico import service
from app.diagnostico.models import CausaIndiceEnum, TipoProductoEnum
from app.diagnostico.schemas import ProductoFitosanitarioListResponse
from app.lotes.service import obtener_lote

logger = logging.getLogger(__name__)

router = APIRouter()
productos_router = APIRouter()


@productos_router.get(
    "",
    response_model=ProductoFitosanitarioListResponse,
    summary="Listar catálogo de productos fitosanitarios",
)
async def listar_productos(
    causa: CausaIndiceEnum | None = Query(None, description="Filtrar por causa diagnóstica"),
    tipo: TipoProductoEnum | None = Query(None, description="Filtrar por tipo de producto"),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    productos = await service.listar_productos(db, causa=causa, tipo=tipo)
    return ProductoFitosanitarioListResponse(total=len(productos), items=productos)


@router.get(
    "/{lote_id}/vuelos/{vuelo_id}/diagnostico",
    summary="Generar diagnóstico agronómico del vuelo (motor de reglas RFDR-01)",
)
async def diagnostico_vuelo(
    lote_id: uuid.UUID,
    vuelo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    lote = await obtener_lote(db, lote_id, usuario_id=uuid.UUID(str(current_user.id)))
    if not lote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado.")

    try:
        resultado = await service.generar_diagnostico(db, lote, vuelo_id)
    except Exception:
        logger.exception("Error generando diagnóstico para vuelo %s del lote %s", vuelo_id, lote_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo generar el diagnóstico.",
        )

    if resultado is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diagnóstico no disponible. El vuelo debe estar en estado 'completado' y tener NDVI calculado.",
        )
    return resultado
