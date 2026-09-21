import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import Usuario
from app.core.database import get_db
from app.ingesta import service
from app.ingesta.schemas import (
    EscenasSatelitalesResponse,
    EstadoVueloResponse,
    IndiceAnalisisIniciarResponse,
    IndiceAnalisisItem,
    IndiceAnalisisRequest,
    IndiceEstadoResponse,
    IndicesBatchIniciarResponse,
    IndicesBatchRequest,
    InspeccionGeotiffResponse,
    LoteDesdeGeotiffResponse,
    VueloDesdeSateliteRequest,
    VueloListItem,
    VueloReintentoResponse,
    VueloUploadResponse,
)
from app.ingesta.tiff_inspector import contar_bandas_geotiff
from app.ingesta.validator import validar_archivo_geotiff
from app.lotes.models import CultivoEnum, EstadoVueloEnum, IndiceEnum, SensorEnum
from app.lotes.schemas import CultivoCreate
from app.lotes.service import obtener_lote, resolver_cultivo_para_analisis

router = APIRouter()


@router.post(
    "/inspeccionar-geotiff",
    response_model=InspeccionGeotiffResponse,
    summary="Chequeo preliminar: cantidad de bandas del archivo vs. sensor seleccionado",
)
async def inspeccionar_geotiff(
    archivo: UploadFile = File(..., description="GeoTIFF a inspeccionar"),
    sensor: SensorEnum = Form(..., description="Sensor seleccionado"),
    current_user: Usuario = Depends(get_current_user),
):
    from workers.gis.band_mapping import MAPEO_SENSORES

    # Leer solo los primeros 512 bytes: suficiente para magic bytes + IFD del TIFF.
    # El inspector es best-effort — si el IFD no está en los primeros 512 bytes
    # (archivos muy grandes con IFD al final), devuelve None y se continúa igual.
    cabecera = await archivo.read(512)
    validar_archivo_geotiff(archivo, cabecera[:4])

    n_bandas = contar_bandas_geotiff(cabecera)
    mapeo = MAPEO_SENSORES[sensor.value]
    bandas_requeridas = max(v for v in mapeo if v is not None)

    compatible = n_bandas is None or n_bandas >= bandas_requeridas
    mensaje = None
    if not compatible:
        mensaje = (
            f"El archivo tiene {n_bandas} banda(s), pero el sensor '{sensor.value}' "
            f"requiere al menos {bandas_requeridas} (NIR en posición {mapeo.NIR}). "
            f"Verificá que elegiste el sensor correcto o que el archivo tenga todas las bandas necesarias."
        )

    return InspeccionGeotiffResponse(
        n_bandas=n_bandas,
        bandas_requeridas=bandas_requeridas,
        compatible=compatible,
        mensaje=mensaje,
    )


