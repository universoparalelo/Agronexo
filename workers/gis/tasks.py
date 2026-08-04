import io
import logging
import tempfile
import time

import rasterio
from workers.celery_app import celery_app

logger = logging.getLogger(__name__)

_DTYPES_VALIDOS = {"float32", "uint8", "uint16", "int16", "int32"}


def _actualizar_lote_geometry(lote_id: str, wkt: str) -> None:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session

    from app.core.config import settings

    engine = create_engine(settings.database_url_sync)
    try:
        with Session(engine) as session:
            session.execute(
                text(
                    "UPDATE lotes SET geometry = ST_GeomFromText(:wkt, 4326) "
                    "WHERE id = CAST(:lote_id AS uuid)"
                ),
                {"wkt": wkt, "lote_id": lote_id},
            )
            session.commit()
    finally:
        engine.dispose()


def _actualizar_vuelo(vuelo_id: str, estado: str, error: str | None = None, geojson_key: str | None = None) -> None:
    # SQL directo para evitar importar app.lotes.models → app.core.database → asyncpg,
    # que no está instalado en el contenedor worker.
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session

    from app.core.config import settings

    engine = create_engine(settings.database_url_sync)
    try:
        with Session(engine) as session:
            session.execute(
                text(
                    "UPDATE vuelos SET estado = CAST(:estado AS estadovueloenum), "
                    "error_detalle = :error, geojson_key = :geojson_key "
                    "WHERE id = CAST(:vuelo_id AS uuid)"
                ),
                {"estado": estado, "error": error, "geojson_key": geojson_key, "vuelo_id": vuelo_id},
            )
            session.commit()
    finally:
        engine.dispose()


def _validar_geotiff_gis(data: bytes) -> dict:
    """Valida CRS, bandas y dtype desde bytes. Usado por tests y analizar_indice."""
    with rasterio.open(io.BytesIO(data)) as src:
        return _validar_geotiff_gis_desde_src(src)


def _validar_geotiff_gis_archivo(path: str) -> dict:
    """Valida CRS, bandas y dtype abriendo directamente el archivo — sin cargar en RAM."""
    with rasterio.open(path) as src:
        return _validar_geotiff_gis_desde_src(src)


def _validar_geotiff_gis_desde_src(src) -> dict:
    """Lógica de validación compartida dado un DatasetReader ya abierto."""
    if src.crs is None:
        raise ValueError(
            "El GeoTIFF no tiene sistema de referencia de coordenadas (CRS) definido. "
            "Reproyectá el archivo a EPSG:4326 o UTM antes de subir."
        )
    if src.count < 1:
        raise ValueError(
            f"El archivo tiene {src.count} banda(s). Se requiere al menos 1 banda válida."
        )
    dtype = src.dtypes[0]
    if dtype not in _DTYPES_VALIDOS:
        raise ValueError(
            f"Tipo de dato '{dtype}' no soportado por el pipeline de vectorización. "
            f"Usar float32, uint8, uint16, int16 o int32."
        )
    return {
        "bandas": src.count,
        "crs": str(src.crs),
        "dtype": dtype,
        "ancho": src.width,
        "alto": src.height,
        "resolucion_m": round(abs(src.res[0]), 6),
    }


