import io
import json
import logging
import os
import tempfile
import time

import numpy as np
import rasterio
from rasterio.windows import Window
from workers.celery_app import celery_app

logger = logging.getLogger(__name__)

_DTYPES_VALIDOS = {"float32", "uint8", "uint16", "int16", "int32"}

# Hilos de GDAL para comprimir (DEFLATE) al optimizar un GeoTIFF. Conservador a
# propósito, mismo criterio que _WARP_NUM_THREADS en reproyeccion.py: con 2 hilos
# la compresión ya es ~3 veces más rápida y queda CPU libre para el resto.
_OPT_NUM_THREADS = 2

# Tope de bytes de una franja de lectura (512 líneas de ancho completo). Un raster
# muy ancho o con muchas bandas puede superarlo: en ese caso se lee por mosaicos.
_OPT_FRANJA_MAX_BYTES = 1 << 30


def _optimizacion_rapida() -> bool:
    """AGRONEXO_OPTIMIZACION_RAPIDA=0 vuelve al comportamiento anterior (mosaicos y un
    solo hilo) sin tocar código ni volver a desplegar."""
    return os.environ.get("AGRONEXO_OPTIMIZACION_RAPIDA", "1") != "0"


def _actualizar_lote_geometry(lote_id: str, wkt: str) -> None:
    """
    Rellena geometry (y area_ha) SOLO si el lote todavía no tiene una: un
    lote creado sin límite toma el del primer GeoTIFF que se le sube (ver
    migración 0005 y _poligono_cobertura_wkt).

    Un lote que YA tiene límite (dibujado a mano) no se toca. El `WHERE
    geometry IS NULL` evita pisarlo con el polígono del raster en cada
    vuelo nuevo — antes de este chequeo, cualquier vuelo (dron o satelital)
    subido a un lote ya dibujado le reemplazaba el polígono real
    silenciosamente (bug real detectado 2026-09-14, ver
    docs/release-v3.0.0.md).

    area_ha se calcula igual que en la API (app/lotes/service.py): ST_Area
    sobre EPSG:32721 (metros) / 10 000. Sin esto el lote figuraba con
    límite pero sin superficie.
    """
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session

    from app.core.config import settings

    engine = create_engine(settings.database_url_sync)
    try:
        with Session(engine) as session:
            session.execute(
                text(
                    "UPDATE lotes SET geometry = ST_GeomFromText(:wkt, 4326), "
                    "area_ha = ROUND((ST_Area(ST_Transform(ST_GeomFromText(:wkt, 4326), 32721)) / 10000)::numeric, 4), "
                    "updated_at = now() "
                    "WHERE id = CAST(:lote_id AS uuid) AND geometry IS NULL"
                ),
                {"wkt": wkt, "lote_id": lote_id},
            )
            session.commit()
    finally:
        engine.dispose()


def _poligono_cobertura_wkt(src) -> str:
    """
    WKT (EPSG:4326, el raster ya viene reproyectado) del área que realmente
    cubre el GeoTIFF: envolvente convexa de los píxeles con dato válido. Un
    ortomosaico rotado o con bordes sin dato tiene un bounding box bastante
    más grande que lo que cubre; si no hay máscara (todo válido) o no se
    puede calcular, es directamente el rectángulo del raster.

    La máscara se lee decimada (máx. ~1024 px de lado) para que sea barata
    aunque el archivo pese varios GB.
    """
    from affine import Affine
    from rasterio.features import shapes
    from shapely.geometry import box, shape
    from shapely.ops import unary_union

    rectangulo = box(*src.bounds)
    try:
        factor = max(1.0, max(src.height, src.width) / 1024)
        alto = max(1, round(src.height / factor))
        ancho = max(1, round(src.width / factor))
        mascara = src.dataset_mask(out_shape=(alto, ancho))
        transform = src.transform * Affine.scale(src.width / ancho, src.height / alto)
        partes = [shape(g) for g, v in shapes(mascara, mask=mascara > 0, transform=transform) if v > 0]
        cobertura = unary_union(partes).convex_hull if partes else rectangulo
        if cobertura.geom_type != "Polygon" or cobertura.area <= 0:
            cobertura = rectangulo
    except Exception:
        logger.exception("No se pudo calcular la cobertura real del GeoTIFF; se usa su bounding box")
        cobertura = rectangulo
    return cobertura.wkt


