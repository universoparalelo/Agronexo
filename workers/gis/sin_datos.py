"""
Parte del lote que NO tiene información real (píxeles sin dato), calculada al
procesar un índice y guardada en el resultado como `sin_datos`.

Sin dato = píxeles donde el índice es NaN (nubes o sombras enmascaradas, bordes
negros del ortomosaico, división por cero) más la parte del lote que el GeoTIFF
directamente no cubre. Se mide sobre el raster, no se deduce del tamaño de los
huecos que dejan las zonas: un hueco entre zonas puede ser una zona menor a 1 ha
descartada por el worker (ahí sí hay datos), y un sin-dato chico no deja hueco
visible. Los mapas dibujan esta forma rayada y la API nunca la rellena.
"""

from __future__ import annotations

import numpy as np
from rasterio.features import shapes
from rasterio.transform import array_bounds
from shapely.geometry import box, mapping, shape
from shapely.ops import unary_union
from shapely.validation import make_valid

# El polígono del lote corta los píxeles por la mitad, y la máscara del raster
# (píxel adentro si su centro cae adentro) nunca calza exacto: a lo largo del
# contorno quedan astillas dentadas de hasta ~0,7 píxel de espesor (más en las
# puntas). Se ignora todo lo más angosto que ~0,9 píxel (apertura morfológica de
# radio 0,45) para no marcar el borde como "sin datos". Un sin-dato real de 1×1
# píxel (ancho 1) sí sobrevive.
FRACCION_PIXEL_ASTILLA = 0.45


def calcular_sin_datos(valores: np.ndarray, transform, limite_wgs84: dict | None = None) -> dict | None:
    """
    Geometría GeoJSON (EPSG:4326) de la parte del lote sin información, o None si
    no hay. `valores` es el índice sin suavizar (NaN = sin dato) sobre la grilla
    de `transform` (ya reproyectada a 4326); `limite_wgs84` es el polígono del lote
    (si no se conoce se usa la huella del raster).
    """
    alto, ancho = valores.shape
    huella = box(*array_bounds(alto, ancho, transform))
    region = make_valid(shape(limite_wgs84)) if limite_wgs84 else huella

    mascara = np.isnan(valores)
    partes = [
        shape(g)
        for g, v in shapes(mascara.astype(np.uint8), mask=mascara, transform=transform)
        if v == 1
    ]
    sin_dato_en_raster = unary_union(partes) if partes else None

    sin_datos = region.difference(huella)   # lo que el GeoTIFF no cubre
    if sin_dato_en_raster is not None:
        sin_datos = unary_union([sin_datos, region.intersection(sin_dato_en_raster)])

    if sin_datos.is_empty:
        return None
    ancla = abs(transform.a) * FRACCION_PIXEL_ASTILLA
    sin_datos = sin_datos.buffer(-ancla).buffer(ancla)
    if sin_datos.is_empty:
        return None
    return mapping(make_valid(sin_datos.simplify(ancla / 3)))
