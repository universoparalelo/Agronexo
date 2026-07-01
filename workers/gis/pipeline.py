"""
Pipeline GIS generalizado: GeoTIFF → índice → clasificación → GeoJSON.

Soporta NDVI, NDRE, SAVI y ExG con mapeo de bandas configurable por sensor.
La lógica de vectorización y exportación reutiliza workers/gis/ndvi.py.
"""

import io

import numpy as np
import rasterio

from workers.gis.band_mapping import BANDAS_POR_INDICE, numero_banda, validar_bandas_disponibles
from workers.gis.indices import calcular_indice
from workers.gis.ndvi import clasificar_ndvi, exportar_geojson, vectorizar_zonas
from workers.gis.reproyeccion import reproyectar_a_4326

# Umbrales de clasificación reutilizados del módulo NDVI.
# ExG no tiene escala -1/1 como los índices ratio; se clasifica con los mismos
# umbrales como aproximación razonable para separar zonas de vigor diferencial.
# Para NDRE la escala también es [-1,1] y los umbrales aplican directamente.


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
    clase = clasificar_ndvi(valores, metodo=metodo_umbral)
    gdf = vectorizar_zonas(clase, valores, meta)
    ruta_salida = exportar_geojson(gdf, geojson_destino)

    total_px = int(np.sum(~np.isnan(valores)))
    estadisticas: dict = {
        "indice": indice,
        "sensor": sensor,
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
