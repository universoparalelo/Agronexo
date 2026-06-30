"""
Reproyección de rasters en memoria.

Si el GeoTIFF llega en un CRS proyectado (ej. UTM) o en uno distinto de
EPSG:4326, lo reproyectamos antes de procesar para que las geometrías de
salida (GeoJSON) estén siempre en coordenadas geográficas estándar.
"""

import io

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.warp import Resampling, calculate_default_transform, reproject


CRS_SALIDA = CRS.from_epsg(4326)


def necesita_reproyeccion(src: rasterio.DatasetReader) -> bool:
    return src.crs is not None and src.crs != CRS_SALIDA


def reproyectar_a_4326(data: bytes) -> bytes:
    """
    Recibe bytes de un GeoTIFF, lo reproyecta a EPSG:4326 si es necesario
    y devuelve los bytes del raster reproyectado.
    Si ya está en 4326, devuelve los bytes originales sin modificación.
    """
    with rasterio.open(io.BytesIO(data)) as src:
        if not necesita_reproyeccion(src):
            return data

        transform, width, height = calculate_default_transform(
            src.crs, CRS_SALIDA, src.width, src.height, *src.bounds
        )

        perfil = src.profile.copy()
        perfil.update(
            crs=CRS_SALIDA,
            transform=transform,
            width=width,
            height=height,
        )

        buf = io.BytesIO()
        with rasterio.open(buf, "w", **perfil) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=CRS_SALIDA,
                    resampling=Resampling.bilinear,
                )

        return buf.getvalue()
