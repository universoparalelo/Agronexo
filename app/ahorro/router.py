import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ahorro import service
from app.ahorro.schemas import AhorroComparativoResponse, AhorroVueloResponse
from app.auth.dependencies import get_current_user
from app.auth.models import Usuario
from app.core.database import get_db
from app.ingesta.service import obtener_vuelo
from app.lotes.service import obtener_cultivo, obtener_lote

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/{lote_id}/vuelos/{vuelo_id}/ahorro",
    response_model=AhorroVueloResponse,
    summary="Ahorro de aplicación variable vs. uniforme de un vuelo puntual (HU-R4-11)",
)
async def ahorro_vuelo(
    lote_id: uuid.UUID,
    vuelo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    lote = await obtener_lote(db, lote_id, usuario_id=uuid.UUID(str(current_user.id)))
    if not lote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado.")

    vuelo = await obtener_vuelo(db, lote_id, vuelo_id)
    if not vuelo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vuelo no encontrado.")

    try:
        resultado = await service.calcular_ahorro_del_vuelo(db, lote, vuelo)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error calculando ahorro para vuelo %s del lote %s", vuelo_id, lote_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No se pudo calcular el ahorro.",
        )

    if resultado is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diagnóstico no disponible. El vuelo debe estar en estado 'completado' y tener NDVI calculado.",
        )
    return resultado


@router.get(
    "/{lote_id}/ahorro-comparativo",
    response_model=AhorroComparativoResponse,
    summary="Ahorro acumulado de una campaña, o comparado contra otra del mismo lote (HU-R4-11)",
)
async def ahorro_comparativo(
    lote_id: uuid.UUID,
    cultivo_a: uuid.UUID = Query(..., description="Campaña principal a mostrar"),
    cultivo_b: uuid.UUID | None = Query(None, description="Campaña opcional para comparar contra cultivo_a"),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    lote = await obtener_lote(db, lote_id, usuario_id=uuid.UUID(str(current_user.id)))
    if not lote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado.")
    if lote.area_ha is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El lote todavía no tiene límites cargados — no se puede calcular la superficie uniforme.",
        )

    cultivo_obj_a = await obtener_cultivo(db, lote_id, cultivo_a)
    if not cultivo_obj_a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaña (cultivo_a) no encontrada.")

    cultivo_obj_b = None
    if cultivo_b is not None:
        cultivo_obj_b = await obtener_cultivo(db, lote_id, cultivo_b)
        if not cultivo_obj_b:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaña (cultivo_b) no encontrada.")

    try:
        campana_a = await service.calcular_ahorro_de_campana(db, lote, cultivo_obj_a)
        campana_b = (
            await service.calcular_ahorro_de_campana(db, lote, cultivo_obj_b) if cultivo_obj_b else None
        )
    except Exception:
        logger.exception("Error calculando ahorro comparativo para lote %s", lote_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No se pudo calcular el ahorro comparativo.",
        )

    return AhorroComparativoResponse(
        lote_id=lote.id,
        area_total_lote_ha=lote.area_ha,
        campana_a=campana_a,
        campana_b=campana_b,
    )
