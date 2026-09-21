"""
Cálculo de índices de vegetación sobre arrays NumPy.

Todas las funciones reciben arrays float32, manejan nodata y división por
cero explícitamente, y devuelven float32. Nunca iteran píxel a píxel.
"""

import numpy as np


def _mascara_nodata(nodata: float | None, *arrays: np.ndarray) -> np.ndarray:
    """Retorna máscara booleana True donde algún array tiene valor nodata."""
    if nodata is None:
        return np.zeros(arrays[0].shape, dtype=bool)
    mask = np.zeros(arrays[0].shape, dtype=bool)
    for arr in arrays:
        mask |= arr == nodata
    return mask


def _division_segura(numerador: np.ndarray, denominador: np.ndarray) -> np.ndarray:
    """Divide evitando NaN/Inf por denominador cero."""
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(denominador == 0, np.nan, numerador / denominador)


def calcular_ndvi(nir: np.ndarray, red: np.ndarray, nodata: float | None = None) -> np.ndarray:
    """NDVI = (NIR - RED) / (NIR + RED)  — rango [-1, 1]."""
    resultado = _division_segura(nir - red, nir + red)
    resultado[_mascara_nodata(nodata, nir, red)] = np.nan
    return resultado.astype(np.float32)


def calcular_ndre(nir: np.ndarray, re: np.ndarray, nodata: float | None = None) -> np.ndarray:
    """NDRE = (NIR - RE) / (NIR + RE)  — sensible a clorofila y estrés nitrogenado."""
    resultado = _division_segura(nir - re, nir + re)
    resultado[_mascara_nodata(nodata, nir, re)] = np.nan
    return resultado.astype(np.float32)


def calcular_savi(nir: np.ndarray, red: np.ndarray, nodata: float | None = None, L: float = 0.5) -> np.ndarray:
    """SAVI = (NIR - RED) / (NIR + RED + L) * (1 + L)
    L=0.5 es el valor estándar para cobertura vegetal media.
    Recomendado para primeras semanas post-siembra (cobertura < 30%).
    """
    resultado = _division_segura(nir - red, nir + red + L) * (1 + L)
    resultado[_mascara_nodata(nodata, nir, red)] = np.nan
    return resultado.astype(np.float32)


def calcular_exg(green: np.ndarray, red: np.ndarray, blue: np.ndarray, nodata: float | None = None) -> np.ndarray:
    """ExG normalizado = 2g − r − b, con g, r, b = cada banda / (R + G + B).

    Como g + r + b = 1, es igual a (2G − R − B) / (R + G + B). Dividir por el
    brillo total deja solo la proporción de verde: el valor no cambia si la
    escena está más o menos iluminada, ni según las unidades de la cámara
    (reflectancia 0-1 o DN 8-bit dan lo mismo), así que se puede comparar
    entre fechas, lotes y sensores. Sin normalizar, sobre reflectancias daba
    valores ~0,02 (rango real −0,02 a 0,07) y la regla R10 (ExG > 0,20) no
    podía dispararse nunca. Rango típico de vegetación: 0,05 a 0,45.

    No requiere NIR. Útil con cámaras RGB cuando no hay banda NIR disponible.
    """
    resultado = _division_segura(2.0 * green - red - blue, red + green + blue)
    resultado[_mascara_nodata(nodata, green, red, blue)] = np.nan
    return resultado.astype(np.float32)


def calcular_gndvi(nir: np.ndarray, green: np.ndarray, nodata: float | None = None) -> np.ndarray:
    """GNDVI = (NIR - GREEN) / (NIR + GREEN)
    Más sensible que el NDVI a variaciones de clorofila en cultivos de alta
    biomasa donde el NDVI ya está saturado (> 0.85).
    """
    resultado = _division_segura(nir - green, nir + green)
    resultado[_mascara_nodata(nodata, nir, green)] = np.nan
    return resultado.astype(np.float32)


CALCULADORES = {
    "ndvi":  calcular_ndvi,
    "ndre":  calcular_ndre,
    "savi":  calcular_savi,
    "exg":   calcular_exg,
    "gndvi": calcular_gndvi,
}


def calcular_indice(indice: str, bandas: dict[str, np.ndarray], nodata: float | None = None) -> np.ndarray:
    """
    Punto de entrada unificado. Recibe el nombre del índice y un dict de arrays
    con claves en mayúsculas (NIR, RED, RE, GREEN, BLUE).
    """
    if indice == "ndvi":
        return calcular_ndvi(bandas["NIR"], bandas["RED"], nodata)
    if indice == "ndre":
        return calcular_ndre(bandas["NIR"], bandas["RE"], nodata)
    if indice == "savi":
        return calcular_savi(bandas["NIR"], bandas["RED"], nodata)
    if indice == "exg":
        return calcular_exg(bandas["GREEN"], bandas["RED"], bandas["BLUE"], nodata)
    if indice == "gndvi":
        return calcular_gndvi(bandas["NIR"], bandas["GREEN"], nodata)
    raise ValueError(f"Índice '{indice}' no soportado. Válidos: {list(CALCULADORES)}")
