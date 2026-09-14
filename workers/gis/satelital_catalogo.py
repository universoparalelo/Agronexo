"""
Búsqueda de escenas Sentinel-2 en el catálogo STAC de Earth Search (AWS
Open Data / Element84) — sin autenticación, sin cuenta.

Solo usa `urllib`/`json`/`datetime` — deliberadamente sin rasterio/numpy,
así que es seguro importarlo tanto desde el proceso FastAPI (endpoint que
lista escenas disponibles) como desde el worker. La descarga y el recorte
de las bandas en sí (que sí necesita rasterio) vive aparte, en
`workers/gis/satelital_descarga.py`, e importa este módulo — no al revés.

Earth Search es un servicio "best effort" sin SLA publicado (ver su propio
README: "This public API does not come with any guaranteed service") — los
datos en sí (bucket AWS Open Data) son sólidos, el catálogo de búsqueda
podría estar caído o lento sin aviso. Ver docs/release-v3.0.0.md, sección
"Problemas abiertos", para la decisión de no sumar Copernicus todavía.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

EARTH_SEARCH_COLLECTION_URL = "https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a"


def bbox_de_poligono(geojson: dict) -> tuple[float, float, float, float]:
    anillo = geojson["coordinates"][0]
    lons = [pt[0] for pt in anillo]
    lats = [pt[1] for pt in anillo]
    return (min(lons), min(lats), max(lons), max(lats))


def buscar_escenas(
    bbox: tuple[float, float, float, float], fecha_centro: str, ventana_dias: int = 15, limit: int = 50,
) -> list[dict]:
    """
    Escenas Sentinel-2 L2A candidatas para el bbox, en una ventana de
    +/- ventana_dias alrededor de fecha_centro, ordenadas por cercanía a
    esa fecha (no por más reciente) — el usuario elige la fecha y ve la
    nubosidad de cada opción, el sistema no la elige por él.

    Cada item devuelto trae, además de los campos STAC estándar,
    `_dias_de_diferencia` (int) para poder ordenar/mostrar en la UI.
    """
    centro = datetime.fromisoformat(fecha_centro)
    desde = (centro - timedelta(days=ventana_dias)).strftime("%Y-%m-%d")
    hasta = (centro + timedelta(days=ventana_dias)).strftime("%Y-%m-%d")

    params = urllib.parse.urlencode({
        "bbox": ",".join(str(round(c, 6)) for c in bbox),
        "datetime": f"{desde}T00:00:00Z/{hasta}T23:59:59Z",
        "limit": limit,
    })
    catalog = _get_json(f"{EARTH_SEARCH_COLLECTION_URL}/items?{params}")

    features = catalog.get("features", [])
    if not features:
        raise RuntimeError(f"Sin escenas Sentinel-2 entre {desde} y {hasta} para este lote.")

    for f in features:
        f["_dias_de_diferencia"] = abs((datetime.fromisoformat(f["properties"]["datetime"][:10]) - centro).days)
    features.sort(key=lambda f: f["_dias_de_diferencia"])
    return features


def obtener_escena_por_id(item_id: str) -> dict:
    """
    Reconsulta una escena puntual por id — se usa justo antes de descargar
    (en el worker) para tener URLs de assets frescas, en vez de pasar URLs
    largas por la cola de Celery.
    """
    return _get_json(f"{EARTH_SEARCH_COLLECTION_URL}/items/{item_id}")


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "agronexo/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())
