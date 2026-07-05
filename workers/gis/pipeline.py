"""
Pipeline GIS generalizado: GeoTIFF → índice → clasificación → GeoJSON.

Soporta NDVI, NDRE, SAVI y ExG con mapeo de bandas configurable por sensor.
La lógica de vectorización y exportación reutiliza workers/gis/zonas.py.
"""

import io

import numpy as np
import rasterio

from workers.gis.band_mapping import BANDAS_POR_INDICE, numero_banda, validar_bandas_disponibles
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
    indice          : "ndvi" | "ndre" | "savi" | "exg"
    geojson_destino : ruta local donde se escribe el GeoJSON de salida
    """
    # Reproyectar a EPSG:4326 si el CRS original es distinto
    data = reproyectar_a_4326(data)

    with rasterio.open(io.BytesIO(data)) as src:
        validar_bandas_disponibles(sensor, indice, src.count)

        bandas, nodata = _leer_bandas_requeridas(src, sensor, indice)
        meta = {
            "crs": src.crs,
            "transform": src.transform,
            "nodata": nodata,
            "shape": (src.height, src.width),
        }

    valores = calcular_indice(indice, bandas, nodata)
    valores_suavizados = suavizar_indice(valores)
    metodo_efectivo = _metodo_umbral_efectivo(indice, metodo_umbral)
    clase = clasificar_ndvi(valores_suavizados, metodo=metodo_efectivo)
    # Las estadísticas (ndvi_promedio, min/max/promedio del lote) usan el valor
    # SIN suavizar — el suavizado es solo una ayuda para la clasificación
    # espacial, no debe alterar el índice real reportado al usuario.
    gdf = vectorizar_zonas(clase, valores, meta, area_minima_m2=area_minima_m2)
    ruta_salida = exportar_geojson(gdf, geojson_destino)

    total_px = int(np.sum(~np.isnan(valores)))
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
            "porcentaje_px": round(px_clase / total_px * 100, 2) if total_px > 0 else 0.0,
        }

    return estadisticas