@celery_app.task(
    bind=True,
    name="workers.gis.tasks.procesar_vuelo",
    autoretry_for=(ConnectionError, OSError),
    max_retries=3,
    default_retry_delay=30,
)
def procesar_vuelo(self, vuelo_id: str, minio_key: str, sensor: str, indice: str = "ndvi", lote_id: str | None = None, metodo_umbral: str = "fijo", area_minima_m2: int = 10_000) -> dict:
    import os
    from app.core.storage import download_geotiff_to_file, upload_bytes
    from workers.gis.pipeline import ejecutar_pipeline_archivo
    from workers.gis.reproyeccion import reproyectar_a_4326_archivo

    self.update_state(state="STARTED", meta={"progreso": 0, "mensaje": "Descargando archivo desde almacenamiento"})

    # Descargar a archivo temporal en disco — sin cargar el archivo completo en RAM
    tiff_tmp = tempfile.NamedTemporaryFile(suffix=".tif", delete=False)
    tiff_path = tiff_tmp.name
    tiff_tmp.close()

    t_descarga = time.perf_counter()
    try:
        download_geotiff_to_file(minio_key, tiff_path)
    except Exception as exc:
        _actualizar_vuelo(vuelo_id, "error", f"Error al descargar el archivo: {exc}")
        os.unlink(tiff_path)
        raise
    size_mb = os.path.getsize(tiff_path) / 1_048_576
    logger.info("[task] descarga MinIO (%.1f MB): %.2fs", size_mb, time.perf_counter() - t_descarga)

    self.update_state(state="PROGRESS", meta={"progreso": 15, "mensaje": "Validando CRS y bandas"})

    try:
        _validar_geotiff_gis_archivo(tiff_path)
    except Exception as exc:
        mensaje = str(exc) if isinstance(exc, ValueError) else "El archivo no es un GeoTIFF válido o está dañado."
        _actualizar_vuelo(vuelo_id, "error", mensaje)
        os.unlink(tiff_path)
        raise ValueError(mensaje) from exc

    if lote_id:
        try:
            repro_tmp = tiff_path + ".bounds_repro.tif"
            path_4326 = reproyectar_a_4326_archivo(tiff_path, repro_tmp)
            with rasterio.open(path_4326) as src:
                b = src.bounds
                wkt = f"POLYGON(({b.left} {b.bottom},{b.right} {b.bottom},{b.right} {b.top},{b.left} {b.top},{b.left} {b.bottom}))"
            _actualizar_lote_geometry(lote_id, wkt)
            # Reemplazar tiff_path con el reproyectado para que el pipeline no lo haga de nuevo
            if path_4326 != tiff_path:
                os.unlink(tiff_path)
                tiff_path = path_4326
            elif os.path.exists(repro_tmp):
                os.unlink(repro_tmp)
        except Exception:
            pass  # no bloquear el pipeline si falla la extracción de bounds

    _actualizar_vuelo(vuelo_id, "procesando")
    self.update_state(state="PROGRESS", meta={"progreso": 30, "mensaje": f"Calculando {indice.upper()}"})

    geojson_tmp = tempfile.NamedTemporaryFile(suffix=".geojson", delete=False)
    geojson_path = geojson_tmp.name
    geojson_tmp.close()

    try:
        estadisticas = ejecutar_pipeline_archivo(
            path=tiff_path,
            sensor=sensor,
            indice=indice,
            geojson_destino=geojson_path,
            metodo_umbral=metodo_umbral,
            area_minima_m2=area_minima_m2,
        )
    except Exception as exc:
        _actualizar_vuelo(vuelo_id, "error", f"Error en el pipeline GIS: {exc}")
        raise
    finally:
        if os.path.exists(tiff_path):
            os.unlink(tiff_path)

    self.update_state(state="PROGRESS", meta={"progreso": 80, "mensaje": "Subiendo resultados"})

    geojson_key_guardado: str | None = None
    try:
        partes = minio_key.split("/")  # {usuario_id}/{lote_id}/{vuelo_id}/original.tif
        prefijo = "/".join(partes[:3])
        geojson_key_guardado = f"{prefijo}/zonas.geojson"
        with open(geojson_path, "rb") as f:
            geojson_bytes = f.read()
        t_upload = time.perf_counter()
        upload_bytes(geojson_key_guardado, geojson_bytes, content_type="application/geo+json")
        logger.info("[task] upload geojson (%.1f KB): %.2fs", len(geojson_bytes) / 1024, time.perf_counter() - t_upload)
    except Exception as exc:
        estadisticas["advertencia_upload"] = str(exc)
        geojson_key_guardado = None
    finally:
        if os.path.exists(geojson_path):
            os.unlink(geojson_path)

    self.update_state(state="PROGRESS", meta={"progreso": 100, "mensaje": "Procesamiento completado"})
    _actualizar_vuelo(vuelo_id, "completado", geojson_key=geojson_key_guardado)

    return {"vuelo_id": vuelo_id, "estadisticas": estadisticas}


def _actualizar_analisis_indice(
    analisis_id: str,
    estado: str,
    error: str | None = None,
    geojson_key: str | None = None,
    metodo_umbral: str | None = None,
) -> None:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session

    from app.core.config import settings

    engine = create_engine(settings.database_url_sync)
    try:
        with Session(engine) as session:
            session.execute(
                text(
                    "UPDATE analisis_indices SET estado = CAST(:estado AS estadovueloenum), "
                    "error_detalle = :error, geojson_key = :geojson_key, "
                    "metodo_umbral = COALESCE(:metodo_umbral, metodo_umbral) "
                    "WHERE id = CAST(:analisis_id AS uuid)"
                ),
                {
                    "estado": estado,
                    "error": error,
                    "geojson_key": geojson_key,
                    "metodo_umbral": metodo_umbral,
                    "analisis_id": analisis_id,
                },
            )
            session.commit()
    finally:
        engine.dispose()


