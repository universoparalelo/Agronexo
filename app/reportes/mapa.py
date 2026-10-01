"""
Genera una imagen PNG estática del mapa de zonas para incrustar en el
reporte PDF ejecutivo, sin navegador headless ni GeoPandas/GDAL.

Reutiliza la misma proyección equirectangular local que
app/diagnostico/forma.py (sin pyproj/GDAL) para que el mapa tenga el
aspect ratio correcto, y la misma paleta de colores que
frontend/src/components/MapaZonas.jsx para que sea visualmente
consistente con el dashboard.

Deliberadamente con Pillow y no matplotlib: matplotlib arrastra NumPy
como dependencia dura, y app/diagnostico/service.py documenta por qué
el proceso de FastAPI no lleva NumPy/GeoPandas a propósito (esas
dependencias GIS pesadas quedan reservadas al worker). Pillow dibuja
polígonos rellenos sin esa dependencia.
"""

from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry

from app.diagnostico.forma import proyectar_a_metros_locales

# Mismos hex que frontend/src/components/MapaZonas.jsx (COLORES_CLASE / COLORES_SEVERIDAD).
COLORES_CLASE = {
    "critica": "#ef4444",
    "deficiente": "#f97316",
    "normal": "#86efac",
    "vigorosa": "#16a34a",
}

COLORES_SEVERIDAD = {
    "critica": "#ef4444",
    "moderada": "#f59e0b",
    "leve": "#fbbf24",
    "normal": "#86efac",
    "vigorosa": "#3b82f6",
}

# Etiquetas de "clase" (valor real del índice) — mismos nombres que
# frontend/src/utils/clasesIndice.js::ETIQUETA_CLASE, distinto de la
# severidad del diagnóstico (crítica/moderada/leve), que habla de la
# gravedad del problema, no del valor del índice.
ETIQUETAS_CLASE = {
    "critica": "Muy bajo",
    "deficiente": "Bajo",
    "normal": "Medio",
    "vigorosa": "Alto",
}

ETIQUETAS_SEVERIDAD = {
    "critica": "Crítica",
    "moderada": "Moderada",
    "leve": "Leve",
    "normal": "Normal",
    "vigorosa": "Vigorosa",
}

_COLOR_FONDO = (255, 255, 255)
_COLOR_SIN_DATO = "#999999"
_MARGEN_PX = 24
_ALTO_LEYENDA_PX = 36

# Misma fuente instalada en la imagen para WeasyPrint (docker/Dockerfile.api,
# paquete fonts-dejavu-core) — la fuente bitmap por defecto de Pillow
# (ImageFont.load_default()) no soporta tildes/ñ correctamente.
_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def _cargar_fuente(size: int = 13) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(_FONT_PATH, size)
    except OSError:
        return ImageFont.load_default()


def generar_imagen_mapa_zonas(
    geojson: dict, modo: str = "clase", ancho: int = 900, alto: int = 640,
) -> bytes:
    """
    Dibuja las zonas del GeoJSON de diagnóstico (el mismo que devuelve
    app.diagnostico.service.generar_diagnostico) como polígonos rellenos,
    coloreados por 'clase' (valor real del índice — default, a pedido: la
    severidad relativa al promedio del lote dejaba casi todo el mapa en
    'normal'/verde en lotes con variación moderada) o 'severidad' según
    `modo`. Devuelve bytes PNG listos para incrustar en el template del
    reporte como data URI.
    """
    prop_color = modo if modo in ("severidad", "clase") else "clase"
    paleta = COLORES_SEVERIDAD if prop_color == "severidad" else COLORES_CLASE
    etiquetas = ETIQUETAS_SEVERIDAD if prop_color == "severidad" else ETIQUETAS_CLASE

    features = geojson.get("features", [])
    imagen = Image.new("RGB", (ancho, alto), _COLOR_FONDO)
    draw = ImageDraw.Draw(imagen)

    if not features:
        draw.text((ancho // 2 - 60, alto // 2), "Sin zonas para mostrar", fill="#666666", font=_cargar_fuente())
        return _a_bytes(imagen)

    geoms: list[BaseGeometry] = [shape(f["geometry"]) for f in features]
    lon0 = sum(g.centroid.x for g in geoms) / len(geoms)
    lat0 = sum(g.centroid.y for g in geoms) / len(geoms)
    geoms_locales = [proyectar_a_metros_locales(g, lon0, lat0) for g in geoms]

    minx = min(g.bounds[0] for g in geoms_locales)
    miny = min(g.bounds[1] for g in geoms_locales)
    maxx = max(g.bounds[2] for g in geoms_locales)
    maxy = max(g.bounds[3] for g in geoms_locales)
    ancho_m = max(maxx - minx, 1.0)
    alto_m = max(maxy - miny, 1.0)

    alto_dibujo = alto - _ALTO_LEYENDA_PX
    escala = min(
        (ancho - 2 * _MARGEN_PX) / ancho_m,
        (alto_dibujo - 2 * _MARGEN_PX) / alto_m,
    )

    def a_px(x: float, y: float) -> tuple[float, float]:
        px = _MARGEN_PX + (x - minx) * escala
        py = _MARGEN_PX + (maxy - y) * escala  # el eje Y de la imagen crece hacia abajo
        return (px, py)

    for feat, geom_local in zip(features, geoms_locales):
        valor = feat.get("properties", {}).get(prop_color, "normal")
        color = paleta.get(valor, _COLOR_SIN_DATO)
        _dibujar_geometria(draw, geom_local, a_px, color)

    _dibujar_leyenda(draw, alto, paleta, etiquetas)

    return _a_bytes(imagen)


def _dibujar_geometria(draw: ImageDraw.ImageDraw, geom: BaseGeometry, a_px, color: str) -> None:
    poligonos = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
    for poligono in poligonos:
        puntos = [a_px(x, y) for x, y in poligono.exterior.coords]
        if len(puntos) >= 3:
            draw.polygon(puntos, fill=color, outline="#ffffff")


def _dibujar_leyenda(
    draw: ImageDraw.ImageDraw, alto: int, paleta: dict[str, str], etiquetas: dict[str, str],
) -> None:
    fuente = _cargar_fuente()
    x = _MARGEN_PX
    y = alto - _ALTO_LEYENDA_PX + 8
    for clave, color in paleta.items():
        draw.rectangle([x, y, x + 14, y + 14], fill=color, outline="#333333")
        draw.text((x + 20, y + 1), etiquetas.get(clave, clave), fill="#111111", font=fuente)
        x += 110


def _a_bytes(imagen: Image.Image) -> bytes:
    buf = io.BytesIO()
    imagen.save(buf, format="PNG")
    return buf.getvalue()
