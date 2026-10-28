import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import Usuario
from app.core.database import get_db
from app.diagnostico import precios, revisiones, service
from app.diagnostico.models import CausaIndiceEnum, TipoProductoEnum
from app.diagnostico.estadios import ESTADIOS_POR_CULTIVO
from app.diagnostico.schemas import (
    EstadiosFenologicosResponse,
    NdviEsperadoListResponse,
    NdviEsperadoPuntoResponse,
    PrecioProductoCreateRequest,
    PrecioProductoResponse,
    ProductoFitosanitarioListResponse,
    RevisionZonaRequest,
    RevisionZonaResponse,
)
from app.lotes.models import CultivoEnum
from app.lotes.service import obtener_lote

logger = logging.getLogger(__name__)

router = APIRouter()
productos_router = APIRouter()
estadios_router = APIRouter()


@estadios_router.get(
    "",
    response_model=EstadiosFenologicosResponse,
    summary="Estadios fenológicos elegibles por tipo de cultivo",
)
async def listar_estadios_fenologicos(current_user: Usuario = Depends(get_current_user)):
    return EstadiosFenologicosResponse(
        estadios={cultivo.value: estadios for cultivo, estadios in ESTADIOS_POR_CULTIVO.items()},
    )


@estadios_router.get(
    "/ndvi-esperado",
    response_model=NdviEsperadoListResponse,
    summary="Curva placeholder de NDVI esperado por estadio para un cultivo",
)
async def listar_ndvi_esperado_cultivo(
    cultivo: CultivoEnum = Query(..., description="Cultivo para el que se pide la curva esperada"),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    puntos = await service.listar_ndvi_esperado(db, cultivo)
    return NdviEsperadoListResponse(
        cultivo=cultivo.value,
        puntos=[
            NdviEsperadoPuntoResponse(
                estadio=p.etiqueta, orden=p.orden,
                ndvi_esperado=p.ndvi_esperado, ndvi_min=p.ndvi_min, ndvi_max=p.ndvi_max,
            )
            for p in puntos
        ],
    )


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


@productos_router.get(
    "/{producto_id}/precios",
    response_model=list[PrecioProductoResponse],
    summary="Historial de precios cargados de un producto (HU-R4-11)",
)
async def listar_precios_producto(
    producto_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return await precios.listar_precios(db, producto_id)


@productos_router.post(
    "/{producto_id}/precios",
    response_model=PrecioProductoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cargar el precio real pagado por un producto (HU-R4-11)",
)
async def crear_precio_producto(
    producto_id: uuid.UUID,
    data: PrecioProductoCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    producto = await service.obtener_producto(db, producto_id)
    if producto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado.")
    return await precios.crear_precio_usuario(
        db, producto_id, data.precio_usd, data.unidad, data.fecha,
    )


@router.get(
    "/{lote_id}/vuelos/{vuelo_id}/diagnostico",
    summary="Diagnóstico agronómico del vuelo (motor de reglas RFDR-01) — guardado, se calcula solo la primera vez",
)
async def diagnostico_vuelo(
    lote_id: uuid.UUID,
    vuelo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return await _resolver_diagnostico(db, lote_id, vuelo_id, current_user, forzar_recalculo=False)


@router.post(
    "/{lote_id}/vuelos/{vuelo_id}/diagnostico/recalcular",
    summary="Recalcula el diagnóstico del vuelo y sobrescribe el guardado",
)
async def recalcular_diagnostico_vuelo(
    lote_id: uuid.UUID,
    vuelo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return await _resolver_diagnostico(db, lote_id, vuelo_id, current_user, forzar_recalculo=True)


async def _resolver_diagnostico(
    db: AsyncSession, lote_id: uuid.UUID, vuelo_id: uuid.UUID, current_user: Usuario, *, forzar_recalculo: bool,
):
    lote = await obtener_lote(db, lote_id, usuario_id=uuid.UUID(str(current_user.id)))
    if not lote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado.")

    try:
        resultado = await service.generar_diagnostico(db, lote, vuelo_id, forzar_recalculo=forzar_recalculo)
    except HTTPException:
        raise
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
    if not resultado.get("features"):
        return resultado
    return revisiones.adjuntar_revisiones(resultado, await revisiones.listar_revisiones(db, vuelo_id))


async def _diagnostico_guardado_del_usuario(
    db: AsyncSession, lote_id: uuid.UUID, vuelo_id: uuid.UUID, current_user: Usuario,
) -> dict:
    lote = await obtener_lote(db, lote_id, usuario_id=uuid.UUID(str(current_user.id)))
    if not lote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado.")
    guardado = await service.obtener_diagnostico_guardado(db, vuelo_id)
    if guardado is None or guardado.resultado.get("metadata", {}).get("lote_id") != str(lote_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Este vuelo todavía no tiene diagnóstico. Abrí el diagnóstico antes de revisarlo.",
        )
    return guardado.resultado


@router.put(
    "/{lote_id}/vuelos/{vuelo_id}/diagnostico/zonas/{zona_id}/revision",
    response_model=RevisionZonaResponse,
    summary="Criterio técnico del agrónomo sobre una zona: aceptar, modificar o rechazar (RFDR-04)",
)
async def revisar_zona(
    lote_id: uuid.UUID,
    vuelo_id: uuid.UUID,
    zona_id: int,
    data: RevisionZonaRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    diagnostico = await _diagnostico_guardado_del_usuario(db, lote_id, vuelo_id, current_user)
    try:
        revision = await revisiones.guardar_revision(
            db, vuelo_id=vuelo_id, zona_id=zona_id, diagnostico=diagnostico,
            decision=data.decision, causa_confirmada=data.causa_confirmada,
            comentario=data.comentario, usuario_id=uuid.UUID(str(current_user.id)),
        )
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except revisiones.RevisionInvalida as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    await db.commit()
    return revisiones.revision_a_dict(revision)


@router.delete(
    "/{lote_id}/vuelos/{vuelo_id}/diagnostico/zonas/{zona_id}/revision",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Quitar el criterio técnico cargado sobre una zona",
)
async def borrar_revision_zona(
    lote_id: uuid.UUID,
    vuelo_id: uuid.UUID,
    zona_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await _diagnostico_guardado_del_usuario(db, lote_id, vuelo_id, current_user)
    if not await revisiones.eliminar_revision(db, vuelo_id, zona_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Esa zona no tiene revisión cargada.")
    await db.commit()
