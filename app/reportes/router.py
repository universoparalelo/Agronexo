import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.auth.dependencies import get_current_user
from app.auth.models import Usuario
from app.core.database import get_db
from app.diagnostico.service import generar_diagnostico
from app.lotes.service import obtener_lote
from app.reportes.service import generar_pdf_reporte

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/{lote_id}/vuelos/{vuelo_id}/reporte/pdf",
    summary="Reporte ejecutivo en PDF (mapa + estadísticas + diagnóstico) del vuelo",
)
async def reporte_pdf_vuelo(
    lote_id: uuid.UUID,
    vuelo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    lote = await obtener_lote(db, lote_id, usuario_id=uuid.UUID(str(current_user.id)))
    if not lote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado.")

    try:
        diagnostico = await generar_diagnostico(db, lote, vuelo_id)
    except Exception:
        logger.exception(
            "Error generando diagnóstico para reporte PDF (vuelo %s, lote %s)", vuelo_id, lote_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No se pudo generar el reporte.",
        )

    if diagnostico is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diagnóstico no disponible. El vuelo debe estar en estado 'completado' y tener NDVI calculado.",
        )

    try:
        # generar_pdf_reporte es CPU-bound y sync (Jinja2 + WeasyPrint) — se
        # delega a threadpool igual que _calcular_diagnostico en
        # app/diagnostico/service.py, para no bloquear el event loop.
        pdf_bytes = await run_in_threadpool(generar_pdf_reporte, diagnostico)
    except Exception:
        logger.exception("Error generando PDF para vuelo %s del lote %s", vuelo_id, lote_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No se pudo generar el PDF.",
        )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="reporte_ejecutivo_{vuelo_id}.pdf"'},
    )
