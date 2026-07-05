"""Inspección liviana del header TIFF, sin GDAL/rasterio.

El contenedor API no tiene rasterio instalado a propósito (la validación GIS
profunda ocurre en el worker). Esto lee únicamente el tag SamplesPerPixel del
IFD para saber cuántas bandas tiene el archivo, de forma instantánea incluso
en archivos grandes — es un chequeo preliminar/best-effort, no reemplaza la
validación completa que hace el worker con rasterio.

Solo soporta TIFF clásico (no BigTIFF). Si el parseo falla por cualquier
motivo devuelve None en vez de levantar una excepción — es informativo, no
debe bloquear el flujo de carga.
"""

import struct

_TAG_SAMPLES_PER_PIXEL = 277
_TIPO_SHORT = 3
_TIPO_LONG = 4


def contar_bandas_geotiff(contenido: bytes) -> int | None:
    """Retorna la cantidad de bandas (SamplesPerPixel) o None si no se pudo determinar."""
    try:
        if len(contenido) < 8:
            return None

        byte_order = contenido[:2]
        if byte_order == b"II":
            fmt = "<"
        elif byte_order == b"MM":
            fmt = ">"
        else:
            return None

        magic = struct.unpack(fmt + "H", contenido[2:4])[0]
        if magic != 42:
            return None  # no es TIFF clásico (podría ser BigTIFF u otro formato)

        ifd_offset = struct.unpack(fmt + "I", contenido[4:8])[0]
        if ifd_offset + 2 > len(contenido):
            return None

        n_entries = struct.unpack(fmt + "H", contenido[ifd_offset:ifd_offset + 2])[0]
        entries_start = ifd_offset + 2

        for i in range(n_entries):
            entry_offset = entries_start + i * 12
            if entry_offset + 12 > len(contenido):
                break
            tag, tipo, count = struct.unpack(fmt + "HHI", contenido[entry_offset:entry_offset + 8])
            if tag != _TAG_SAMPLES_PER_PIXEL or count != 1:
                continue
            valor_bytes = contenido[entry_offset + 8:entry_offset + 12]
            if tipo == _TIPO_SHORT:
                return struct.unpack(fmt + "H", valor_bytes[:2])[0]
            if tipo == _TIPO_LONG:
                return struct.unpack(fmt + "I", valor_bytes)[0]

        return 1  # TIFF sin SamplesPerPixel explícito → 1 banda por spec
    except Exception:
        return None