def _actualizar_vuelo(
    vuelo_id: str,
    estado: str,
    error: str | None = None,
    geojson_key: str | None = None,
    metodo_umbral: str | None = None,
    mapeo_bandas: dict | None = None,
) -> None:
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
                    "error_detalle = :error, geojson_key = :geojson_key, "
                    "metodo_umbral = COALESCE(:metodo_umbral, metodo_umbral), "
                    "mapeo_bandas = COALESCE(CAST(:mapeo_bandas AS JSONB), mapeo_bandas) "
                    "WHERE id = CAST(:vuelo_id AS uuid)"
                ),
                {
                    "estado": estado,
                    "error": error,
                    "geojson_key": geojson_key,
                    "metodo_umbral": metodo_umbral,
                    "mapeo_bandas": json.dumps(mapeo_bandas) if mapeo_bandas is not None else None,
                    "vuelo_id": vuelo_id,
                },
            )
            session.commit()
    finally:
        engine.dispose()


def _copiar_a_destino_tileado(src, dst) -> None:
    """
    Copia src a dst (tileado) leyendo franjas de líneas completas, no mosaicos.

    En un GeoTIFF por líneas (strip-based) leer mosaico por mosaico obliga a
    releer las mismas líneas por cada mosaico de la franja; leyendo la franja
    una sola vez se escriben de golpe todos sus mosaicos.
    """
    alto_franja = dst.block_shapes[0][0]
    bytes_franja = src.width * alto_franja * src.count * np.dtype(src.dtypes[0]).itemsize
    if not _optimizacion_rapida() or bytes_franja > _OPT_FRANJA_MAX_BYTES:
        for _, window in dst.block_windows(1):
            dst.write(src.read(window=window), window=window)
        return
    for fila in range(0, src.height, alto_franja):
        window = Window(0, fila, src.width, min(alto_franja, src.height - fila))
        dst.write(src.read(window=window), window=window)


def _optimizar_si_necesario(src_path: str) -> str:
    """
    Si el GeoTIFF no tiene compresión + tileado, lo reescribe con DEFLATE
    y tiles de 512×512 antes de procesarlo.

    Archivos de dron exportados sin compresión (strip-based layout) obligan a
    GDAL a leer el archivo completo para acceder a cualquier banda. Convertirlo
    al formato tileado hace que GDAL solo lea los bloques necesarios para la
    ventana pedida, reduciendo el tiempo de I/O de minutos a segundos.

    Retorna src_path si el archivo ya está en formato óptimo (sin I/O extra).
    Si necesita optimización, borra el original y retorna la ruta del nuevo archivo.
    """
    with rasterio.open(src_path) as src:
        ya_comprimido = src.profile.get("compress") is not None
        ya_tileado = src.profile.get("tiled", False)
        if ya_comprimido and ya_tileado:
            return src_path
        perfil = src.profile.copy()

    # predictor=3 para datos float (float32/float64); predictor=2 para enteros.
    # Usar predictor=2 con float32 corrompe los datos al leerlos de vuelta.
    dtype = perfil.get("dtype", "float32")
    predictor = 3 if str(dtype).startswith("float") else 2
    perfil.update(
        compress="deflate",
        predictor=predictor,
        tiled=True,
        blockxsize=512,
        blockysize=512,
        # datos ya cercanos a 4 GiB sin comprimir pueden no reducirse lo
        # suficiente con DEFLATE — sin esto, GDAL falla al cruzar el límite
        # de TIFF clásico igual que en reproyeccion.py.
        bigtiff="IF_SAFER",
    )
    if _optimizacion_rapida():
        perfil["num_threads"] = str(_OPT_NUM_THREADS)
    dst_path = src_path + ".opt.tif"
    size_orig_mb = os.path.getsize(src_path) / 1_048_576
    t0 = time.perf_counter()
    logger.info("[task] optimizando GeoTIFF (%.0f MB, strip-based sin compresión)…", size_orig_mb)

    try:
        with rasterio.open(src_path) as src, rasterio.open(dst_path, "w", **perfil) as dst:
            _copiar_a_destino_tileado(src, dst)
    except Exception:
        if os.path.exists(dst_path):
            os.unlink(dst_path)
        raise

    size_opt_mb = os.path.getsize(dst_path) / 1_048_576
    logger.info(
        "[task] optimización completada: %.0f MB → %.0f MB en %.2fs",
        size_orig_mb, size_opt_mb, time.perf_counter() - t0,
    )
    os.unlink(src_path)
    return dst_path


