import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import Usuario
from app.core.database import get_db
from app.lotes import service
from app.lotes.models import CultivoEnum, EstadoVueloEnum
from app.lotes.schemas import (
    CultivoCreate,
    CultivoResponse,
    CultivoUpdate,
    LoteCreate,
    LoteListResponse,
    LoteResponse,
    LoteUpdate,
)

router = APIRouter()


async def _get_lote_o_404(lote_id: uuid.UUID, db: AsyncSession, usuario_id: uuid.UUID) -> service.Lote:
    lote = await service.obtener_lote(db, lote_id, usuario_id)
    if not lote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado")
    return lote


@router.get("", response_model=LoteListResponse)
async def listar_lotes(
    q: str | None = Query(None, description="Buscar por nombre del lote"),
    cultivo: CultivoEnum | None = Query(None, description="Filtrar por el cultivo actual del lote"),
    campana: int | None = Query(None, description="Filtrar por año de siembra del cultivo actual"),
    estado: EstadoVueloEnum | None = Query(None, description="Filtrar por estado del último análisis"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    lotes, total = await service.listar_lotes(
        db, usuario_id=uuid.UUID(current_user.id),
        q=q, cultivo=cultivo, campana=campana, estado=estado,
        page=page, page_size=page_size,
    )
    return LoteListResponse(total=total, page=page, page_size=page_size, items=lotes)


@router.post("", response_model=LoteResponse, status_code=status.HTTP_201_CREATED)
async def crear_lote(
    data: LoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return await service.crear_lote(db, data, usuario_id=uuid.UUID(current_user.id))


@router.get("/{lote_id}", response_model=LoteResponse)
async def obtener_lote(
    lote_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return await _get_lote_o_404(lote_id, db, uuid.UUID(current_user.id))


@router.put("/{lote_id}", response_model=LoteResponse)
async def actualizar_lote(
    lote_id: uuid.UUID,
    data: LoteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    lote = await _get_lote_o_404(lote_id, db, uuid.UUID(current_user.id))
    return await service.actualizar_lote(db, lote, data)


@router.delete("/{lote_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_lote(
    lote_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    lote = await _get_lote_o_404(lote_id, db, uuid.UUID(current_user.id))
    await service.eliminar_lote(db, lote)


@router.get("/{lote_id}/historial")
async def historial_lote(
    lote_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await _get_lote_o_404(lote_id, db, uuid.UUID(current_user.id))
    return {"lote_id": str(lote_id), "intervenciones": []}


# ── Cultivos del lote ───────────────────────────────────────────────

async def _get_cultivo_o_404(lote_id: uuid.UUID, cultivo_id: uuid.UUID, db: AsyncSession):
    cultivo = await service.obtener_cultivo(db, lote_id, cultivo_id)
    if not cultivo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cultivo no encontrado")
    return cultivo


@router.get("/{lote_id}/cultivos", response_model=list[CultivoResponse])
async def listar_cultivos(
    lote_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await _get_lote_o_404(lote_id, db, uuid.UUID(current_user.id))
    return await service.listar_cultivos(db, lote_id)


@router.post("/{lote_id}/cultivos", response_model=CultivoResponse, status_code=status.HTTP_201_CREATED)
async def crear_cultivo(
    lote_id: uuid.UUID,
    data: CultivoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await _get_lote_o_404(lote_id, db, uuid.UUID(current_user.id))
    return await service.crear_cultivo(db, lote_id, data)


@router.put("/{lote_id}/cultivos/{cultivo_id}", response_model=CultivoResponse)
async def actualizar_cultivo(
    lote_id: uuid.UUID,
    cultivo_id: uuid.UUID,
    data: CultivoUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await _get_lote_o_404(lote_id, db, uuid.UUID(current_user.id))
    cultivo = await _get_cultivo_o_404(lote_id, cultivo_id, db)
    return await service.actualizar_cultivo(db, cultivo, data)


@router.delete("/{lote_id}/cultivos/{cultivo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_cultivo(
    lote_id: uuid.UUID,
    cultivo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await _get_lote_o_404(lote_id, db, uuid.UUID(current_user.id))
    cultivo = await _get_cultivo_o_404(lote_id, cultivo_id, db)
    await service.eliminar_cultivo(db, cultivo)
