import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response
from geoalchemy2.shape import to_shape
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.auth.dependencies import get_current_user
from app.auth.models import Usuario
from app.core.database import get_db
from app.diagnostico.orden_trabajo import generar_orden_trabajo
from app.diagnostico.service import generar_diagnostico
from app.lotes.service import obtener_lote
from app.ordenes_trabajo.service import cargar_catalogo_dosis
from app.prescripcion.mapa import armar_mapa_prescripcion
from app.prescripcion.maquinas import MaquinaEnum, resolver_perfil
from app.prescripcion.paquete import generar_paquete_prescripcion

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/{lote_id}/vuelos/{vuelo_id}/prescripcion",
    summary="Paquete de prescripción para maquinaria (.zip): Shapefile e ISO-XML por producto y recorrido sugerido",
)
async def paquete_prescripcion(
    request: Request,
    lote_id: uuid.UUID,
    vuelo_id: uuid.UUID,
    maquina: MaquinaEnum = Query(MaquinaEnum.mosquito, description="dron o mosquito (pulverizadora autopropulsada)."),
    ancho_labor_m: float | None = Query(None, gt=0, le=60, description="Ancho de labor; por defecto el de la máquina."),
    margen_m: float | None = Query(None, ge=0, le=20, description="Margen alrededor de cada zona; por defecto el de la máquina."),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    lote = await obtener_lote(db, lote_id, usuario_id=uuid.UUID(str(current_user.id)))
    if not lote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado.")

    try:
        diagnostico = await generar_diagnostico(db, lote, vuelo_id)
    except Exception:
        logger.exception("Error generando diagnóstico para prescripción (vuelo %s, lote %s)", vuelo_id, lote_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No se pudo generar la prescripción.",
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
            detail="No hay unidades de manejo: todas las zonas del lote están dentro de rangos normales.",
        )

    catalogo_dosis = await cargar_catalogo_dosis(db)
    orden = generar_orden_trabajo(unidades_manejo, catalogo_dosis, diagnostico.get("alternativas_marca"))
    perfil = resolver_perfil(maquina, ancho_labor_m, margen_m)
    limite = to_shape(lote.geometry) if lote.geometry is not None else None

    try:
        # Shapely + pyshp son CPU-bound y sync: mismo criterio de threadpool
        # que las exportaciones de app/reportes/router.py.
        mapa = await run_in_threadpool(armar_mapa_prescripcion, unidades_manejo, orden, limite, perfil.margen_m)
        if not mapa.productos:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ninguna unidad de manejo tiene producto con dosis: no hay nada que prescribir.",
            )
        zip_bytes, _ = await run_in_threadpool(
            generar_paquete_prescripcion, mapa, perfil, diagnostico.get("metadata", {}), request.app.version,
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error generando paquete de prescripción para vuelo %s del lote %s", vuelo_id, lote_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No se pudo generar la prescripción.",
        )

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="prescripcion_{maquina.value}_{vuelo_id}.zip"'},
    )
