"""
Pipeline GIS generalizado: GeoTIFF → índice → clasificación → GeoJSON.

Soporta NDVI, NDRE, SAVI y ExG con mapeo de bandas configurable por sensor.
La lógica de vectorización y exportación reutiliza workers/gis/zonas.py.
"""

import io
import logging
import time

import numpy as np
import rasterio
from rasterio.enums import Resampling

logger = logging.getLogger(__name__)

from workers.gis.band_mapping import BANDAS_POR_INDICE, numero_banda, validar_bandas_disponibles

# Umbral en píxeles totales a partir del cual se activa la lectura decimada.
# ~3000×3000 px — por encima de esto, materializar la banda a resolución
# completa en RAM (varios GB para un GeoTIFF grande ya reproyectado) puede
# tirar el worker por out-of-memory, además de volver lenta la clasificación
# y vectorización.
_UMBRAL_DOWNSAMPLE_PX = 9_000_000


def _factor_downsample(shape: tuple[int, int]) -> int:
    """Factor de reducción entero (1 = sin reducción)."""
    total = shape[0] * shape[1]
    if total <= _UMBRAL_DOWNSAMPLE_PX:
        return 1
    return int(np.ceil(np.sqrt(total / _UMBRAL_DOWNSAMPLE_PX)))


def _downsample_meta(meta: dict, factor: int) -> dict:
    """Devuelve meta actualizado con transform y shape a la resolución reducida."""
    from rasterio.transform import Affine
    t = meta["transform"]
    h, w = meta["shape"]
    return {
        **meta,
        "transform": Affine(t.a * factor, t.b, t.c, t.d, t.e * factor, t.f),
        "shape": (h // factor, w // factor),
    }


from workers.gis.indices import calcular_indice
from workers.gis.reproyeccion import reproyectar_a_4326
from workers.gis.zonas import clasificar_ndvi, exportar_geojson, suavizar_indice, vectorizar_zonas

# Umbrales de clasificación reutilizados del módulo de zonificación.
# NDVI, NDRE y SAVI son índices "razón" (diferencia sobre suma) — su rango
# es siempre ~[-1,1] sin importar la escala de las bandas de entrada
# (reflectancia 0-1 o DN crudo), así que el umbral fijo aplica directamente.
# ExG (2*GREEN-RED-BLUE) NO es una razón — es una resta lineal absoluta cuya
# escala depende de las unidades crudas de la cámara (reflectancia 0-1 da
# valores ~[-2,2]; DN 8-bit sin calibrar da valores de cientos). El umbral
# fijo pensado para NDVI no tiene sentido ahí — ver _metodo_umbral_efectivo().


def _metodo_umbral_efectivo(indice: str, metodo_umbral: str) -> str:
    """
    ExG no es un índice normalizado (a diferencia de NDVI/NDRE/SAVI) — su rango
    depende de la escala cruda de las bandas de entrada, así que el umbral
    "fijo" [0.20, 0.40, 0.70] (pensado para índices razón en [-1,1]) puede
    clasificar todo el lote en una sola clase sin relación con el vigor real.
    Si el caller no pidió explícitamente un método adaptativo, forzamos "otsu"
    para ExG, que calcula el corte según la distribución real de los datos.
    """
    if indice == "exg" and metodo_umbral == "fijo":
        return "otsu"
    return metodo_umbral


def _leer_banda(src: rasterio.DatasetReader, num: int, factor: int) -> np.ndarray:
    """
    Lee una banda a resolución completa, o decimada si factor > 1 (raster
    grande, ver _factor_downsample) usando el resampling nativo de GDAL
    (out_shape + Resampling.average) en vez de leer la banda completa y
    recién después reducirla en NumPy.

    Esto es imprescindible para rasters muy grandes: materializar un array
    float32 a resolución completa (varios GB para un GeoTIFF de pocos GB ya
    reproyectado) puede tirar el worker por out-of-memory — GDAL decima
    mientras lee, sin cargar nunca el array completo en RAM. masked=True
    respeta el nodata del dataset durante el promedio — sin esto, un bloque
    de borde podría promediar el valor crudo del nodata como si fuera dato
    real y corromper el índice en el borde del raster.
    """
    if factor <= 1:
        return src.read(num).astype(np.float32)
    out_h = max(1, src.height // factor)
    out_w = max(1, src.width // factor)
    banda = src.read(num, out_shape=(out_h, out_w), resampling=Resampling.average, masked=True)
    # Castear a float32 ANTES de rellenar con NaN — el dtype de origen puede
    # ser entero (uint8/uint16, DN crudo de dron/satélite sin calibrar), que
    # no puede representar NaN y hace fallar np.ma.filled con TypeError.
    return np.ma.filled(banda.astype(np.float32), np.nan)


def _leer_bandas_requeridas(
    src: rasterio.DatasetReader,
    sensor: str,
    indice: str,
    factor: int = 1,
) -> tuple[dict[str, np.ndarray], float | None]:
    """Lee solo las bandas necesarias para el índice y sensor dados."""
    nombres = BANDAS_POR_INDICE[indice]
    bandas: dict[str, np.ndarray] = {}
    for nombre in nombres:
        num = numero_banda(sensor, nombre)
        bandas[nombre] = _leer_banda(src, num, factor)
    return bandas, src.nodata


def _procesar_indice_desde_bandas(
    indice: str,
    sensor: str,
    bandas: dict[str, np.ndarray],
    nodata: float | None,
    meta: dict,
    geojson_destino: str,
    metodo_umbral: str,
    area_minima_m2: int,
    t0: float | None = None,
) -> dict:
    """
    Núcleo del pipeline a partir de bandas ya leídas (a la resolución que
    haya decidido _leer_banda — completa, o decimada por GDAL si el raster
    es grande): calcular índice → suavizar → clasificar → vectorizar →
    exportar GeoJSON → estadísticas.

    Extraído de ejecutar_pipeline/ejecutar_pipeline_archivo para que
    ejecutar_pipeline_multi_indice_archivo pueda reusarlo por cada índice
    de un batch sin releer las bandas compartidas (NIR, RED, etc.) del disco
    una vez por índice.

    Nota: para rasters grandes, `bandas` ya viene decimada — las
    estadísticas del lote (min/max/promedio) y la vectorización se calculan
    sobre esa misma resolución reducida, no sobre resolución completa. Es
    una diferencia deliberada respecto al comportamiento anterior (que sí
    calculaba sobre resolución completa) — leer y promediar la banda
    completa en RAM para un raster de varios GB puede tirar el worker por
    out-of-memory, así que se prioriza que el análisis termine sobre
    precisión estadística exacta en el caso de imágenes muy grandes.
    """
    if t0 is None:
        t0 = time.perf_counter()

    t2 = time.perf_counter()
    valores = calcular_indice(indice, bandas, nodata)
    logger.info(
        "[pipeline] calculo %s (%dx%d): %.2fs",
        indice.upper(), meta["shape"][1], meta["shape"][0], time.perf_counter() - t2,
    )

    t3 = time.perf_counter()
    valores_suavizados = suavizar_indice(valores)
    logger.info("[pipeline] suavizado: %.2fs", time.perf_counter() - t3)

    metodo_efectivo = _metodo_umbral_efectivo(indice, metodo_umbral)

    t4 = time.perf_counter()
    clase = clasificar_ndvi(valores_suavizados, metodo=metodo_efectivo)
    logger.info("[pipeline] clasificacion (%s): %.2fs", metodo_efectivo, time.perf_counter() - t4)

    t5 = time.perf_counter()
    gdf = vectorizar_zonas(clase, valores, meta, area_minima_m2=area_minima_m2)
    logger.info("[pipeline] vectorizacion (%d poligonos): %.2fs", len(gdf), time.perf_counter() - t5)

    t6 = time.perf_counter()
    ruta_salida = exportar_geojson(gdf, geojson_destino)
    logger.info("[pipeline] exportacion geojson: %.2fs", time.perf_counter() - t6)

    logger.info("[pipeline] TOTAL %s: %.2fs", indice.upper(), time.perf_counter() - t0)

    total_px_clase = int(np.sum(clase > 0))
    estadisticas: dict = {
        "indice": indice,
        "sensor": sensor,
        "metodo_umbral": metodo_efectivo,
        "geojson": ruta_salida,
        "total_poligonos": len(gdf),
        f"{indice}_promedio_lote": round(float(np.nanmean(valores)), 4),
        f"{indice}_min": round(float(np.nanmin(valores)), 4),
        f"{indice}_max": round(float(np.nanmax(valores)), 4),
        "clases": {},
    }

    codigos = {1: "critica", 2: "deficiente", 3: "normal", 4: "vigorosa"}
    for codigo, nombre in codigos.items():
        zonas = gdf[gdf["clase"] == nombre] if "clase" in gdf.columns else gdf.iloc[0:0]
        px_clase = int(np.sum(clase == codigo))
        estadisticas["clases"][nombre] = {
            "poligonos": len(zonas),
            "area_ha_total": round(float(zonas["area_ha"].sum()), 4) if len(zonas) > 0 else 0.0,
            "porcentaje_px": round(px_clase / total_px_clase * 100, 2) if total_px_clase > 0 else 0.0,
        }

    return estadisticas


def ejecutar_pipeline(
    data: bytes,
    sensor: str,
    indice: str,
    geojson_destino: str,
    metodo_umbral: str = "fijo",
    area_minima_m2: int = 1000,
) -> dict:
    """
    Pipeline completo en memoria:
      bytes GeoTIFF → reproyectar → leer bandas → calcular índice
      → clasificar → vectorizar → exportar GeoJSON → estadísticas

    Parámetros
    ----------
    data            : bytes del GeoTIFF descargado desde MinIO
    sensor          : "sentinel2" | "dji_mavic3"
    indice          : "ndvi" | "ndre" | "savi" | "exg"
    geojson_destino : ruta local donde se escribe el GeoJSON de salida
    """
    t0 = time.perf_counter()

    # Reproyectar a EPSG:4326 si el CRS original es distinto
    data = reproyectar_a_4326(data)
    logger.info("[pipeline] reproyeccion: %.2fs", time.perf_counter() - t0)

    t1 = time.perf_counter()
    with rasterio.open(io.BytesIO(data)) as src:
        validar_bandas_disponibles(sensor, indice, src.count)

        shape_original = (src.height, src.width)
        factor = _factor_downsample(shape_original)
        bandas, nodata = _leer_bandas_requeridas(src, sensor, indice, factor)
        meta = {
            "crs": src.crs,
            "transform": src.transform,
            "nodata": nodata,
            "shape": shape_original,
        }
        if factor > 1:
            logger.info(
                "[pipeline] lectura decimada x%d: %dx%d → %dx%d (raster grande)",
                factor, shape_original[1], shape_original[0],
                shape_original[1] // factor, shape_original[0] // factor,
            )
            meta = _downsample_meta(meta, factor)
    logger.info("[pipeline] lectura de bandas (%dx%d): %.2fs", meta["shape"][1], meta["shape"][0], time.perf_counter() - t1)

    return _procesar_indice_desde_bandas(
        indice, sensor, bandas, nodata, meta, geojson_destino, metodo_umbral, area_minima_m2, t0=t0,
    )


def ejecutar_pipeline_archivo(
    path: str,
    sensor: str,
    indice: str,
    geojson_destino: str,
    metodo_umbral: str = "fijo",
    area_minima_m2: int = 10_000,
) -> dict:
    """
    Variante de ejecutar_pipeline para archivos grandes (> 500 MB / 3 GB+).

    Lee directamente desde disco — GDAL hace el I/O tileado internamente
    sin cargar el raster completo en memoria. Si el raster es grande
    (ver _UMBRAL_DOWNSAMPLE_PX), la banda se lee ya decimada por GDAL en
    vez de leerse completa y reducirse después — evita materializar en RAM
    un array de varios GB.

    path             : ruta al GeoTIFF en disco (archivo local del worker)
    """
    import os

    from workers.gis.reproyeccion import reproyectar_a_4326_archivo

    t0 = time.perf_counter()

    # Reproyectar a disco si hace falta; si ya está en 4326, devuelve path sin tocar
    dst_repro = path + ".repro.tif"
    try:
        path_4326 = reproyectar_a_4326_archivo(path, dst_repro)
        logger.info("[pipeline] reproyeccion: %.2fs", time.perf_counter() - t0)

        t1 = time.perf_counter()
        with rasterio.open(path_4326) as src:
            validar_bandas_disponibles(sensor, indice, src.count)
            shape_original = (src.height, src.width)
            factor = _factor_downsample(shape_original)
            bandas, nodata = _leer_bandas_requeridas(src, sensor, indice, factor)
            meta = {
                "crs": src.crs,
                "transform": src.transform,
                "nodata": nodata,
                "shape": shape_original,
            }
            if factor > 1:
                logger.info(
                    "[pipeline] lectura decimada x%d: %dx%d → %dx%d (raster grande)",
                    factor, shape_original[1], shape_original[0],
                    shape_original[1] // factor, shape_original[0] // factor,
                )
                meta = _downsample_meta(meta, factor)
        logger.info("[pipeline] lectura de bandas (%dx%d): %.2fs", meta["shape"][1], meta["shape"][0], time.perf_counter() - t1)

        return _procesar_indice_desde_bandas(
            indice, sensor, bandas, nodata, meta, geojson_destino, metodo_umbral, area_minima_m2, t0=t0,
        )

    finally:
        # Limpiar archivo reproyectado temporal si se creó uno nuevo
        if os.path.exists(dst_repro):
            os.unlink(dst_repro)


def ejecutar_pipeline_multi_indice_archivo(
    path: str,
    sensor: str,
    indices: list[str],
    geojson_destino_por_indice: dict[str, str],
    metodo_umbral: str = "fijo",
    area_minima_m2: int = 10_000,
    on_indice_completado=None,
    on_indice_error=None,
) -> dict[str, dict]:
    """
    Variante batch de ejecutar_pipeline_archivo: reproyecta y abre el
    archivo UNA sola vez, y lee cada banda distinta (NIR, RED, RE, GREEN,
    BLUE) UNA sola vez, aunque varios índices de la lista la compartan
    (NIR la usan NDVI/NDRE/SAVI/GNDVI, RED la usan NDVI/SAVI/ExG). El factor
    de decimación (ver _leer_banda) se calcula una sola vez para el archivo
    y se aplica por igual a todas las bandas del batch.

    Pensada para cuando el usuario pide varios índices sobre el mismo vuelo
    de una — evita repetir la descarga+lectura completa del GeoTIFF una vez
    por índice (ver workers/gis/tasks.py::analizar_indices_batch).

    on_indice_completado(indice, estadisticas): se invoca después de cada
    índice individual, para persistir su resultado de forma incremental.
    on_indice_error(indice, exc): se invoca si UN índice falla (p.ej. banda
    faltante para ese índice puntual) — el resto de los índices de la lista
    se siguen procesando igual.
    """
    import os

    from workers.gis.reproyeccion import reproyectar_a_4326_archivo

    t0 = time.perf_counter()
    dst_repro = path + ".repro.tif"
    resultados: dict[str, dict] = {}

    try:
        path_4326 = reproyectar_a_4326_archivo(path, dst_repro)
        logger.info("[pipeline] reproyeccion (batch %d indices): %.2fs", len(indices), time.perf_counter() - t0)

        bandas_cache: dict[str, np.ndarray] = {}
        with rasterio.open(path_4326) as src:
            shape_original = (src.height, src.width)
            factor = _factor_downsample(shape_original)
            meta = {
                "crs": src.crs,
                "transform": src.transform,
                "nodata": src.nodata,
                "shape": shape_original,
            }
            if factor > 1:
                logger.info(
                    "[pipeline] lectura decimada x%d: %dx%d → %dx%d (raster grande, batch %d indices)",
                    factor, shape_original[1], shape_original[0],
                    shape_original[1] // factor, shape_original[0] // factor, len(indices),
                )
                meta = _downsample_meta(meta, factor)

            for indice in indices:
                try:
                    validar_bandas_disponibles(sensor, indice, src.count)
                    nombres = BANDAS_POR_INDICE[indice]
                    for nombre in nombres:
                        if nombre in bandas_cache:
                            continue
                        num = numero_banda(sensor, nombre)
                        t_banda = time.perf_counter()
                        bandas_cache[nombre] = _leer_banda(src, num, factor)
                        logger.info("[pipeline] lectura banda %s: %.2fs", nombre, time.perf_counter() - t_banda)

                    bandas_indice = {n: bandas_cache[n] for n in nombres}
                    estadisticas = _procesar_indice_desde_bandas(
                        indice, sensor, bandas_indice, meta["nodata"], meta,
                        geojson_destino_por_indice[indice], metodo_umbral, area_minima_m2,
                    )
                    resultados[indice] = estadisticas
                    if on_indice_completado is not None:
                        on_indice_completado(indice, estadisticas)
                except Exception as exc:
                    logger.exception("[pipeline] fallo calculando %s en batch", indice)
                    if on_indice_error is not None:
                        on_indice_error(indice, exc)

        logger.info("[pipeline] TOTAL batch (%d/%d indices ok): %.2fs", len(resultados), len(indices), time.perf_counter() - t0)
        return resultados

    finally:
        if os.path.exists(dst_repro):
            os.unlink(dst_repro)
