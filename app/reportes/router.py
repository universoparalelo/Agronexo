import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.auth.dependencies import get_current_user
from app.auth.models import Usuario
from app.core.config import settings
from app.core.database import get_db
from app.core.storage import object_exists, presigned_url, upload_bytes
from app.diagnostico.service import generar_diagnostico
from app.lotes.models import IndiceEnum, Lote
from app.lotes.service import obtener_lote
from app.reportes.exportacion import generar_geojson_zonas, generar_shapefile_zip
from app.reportes.schemas import ExportZonasResponse, FormatoExportEnum
from app.reportes.service import generar_pdf_reporte

logger = logging.getLogger(__name__)

router = APIRouter()

_EXTENSIONES = {FormatoExportEnum.geojson: "geojson", FormatoExportEnum.shapefile: "zip"}
_CONTENT_TYPES = {
    FormatoExportEnum.geojson: "application/geo+json",
    FormatoExportEnum.shapefile: "application/zip",
}


async def _resolver_lote_o_404(
    db: AsyncSession, lote_id: uuid.UUID, current_user: Usuario,
) -> Lote:
    lote = await obtener_lote(db, lote_id, usuario_id=uuid.UUID(str(current_user.id)))
    if not lote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado.")
    return lote


async def _generar_diagnostico_o_404(db: AsyncSession, lote: Lote, vuelo_id: uuid.UUID) -> dict:
    try:
        diagnostico = await generar_diagnostico(db, lote, vuelo_id)
    except Exception:
        logger.exception(
            "Error generando diagnóstico para exportación (vuelo %s, lote %s)", vuelo_id, lote.id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No se pudo generar el reporte.",
        )

    if diagnostico is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diagnóstico no disponible. El vuelo debe estar en estado 'completado' y tener NDVI calculado.",
        )

    return diagnostico


async def _resolver_diagnostico_o_404(
    db: AsyncSession, lote_id: uuid.UUID, vuelo_id: uuid.UUID, current_user: Usuario,
) -> dict:
    """
    Resolución de lote + diagnóstico compartida por los endpoints de este
    router (reporte PDF, exportación GeoJSON, exportación Shapefile) —
    todos parten del mismo dict de generar_diagnostico().
    """
    lote = await _resolver_lote_o_404(db, lote_id, current_user)
    return await _generar_diagnostico_o_404(db, lote, vuelo_id)


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
    diagnostico = await _resolver_diagnostico_o_404(db, lote_id, vuelo_id, current_user)

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


@router.get(
    "/{lote_id}/vuelos/{vuelo_id}/zonas/geojson",
    summary="Exportar las zonas de diagnóstico como GeoJSON descargable",
)
async def exportar_zonas_geojson(
    lote_id: uuid.UUID,
    vuelo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    diagnostico = await _resolver_diagnostico_o_404(db, lote_id, vuelo_id, current_user)
    contenido = generar_geojson_zonas(diagnostico)

    return Response(
        content=contenido,
        media_type="application/geo+json",
        headers={"Content-Disposition": f'attachment; filename="zonas_{vuelo_id}.geojson"'},
    )


@router.get(
    "/{lote_id}/vuelos/{vuelo_id}/zonas/shapefile",
    summary="Exportar las zonas de diagnóstico como Shapefile (.zip)",
)
async def exportar_zonas_shapefile(
    lote_id: uuid.UUID,
    vuelo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    diagnostico = await _resolver_diagnostico_o_404(db, lote_id, vuelo_id, current_user)

    try:
        # pyshp + Shapely son CPU-bound y sync — mismo criterio de
        # threadpool que el PDF (ver reporte_pdf_vuelo más arriba).
        zip_bytes = await run_in_threadpool(generar_shapefile_zip, diagnostico)
    except Exception:
        logger.exception("Error generando Shapefile para vuelo %s del lote %s", vuelo_id, lote_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No se pudo generar el Shapefile.",
        )

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="zonas_{vuelo_id}.zip"'},
    )


@router.get(
    "/{lote_id}/vuelos/{vuelo_id}/zonas/export",
    response_model=ExportZonasResponse,
    summary="URL de descarga firmada (MinIO) de las zonas de diagnóstico, con caché por vuelo y formato",
)
async def exportar_zonas(
    lote_id: uuid.UUID,
    vuelo_id: uuid.UUID,
    formato: FormatoExportEnum = Query(..., description="Formato de exportación: geojson o shapefile."),
    indice: IndiceEnum = Query(
        IndiceEnum.ndvi,
        description=(
            "Reservado para exportación multi-índice a futuro — hoy solo 'ndvi' está soportado "
            "(el motor de diagnóstico todavía no consume NDRE/SAVI/ExG, ver Problemas abiertos "
            "en docs/release-v3.0.0.md)."
        ),
    ),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if indice != IndiceEnum.ndvi:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Exportación multi-índice todavía no implementada — solo 'ndvi' está disponible.",
        )

    lote = await _resolver_lote_o_404(db, lote_id, current_user)

    # Key determinística por lote+vuelo+formato: object_exists() decide si
    # se sirve la versión cacheada o se regenera, sin correr de nuevo el
    # motor de diagnóstico en cada request.
    key = f"{current_user.id}/{lote_id}/{vuelo_id}/export_{formato.value}.{_EXTENSIONES[formato]}"

    if not await run_in_threadpool(object_exists, key):
        diagnostico = await _generar_diagnostico_o_404(db, lote, vuelo_id)
        generador = generar_geojson_zonas if formato == FormatoExportEnum.geojson else generar_shapefile_zip
        try:
            # CPU-bound y sync (pyshp/Shapely o json.dumps) — mismo criterio
            # de threadpool que /zonas/geojson y /zonas/shapefile.
            contenido = await run_in_threadpool(generador, diagnostico)
        except Exception:
            logger.exception(
                "Error generando export %s para vuelo %s del lote %s", formato.value, vuelo_id, lote_id,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"No se pudo generar el export en formato {formato.value}.",
            )
        await run_in_threadpool(upload_bytes, key, contenido, _CONTENT_TYPES[formato])

    url = await run_in_threadpool(presigned_url, key)
    return ExportZonasResponse(
        vuelo_id=vuelo_id,
        formato=formato,
        indice=indice,
        url=url,
        expira_en_segundos=settings.minio_presigned_url_expiry,
    )