@router.post(
    "/desde-geotiff",
    response_model=LoteDesdeGeotiffResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Crear lote y subir GeoTIFF en un solo paso",
)
async def crear_lote_desde_geotiff(
    archivo: UploadFile = File(..., description="GeoTIFF multiespectral (.tif / .tiff)"),
    nombre: str = Form(..., min_length=1, max_length=200),
    cultivo: CultivoEnum = Form(...),
    sensor: SensorEnum = Form(...),
    estadio_fenologico: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    primeros_bytes = await archivo.read(4)
    validar_archivo_geotiff(archivo, primeros_bytes)
    await archivo.seek(0)

    # Tamaño conocido si el cliente lo envió en el header del campo multipart.
    # -1 = desconocido → MinIO usa multipart con partes de 64 MB.
    file_size = getattr(archivo, "size", None) or -1

    resultado = await service.crear_lote_y_vuelo_desde_geotiff(
        db=db,
        usuario_id=uuid.UUID(str(current_user.id)),
        nombre=nombre,
        cultivo=cultivo,
        sensor=sensor,
        file_stream=archivo.file,
        file_size=file_size,
        estadio_fenologico=estadio_fenologico,
    )
    await db.commit()
    return resultado


@router.post(
    "/{lote_id}/vuelos",
    response_model=VueloUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Subir GeoTIFF y encolar procesamiento",
)
async def subir_vuelo(
    lote_id: uuid.UUID,
    archivo: UploadFile = File(..., description="GeoTIFF multiespectral (.tif / .tiff)"),
    sensor: SensorEnum = Form(..., description="Tipo de sensor utilizado"),
    fecha_vuelo: datetime = Form(
        default=None,
        description="Fecha y hora del vuelo (ISO 8601). Por defecto: ahora.",
    ),
    estadio_fenologico: str = Form(
        ...,
        max_length=30,
        description="Estadio fenológico del cultivo en este vuelo puntual (obligatorio).",
    ),
    cultivo_id: uuid.UUID | None = Form(
        default=None,
        description="Cultivo ya cargado en el lote sobre el que se hace el análisis. Alternativa: cultivo_tipo para crear uno nuevo.",
    ),
    cultivo_tipo: CultivoEnum | None = Form(default=None, description="Tipo de un cultivo nuevo a crear en el lote."),
    cultivo_variedad: str | None = Form(default=None, max_length=100),
    cultivo_fecha_siembra: datetime | None = Form(default=None),
    cultivo_fecha_cosecha: datetime | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    lote = await obtener_lote(db, lote_id, usuario_id=uuid.UUID(str(current_user.id)))
    if not lote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado.")

    estadio_fenologico = estadio_fenologico.strip()
    if not estadio_fenologico:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El estadio fenológico es obligatorio.",
        )

    primeros_bytes = await archivo.read(4)
    validar_archivo_geotiff(archivo, primeros_bytes)
    await archivo.seek(0)

    file_size = getattr(archivo, "size", None) or -1

    if fecha_vuelo is None:
        fecha_vuelo = datetime.now(timezone.utc)

    cultivo_nuevo = None
    if cultivo_tipo is not None:
        try:
            cultivo_nuevo = CultivoCreate(
                tipo_cultivo=cultivo_tipo,
                variedad=cultivo_variedad,
                fecha_siembra=cultivo_fecha_siembra,
                fecha_cosecha=cultivo_fecha_cosecha,
            )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="fecha_cosecha no puede ser anterior a fecha_siembra.",
            )
    cultivo = await resolver_cultivo_para_analisis(db, lote_id, cultivo_id, cultivo_nuevo)

    vuelo = await service.crear_vuelo_desde_upload(
        db=db,
        lote_id=lote_id,
        usuario_id=uuid.UUID(str(current_user.id)),
        sensor=sensor,
        fecha_vuelo=fecha_vuelo,
        file_stream=archivo.file,
        file_size=file_size,
        estadio_fenologico=estadio_fenologico,
        cultivo_id=cultivo.id,
    )
    await db.commit()

    return VueloUploadResponse(
        vuelo_id=vuelo.id,
        lote_id=vuelo.lote_id,
        sensor=vuelo.sensor,
        estado=vuelo.estado,
        task_id=vuelo.task_id,
        created_at=vuelo.created_at,
        estadio_fenologico=vuelo.estadio_fenologico,
        cultivo_id=cultivo.id,
        cultivo=cultivo,
    )


@router.get(
    "/{lote_id}/vuelos/imagenes-satelitales",
    response_model=EscenasSatelitalesResponse,
    summary="Buscar escenas Sentinel-2 disponibles para el lote cerca de una fecha",
)
async def buscar_imagenes_satelitales(
    lote_id: uuid.UUID,
    fecha: date = Query(..., description="Fecha elegida por el usuario"),
    ventana_dias: int = Query(default=15, ge=1, le=60, description="Ventana +/- días alrededor de la fecha"),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    lote = await obtener_lote(db, lote_id, usuario_id=uuid.UUID(str(current_user.id)))
    if not lote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado.")
    if lote.geometry is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El lote no tiene límite (geometry) cargado. Dibujá o subí el límite del lote antes de buscar imágenes satelitales.",
        )

    try:
        items = await service.buscar_imagenes_satelitales(lote, fecha.isoformat(), ventana_dias)
    except RuntimeError as exc:
        # Sin escenas en la ventana pedida — no es un error del servidor,
        # es información para que el usuario pruebe otra fecha/ventana.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    return EscenasSatelitalesResponse(items=items, fecha_elegida=fecha.isoformat(), ventana_dias=ventana_dias)


@router.post(
    "/{lote_id}/vuelos/desde-satelite",
    response_model=VueloUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Cargar vuelo a partir de una escena satelital ya elegida",
)
async def crear_vuelo_desde_satelite(
    lote_id: uuid.UUID,
    data: VueloDesdeSateliteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    lote = await obtener_lote(db, lote_id, usuario_id=uuid.UUID(str(current_user.id)))
    if not lote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado.")
    if lote.geometry is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El lote no tiene límite (geometry) cargado. Dibujá o subí el límite del lote antes de cargar una imagen satelital.",
        )

    cultivo = await resolver_cultivo_para_analisis(db, lote_id, data.cultivo_id, data.cultivo)

    vuelo = await service.crear_vuelo_desde_satelite(
        db=db,
        lote_id=lote_id,
        usuario_id=uuid.UUID(str(current_user.id)),
        escena_id=data.escena_id,
        fecha_vuelo=data.fecha_vuelo,
        estadio_fenologico=data.estadio_fenologico,
        indices=data.indices,
        cultivo_id=cultivo.id,
    )
    await db.commit()

    return VueloUploadResponse(
        vuelo_id=vuelo.id,
        lote_id=vuelo.lote_id,
        sensor=vuelo.sensor,
        estado=vuelo.estado,
        task_id=vuelo.task_id,
        created_at=vuelo.created_at,
        estadio_fenologico=vuelo.estadio_fenologico,
        cultivo_id=cultivo.id,
        cultivo=cultivo,
        mensaje="Imagen satelital solicitada. Descarga y procesamiento iniciados.",
    )


