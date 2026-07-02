from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import geometry_mask, shapes
from shapely.geometry import shape

from workers.gis.clasificacion import calcular_umbrales, clasificar_con_umbrales

# Área mínima de un polígono para no considerarlo ruido (0.1 ha = 1000 m²)
AREA_MINIMA_M2 = 1000


def leer_bandas(path: str | Path, banda_nir: int = 1, banda_red: int = 2) -> tuple[np.ndarray, np.ndarray, dict]:
    """Lee bandas NIR y RED de un GeoTIFF y devuelve arrays float32 + metadatos."""
    with rasterio.open(path) as src:
        nir = src.read(banda_nir).astype(np.float32)
        red = src.read(banda_red).astype(np.float32)
        meta = {
            "crs": src.crs,
            "transform": src.transform,
            "nodata": src.nodata,
            "shape": (src.height, src.width),
        }
    return nir, red, meta


def calcular_ndvi(nir: np.ndarray, red: np.ndarray, nodata: float | None = None) -> np.ndarray:
    """
    Calcula NDVI = (NIR - RED) / (NIR + RED).
    Maneja división por cero y píxeles nodata explícitamente.
    """
    denominador = nir + red

    # Evitar división por cero — ocurre en píxeles de agua pura o sin dato
    with np.errstate(invalid="ignore", divide="ignore"):
        ndvi = np.where(denominador == 0, np.nan, (nir - red) / denominador)

    if nodata is not None:
        ndvi[(nir == nodata) | (red == nodata)] = np.nan

    return ndvi.astype(np.float32)


def clasificar_ndvi(ndvi: np.ndarray, metodo: str = "fijo") -> np.ndarray:
    """
    Asigna un código entero a cada píxel según su clase.
    0 = nodata/nan, 1 = critica, 2 = deficiente, 3 = normal, 4 = vigorosa

    metodo: "fijo" (umbrales agronómicos estándar) | "otsu" | "percentil"
    """
    umbrales = calcular_umbrales(ndvi, metodo)
    return clasificar_con_umbrales(ndvi, umbrales)


def _codigo_a_nombre(codigo: int) -> str:
    return {1: "critica", 2: "deficiente", 3: "normal", 4: "vigorosa"}.get(codigo, "sin_dato")


def vectorizar_zonas(
    clase: np.ndarray,
    ndvi: np.ndarray,
    meta: dict,
    area_minima_m2: int = AREA_MINIMA_M2,
) -> gpd.GeoDataFrame:
    """
    Convierte la máscara de clases en polígonos GeoDataFrame.
    Filtra ruido por área mínima y simplifica con Douglas-Peucker.
    Las estadísticas de índice se calculan por polígono individual, no por clase global.
    """
    transform = meta["transform"]
    crs = meta["crs"]
    out_shape = ndvi.shape

    # Tolerancia adaptativa: media pixel en unidades del CRS (grados si EPSG:4326)
    tolerancia = abs(transform.a) * 0.5

    filas = []
    for codigo in range(1, 5):
        mascara = (clase == codigo).astype(np.uint8)
        if not mascara.any():
            continue

        for geom_dict, _ in shapes(mascara, mask=mascara, connectivity=8, transform=transform):
            geom = shape(geom_dict)

            if not geom.is_valid:
                geom = geom.buffer(0)

            geom = geom.simplify(tolerance=tolerancia, preserve_topology=True)

            # Estadísticas reales del polígono individual (no de toda la clase)
            try:
                poly_mask = geometry_mask(
                    [geom.__geo_interface__],
                    out_shape=out_shape,
                    transform=transform,
                    invert=True,
                )
                px = ndvi[poly_mask]
                ndvi_promedio = float(np.nanmean(px)) if px.size > 0 else 0.0
            except Exception:
                ndvi_promedio = 0.0

            filas.append({
                "geometry": geom,
                "clase": _codigo_a_nombre(codigo),
                "codigo": codigo,
                "ndvi_promedio": round(ndvi_promedio, 4),
            })

    if not filas:
        return gpd.GeoDataFrame(
            columns=["geometry", "clase", "codigo", "ndvi_promedio", "area_ha", "zscore", "es_atipica"],
            crs=crs,
        )

    gdf = gpd.GeoDataFrame(filas, crs=crs)

    # Calcular área en hectáreas (reproyectar a UTM para que sea en metros)
    gdf_utm = gdf.to_crs(epsg=32721)
    gdf["area_ha"] = (gdf_utm.geometry.area / 10_000).round(4)

    # Filtrar polígonos menores al área mínima
    gdf_utm_area = gdf_utm.geometry.area
    gdf = gdf[gdf_utm_area >= area_minima_m2].reset_index(drop=True)

    # Zonas atípicas por z-score sobre ndvi_promedio de todos los polígonos del lote
    promedios = gdf["ndvi_promedio"]
    if len(gdf) >= 3:
        media = promedios.mean()
        std = promedios.std()
        if std > 0:
            gdf["zscore"] = ((promedios - media) / std).round(4)
        else:
            gdf["zscore"] = 0.0
        gdf["es_atipica"] = gdf["zscore"].abs() > 1.5
    else:
        gdf["zscore"] = 0.0
        gdf["es_atipica"] = False

    return gdf


def exportar_geojson(gdf: gpd.GeoDataFrame, destino: str | Path) -> str:
    """Exporta el GeoDataFrame a GeoJSON en EPSG:4326 y devuelve el path."""
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_crs(epsg=4326).to_file(str(destino), driver="GeoJSON")
    return str(destino)


def pipeline_ndvi(
    geotiff_path: str | Path,
    geojson_destino: str | Path,
    banda_nir: int = 1,
    banda_red: int = 2,
) -> dict:
    """
    Pipeline completo: GeoTIFF → NDVI → clasificación → GeoJSON.
    Devuelve estadísticas del análisis.
    """
    nir, red, meta = leer_bandas(geotiff_path, banda_nir, banda_red)
    ndvi = calcular_ndvi(nir, red, nodata=meta["nodata"])
    clase = clasificar_ndvi(ndvi)
    gdf = vectorizar_zonas(clase, ndvi, meta)
    ruta_salida = exportar_geojson(gdf, geojson_destino)

    total_px = int(np.sum(~np.isnan(ndvi)))
    estadisticas = {
        "geojson": ruta_salida,
        "total_poligonos": len(gdf),
        "ndvi_promedio_lote": round(float(np.nanmean(ndvi)), 4),
        "ndvi_min": round(float(np.nanmin(ndvi)), 4),
        "ndvi_max": round(float(np.nanmax(ndvi)), 4),
        "clases": {},
    }

    for nombre in ["critica", "deficiente", "normal", "vigorosa"]:
        zonas = gdf[gdf["clase"] == nombre]
        px_clase = int(np.sum(clase == list(_codigo_a_nombre(c) for c in range(1, 5)).index(nombre) + 1))
        estadisticas["clases"][nombre] = {
            "poligonos": len(zonas),
            "area_ha_total": round(float(zonas["area_ha"].sum()), 4),
            "porcentaje_px": round(px_clase / total_px * 100, 2) if total_px > 0 else 0,
        }

    return estadisticas
