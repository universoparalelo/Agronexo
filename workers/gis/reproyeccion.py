"""
Reproyección de rasters en memoria.

Si el GeoTIFF llega en un CRS proyectado (ej. UTM) o en uno distinto de
EPSG:4326, lo reproyectamos antes de procesar para que las geometrías de
salida (GeoJSON) estén siempre en coordenadas geográficas estándar.
"""

import io
import json

import rasterio
from rasterio.crs import CRS
from rasterio.warp import Resampling, calculate_default_transform, reproject


CRS_SALIDA = CRS.from_epsg(4326)


def _resolver_crs(crs: CRS) -> CRS:
    """
    Algunos exportadores de drones (Pix4D, DJI Terra) embuten un CRS con
    código EPSG correcto pero sin metadatos de datum completos, lo que hace
    que PROJ lo clasifique como 'EngineeringCRS' y rechace transformaciones
    (error "Cannot find coordinate operations from '...' to 'EPSG:4326'").
    Si detectamos ese patrón, reconstruimos el CRS desde el código EPSG
    embebido en el PROJJSON, que sí tiene la cadena de transformación completa.

    Usa _projjson() (PROJJSON) — NO to_dict(), que devuelve parámetros PROJ4
    y no tiene el campo "type". rasterio.crs.CRS no expone to_json_dict()
    (eso es un método de pyproj.CRS, una clase distinta) — _projjson() es
    el único acceso al PROJJSON disponible en esta clase.
    """
    try:
        d = json.loads(crs._projjson())
        if d.get("type") == "EngineeringCRS":
            crs_id = d.get("id", {})
            if crs_id.get("authority") == "EPSG":
                return CRS.from_epsg(crs_id["code"])
    except Exception:
        pass
    return crs


def necesita_reproyeccion(src: rasterio.DatasetReader) -> bool:
    if src.crs is None:
        return False
    return _resolver_crs(src.crs) != CRS_SALIDA


def reproyectar_a_4326(data: bytes) -> bytes:
    """
    Recibe bytes de un GeoTIFF, lo reproyecta a EPSG:4326 si es necesario
    y devuelve los bytes del raster reproyectado.
    Si ya está en 4326, devuelve los bytes originales sin modificación.
    """
    with rasterio.open(io.BytesIO(data)) as src:
        if not necesita_reproyeccion(src):
            return data

        original_crs = src.crs
        src_crs = _resolver_crs(original_crs)
        transform, width, height = calculate_default_transform(
            src_crs, CRS_SALIDA, src.width, src.height, *src.bounds
        )

        perfil = src.profile.copy()
        perfil.update(
            crs=CRS_SALIDA,
            transform=transform,
            width=width,
            height=height,
        )

        # reproject() con source=rasterio.band() ignora src_crs/src_transform
        # y relee esos valores directamente de los metadatos del dataset —
        # si _resolver_crs tuvo que corregir un CRS mal clasificado
        # (EngineeringCRS), hace falta una copia con el CRS ya corregido
        # embebido, porque MemoryFile no admite reasignar .crs en modo r+
        # (a diferencia de un archivo en disco).
        fix_memfile = None
        src_fix = src
        if src_crs != original_crs:
            perfil_fix = src.profile.copy()
            perfil_fix.update(crs=src_crs)
            fix_memfile = rasterio.MemoryFile()
            with fix_memfile.open(**perfil_fix) as dst_fix:
                dst_fix.write(src.read())
            src_fix = fix_memfile.open()

        try:
            # MemoryFile usa VSIMEM (filesystem virtual de GDAL) — más eficiente
            # que BytesIO para archivos grandes porque evita copias del buffer Python.
            with rasterio.MemoryFile() as memfile:
                with memfile.open(**perfil) as dst:
                    for i in range(1, src_fix.count + 1):
                        reproject(
                            source=rasterio.band(src_fix, i),
                            destination=rasterio.band(dst, i),
                            resampling=Resampling.bilinear,
                        )
                return memfile.read()
        finally:
            if fix_memfile is not None:
                src_fix.close()
                fix_memfile.close()


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

        original_crs = src.crs
        src_crs = _resolver_crs(original_crs)
        transform, width, height = calculate_default_transform(
            src_crs, CRS_SALIDA, src.width, src.height, *src.bounds
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
            # La reproyección puede ensanchar el bounding box (raster rotado
            # que pasa a alinearse a ejes) y superar el límite de 4 GiB de
            # TIFF clásico — sin esto, GDAL falla a mitad de escritura con
            # "error writing dirty block" al cruzar ese límite.
            bigtiff="IF_SAFER",
        )

    # reproject() con source=rasterio.band() ignora src_crs/src_transform y
    # relee esos valores directamente de los metadatos del dataset en disco —
    # si _resolver_crs tuvo que corregir un CRS mal clasificado (EngineeringCRS),
    # hace falta corregir el CRS embebido en el archivo antes de reabrirlo,
    # no alcanza con pasarlo como argumento a reproject().
    if src_crs != original_crs:
        with rasterio.open(src_path, "r+") as src_fix:
            src_fix.crs = src_crs

    with rasterio.open(src_path) as src, rasterio.open(dst_path, "w", **perfil) as dst:
        for i in range(1, src.count + 1):
            reproject(
                source=rasterio.band(src, i),
                destination=rasterio.band(dst, i),
                resampling=Resampling.bilinear,
            )

    return dst_path
