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
    """ExG = 2*GREEN - RED - BLUE  — índice de verdor, no requiere NIR.
    Útil con cámaras RGB cuando no hay banda NIR disponible.
    """
    resultado = 2.0 * green - red - blue
    resultado[_mascara_nodata(nodata, green, red, blue)] = np.nan
    return resultado.astype(np.float32)


def calcular_gndvi(nir: np.ndarray, green: np.ndarray, nodata: float | None = None) -> np.ndarray:
    """GNDVI = (NIR - GREEN) / (NIR + GREEN)  — rango [-1, 1].
    Reemplaza RED por GREEN respecto al NDVI: no satura tan rápido en fases
    reproductivas, útil cuando NDVI > 0.75.
    """
    resultado = _division_segura(nir - green, nir + green)
    resultado[_mascara_nodata(nodata, nir, green)] = np.nan
    return resultado.astype(np.float32)


def calcular_msavi(nir: np.ndarray, red: np.ndarray, nodata: float | None = None) -> np.ndarray:
    """MSAVI2 = (2*NIR + 1 - sqrt((2*NIR + 1)² - 8*(NIR - RED))) / 2  — rango ~[-1, 1].
    Versión auto-ajustada de SAVI (no requiere calibrar L a mano). Recomendado
    al inicio de campaña con suelo muy expuesto.
    """
    termino = (2.0 * nir + 1.0) ** 2 - 8.0 * (nir - red)
    resultado = (2.0 * nir + 1.0 - np.sqrt(np.maximum(termino, 0.0))) / 2.0
    resultado[_mascara_nodata(nodata, nir, red)] = np.nan
    return resultado.astype(np.float32)


def calcular_ndwi(green: np.ndarray, nir: np.ndarray, nodata: float | None = None) -> np.ndarray:
    """NDWI (McFeeters) = (GREEN - NIR) / (GREEN + NIR)  — rango [-1, 1].
    Proxy de agua superficial: sensores sin banda SWIR (DJI Mavic 3
    Multispectral) no pueden calcular el NDWI convencional (NIR-SWIR).
    """
    resultado = _division_segura(green - nir, green + nir)
    resultado[_mascara_nodata(nodata, green, nir)] = np.nan
    return resultado.astype(np.float32)


CALCULADORES = {
    "ndvi":  calcular_ndvi,
    "ndre":  calcular_ndre,
    "savi":  calcular_savi,
    "exg":   calcular_exg,
    "gndvi": calcular_gndvi,
    "msavi": calcular_msavi,
    "ndwi":  calcular_ndwi,
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
    if indice == "msavi":
        return calcular_msavi(bandas["NIR"], bandas["RED"], nodata)
    if indice == "ndwi":
        return calcular_ndwi(bandas["GREEN"], bandas["NIR"], nodata)
    raise ValueError(f"Índice '{indice}' no soportado. Válidos: {list(CALCULADORES)}")
