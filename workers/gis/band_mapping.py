"""
Mapeo configurable de bandas por sensor.

Sentinel-2 y DJI Mavic 3 Multispectral tienen el mismo conjunto de bandas
pero en distinto orden dentro del GeoTIFF. Este módulo centraliza esa
configuración para que el pipeline no tenga números de banda hardcodeados.
"""

from typing import NamedTuple


class MapaBandas(NamedTuple):
    BLUE: int | None = None
    GREEN: int | None = None
    RED: int | None = None
    RE: int | None = None   # Red Edge
    NIR: int | None = None


# Números de banda (1-indexed, tal como los devuelve rasterio)
MAPEO_SENSORES: dict[str, MapaBandas] = {
    "sentinel2": MapaBandas(
        BLUE=2,
        GREEN=3,
        RED=4,
        RE=5,    # B5 — Red Edge 705 nm
        NIR=8,   # B8 — NIR 842 nm
    ),
    "dji_mavic3": MapaBandas(
        # El DJI Mavic 3 Multispectral real captura 4 bandas — no tiene Blue
        # (confirmado con orthomosaicos reales: _MS_G, _MS_R, _MS_RE, _MS_NIR).
        GREEN=1,
        RED=2,
        RE=3,    # Red Edge 730 nm
        NIR=4,   # NIR 860 nm
    ),
}

# Bandas requeridas por cada índice
BANDAS_POR_INDICE: dict[str, list[str]] = {
    "ndvi":  ["NIR", "RED"],
    "ndre":  ["NIR", "RE"],
    "savi":  ["NIR", "RED"],
    "exg":   ["GREEN", "RED", "BLUE"],
}


def obtener_mapeo(sensor: str) -> MapaBandas:
    mapeo = MAPEO_SENSORES.get(sensor)
    if mapeo is None:
        sensores_validos = ", ".join(MAPEO_SENSORES.keys())
        raise ValueError(f"Sensor '{sensor}' no reconocido. Válidos: {sensores_validos}")
    return mapeo


def numero_banda(sensor: str, nombre: str) -> int:
    """Retorna el número de banda (1-indexed) para un sensor e índice de banda dados."""
    mapeo = obtener_mapeo(sensor)
    num = getattr(mapeo, nombre, None)
    if num is None:
        raise ValueError(
            f"El sensor '{sensor}' no tiene banda '{nombre}'. "
            f"Revisá el mapeo en band_mapping.py."
        )
    return num


def validar_bandas_disponibles(sensor: str, indice: str, n_bandas_archivo: int) -> None:
    """Verifica que el archivo tenga suficientes bandas para calcular el índice dado."""
    nombres = BANDAS_POR_INDICE.get(indice)
    if nombres is None:
        raise ValueError(f"Índice '{indice}' no soportado. Válidos: {list(BANDAS_POR_INDICE)}")

    mapeo = obtener_mapeo(sensor)
    for nombre in nombres:
        num = getattr(mapeo, nombre, None)
        if num is None:
            raise ValueError(f"Sensor '{sensor}' no tiene banda {nombre} requerida por {indice.upper()}.")
        if num > n_bandas_archivo:
            raise ValueError(
                f"El archivo tiene {n_bandas_archivo} banda(s) pero {indice.upper()} "
                f"requiere la banda {nombre} en posición {num} para sensor '{sensor}'."
            )
