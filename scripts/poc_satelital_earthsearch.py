"""
POC: cargar un vuelo desde imagen satelital (Sentinel-2) en vez de subir un
GeoTIFF de dron, dado el polígono real de un lote + una fecha elegida por
el usuario.

Extiende scripts/descargar_sentinel2_real.py (agregado en c5e41ae) en dos
puntos, para validar si alcanza con AWS Earth Search o si hace falta sumar
Copernicus Data Space Ecosystem como plan B:

  1. Búsqueda por VENTANA DE FECHAS alrededor de la fecha elegida (no solo
     "la más reciente") — imprime todas las escenas candidatas con su
     nubosidad, simulando la pantalla donde el usuario vería "esta fecha
     tiene 80% de nubes, elijo otra".
  2. Recorte al POLÍGONO REAL del lote (rasterio.mask), no solo al bbox
     rectangular — el script original dejaba píxeles fuera del lote real
     dentro del rectángulo de descarga.

Polígono de prueba: lote real "Lote Nuevisimo" (a9f9c87d-9d01-4461-8fb9-
5d33445d0f63, ~1.26 ha), dibujado a mano con leaflet-geoman en el feature
de dibujo de límites — no es un polígono inventado.

Uso (dentro del contenedor worker, que tiene rasterio/GDAL):
    docker compose exec worker python3 scripts/poc_satelital_earthsearch.py [fecha] [ventana_dias]
    docker compose exec worker python3 scripts/poc_satelital_earthsearch.py 2026-08-15 15
"""

import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import rasterio
from rasterio.env import Env
from rasterio.mask import mask
from rasterio.crs import CRS
from rasterio.warp import transform_bounds, transform_geom
from rasterio.windows import from_bounds as window_from_bounds

FECHA_ELEGIDA = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
VENTANA_DIAS = int(sys.argv[2]) if len(sys.argv) > 2 else 15
NUBES_MAX_ACEPTABLE = 30  # %, mismo umbral que descargar_sentinel2_real.py

OUTPUT = Path(f"/tmp/sentinel2_lote_nuevisimo_{FECHA_ELEGIDA}.tif")

# Lote real "Lote Nuevisimo" (a9f9c87d-9d01-4461-8fb9-5d33445d0f63) — WGS84.
LOTE_GEOJSON = {
    "type": "Polygon",
    "coordinates": [[
        [-61.218846, -27.231062],
        [-61.219929, -27.230308],
        [-61.22023, -27.230582],
        [-61.220391, -27.230871],
        [-61.220251, -27.231136],
        [-61.219983, -27.231365],
        [-61.219404, -27.23172],
        [-61.218846, -27.231062],
    ]],
}

# Claves de asset en Earth Search → posición en el GeoTIFF de salida (1-indexed).
# El pipeline usa sensor="sentinel2": BLUE=2, GREEN=3, RED=4, RE=5, NIR=8.
BANDAS = {
    "blue": 2,
    "green": 3,
    "red": 4,
    "rededge1": 5,
    "nir": 8,
}


def _bbox_de_poligono(geojson: dict) -> tuple[float, float, float, float]:
    lons = [pt[0] for pt in geojson["coordinates"][0]]
    lats = [pt[1] for pt in geojson["coordinates"][0]]
    return (min(lons), min(lats), max(lons), max(lats))


def buscar_escenas(bbox: tuple[float, float, float, float], fecha_centro: str, ventana_dias: int) -> list[dict]:
    """
    Busca escenas en una ventana de fechas alrededor de fecha_centro (no
    solo la más reciente) — el usuario elige la fecha, no el sistema.
    """
    centro = datetime.fromisoformat(fecha_centro)
    desde = (centro - timedelta(days=ventana_dias)).strftime("%Y-%m-%d")
    hasta = (centro + timedelta(days=ventana_dias)).strftime("%Y-%m-%d")

    bbox_str = ",".join(str(round(c, 6)) for c in bbox)
    params = urllib.parse.urlencode({
        "bbox": bbox_str,
        "datetime": f"{desde}T00:00:00Z/{hasta}T23:59:59Z",
        "limit": 50,
    })
    url = f"https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items?{params}"

    req = urllib.request.Request(url, headers={"User-Agent": "agronexo-poc/1.0"})
    # host fijo (earth-search.aws.element84.com arriba), solo bbox/fechas son dinamicos
    with urllib.request.urlopen(req, timeout=30) as resp:  # nosec B310  # nosemgrep: dynamic-urllib-use-detected
        catalog = json.loads(resp.read())

    features = catalog.get("features", [])
    if not features:
        raise RuntimeError(f"Sin escenas Sentinel-2 entre {desde} y {hasta} para bbox={bbox_str}")

    for f in features:
        f["_dias_de_diferencia"] = abs((datetime.fromisoformat(f["properties"]["datetime"][:10]) - centro).days)
    features.sort(key=lambda f: f["_dias_de_diferencia"])
    return features


