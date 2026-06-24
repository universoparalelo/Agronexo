import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.lotes import service
from app.lotes.schemas import LoteCreate, LoteListResponse, LoteResponse, LoteUpdate, VueloResponse

router = APIRouter()


async def _get_lote_o_404(lote_id: uuid.UUID, db: AsyncSession) -> service.Lote:
    lote = await service.obtener_lote(db, lote_id)
    if not lote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado")
    return lote


@router.get("", response_model=LoteListResponse)
async def listar_lotes(db: AsyncSession = Depends(get_db)):
    lotes = await service.listar_lotes(db)
    return LoteListResponse(total=len(lotes), items=lotes)


@router.post("", response_model=LoteResponse, status_code=status.HTTP_201_CREATED)
async def crear_lote(data: LoteCreate, db: AsyncSession = Depends(get_db)):
    lote = await service.crear_lote(db, data)
    return lote


@router.get("/{lote_id}", response_model=LoteResponse)
async def obtener_lote(lote_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await _get_lote_o_404(lote_id, db)


@router.put("/{lote_id}", response_model=LoteResponse)
async def actualizar_lote(lote_id: uuid.UUID, data: LoteUpdate, db: AsyncSession = Depends(get_db)):
    lote = await _get_lote_o_404(lote_id, db)
    return await service.actualizar_lote(db, lote, data)


@router.delete("/{lote_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_lote(lote_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    lote = await _get_lote_o_404(lote_id, db)
    await service.eliminar_lote(db, lote)


@router.get("/{lote_id}/historial")
async def historial_lote(lote_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await _get_lote_o_404(lote_id, db)
    # Se implementa en el sprint de intervenciones (RFGL-03)
    return {"lote_id": str(lote_id), "intervenciones": []}


@router.get("/{lote_id}/vuelos", response_model=list[VueloResponse])
async def listar_vuelos(lote_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await _get_lote_o_404(lote_id, db)
    return await service.listar_vuelos(db, lote_id)
