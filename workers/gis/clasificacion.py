from __future__ import annotations

import numpy as np

_UMBRALES_FIJOS = [0.20, 0.40, 0.70]


def calcular_umbrales(valores: np.ndarray, metodo: str) -> list[float]:
    """
    Calcula los 3 umbrales de clasificación para dividir en 4 clases.

    metodo="fijo"     → umbrales agronómicos estándar [0.20, 0.40, 0.70]
    metodo="otsu"     → threshold_multiotsu sobre los píxeles válidos (scikit-image)
    metodo="percentil"→ percentiles 25, 50 y 75 de los píxeles válidos

    Si otsu o percentil no pueden calcularse (imagen muy uniforme o todos NaN)
    se hace fallback silencioso a "fijo".
    """
    if metodo == "fijo":
        return _UMBRALES_FIJOS[:]

    validos = valores[~np.isnan(valores)].ravel()
    if validos.size == 0:
        return _UMBRALES_FIJOS[:]

    if metodo == "percentil":
        u = [float(np.percentile(validos, p)) for p in (25, 50, 75)]
        # Si percentiles colapsan (distribución muy plana) usar fijo
        if len(set(u)) < 3:
            return _UMBRALES_FIJOS[:]
        return sorted(u)

    if metodo == "otsu":
        try:
            from skimage.filters import threshold_multiotsu
            umbrales = threshold_multiotsu(validos, nclasses=4)
            return sorted(float(u) for u in umbrales)
        except Exception:
            # Falla cuando la imagen tiene < 4 valores únicos
            return _UMBRALES_FIJOS[:]

    raise ValueError(f"metodo_umbral desconocido: '{metodo}'. Usar 'fijo', 'otsu' o 'percentil'.")


def clasificar_con_umbrales(valores: np.ndarray, umbrales: list[float]) -> np.ndarray:
    """
    Asigna código de clase a cada píxel según los umbrales dados.
    0 = nodata/nan  1 = crítica  2 = deficiente  3 = normal  4 = vigorosa
    """
    u1, u2, u3 = umbrales
    clase = np.zeros(valores.shape, dtype=np.uint8)
    valido = ~np.isnan(valores)
    clase[valido & (valores < u1)]                        = 1
    clase[valido & (valores >= u1) & (valores < u2)]      = 2
    clase[valido & (valores >= u2) & (valores < u3)]      = 3
    clase[valido & (valores >= u3)]                       = 4
    return clase
