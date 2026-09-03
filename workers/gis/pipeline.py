"""
Pipeline GIS generalizado: GeoTIFF → índice → clasificación → GeoJSON.

Soporta NDVI, NDRE, SAVI, ExG, GNDVI, MSAVI y NDWI con mapeo de bandas configurable por sensor.
La lógica de vectorización y exportación reutiliza workers/gis/zonas.py.
"""

import io
import logging
import time

import numpy as np
import rasterio

logger = logging.getLogger(__name__)

from workers.gis.band_mapping import BANDAS_POR_INDICE, numero_banda, validar_bandas_disponibles

# Umbral en píxeles totales a partir del cual se activa el downsampling.
# ~3000×3000 px — por encima de esto, clasificación y vectorización se vuelven lentas.
_UMBRAL_DOWNSAMPLE_PX = 9_000_000


def _factor_downsample(shape: tuple[int, int]) -> int:
    """Factor de reducción entero (1 = sin reducción)."""
    total = shape[0] * shape[1]
    if total <= _UMBRAL_DOWNSAMPLE_PX:
        return 1
    return int(np.ceil(np.sqrt(total / _UMBRAL_DOWNSAMPLE_PX)))


def _downsample_array(arr: np.ndarray, factor: int) -> np.ndarray:
    """Average pooling NaN-safe. Recorta al múltiplo exacto de factor."""
    h, w = arr.shape
    h2, w2 = h // factor, w // factor
    reshaped = arr[:h2 * factor, :w2 * factor].reshape(h2, factor, w2, factor)
    with np.errstate(invalid="ignore"):
        return np.nanmean(reshaped, axis=(1, 3)).astype(np.float32)


def _downsample_meta(meta: dict, factor: int) -> dict:
    """Devuelve meta actualizado con transform y shape del array reducido."""
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
# NDVI, NDRE, SAVI, GNDVI y NDWI son índices "razón" (diferencia sobre suma)
# — su rango es siempre ~[-1,1] sin importar la escala de las bandas de
# entrada (reflectancia 0-1 o DN crudo), así que el umbral fijo aplica
# directamente. MSAVI2 no es una razón simple pero su fórmula está acotada
# al mismo rango ~[-1,1], así que también admite el umbral fijo sin ajuste.
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


