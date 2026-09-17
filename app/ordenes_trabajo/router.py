import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.auth.dependencies import get_current_user
from app.auth.models import Usuario
from app.core.database import get_db
from app.diagnostico.orden_trabajo import generar_orden_trabajo
from app.diagnostico.service import generar_diagnostico
from app.lotes.models import Lote
from app.lotes.service import obtener_lote
from app.ordenes_trabajo.service import cargar_catalogo_dosis, generar_pdf_orden_trabajo

logger = logging.getLogger(__name__)

router = APIRouter()


async def _resolver_lote_o_404(
    db: AsyncSession, lote_id: uuid.UUID, current_user: Usuario,
) -> Lote:
    lote = await obtener_lote(db, lote_id, usuario_id=uuid.UUID(str(current_user.id)))
    if not lote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado.")
    return lote


@router.get(
    "/{lote_id}/vuelos/{vuelo_id}/orden-trabajo/pdf",
    summary="Documento de orden de trabajo en PDF (dosis por unidad de manejo, totales y sección legal/seguridad)",
)
async def orden_trabajo_pdf(
    lote_id: uuid.UUID,
    vuelo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    lote = await _resolver_lote_o_404(db, lote_id, current_user)

    try:
        diagnostico = await generar_diagnostico(db, lote, vuelo_id)
    except Exception:
        logger.exception(
            "Error generando diagnóstico para orden de trabajo (vuelo %s, lote %s)", vuelo_id, lote_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo generar la orden de trabajo.",
        )

    if diagnostico is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diagnóstico no disponible. El vuelo debe estar en estado 'completado' y tener NDVI calculado.",
        )

    unidades_manejo = diagnostico.get("unidades_manejo", [])
    if not unidades_manejo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "No hay unidades de manejo para generar una orden de trabajo — todas las "
                "zonas del lote están dentro de rangos normales."
            ),
        )

    catalogo_dosis = await cargar_catalogo_dosis(db)
    orden = generar_orden_trabajo(unidades_manejo, catalogo_dosis)

    try:
        # Jinja2 + WeasyPrint son CPU-bound y sync — mismo criterio de
        # threadpool que app/reportes/router.py.
        pdf_bytes = await run_in_threadpool(generar_pdf_orden_trabajo, orden, diagnostico.get("metadata", {}))
    except Exception:
        logger.exception(
            "Error generando PDF de orden de trabajo para vuelo %s del lote %s", vuelo_id, lote_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo generar el PDF de la orden de trabajo.",
        )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="orden_trabajo_{vuelo_id}.pdf"'},
    )
