"""
Descarga y recorte al polígono real de un lote de una escena Sentinel-2 ya
elegida (ver satelital_catalogo.py para la búsqueda). Usa rasterio/numpy —
solo se importa desde el worker, nunca desde el proceso FastAPI (ver nota
en satelital_catalogo.py).

Sentinel-2 no tiene todas las bandas a la misma resolución nativa:
Blue/Green/Red/NIR son 10 m/px pero RedEdge (B05) es 20 m/px — leer cada
banda a su resolución nativa produce arrays de distinto shape que no se
pueden apilar en un único GeoTIFF. `out_shape` fuerza el remuestreo de
cada banda a una grilla común de PIXEL_SIZE_OBJETIVO_M, sea cual sea su
resolución nativa (bug real encontrado en el POC — ver docs/release-v3.0.0.md).
"""

from __future__ import annotations

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.env import Env
from rasterio.mask import mask
from rasterio.warp import transform_bounds, transform_geom
from rasterio.windows import from_bounds as window_from_bounds

from workers.gis.band_mapping import MAPEO_SENSORES
from workers.gis.satelital_catalogo import bbox_de_poligono

PIXEL_SIZE_OBJETIVO_M = 10.0
MARGEN_M = 300.0

# Clave de asset en Earth Search → nombre de atributo en MapaBandas.
_ASSET_A_ATRIBUTO = {
    "blue": "BLUE",
    "green": "GREEN",
    "red": "RED",
    "rededge1": "RE",
    "nir": "NIR",
}


def descargar_y_recortar_geotiff(item: dict, poligono_wgs84: dict, destino_path: str) -> str:
    """
    Descarga las bandas de `item` (un Feature STAC de Earth Search) que
    necesita sensor="sentinel2" según band_mapping.py, recortadas al
    polígono real del lote, y escribe un GeoTIFF multibanda en
    destino_path. Retorna destino_path.
    """
    mapeo = MAPEO_SENSORES["sentinel2"]
    n_bandas = max(v for v in mapeo if v is not None)

    assets = item.get("assets", {})
    arrays: dict[int, np.ndarray] = {}
    meta_ref: dict | None = None

    with Env(GDAL_HTTP_TIMEOUT="30", GDAL_HTTP_CONNECTTIMEOUT="10", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif"):
        for asset_key, atributo in _ASSET_A_ATRIBUTO.items():
            pos_out = getattr(mapeo, atributo, None)
            if pos_out is None:
                continue
            url = assets.get(asset_key, {}).get("href")
            if not url:
                raise RuntimeError(f"La escena {item.get('id')} no tiene el asset '{asset_key}'.")

            data, meta = _leer_banda_recortada(url, poligono_wgs84)
            data = np.clip(data / 10_000.0, 0.0, 1.0).astype(np.float32)
            arrays[pos_out] = data
            if meta_ref is None:
                meta_ref = meta

    if not arrays or meta_ref is None:
        raise RuntimeError(f"No se pudo descargar ninguna banda de la escena {item.get('id')}.")

    alto, ancho = next(iter(arrays.values())).shape
    out = np.zeros((n_bandas, alto, ancho), dtype=np.float32)
    for pos, arr in arrays.items():
        out[pos - 1] = arr

    with rasterio.open(
        destino_path, "w", driver="GTiff", dtype="float32", width=ancho, height=alto, count=n_bandas,
        crs=meta_ref["crs"], transform=meta_ref["transform"], compress="lzw", nodata=0,
    ) as dst:
        for i in range(n_bandas):
            dst.write(out[i], i + 1)

    return destino_path


def _leer_banda_recortada(
    url: str, poligono_wgs84: dict,
    pixel_size_objetivo_m: float = PIXEL_SIZE_OBJETIVO_M, margen_m: float = MARGEN_M,
) -> tuple[np.ndarray, dict]:
    with rasterio.open(url) as src:
        poligono_nativo = transform_geom("EPSG:4326", src.crs, poligono_wgs84)
        bbox_wgs84 = bbox_de_poligono(poligono_wgs84)
        xmin, ymin, xmax, ymax = transform_bounds(CRS.from_epsg(4326), src.crs, *bbox_wgs84)
        bbox_con_margen = (xmin - margen_m, ymin - margen_m, xmax + margen_m, ymax + margen_m)

        ancho_px = max(1, round((bbox_con_margen[2] - bbox_con_margen[0]) / pixel_size_objetivo_m))
        alto_px = max(1, round((bbox_con_margen[3] - bbox_con_margen[1]) / pixel_size_objetivo_m))

        win = window_from_bounds(*bbox_con_margen, transform=src.transform)
        data_ventana = src.read(
            1, window=win, out_shape=(alto_px, ancho_px), resampling=rasterio.enums.Resampling.bilinear,
        ).astype(np.float32)

        ventana_transform = rasterio.transform.from_bounds(*bbox_con_margen, ancho_px, alto_px)

        with rasterio.io.MemoryFile() as memfile:
            with memfile.open(
                driver="GTiff", dtype="float32", width=ancho_px, height=alto_px,
                count=1, crs=src.crs, transform=ventana_transform,
            ) as tmp:
                tmp.write(data_ventana, 1)
            with memfile.open() as tmp_r:
                data_recortada, transform_recorte = mask(tmp_r, [poligono_nativo], crop=True, nodata=0)

        meta = {"transform": transform_recorte, "crs": src.crs}
    return data_recortada[0], meta
