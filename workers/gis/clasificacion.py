from __future__ import annotations

import numpy as np

# Umbrales agronómicos "fijo" por índice — NO intercambiables entre sí.
# NDVI, NDRE, SAVI y GNDVI son todos índices razón acotados en ~[-1,1], pero
# su rango *típico* sobre vegetación real difiere mucho: NDRE ronda 0.1-0.4
# para el mismo canopeo donde NDVI ronda 0.4-0.8 (la banda RedEdge satura
# mucho menos que RED), y SAVI corre sistemáticamente por debajo de NDVI por
# el factor (1+L) sobre el suelo expuesto que corrige. Aplicar los umbrales
# de NDVI a NDRE clasificaría casi cualquier lote sano como "crítico".
# GNDVI se comporta lo bastante parecido a NDVI (mismo orden de magnitud,
# mismo uso agronómico) como para reutilizar sus umbrales sin distorsión.
# ExG queda afuera de esta tabla a propósito: no es un índice razón (ver
# pipeline.py::_metodo_umbral_efectivo), su escala depende de las unidades
# crudas de la cámara y siempre se clasifica con método adaptativo (otsu).
_UMBRALES_POR_INDICE: dict[str, list[float]] = {
    "ndvi":  [0.20, 0.40, 0.70],
    "gndvi": [0.20, 0.40, 0.70],
    "ndre":  [0.10, 0.20, 0.35],
    "savi":  [0.15, 0.30, 0.50],
}
_UMBRALES_FIJOS_DEFAULT = _UMBRALES_POR_INDICE["ndvi"]


def _umbrales_fijos(indice: str) -> list[float]:
    return _UMBRALES_POR_INDICE.get(indice, _UMBRALES_FIJOS_DEFAULT)[:]


def calcular_umbrales(valores: np.ndarray, metodo: str, indice: str = "ndvi") -> list[float]:
    """
    Calcula los 3 umbrales de clasificación para dividir en 4 clases.

    metodo="fijo"     → umbrales agronómicos estándar por índice (ver _UMBRALES_POR_INDICE)
    metodo="otsu"     → threshold_multiotsu sobre los píxeles válidos (scikit-image)
    metodo="percentil"→ percentiles 25, 50 y 75 de los píxeles válidos

    indice: qué índice se está clasificando (ndvi/ndre/savi/gndvi/exg) — solo
    afecta al método "fijo" y al fallback de otsu/percentil cuando no pueden
    calcularse (imagen muy uniforme o todos NaN).
    """
    if metodo == "fijo":
        return _umbrales_fijos(indice)

    validos = valores[~np.isnan(valores)].ravel()
    if validos.size == 0:
        return _umbrales_fijos(indice)

    if metodo == "percentil":
        u = [float(np.percentile(validos, p)) for p in (25, 50, 75)]
        # Si percentiles colapsan (distribución muy plana) usar fijo
        if len(set(u)) < 3:
            return _umbrales_fijos(indice)
        return sorted(u)

    if metodo == "otsu":
        try:
            from skimage.filters import threshold_multiotsu
            umbrales = threshold_multiotsu(validos, nclasses=4)
            return sorted(float(u) for u in umbrales)
        except Exception:
            # Falla cuando la imagen tiene < 4 valores únicos
            return _umbrales_fijos(indice)

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
