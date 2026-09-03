import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import Usuario
from app.core.database import get_db
from app.lotes import service
from app.lotes.schemas import CultivoResponse, LoteCreate, LoteListResponse, LoteResponse, LoteUpdate, SueloResponse

router = APIRouter()


@router.get("/suelos", response_model=list[SueloResponse])
async def listar_suelos(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return await service.listar_suelos(db)


async def _get_lote_o_404(lote_id: uuid.UUID, db: AsyncSession, usuario_id: uuid.UUID) -> service.Lote:
    lote = await service.obtener_lote(db, lote_id, usuario_id)
    if not lote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado")
    return lote


@router.get("", response_model=LoteListResponse)
async def listar_lotes(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    lotes = await service.listar_lotes(db, usuario_id=uuid.UUID(current_user.id))
    return LoteListResponse(total=len(lotes), items=lotes)


@router.post("", response_model=LoteResponse, status_code=status.HTTP_201_CREATED)
async def crear_lote(
    data: LoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    suelo = await service.obtener_suelo(db, data.suelo_id)
    if not suelo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suelo no encontrado.")
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
    if data.suelo_id is not None:
        suelo = await service.obtener_suelo(db, data.suelo_id)
        if not suelo:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suelo no encontrado.")
    return await service.actualizar_lote(db, lote, data)


@router.delete("/{lote_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_lote(
    lote_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    lote = await _get_lote_o_404(lote_id, db, uuid.UUID(current_user.id))
    await service.eliminar_lote(db, lote)


@router.get("/{lote_id}/cultivos", response_model=list[CultivoResponse])
async def listar_cultivos_lote(
    lote_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await _get_lote_o_404(lote_id, db, uuid.UUID(current_user.id))
    return await service.listar_cultivos_lote(db, lote_id)


@router.get("/{lote_id}/historial")
async def historial_lote(
    lote_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await _get_lote_o_404(lote_id, db, uuid.UUID(current_user.id))
    return {"lote_id": str(lote_id), "intervenciones": []}