def _key_preparado(minio_key: str) -> str:
    """
    {usuario}/{lote}/{vuelo}/original.tif -> {usuario}/{lote}/{vuelo}/preparado_4326.tif

    Cachea el archivo ya optimizado (tileado+comprimido) y reproyectado a
    EPSG:4326 en MinIO. Sin esto, cada índice adicional (NDRE/SAVI/ExG/GNDVI)
    pedido sobre el mismo vuelo repetía desde cero la descarga del original
    completo, la recompresión y la reproyección — pasos costosos que dan
    exactamente el mismo resultado sin importar qué índice se calcule después.
    """
    partes = minio_key.rsplit("/", 1)
    prefijo = partes[0] if len(partes) > 1 else ""
    return f"{prefijo}/preparado_4326.tif" if prefijo else "preparado_4326.tif"


def _preparar_geotiff(tiff_path: str) -> str:
    """
    Deja el archivo listo para el pipeline: reproyectado a EPSG:4326 (si
    hace falta) y tileado+comprimido.

    Si hace falta reproyectar, reproyectar_a_4326_archivo() ya escribe el
    resultado tileado+comprimido — correr _optimizar_si_necesario después
    reescribiría el archivo por segunda vez para nada. Si ya está en 4326,
    solo hace falta el paso de optimización.
    """
    from workers.gis.reproyeccion import necesita_reproyeccion, reproyectar_a_4326_archivo

    with rasterio.open(tiff_path) as src:
        hace_falta_reproyectar = necesita_reproyeccion(src)

    if not hace_falta_reproyectar:
        return _optimizar_si_necesario(tiff_path)

    dst_path = tiff_path + ".repro.tif"
    resultado = reproyectar_a_4326_archivo(tiff_path, dst_path)
    if resultado != tiff_path:
        os.unlink(tiff_path)
    return resultado


def _descargar_preparado(minio_key: str, tiff_path: str) -> bool:
    """
    Descarga a tiff_path el archivo listo para procesar. Si ya existe una
    versión preparada en caché (ver _key_preparado), la descarga directamente
    y devuelve True — el caller debe saltear validación/optimización/
    reproyección, ya se hicieron la primera vez que se procesó este vuelo.
    Si no hay caché, descarga el original tal cual y devuelve False.
    """
    from app.core.storage import download_geotiff_to_file, object_exists

    key_cache = _key_preparado(minio_key)
    if object_exists(key_cache):
        logger.info("[task] GeoTIFF preparado encontrado en caché: %s", key_cache)
        download_geotiff_to_file(key_cache, tiff_path)
        return True

    download_geotiff_to_file(minio_key, tiff_path)
    return False


def _guardar_preparado_en_cache(minio_key: str, tiff_path: str) -> None:
    """Sube el archivo ya preparado a la caché — best-effort, nunca bloquea el pipeline."""
    from app.core.storage import upload_file

    try:
        t0 = time.perf_counter()
        upload_file(_key_preparado(minio_key), tiff_path, content_type="image/tiff")
        logger.info("[task] GeoTIFF preparado guardado en caché: %.2fs", time.perf_counter() - t0)
    except Exception as exc:
        logger.warning("[task] no se pudo guardar el GeoTIFF preparado en caché: %s", exc)


# TTL del lock de preparación en Redis — cota superior generosa para un
# archivo de varios GB (optimizar+reproyectar puede tardar minutos). Si el
# holder del lock muere sin liberarlo, expira solo y no queda trabado.
_LOCK_PREP_TTL_S = 1800
_LOCK_PREP_POLL_S = 3


def _cliente_redis_lock():
    import redis
    from app.core.config import settings
    return redis.from_url(settings.celery_broker_url)