def _leer_bandas_requeridas(
    src: rasterio.DatasetReader,
    sensor: str,
    indice: str,
) -> tuple[dict[str, np.ndarray], float | None]:
    """Lee solo las bandas necesarias para el índice y sensor dados."""
    nombres = BANDAS_POR_INDICE[indice]
    bandas: dict[str, np.ndarray] = {}
    for nombre in nombres:
        num = numero_banda(sensor, nombre)
        bandas[nombre] = src.read(num).astype(np.float32)
    return bandas, src.nodata


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
    indice          : "ndvi" | "ndre" | "savi" | "exg" | "gndvi" | "msavi" | "ndwi"
    geojson_destino : ruta local donde se escribe el GeoJSON de salida
    """
    t0 = time.perf_counter()

    # Reproyectar a EPSG:4326 si el CRS original es distinto
    data = reproyectar_a_4326(data)
    logger.info("[pipeline] reproyeccion: %.2fs", time.perf_counter() - t0)

    t1 = time.perf_counter()
    with rasterio.open(io.BytesIO(data)) as src:
        validar_bandas_disponibles(sensor, indice, src.count)

        bandas, nodata = _leer_bandas_requeridas(src, sensor, indice)
        meta = {
            "crs": src.crs,
            "transform": src.transform,
            "nodata": nodata,
            "shape": (src.height, src.width),
        }
    logger.info("[pipeline] lectura de bandas (%dx%d): %.2fs", meta["shape"][1], meta["shape"][0], time.perf_counter() - t1)

    t2 = time.perf_counter()
    valores = calcular_indice(indice, bandas, nodata)
    logger.info("[pipeline] calculo %s: %.2fs", indice.upper(), time.perf_counter() - t2)

    # Downsampling para rasters grandes: reduce la resolución solo para
    # clasificación y vectorización. Las estadísticas globales (min/max/media)
    # se calculan siempre sobre el array a resolución completa.
    factor = _factor_downsample(meta["shape"])
    if factor > 1:
        logger.info(
            "[pipeline] downsample x%d: %dx%d → %dx%d",
            factor,
            meta["shape"][1], meta["shape"][0],
            meta["shape"][1] // factor, meta["shape"][0] // factor,
        )
        valores_vector = _downsample_array(valores, factor)
        meta_vector = _downsample_meta(meta, factor)
    else:
        valores_vector = valores
        meta_vector = meta

    t3 = time.perf_counter()
    valores_suavizados = suavizar_indice(valores_vector)
    logger.info("[pipeline] suavizado: %.2fs", time.perf_counter() - t3)

    metodo_efectivo = _metodo_umbral_efectivo(indice, metodo_umbral)

    t4 = time.perf_counter()
    clase = clasificar_ndvi(valores_suavizados, metodo=metodo_efectivo)
    logger.info("[pipeline] clasificacion (%s): %.2fs", metodo_efectivo, time.perf_counter() - t4)

    t5 = time.perf_counter()
    # Las estadísticas de índice por polígono usan valores_vector (consistente
    # con la resolución de clase). Las estadísticas globales del lote usan
    # el array original a resolución completa.
    gdf = vectorizar_zonas(clase, valores_vector, meta_vector, area_minima_m2=area_minima_m2)
    logger.info("[pipeline] vectorizacion (%d poligonos): %.2fs", len(gdf), time.perf_counter() - t5)

    t6 = time.perf_counter()
    ruta_salida = exportar_geojson(gdf, geojson_destino)
    logger.info("[pipeline] exportacion geojson: %.2fs", time.perf_counter() - t6)

    logger.info("[pipeline] TOTAL: %.2fs", time.perf_counter() - t0)

    # porcentaje_px usa clase (potencialmente downsampled) — total y por clase
    # son consistentes entre sí. Min/max/promedio global usan resolución completa.
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
    sin cargar el raster completo en memoria. El único array grande en RAM
    son las bandas necesarias (p.ej. NIR + RED para NDVI), no el archivo entero.

    path             : ruta al GeoTIFF en disco (archivo local del worker)
    """
    import os
    import tempfile

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
            bandas, nodata = _leer_bandas_requeridas(src, sensor, indice)
            meta = {
                "crs": src.crs,
                "transform": src.transform,
                "nodata": nodata,
                "shape": (src.height, src.width),
            }
        logger.info("[pipeline] lectura de bandas (%dx%d): %.2fs", meta["shape"][1], meta["shape"][0], time.perf_counter() - t1)

        t2 = time.perf_counter()
        valores = calcular_indice(indice, bandas, nodata)
        logger.info("[pipeline] calculo %s: %.2fs", indice.upper(), time.perf_counter() - t2)

        factor = _factor_downsample(meta["shape"])
        if factor > 1:
            logger.info(
                "[pipeline] downsample x%d: %dx%d → %dx%d",
                factor,
                meta["shape"][1], meta["shape"][0],
                meta["shape"][1] // factor, meta["shape"][0] // factor,
            )
            valores_vector = _downsample_array(valores, factor)
            meta_vector = _downsample_meta(meta, factor)
        else:
            valores_vector = valores
            meta_vector = meta

        t3 = time.perf_counter()
        valores_suavizados = suavizar_indice(valores_vector)
        logger.info("[pipeline] suavizado: %.2fs", time.perf_counter() - t3)

        metodo_efectivo = _metodo_umbral_efectivo(indice, metodo_umbral)

        t4 = time.perf_counter()
        clase = clasificar_ndvi(valores_suavizados, metodo=metodo_efectivo)
        logger.info("[pipeline] clasificacion (%s): %.2fs", metodo_efectivo, time.perf_counter() - t4)

        t5 = time.perf_counter()
        gdf = vectorizar_zonas(clase, valores_vector, meta_vector, area_minima_m2=area_minima_m2)
        logger.info("[pipeline] vectorizacion (%d poligonos): %.2fs", len(gdf), time.perf_counter() - t5)

        t6 = time.perf_counter()
        ruta_salida = exportar_geojson(gdf, geojson_destino)
        logger.info("[pipeline] exportacion geojson: %.2fs", time.perf_counter() - t6)

        logger.info("[pipeline] TOTAL: %.2fs", time.perf_counter() - t0)

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

    finally:
        # Limpiar archivo reproyectado temporal si se creó uno nuevo
        if os.path.exists(dst_repro):
            os.unlink(dst_repro)