@celery_app.task(
    bind=True,
    name="workers.gis.tasks.analizar_indice",
    autoretry_for=(ConnectionError, OSError),
    max_retries=3,
    default_retry_delay=30,
)
def analizar_indice(
    self,
    analisis_id: str,
    minio_key: str,
    sensor: str,
    indice: str,
    metodo_umbral: str = "fijo",
    area_minima_m2: int = 10_000,
) -> dict:
    """
    Analiza UN índice adicional sobre un vuelo ya existente (NDRE, SAVI, ExG —
    el primer índice, NDVI, se calcula siempre al subir vía procesar_vuelo).
    Reusa exactamente la misma lógica de pipeline; solo cambia dónde se
    guarda el resultado: fila propia en analisis_indices, no en vuelos.
    """
    import os
    from app.core.storage import download_geotiff_to_file, upload_bytes
    from workers.gis.pipeline import ejecutar_pipeline_archivo

    self.update_state(state="STARTED", meta={"progreso": 0, "mensaje": "Descargando archivo desde almacenamiento"})

    tiff_tmp = tempfile.NamedTemporaryFile(suffix=".tif", delete=False)
    tiff_path = tiff_tmp.name
    tiff_tmp.close()

    try:
        download_geotiff_to_file(minio_key, tiff_path)
    except Exception as exc:
        _actualizar_analisis_indice(analisis_id, "error", f"Error al descargar el archivo: {exc}")
        os.unlink(tiff_path)
        raise

    self.update_state(state="PROGRESS", meta={"progreso": 15, "mensaje": "Validando CRS y bandas"})

    try:
        _validar_geotiff_gis_archivo(tiff_path)
    except Exception as exc:
        mensaje = str(exc) if isinstance(exc, ValueError) else "El archivo no es un GeoTIFF válido o está dañado."
        _actualizar_analisis_indice(analisis_id, "error", mensaje)
        os.unlink(tiff_path)
        raise ValueError(mensaje) from exc

    self.update_state(state="PROGRESS", meta={"progreso": 30, "mensaje": f"Calculando {indice.upper()}"})

    geojson_tmp = tempfile.NamedTemporaryFile(suffix=".geojson", delete=False)
    geojson_path = geojson_tmp.name
    geojson_tmp.close()

    try:
        estadisticas = ejecutar_pipeline_archivo(
            path=tiff_path,
            sensor=sensor,
            indice=indice,
            geojson_destino=geojson_path,
            metodo_umbral=metodo_umbral,
            area_minima_m2=area_minima_m2,
        )
    except Exception as exc:
        _actualizar_analisis_indice(analisis_id, "error", f"Error en el pipeline GIS: {exc}")
        raise
    finally:
        if os.path.exists(tiff_path):
            os.unlink(tiff_path)

    self.update_state(state="PROGRESS", meta={"progreso": 80, "mensaje": "Subiendo resultados"})

    geojson_key_guardado: str | None = None
    try:
        partes = minio_key.split("/")  # {usuario_id}/{lote_id}/{vuelo_id}/original.tif
        prefijo = "/".join(partes[:3])
        geojson_key_guardado = f"{prefijo}/zonas_{indice}.geojson"
        with open(geojson_path, "rb") as f:
            geojson_bytes = f.read()
        upload_bytes(geojson_key_guardado, geojson_bytes, content_type="application/geo+json")
    except Exception as exc:
        estadisticas["advertencia_upload"] = str(exc)
        geojson_key_guardado = None
    finally:
        if os.path.exists(geojson_path):
            os.unlink(geojson_path)

    self.update_state(state="PROGRESS", meta={"progreso": 100, "mensaje": "Procesamiento completado"})
    _actualizar_analisis_indice(
        analisis_id,
        "completado",
        geojson_key=geojson_key_guardado,
        metodo_umbral=estadisticas.get("metodo_umbral"),
    )

    return {"analisis_id": analisis_id, "estadisticas": estadisticas}


# Tarea legacy — se mantiene por compatibilidad con tests existentes
@celery_app.task(bind=True, name="workers.gis.tasks.procesar_analisis")
def procesar_analisis(self, analisis_id: str) -> dict:
    self.update_state(state="STARTED", meta={"progreso": 0, "mensaje": "Iniciando procesamiento"})
    return {"analisis_id": analisis_id, "status": "pendiente_implementacion"}
