"""
Reproyección de rasters en memoria.

Si el GeoTIFF llega en un CRS proyectado (ej. UTM) o en uno distinto de
EPSG:4326, lo reproyectamos antes de procesar para que las geometrías de
salida (GeoJSON) estén siempre en coordenadas geográficas estándar.
"""

import io

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

        # MemoryFile usa VSIMEM (filesystem virtual de GDAL) — más eficiente
        # que BytesIO para archivos grandes porque evita copias del buffer Python.
        with rasterio.MemoryFile() as memfile:
            with memfile.open(**perfil) as dst:
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
            return memfile.read()


def reproyectar_a_4326_archivo(src_path: str, dst_path: str) -> str:
    """
    Versión con I/O de archivo para GeoTIFFs grandes (> 500 MB).

    Lee y escribe en disco en lugar de RAM — GDAL hace el reproject tileado
    internamente sin cargar el raster completo en memoria. Retorna src_path si
    el CRS ya es EPSG:4326 (sin escritura), o dst_path si hubo que reproyectar.
    """
    with rasterio.open(src_path) as src:
        if not necesita_reproyeccion(src):
            return src_path

        transform, width, height = calculate_default_transform(
            src.crs, CRS_SALIDA, src.width, src.height, *src.bounds
        )
        perfil = src.profile.copy()
        perfil.update(
            crs=CRS_SALIDA,
            transform=transform,
            width=width,
            height=height,
            # Asegurar formato GTiff con compresión LZW para que el archivo
            # resultante en disco no sea mucho mayor que el original
            driver="GTiff",
            compress="lzw",
            tiled=True,
            blockxsize=512,
            blockysize=512,
        )

        with rasterio.open(dst_path, "w", **perfil) as dst:
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

    return dst_path
