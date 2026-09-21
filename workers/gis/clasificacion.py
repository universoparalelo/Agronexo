from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)

# Umbrales agronómicos "fijo" por índice — NO intercambiables entre sí.
# NDVI, NDRE, SAVI y GNDVI son todos índices razón acotados en ~[-1,1], pero
# su rango *típico* sobre vegetación real difiere mucho: NDRE ronda 0.1-0.4
# para el mismo canopeo donde NDVI ronda 0.4-0.8 (la banda RedEdge satura
# mucho menos que RED), y SAVI corre sistemáticamente por debajo de NDVI por
# el factor (1+L) sobre el suelo expuesto que corrige. Aplicar los umbrales
# de NDVI a NDRE clasificaría casi cualquier lote sano como "crítico".
# GNDVI también tiene los suyos: usa la banda verde, que refleja bastante en casi
# cualquier vegetación, así que varía la mitad que el NDVI (p5–p95 de 0,13–0,22
# contra 0,26–0,37) y un canopeo con NDVI 0,70 tiene GNDVI ≈ 0,63. Con los
# umbrales del NDVI (0,20 / 0,40 / 0,70) el 85–99 % de un lote sano caía en
# "Normal" y "Alto" era casi inalcanzable. Los cortes salen de cruzar con los del
# NDVI (≈ 0,25 / 0,45 / 0,63); el último se fijó en 0,60 a pedido. CALIBRACIÓN
# PROVISORIA: 3 escenas Sentinel-2 de cultivo sano, el corte de 0,25 se apoya
# en ~40 píxeles.
# ExG (normalizado, ver indices.calcular_exg) tiene su propia escala: en las
# escenas Sentinel-2 disponibles cruza los cortes del NDVI en ~0,05 (NDVI 0,40)
# y ~0,29 (NDVI 0,70). El corte intermedio se bajó de 0,20 a 0,15: con 0,20 el
# "Normal" contradecía al NDVI (63 % de un lote quedaba en "Bajo" cuando el NDVI
# lo clasifica casi todo como normal). CALIBRACIÓN
# PROVISORIA: 3 escenas, todas con cultivo, casi sin suelo desnudo — validar
# con más lotes o con un agrónomo. Son cortes para Sentinel-2; para otro sensor
# hay que revisarlos.
_UMBRALES_POR_INDICE: dict[str, list[float]] = {
    "ndvi":  [0.20, 0.40, 0.70],
    "gndvi": [0.25, 0.45, 0.60],
    "ndre":  [0.10, 0.20, 0.35],
    "savi":  [0.15, 0.30, 0.50],
    "exg":   [0.05, 0.15, 0.30],
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
            umbrales = threshold_multiotsu(validos, classes=4)
            return sorted(float(u) for u in umbrales)
        except ValueError:
            # Esperable: la imagen tiene < 4 valores únicos y no se puede separar en 4 clases
            return _umbrales_fijos(indice)
        except Exception:
            # Cualquier otro fallo (p. ej. un parámetro que cambió entre versiones de
            # scikit-image) NO debe pasar callado: un TypeError por `nclasses` (el
            # nombre correcto es `classes`) dejó a "otsu" clasificando con umbrales
            # fijos sin que nadie lo notara — ExG quedaba entero en la clase más baja.
            logger.exception("threshold_multiotsu falló; se usan los umbrales fijos de '%s'", indice)
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