def leer_banda_recortada(
    url: str, poligono_wgs84: dict, pixel_size_objetivo_m: float = 10.0, margen_m: float = 300.0,
) -> tuple[np.ndarray, dict]:
    """
    Lee del COG remoto solo la ventana que cubre el polígono (no toda la
    escena) y aplica rasterio.mask para dejar en nodata todo lo que está
    fuera del polígono real del lote — a diferencia del script original,
    que solo recortaba al bbox rectangular.

    Sentinel-2 no tiene todas las bandas a la misma resolución nativa:
    Blue/Green/Red/NIR son 10 m/px pero RedEdge (B05) es 20 m/px — leer
    cada banda con su tamaño de píxel nativo produce arrays de distinto
    shape que no se pueden apilar en el mismo GeoTIFF. `out_shape` fuerza
    el remuestreo de cada banda a una grilla común de pixel_size_objetivo_m
    (10 m), sea cual sea su resolución nativa.
    """
    with rasterio.open(url) as src:
        poligono_nativo = transform_geom("EPSG:4326", src.crs, poligono_wgs84)
        bbox_wgs84 = _bbox_de_poligono(poligono_wgs84)
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


def main():
    t0 = time.perf_counter()
    bbox = _bbox_de_poligono(LOTE_GEOJSON)

    print(f"Lote de prueba: 'Lote Nuevisimo' (a9f9c87d-...) — bbox {bbox}")
    print(f"Fecha elegida por el usuario: {FECHA_ELEGIDA} (ventana ±{VENTANA_DIAS} días)\n")

    print("Consultando Earth Search (AWS STAC API)...")
    try:
        escenas = buscar_escenas(bbox, FECHA_ELEGIDA, VENTANA_DIAS)
    except Exception as e:
        print(f"ERROR consultando STAC: {e}")
        return

    print(f"\n{len(escenas)} escena(s) encontradas — esto es lo que vería el usuario para elegir:")
    print(f"{'Fecha':<12} {'Nubes %':>8} {'Días de diferencia':>20}  Escena")
    for f in escenas:
        p = f["properties"]
        marca = " ← elegida" if f is escenas[0] else ""
        print(f"{p['datetime'][:10]:<12} {p.get('eo:cloud_cover', '?'):>8} {f['_dias_de_diferencia']:>20}  {f['id']}{marca}")

    elegida = escenas[0]
    nubes = elegida["properties"].get("eo:cloud_cover", 100)
    if nubes > NUBES_MAX_ACEPTABLE:
        print(f"\n⚠️  La escena más cercana a la fecha elegida tiene {nubes}% de nubes (umbral: {NUBES_MAX_ACEPTABLE}%).")
        print("   En la UI real, acá el usuario vería la lista de arriba y elegiría otra fecha.")

    print(f"\nDescargando bandas de la escena {elegida['id']} ({elegida['properties']['datetime'][:10]})...")
    assets = elegida["assets"]
    arrays: dict[int, np.ndarray] = {}
    meta_ref: dict | None = None

    with Env(GDAL_HTTP_TIMEOUT="30", GDAL_HTTP_CONNECTTIMEOUT="10", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif"):
        for band_s2, pos_out in BANDAS.items():
            url = assets.get(band_s2, {}).get("href", "")
            if not url:
                print(f"  {band_s2}: no encontrada en assets")
                continue
            print(f"  {band_s2} → posición {pos_out}... ", end="", flush=True)
            tb = time.perf_counter()
            try:
                data, meta = leer_banda_recortada(url, LOTE_GEOJSON)
                data = np.clip(data / 10_000.0, 0.0, 1.0).astype(np.float32)
                arrays[pos_out] = data
                if meta_ref is None:
                    meta_ref = meta
                print(f"OK ({time.perf_counter()-tb:.1f}s) — {data.shape[1]}x{data.shape[0]} px, rango [{data.min():.3f}, {data.max():.3f}]")
            except Exception as e:
                print(f"ERROR: {e}")

    if not arrays or meta_ref is None:
        print("No se pudo descargar ninguna banda. Verificá conectividad.")
        return

    alto, ancho = next(iter(arrays.values())).shape
    out = np.zeros((8, alto, ancho), dtype=np.float32)
    for pos, arr in arrays.items():
        out[pos - 1] = arr

    print(f"\nEscribiendo GeoTIFF recortado al polígono real del lote ({ancho}x{alto} px, 8 bandas)...")
    with rasterio.open(
        OUTPUT, "w", driver="GTiff", dtype="float32", width=ancho, height=alto, count=8,
        crs=meta_ref["crs"], transform=meta_ref["transform"], compress="lzw", nodata=0,
    ) as dst:
        for i in range(8):
            dst.write(out[i], i + 1)

    size_kb = OUTPUT.stat().st_size / 1024
    print(f"\n✓ Archivo: {OUTPUT}")
    print(f"  Tamaño:  {size_kb:.0f} KB")
    print(f"  Fuente:  Earth Search (AWS, sin login) — escena {elegida['id']}")
    print(f"  Tiempo:  {time.perf_counter()-t0:.1f}s")
    print(f"\nCopiar a Windows:")
    print(f"  docker compose cp worker:{OUTPUT} .")
    print(f"\nSubir con sensor: sentinel2")


if __name__ == "__main__":
    main()
