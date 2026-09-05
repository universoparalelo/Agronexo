from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import rasterize, shapes
from shapely.geometry import shape

from workers.gis.clasificacion import calcular_umbrales, clasificar_con_umbrales

# Área mínima de un polígono para no considerarlo ruido.
# 10 000 m² = 1 ha — umbral razonable para Sentinel-2 a 10 m/px (donde 1 ha = 100 píxeles).
# Para drones de alta resolución (< 0,5 m/px) bajar a 500–2 000 m² si se necesita más detalle.
AREA_MINIMA_M2 = 10_000


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


def suavizar_indice(valores: np.ndarray, sigma: float = 1.0) -> np.ndarray:
    """
    Suaviza el índice con un filtro de caja antes de clasificar para reducir
    fragmentación "sal y pimienta" en gradientes continuos.

    Usa uniform_filter (caja 1D separable) en lugar de gaussian_filter — produce
    el mismo efecto práctico de reducción de ruido antes de umbralar pero es
    3-5x más rápido. Preserva NaN correctamente normalizando por el peso del
    kernel sobre la máscara de píxeles válidos.
    """
    from scipy.ndimage import uniform_filter

    mascara_valida = ~np.isnan(valores)
    if not mascara_valida.any():
        return valores

    # size impar equivalente al sigma dado (mínimo 3 para cualquier sigma > 0)
    size = max(3, int(sigma * 3) | 1)
    valores_rellenos = np.where(mascara_valida, valores, 0.0).astype(np.float32)
    peso = uniform_filter(mascara_valida.astype(np.float32), size=size)
    suma = uniform_filter(valores_rellenos, size=size)

    with np.errstate(invalid="ignore", divide="ignore"):
        suavizado = np.where(peso > 1e-6, suma / peso, np.nan)

    return suavizado.astype(np.float32)


def clasificar_ndvi(ndvi: np.ndarray, metodo: str = "fijo", indice: str = "ndvi") -> np.ndarray:
    """
    Asigna un código entero a cada píxel según su clase.
    0 = nodata/nan, 1 = critica, 2 = deficiente, 3 = normal, 4 = vigorosa

    metodo: "fijo" (umbrales agronómicos estándar por índice) | "otsu" | "percentil"
    indice: qué índice se está clasificando — determina los umbrales "fijo"
    (ver workers/gis/clasificacion.py::_UMBRALES_POR_INDICE). El nombre de la
    función quedó de cuando solo existía NDVI; ahora clasifica cualquier
    índice razón (NDVI/NDRE/SAVI/GNDVI).
    """
    umbrales = calcular_umbrales(ndvi, metodo, indice)
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
    Las estadísticas de índice se calculan por polígono individual con
    un único rasterize+bincount en lugar del costoso geometry_mask por polígono.
    """
    transform = meta["transform"]
    crs = meta["crs"]
    out_shape = ndvi.shape

    # 0.5px daba polígonos con cientos de miles de vértices en rasters reales
    # ruidosos (una sola zona de 28 ha con 383k vértices, medido contra
    # ORTOMOSAICO.tif — ver docs/release-v1.0.0.md 2026-08-28) porque a esa
    # tolerancia casi no se limpia el patrón "escalera" de los bordes de
    # píxeles. 2px sigue siendo indistinguible a la escala de un mapa web y
    # reduce el costo de las intersecciones geométricas del motor de
    # diagnóstico (app/diagnostico/service.py) — no elimina el problema en
    # rasters extremadamente ruidosos (ahí la simplificación por sí sola no
    # alcanza, ver mismo doc), pero ayuda al caso general sin distorsionar la forma.
    tolerancia = abs(transform.a) * 2

    filas = []
    # Una sola pasada sobre el raster en lugar de 4 (una por clase):
    # shapes() emite un polígono por cada región contigua de igual valor.
    for geom_dict, val in shapes(clase.astype(np.int32), connectivity=8, transform=transform):
        codigo = int(val)
        if codigo == 0:
            continue
        geom = shape(geom_dict)
        if not geom.is_valid:
            geom = geom.buffer(0)
        geom = geom.simplify(tolerance=tolerancia, preserve_topology=True)
        filas.append({"geometry": geom, "clase": _codigo_a_nombre(codigo), "codigo": codigo})

    if not filas:
        return gpd.GeoDataFrame(
            columns=["geometry", "clase", "codigo", "ndvi_promedio", "area_ha", "zscore", "es_atipica"],
            crs=crs,
        )

    gdf = gpd.GeoDataFrame(filas, crs=crs)
    gdf = gdf.explode(index_parts=False).reset_index(drop=True)

    # 1. Filtrar por área ANTES de calcular estadísticas — descarta ruido barato
    gdf_utm = gdf.to_crs(epsg=32721)
    areas_m2 = gdf_utm.geometry.area
    gdf["area_ha"] = (areas_m2 / 10_000).round(4)
    gdf = gdf[areas_m2 >= area_minima_m2].reset_index(drop=True)

    if len(gdf) == 0:
        return gpd.GeoDataFrame(
            columns=["geometry", "clase", "codigo", "ndvi_promedio", "area_ha", "zscore", "es_atipica"],
            crs=crs,
        )

    # 2. Estadísticas por polígono en un solo barrido vectorizado.
    #    rasterize asigna a cada píxel el ID del polígono que lo contiene (0 = sin polígono).
    #    bincount acumula sumas y conteos en un único pass — O(H×W) sin importar n_polígonos,
    #    en lugar del anterior O(n_polígonos × H×W) con geometry_mask por polígono.
    n = len(gdf)
    id_raster = rasterize(
        [(geom.__geo_interface__, i + 1) for i, geom in enumerate(gdf.geometry)],
        out_shape=out_shape,
        transform=transform,
        fill=0,
        dtype=np.int32,
    )
    ndvi_flat = ndvi.ravel().astype(np.float64)
    id_flat = id_raster.ravel()
    valid = (id_flat > 0) & ~np.isnan(ndvi_flat)
    sums = np.bincount(id_flat[valid], weights=ndvi_flat[valid], minlength=n + 1)
    counts = np.bincount(id_flat[valid], minlength=n + 1)
    gdf["ndvi_promedio"] = np.round(
        np.where(counts[1:] > 0, sums[1:] / counts[1:], 0.0), 4
    )

    # 3. z-score
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