def _esperar_preparacion_en_curso(key_cache: str, lock_key: str, r, self_task) -> bool:
    """
    Sondea hasta _LOCK_PREP_TTL_S esperando que la task que tiene el lock
    termine de optimizar/reproyectar el archivo. Devuelve True si encontró
    la caché lista (el caller debe descargarla en vez de reproyectar de
    nuevo); False si hay que tomar el lock y prepararlo uno mismo (timeout,
    o el que tenía el lock lo soltó sin dejar caché — falló).
    """
    from app.core.storage import object_exists

    self_task.update_state(state="PROGRESS", meta={
        "progreso": 12,
        "mensaje": "Esperando preparación en curso de otro análisis de este mismo vuelo",
    })
    t_espera = time.perf_counter()
    while time.perf_counter() - t_espera < _LOCK_PREP_TTL_S:
        if object_exists(key_cache):
            logger.info(
                "[task] otro análisis del mismo vuelo ya preparó el archivo (%.0fs esperados) — se reusa en vez de reproyectar de nuevo",
                time.perf_counter() - t_espera,
            )
            return True
        if r.exists(lock_key) == 0:
            return False
        time.sleep(_LOCK_PREP_POLL_S)
    return False


def _preparar_archivo_para_pipeline(minio_key: str, tiff_path: str, self_task, marcar_error) -> str:
    """
    Descarga (con caché, ver _descargar_preparado) + valida + optimiza/
    reproyecta un GeoTIFF antes de correr el pipeline sobre él. Compartido
    por procesar_vuelo, analizar_indice y analizar_indices_batch para no
    triplicar este preámbulo — es idéntico en los tres, solo cambia a quién
    se le reporta el error si algo falla.

    Devuelve la ruta final a usar (puede diferir de tiff_path si
    _preparar_geotiff generó un archivo nuevo). Si falla la descarga o la
    validación, llama a marcar_error(mensaje), borra tiff_path y re-lanza.

    El paso de optimizar/reproyectar está protegido por un lock en Redis
    (por vuelo): al subir un vuelo con varios índices tildados, NDVI
    (procesar_vuelo) y el batch de índices adicionales (analizar_indices_batch)
    se disparan casi al mismo tiempo, y sin este lock ambas tasks terminaban
    reproyectando el mismo archivo de varios GB en paralelo — en archivos
    pesados eso duplicaba el paso más caro del pipeline (minutos) en vez de
    aprovechar la caché entre sí. Si Redis no está disponible por algún
    motivo, se sigue sin lock (mismo comportamiento que antes) en vez de
    bloquear el pipeline.
    """
    from app.core.storage import download_geotiff_to_file, object_exists

    t_descarga = time.perf_counter()
    try:
        desde_cache = _descargar_preparado(minio_key, tiff_path)
    except Exception as exc:
        marcar_error(f"Error al descargar el archivo: {exc}")
        os.unlink(tiff_path)
        raise
    size_mb = os.path.getsize(tiff_path) / 1_048_576
    logger.info("[task] descarga MinIO (%.1f MB, cache=%s): %.2fs", size_mb, desde_cache, time.perf_counter() - t_descarga)

    if desde_cache:
        return tiff_path

    key_cache = _key_preparado(minio_key)
    lock_key = f"prep_lock:{key_cache}"
    lock_propio = False
    r = None
    try:
        r = _cliente_redis_lock()
        lock_propio = bool(r.set(lock_key, "1", nx=True, ex=_LOCK_PREP_TTL_S))
        if not lock_propio:
            if _esperar_preparacion_en_curso(key_cache, lock_key, r, self_task):
                os.unlink(tiff_path)
                download_geotiff_to_file(key_cache, tiff_path)
                return tiff_path
            lock_propio = bool(r.set(lock_key, "1", nx=True, ex=_LOCK_PREP_TTL_S))
    except Exception as exc:
        logger.warning("[task] lock de preparación (Redis) no disponible, se continúa sin dedupe: %s", exc)
        r = None

    try:
        self_task.update_state(state="PROGRESS", meta={"progreso": 15, "mensaje": "Validando CRS y bandas"})
        try:
            _validar_geotiff_gis_archivo(tiff_path)
        except Exception as exc:
            mensaje = str(exc) if isinstance(exc, ValueError) else "El archivo no es un GeoTIFF válido o está dañado."
            marcar_error(mensaje)
            os.unlink(tiff_path)
            raise ValueError(mensaje) from exc

        self_task.update_state(state="PROGRESS", meta={"progreso": 20, "mensaje": "Optimizando y reproyectando"})
        t_prep = time.perf_counter()
        try:
            tiff_path_preparado = _preparar_geotiff(tiff_path)
        except Exception as exc:
            logger.warning("[task] preparación GeoTIFF fallida, continuando con archivo original: %s", exc)
            return tiff_path
        logger.info("[task] preparación (optimizar+reproyectar): %.2fs", time.perf_counter() - t_prep)
        _guardar_preparado_en_cache(minio_key, tiff_path_preparado)
        return tiff_path_preparado
    finally:
        if lock_propio and r is not None:
            try:
                r.delete(lock_key)
            except Exception:
                pass


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
    # Detectar CRS tipo EngineeringCRS sin código EPSG recuperable: PROJ no
    # puede transformarlo a geográfico y `_resolver_crs` (reproyeccion.py)
    # tampoco puede reconstruirlo. Cuando SÍ trae un código EPSG embebido,
    # dejamos pasar — `reproyectar_a_4326_archivo` lo resuelve más adelante
    # en el pipeline (ver _resolver_crs). Rechazar acá incondicionalmente
    # bloquearía archivos que el pipeline sabe procesar igual.
    try:
        # rasterio.crs.CRS no tiene to_json_dict() (eso es de pyproj.CRS) —
        # _projjson() es el equivalente real disponible en esta clase.
        d = json.loads(src.crs._projjson())
        if d.get("type") == "EngineeringCRS":
            crs_id = d.get("id", {})
            if crs_id.get("authority") != "EPSG":
                raise ValueError(
                    "El CRS del archivo es de tipo 'EngineeringCRS' sin código EPSG "
                    "reconstruible — el software que lo exportó generó metadatos de "
                    "proyección incompletos y no hay forma de recuperar el sistema de "
                    "referencia original.\n"
                    "Solución: abrí el archivo en QGIS y exportalo con CRS EPSG:4326, "
                    "o usá GDAL desde la terminal:\n"
                    "  gdalwarp -t_srs EPSG:4326 archivo.tif archivo_corregido.tif"
                )
    except ValueError:
        raise
    except Exception:
        pass
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
    # Muestra de 128×128 px para detectar imágenes vacías sin leer el archivo completo.
    # Recorre TODAS las bandas (no solo la 1) — el mapeo sentinel2 de
    # band_mapping.py deja la banda 1 sin usar a propósito (BLUE arranca en
    # la posición 2, replicando la numeración real de Sentinel-2 donde la
    # banda 1 es Coastal Aerosol). Chequear solo la banda 1 rechazaba como
    # "vacío" cualquier GeoTIFF sentinel2 real, aunque el resto de las
    # bandas tuviera datos válidos.
    nodata = src.nodata
    px_validos = 0
    for banda in range(1, min(src.count, 8) + 1):
        muestra = src.read(banda, out_shape=(1, min(128, src.height), min(128, src.width))).astype(np.float64)
        if nodata is not None and not (isinstance(nodata, float) and np.isnan(nodata)):
            px_validos += int(np.sum(muestra != nodata))
        else:
            px_validos += int(np.sum(~np.isnan(muestra)))
        if px_validos > 0:
            break
    if px_validos == 0:
        raise ValueError(
            "La imagen no tiene píxeles con datos válidos — el archivo está vacío. "
            "Probable causa: error de exportación en DJI Terra / Pix4D / Agisoft. "
            "Solución: abrí el archivo en QGIS para verificar que tenga datos y "
            "volvé a exportar el ortomosaico desde tu software."
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
    from app.core.storage import upload_bytes
    from workers.gis.pipeline import ejecutar_pipeline_archivo

    self.update_state(state="STARTED", meta={"progreso": 0, "mensaje": "Descargando archivo desde almacenamiento"})

    # Descargar a archivo temporal en disco — sin cargar el archivo completo en RAM
    tiff_tmp = tempfile.NamedTemporaryFile(suffix=".tif", delete=False)
    tiff_path = tiff_tmp.name
    tiff_tmp.close()

    tiff_path = _preparar_archivo_para_pipeline(
        minio_key, tiff_path, self,
        marcar_error=lambda msg: _actualizar_vuelo(vuelo_id, "error", msg),
    )

    if lote_id:
        try:
            # A esta altura tiff_path ya está garantizado en EPSG:4326
            # (recién preparado, o descargado directo de la caché) — no
            # hace falta reproyectar de nuevo solo para leer los bounds.
            with rasterio.open(tiff_path) as src:
                wkt = _poligono_cobertura_wkt(src)
            _actualizar_lote_geometry(lote_id, wkt)
        except Exception:
            # no bloquear el pipeline, pero dejar rastro: sin esto el lote
            # quedaba sin límite y nadie sabía por qué
            logger.exception("No se pudo completar el límite del lote %s desde el GeoTIFF", lote_id)

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
            limite_wgs84=_limite_para_recorte(minio_key),
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
    from workers.gis.band_mapping import obtener_mapeo
    _actualizar_vuelo(
        vuelo_id, "completado", geojson_key=geojson_key_guardado,
        metodo_umbral=metodo_umbral, mapeo_bandas=obtener_mapeo(sensor)._asdict(),
    )

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


# ── Carga de vuelo desde imagen satelital (Sentinel-2 / Earth Search) ───────

def _obtener_geometry_lote_geojson(lote_id: str) -> dict | None:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session

    from app.core.config import settings

    engine = create_engine(settings.database_url_sync)
    try:
        with Session(engine) as session:
            row = session.execute(
                text("SELECT ST_AsGeoJSON(geometry) FROM lotes WHERE id = CAST(:lote_id AS uuid)"),
                {"lote_id": lote_id},
            ).scalar_one_or_none()
        return json.loads(row) if row else None
    finally:
        engine.dispose()


def _limite_para_recorte(minio_key: str) -> dict | None:
    """
    Límite del lote al que pertenece el archivo, para recortar las zonas
    vectorizadas. El enmascarado por píxeles de las escenas satelitales deja
    un borde afuera del polígono, y un ortomosaico puede cubrir más que el
    lote — en ambos casos el resultado no debe salir del límite guardado.
    Si el lote todavía no tiene geometry no se recorta.
    """
    partes = minio_key.split("/")  # {usuario_id}/{lote_id}/{vuelo_id}/original.tif
    if len(partes) < 3:
        return None
    try:
        return _obtener_geometry_lote_geojson(partes[1])
    except Exception:
        logger.exception("No se pudo leer el límite del lote %s para recortar las zonas", partes[1])
        return None


def _actualizar_vuelo_archivo_y_task(vuelo_id: str, minio_key: str, task_id: str) -> None:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session

    from app.core.config import settings

    engine = create_engine(settings.database_url_sync)
    try:
        with Session(engine) as session:
            session.execute(
                text(
                    "UPDATE vuelos SET archivo_original = :minio_key, task_id = :task_id "
                    "WHERE id = CAST(:vuelo_id AS uuid)"
                ),
                {"minio_key": minio_key, "task_id": task_id, "vuelo_id": vuelo_id},
            )
            session.commit()
    finally:
        engine.dispose()


@celery_app.task(
    bind=True,
    name="workers.gis.tasks.descargar_satelital",
    autoretry_for=(ConnectionError, OSError),
    max_retries=3,
    default_retry_delay=30,
)
def descargar_satelital(
    self, vuelo_id: str, lote_id: str, usuario_id: str, escena_id: str, sensor: str = "sentinel2",
    analisis_ids: dict | None = None,
) -> dict:
    """
    Descarga la escena Sentinel-2 `escena_id` (elegida por el usuario en
    GET .../imagenes-satelitales), la recorta al polígono real del lote,
    la sube a MinIO con la misma convención de key que un upload de dron
    ({usuario}/{lote}/{vuelo}/original.tif), y encola procesar_vuelo con
    ese archivo — de ahí en más es el mismo pipeline que un vuelo de dron,
    sin cambios.
    """
    from app.core.storage import upload_geotiff_stream
    from workers.gis.satelital_catalogo import obtener_escena_por_id
    from workers.gis.satelital_descarga import descargar_y_recortar_geotiff

    self.update_state(state="STARTED", meta={"progreso": 0, "mensaje": "Consultando escena satelital"})

    poligono = _obtener_geometry_lote_geojson(lote_id)
    if poligono is None:
        _actualizar_vuelo(vuelo_id, "error", "El lote no tiene límite (geometry) cargado — no se puede recortar la imagen satelital.")
        raise ValueError(f"Lote {lote_id} sin geometry, no se puede procesar imagen satelital.")

    try:
        item = obtener_escena_por_id(escena_id)
    except Exception as exc:
        _actualizar_vuelo(vuelo_id, "error", f"No se pudo consultar la escena satelital: {exc}")
        raise

    self.update_state(state="PROGRESS", meta={"progreso": 20, "mensaje": "Descargando y recortando bandas Sentinel-2"})

    tiff_tmp = tempfile.NamedTemporaryFile(suffix=".tif", delete=False)
    tiff_path = tiff_tmp.name
    tiff_tmp.close()

    try:
        descargar_y_recortar_geotiff(item, poligono, tiff_path)

        self.update_state(state="PROGRESS", meta={"progreso": 60, "mensaje": "Subiendo a almacenamiento"})
        with open(tiff_path, "rb") as f:
            key = upload_geotiff_stream(
                usuario_id=usuario_id, lote_id=lote_id, vuelo_id=vuelo_id,
                stream=f, length=os.path.getsize(tiff_path),
            )
    except Exception as exc:
        _actualizar_vuelo(vuelo_id, "error", f"Error descargando imagen satelital: {exc}")
        raise
    finally:
        if os.path.exists(tiff_path):
            os.unlink(tiff_path)

    self.update_state(state="PROGRESS", meta={"progreso": 70, "mensaje": "Encolando cálculo de NDVI"})

    tarea_procesamiento = celery_app.send_task(
        "workers.gis.tasks.procesar_vuelo",
        kwargs={"vuelo_id": vuelo_id, "lote_id": lote_id, "minio_key": key, "sensor": sensor, "indice": "ndvi"},
        queue="gis",
    )
    # El polling de GET /vuelos/{id}/estado sigue vuelo.task_id — hay que
    # apuntarlo a la tarea nueva (procesar_vuelo). Si no, el frontend vería
    # esta tarea (ya terminada) en vez del progreso real del procesamiento.
    _actualizar_vuelo_archivo_y_task(vuelo_id, key, tarea_procesamiento.id)

    if analisis_ids:
        celery_app.send_task(
            "workers.gis.tasks.analizar_indices_batch",
            kwargs={
                "analisis_ids": analisis_ids,
                "minio_key": key,
                "sensor": sensor,
                "indices": list(analisis_ids.keys()),
                "metodo_umbral": "fijo",
            },
            queue="gis",
        )

    return {
        "vuelo_id": vuelo_id,
        "minio_key": key,
        "escena_id": escena_id,
        "task_id_procesamiento": tarea_procesamiento.id,
    }


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
    from app.core.storage import upload_bytes
    from workers.gis.pipeline import ejecutar_pipeline_archivo

    self.update_state(state="STARTED", meta={"progreso": 0, "mensaje": "Descargando archivo desde almacenamiento"})

    tiff_tmp = tempfile.NamedTemporaryFile(suffix=".tif", delete=False)
    tiff_path = tiff_tmp.name
    tiff_tmp.close()

    tiff_path = _preparar_archivo_para_pipeline(
        minio_key, tiff_path, self,
        marcar_error=lambda msg: _actualizar_analisis_indice(analisis_id, "error", msg),
    )

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
            limite_wgs84=_limite_para_recorte(minio_key),
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


@celery_app.task(
    bind=True,
    name="workers.gis.tasks.analizar_indices_batch",
    autoretry_for=(ConnectionError, OSError),
    max_retries=3,
    default_retry_delay=30,
)
def analizar_indices_batch(
    self,
    analisis_ids: dict[str, str],
    minio_key: str,
    sensor: str,
    indices: list[str],
    metodo_umbral: str = "fijo",
    area_minima_m2: int = 10_000,
) -> dict:
    """
    Calcula varios índices adicionales sobre un mismo vuelo en una sola
    corrida: descarga el GeoTIFF una vez y lee cada banda una vez (NIR se
    comparte entre NDVI/NDRE/SAVI/GNDVI, RED entre NDVI/SAVI/ExG), en lugar
    de repetir el pipeline completo por índice como hace analizar_indice.
    Se usa cuando el usuario tilda varios índices a la vez al subir un
    vuelo (ver ModalCargaGeoTIFF.jsx); analizar_indice sigue existiendo
    para cuando se pide un único índice adicional después.

    analisis_ids: {"ndre": "<uuid fila AnalisisIndice>", "savi": "<uuid>", ...}
    — cada fila se actualiza de forma independiente a medida que su índice
    termina, así que el polling por índice (GET .../indices/{indice}/estado)
    sigue funcionando igual que con la task single.
    """
    from app.core.storage import upload_bytes
    from workers.gis.pipeline import ejecutar_pipeline_multi_indice_archivo

    self.update_state(state="STARTED", meta={"progreso": 0, "mensaje": "Descargando archivo desde almacenamiento"})

    tiff_tmp = tempfile.NamedTemporaryFile(suffix=".tif", delete=False)
    tiff_path = tiff_tmp.name
    tiff_tmp.close()

    def _marcar_todos_error(mensaje: str) -> None:
        for analisis_id in analisis_ids.values():
            _actualizar_analisis_indice(analisis_id, "error", mensaje)

    tiff_path = _preparar_archivo_para_pipeline(minio_key, tiff_path, self, marcar_error=_marcar_todos_error)

    for analisis_id in analisis_ids.values():
        _actualizar_analisis_indice(analisis_id, "procesando")
    self.update_state(state="PROGRESS", meta={"progreso": 30, "mensaje": f"Calculando {len(indices)} índices"})

    partes = minio_key.split("/")  # {usuario_id}/{lote_id}/{vuelo_id}/original.tif
    prefijo = "/".join(partes[:3])

    geojson_paths: dict[str, str] = {}
    for indice in indices:
        tmp = tempfile.NamedTemporaryFile(suffix=".geojson", delete=False)
        geojson_paths[indice] = tmp.name
        tmp.close()

    resultados: dict[str, dict] = {}
    errores: dict[str, str] = {}

    def _on_completado(indice: str, estadisticas: dict) -> None:
        geojson_key_guardado: str | None = f"{prefijo}/zonas_{indice}.geojson"
        try:
            with open(geojson_paths[indice], "rb") as f:
                geojson_bytes = f.read()
            upload_bytes(geojson_key_guardado, geojson_bytes, content_type="application/geo+json")
        except Exception as exc:
            estadisticas["advertencia_upload"] = str(exc)
            geojson_key_guardado = None
        resultados[indice] = estadisticas
        _actualizar_analisis_indice(
            analisis_ids[indice], "completado",
            geojson_key=geojson_key_guardado,
            metodo_umbral=estadisticas.get("metodo_umbral"),
        )
        self.update_state(state="PROGRESS", meta={
            "progreso": 30 + int(60 * (len(resultados) + len(errores)) / len(indices)),
            "mensaje": f"{indice.upper()} completado",
        })

    def _on_error(indice: str, exc: Exception) -> None:
        errores[indice] = str(exc)
        _actualizar_analisis_indice(analisis_ids[indice], "error", f"Error en el pipeline GIS: {exc}")
        self.update_state(state="PROGRESS", meta={
            "progreso": 30 + int(60 * (len(resultados) + len(errores)) / len(indices)),
            "mensaje": f"{indice.upper()} falló",
        })

    try:
        ejecutar_pipeline_multi_indice_archivo(
            path=tiff_path,
            sensor=sensor,
            indices=indices,
            geojson_destino_por_indice=geojson_paths,
            metodo_umbral=metodo_umbral,
            area_minima_m2=area_minima_m2,
            on_indice_completado=_on_completado,
            on_indice_error=_on_error,
            limite_wgs84=_limite_para_recorte(minio_key),
        )
    finally:
        if os.path.exists(tiff_path):
            os.unlink(tiff_path)
        for p in geojson_paths.values():
            if os.path.exists(p):
                os.unlink(p)

    self.update_state(state="PROGRESS", meta={"progreso": 100, "mensaje": "Procesamiento completado"})
    return {"resultados": resultados, "errores": errores}


# Tarea legacy — se mantiene por compatibilidad con tests existentes
@celery_app.task(bind=True, name="workers.gis.tasks.procesar_analisis")
def procesar_analisis(self, analisis_id: str) -> dict:
    self.update_state(state="STARTED", meta={"progreso": 0, "mensaje": "Iniciando procesamiento"})
    return {"analisis_id": analisis_id, "status": "pendiente_implementacion"}
