import io
import tempfile

import rasterio
from workers.celery_app import celery_app

_DTYPES_VALIDOS = {"float32", "uint8", "uint16", "int16", "int32"}


def _actualizar_vuelo(vuelo_id: str, estado: str, error: str | None = None) -> None:
    # Importaciones lazy: evitan cargar app.core.database (asyncpg) a nivel de módulo.
    from sqlalchemy import create_engine, update
    from sqlalchemy.orm import Session

    from app.core.config import settings
    from app.lotes.models import Vuelo

    engine = create_engine(settings.database_url_sync)
    try:
        with Session(engine) as session:
            session.execute(
                update(Vuelo)
                .where(Vuelo.id == vuelo_id)
                .values(estado=estado, error_detalle=error)
            )
            session.commit()
    finally:
        engine.dispose()


def _validar_geotiff_gis(data: bytes) -> dict:
    """Valida CRS, bandas y dtype. Retorna metadata o lanza ValueError con mensaje claro."""
    with rasterio.open(io.BytesIO(data)) as src:
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


@celery_app.task(bind=True, name="workers.gis.tasks.procesar_vuelo")
def procesar_vuelo(self, vuelo_id: str, minio_key: str, sensor: str, indice: str = "ndvi") -> dict:
    from app.core.storage import download_geotiff, upload_geotiff
    from workers.gis.pipeline import ejecutar_pipeline

    self.update_state(state="STARTED", meta={"progreso": 0, "mensaje": "Descargando archivo desde almacenamiento"})

    try:
        data = download_geotiff(minio_key)
    except Exception as exc:
        _actualizar_vuelo(vuelo_id, "error", f"Error al descargar el archivo: {exc}")
        raise

    self.update_state(state="PROGRESS", meta={"progreso": 15, "mensaje": "Validando CRS y bandas"})

    try:
        _validar_geotiff_gis(data)
    except Exception as exc:
        mensaje = str(exc) if isinstance(exc, ValueError) else "El archivo no es un GeoTIFF válido o está dañado."
        _actualizar_vuelo(vuelo_id, "error", mensaje)
        raise ValueError(mensaje) from exc

    _actualizar_vuelo(vuelo_id, "procesando")
    self.update_state(state="PROGRESS", meta={"progreso": 30, "mensaje": f"Calculando {indice.upper()}"})

    try:
        with tempfile.NamedTemporaryFile(suffix=".geojson", delete=False) as tmp:
            geojson_path = tmp.name

        estadisticas = ejecutar_pipeline(
            data=data,
            sensor=sensor,
            indice=indice,
            geojson_destino=geojson_path,
        )
    except Exception as exc:
        _actualizar_vuelo(vuelo_id, "error", f"Error en el pipeline GIS: {exc}")
        raise

    self.update_state(state="PROGRESS", meta={"progreso": 80, "mensaje": "Subiendo resultados"})

    try:
        from app.core.storage import upload_bytes
        partes = minio_key.split("/")  # {usuario_id}/{lote_id}/{vuelo_id}/original.tif
        prefijo = "/".join(partes[:3])
        with open(geojson_path, "rb") as f:
            geojson_bytes = f.read()
        upload_bytes(f"{prefijo}/zonas.geojson", geojson_bytes, content_type="application/geo+json")
    except Exception as exc:
        # Error no crítico — el análisis es válido aunque no se haya subido el GeoJSON
        estadisticas["advertencia_upload"] = str(exc)

    self.update_state(state="PROGRESS", meta={"progreso": 100, "mensaje": "Procesamiento completado"})
    _actualizar_vuelo(vuelo_id, "completado")

    return {"vuelo_id": vuelo_id, "estadisticas": estadisticas}


# Tarea legacy — se mantiene por compatibilidad con tests existentes
@celery_app.task(bind=True, name="workers.gis.tasks.procesar_analisis")
def procesar_analisis(self, analisis_id: str) -> dict:
    self.update_state(state="STARTED", meta={"progreso": 0, "mensaje": "Iniciando procesamiento"})
    return {"analisis_id": analisis_id, "status": "pendiente_implementacion"}