@router.get(
    "/{lote_id}/vuelos",
    response_model=list[VueloListItem],
    summary="Listar vuelos de un lote",
)
async def listar_vuelos_lote(
    lote_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    lote = await obtener_lote(db, lote_id, usuario_id=uuid.UUID(str(current_user.id)))
    if not lote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado.")
    vuelos = await service.listar_vuelos(db, lote_id)
    return [
        VueloListItem(
            vuelo_id=v.id,
            lote_id=v.lote_id,
            sensor=v.sensor,
            estado=v.estado,
            fecha_vuelo=v.fecha_vuelo,
            hora_inicio=v.hora_inicio,
            hora_fin=v.hora_fin,
            task_id=v.task_id,
            created_at=v.created_at,
            estadio_fenologico=v.estadio_fenologico,
            cultivo_id=v.cultivo_id,
            cultivo=v.cultivo,
            indices=await service.listar_analisis_indices(db, v),
        )
        for v in vuelos
    ]


@router.get(
    "/{lote_id}/vuelos/{vuelo_id}/resultado",
    summary="Obtener GeoJSON del resultado del índice procesado",
)
async def resultado_vuelo(
    lote_id: uuid.UUID,
    vuelo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    lote = await obtener_lote(db, lote_id, usuario_id=uuid.UUID(str(current_user.id)))
    if not lote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado.")
    geojson = await service.obtener_resultado_geojson(db, lote_id, vuelo_id)
    if geojson is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resultado no disponible. El vuelo debe estar en estado 'completado'.",
        )
    return geojson


@router.get(
    "/{lote_id}/vuelos/{vuelo_id}/estado",
    response_model=EstadoVueloResponse,
    summary="Consultar estado del procesamiento de un vuelo",
)
async def estado_vuelo(
    lote_id: uuid.UUID,
    vuelo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    lote = await obtener_lote(db, lote_id, usuario_id=uuid.UUID(str(current_user.id)))
    if not lote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado.")

    estado = await service.obtener_estado_vuelo(db, lote_id, vuelo_id)
    if not estado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vuelo no encontrado.")
    return estado


@router.delete(
    "/{lote_id}/vuelos/{vuelo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar (soft delete) un vuelo/análisis",
)
async def eliminar_vuelo(
    lote_id: uuid.UUID,
    vuelo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    lote = await obtener_lote(db, lote_id, usuario_id=uuid.UUID(str(current_user.id)))
    if not lote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado.")

    vuelo = await service.obtener_vuelo(db, lote_id, vuelo_id)
    if not vuelo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vuelo no encontrado.")

    await service.eliminar_vuelo(db, vuelo)
    await db.commit()


@router.post(
    "/{lote_id}/vuelos/{vuelo_id}/reintentar",
    response_model=VueloReintentoResponse,
    summary="Reintentar el procesamiento de un vuelo que falló",
)
async def reintentar_vuelo(
    lote_id: uuid.UUID,
    vuelo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    lote = await obtener_lote(db, lote_id, usuario_id=uuid.UUID(str(current_user.id)))
    if not lote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado.")

    vuelo = await service.obtener_vuelo(db, lote_id, vuelo_id)
    if not vuelo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vuelo no encontrado.")

    if vuelo.estado != EstadoVueloEnum.error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden reintentar vuelos en estado 'error'.",
        )
    if not vuelo.archivo_original:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El vuelo no tiene un archivo original disponible para reprocesar.",
        )

    vuelo = await service.reintentar_vuelo(db, vuelo)
    await db.commit()

    return VueloReintentoResponse(
        vuelo_id=vuelo.id,
        lote_id=vuelo.lote_id,
        sensor=vuelo.sensor,
        estado=vuelo.estado,
        task_id=vuelo.task_id,
        created_at=vuelo.created_at,
    )


@router.get(
    "/{lote_id}/vuelos/{vuelo_id}/indices",
    response_model=list[IndiceAnalisisItem],
    summary="Listar índices calculados (o en curso) para un vuelo",
)
async def listar_indices_vuelo(
    lote_id: uuid.UUID,
    vuelo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    lote = await obtener_lote(db, lote_id, usuario_id=uuid.UUID(str(current_user.id)))
    if not lote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado.")

    vuelo = await service.obtener_vuelo(db, lote_id, vuelo_id)
    if not vuelo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vuelo no encontrado.")

    return await service.listar_analisis_indices(db, vuelo)


@router.post(
    "/{lote_id}/vuelos/{vuelo_id}/indices",
    response_model=IndiceAnalisisIniciarResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Analizar un índice adicional sobre un vuelo ya existente (NDRE, SAVI, ExG)",
)
async def analizar_indice_vuelo(
    lote_id: uuid.UUID,
    vuelo_id: uuid.UUID,
    data: IndiceAnalisisRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    lote = await obtener_lote(db, lote_id, usuario_id=uuid.UUID(str(current_user.id)))
    if not lote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado.")

    vuelo = await service.obtener_vuelo(db, lote_id, vuelo_id)
    if not vuelo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vuelo no encontrado.")

    if data.indice == IndiceEnum.ndvi:
        # NDVI ya se calculó automáticamente al subir el vuelo — no hay nada
        # nuevo que encolar, devolvemos el estado real del vuelo.
        return IndiceAnalisisIniciarResponse(
            indice=IndiceEnum.ndvi,
            estado=vuelo.estado,
            task_id=vuelo.task_id,
            mensaje="NDVI ya se calcula automáticamente al subir el vuelo.",
        )

    if not vuelo.archivo_original:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El vuelo no tiene un archivo original disponible para analizar.",
        )

    analisis = await service.crear_analisis_indice(db, vuelo, data.indice, data.metodo_umbral)
    await db.commit()

    return IndiceAnalisisIniciarResponse(
        indice=analisis.indice,
        estado=analisis.estado,
        task_id=analisis.task_id,
    )


@router.post(
    "/{lote_id}/vuelos/{vuelo_id}/indices/batch",
    response_model=IndicesBatchIniciarResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Analizar varios índices adicionales en una sola corrida (evita releer el GeoTIFF por índice)",
)
async def analizar_indices_batch_vuelo(
    lote_id: uuid.UUID,
    vuelo_id: uuid.UUID,
    data: IndicesBatchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    lote = await obtener_lote(db, lote_id, usuario_id=uuid.UUID(str(current_user.id)))
    if not lote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado.")

    vuelo = await service.obtener_vuelo(db, lote_id, vuelo_id)
    if not vuelo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vuelo no encontrado.")

    if not vuelo.archivo_original:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El vuelo no tiene un archivo original disponible para analizar.",
        )

    # NDVI ya se calcula automáticamente al subir el vuelo — no hay nada
    # nuevo que encolar para ese índice dentro del batch.
    indices_a_encolar = [i for i in data.indices if i != IndiceEnum.ndvi]
    if not indices_a_encolar:
        return IndicesBatchIniciarResponse(items=[], mensaje="Nada para encolar (NDVI ya se calcula al subir).")

    filas = await service.crear_analisis_indices_batch(db, vuelo, indices_a_encolar, data.metodo_umbral)
    await db.commit()

    return IndicesBatchIniciarResponse(items=[
        IndiceAnalisisIniciarResponse(indice=f.indice, estado=f.estado, task_id=f.task_id)
        for f in filas
    ])


@router.get(
    "/{lote_id}/vuelos/{vuelo_id}/indices/{indice}/estado",
    response_model=IndiceEstadoResponse,
    summary="Consultar estado del análisis de un índice adicional",
)
async def estado_indice_vuelo(
    lote_id: uuid.UUID,
    vuelo_id: uuid.UUID,
    indice: IndiceEnum,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    lote = await obtener_lote(db, lote_id, usuario_id=uuid.UUID(str(current_user.id)))
    if not lote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado.")

    estado = await service.obtener_estado_analisis_indice(db, vuelo_id, indice)
    if not estado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Análisis no encontrado.")
    return estado


@router.get(
    "/{lote_id}/vuelos/{vuelo_id}/indices/{indice}/resultado",
    summary="Obtener GeoJSON del resultado de un índice adicional",
)
async def resultado_indice_vuelo(
    lote_id: uuid.UUID,
    vuelo_id: uuid.UUID,
    indice: IndiceEnum,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    lote = await obtener_lote(db, lote_id, usuario_id=uuid.UUID(str(current_user.id)))
    if not lote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado.")

    geojson = await service.obtener_resultado_geojson_indice(db, vuelo_id, indice)
    if geojson is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resultado no disponible. El análisis debe estar en estado 'completado'.",
        )
    return geojson
