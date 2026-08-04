"""
Descarga una escena real de Sentinel-2 L2A sobre el NEA argentino
desde AWS Open Data Registry (sin login, sin registro).

Produce un GeoTIFF de 8 bandas compatible con sensor="sentinel2" del pipeline:
  posición 2=BLUE, 3=GREEN, 4=RED, 5=RedEdge, 8=NIR

Uso:
    python3 scripts/descargar_sentinel2_real.py [tamaño_px]
    python3 scripts/descargar_sentinel2_real.py 2000   # ~20km x 20km (~30 MB)
    python3 scripts/descargar_sentinel2_real.py 4000   # ~40km x 40km (~80 MB) — activa downsample
"""

import json
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import rasterio
from rasterio.env import Env
from rasterio.windows import Window

WINDOW_SIZE = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
OUTPUT = Path(f"/tmp/sentinel2_chaco_{WINDOW_SIZE}px.tif")

# Claves de asset en Earth Search → posición en el GeoTIFF de salida (1-indexed)
# El pipeline usa sentinel2: BLUE=2, GREEN=3, RED=4, RE=5, NIR=8
BANDAS = {
    "blue":      2,   # B02
    "green":     3,   # B03
    "red":       4,   # B04
    "rededge1":  5,   # B05 — Red Edge 705nm
    "nir":       8,   # B08 — NIR 842nm
}


def consultar_stac(bbox: str, max_nubes: int = 30) -> dict:
    url = (
        "https://earth-search.aws.element84.com/v1"
        f"/collections/sentinel-2-l2a/items"
        f"?bbox={bbox}&limit=20&sortby=-properties.datetime"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "agronexo/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        catalog = json.loads(resp.read())

    features = catalog.get("features", [])
    if not features:
        raise RuntimeError(f"Sin escenas para bbox={bbox}")

    # La más reciente con poca nubosidad
    for f in features:
        if f["properties"].get("eo:cloud_cover", 100) <= max_nubes:
            return f
    return features[0]  # fallback: la más reciente sin importar nubes


def leer_banda_remota(url: str, bbox_wgs84: tuple, window_size: int) -> tuple[np.ndarray, dict]:
    """
    Lee la ventana del COG que corresponde al bbox geográfico dado.
    Transforma el bbox de WGS84 al CRS nativo del COG (UTM) antes de calcular
    la ventana — así siempre leemos los píxeles correctos sin importar el tamaño
    del tile ni la posición del área de interés dentro de él.
    """
    from rasterio.crs import CRS
    from rasterio.warp import transform_bounds
    from rasterio.windows import from_bounds as window_from_bounds

    with rasterio.open(url) as src:
        # Pasar bbox de WGS84 al CRS nativo del COG (normalmente UTM)
        bbox_nativo = transform_bounds(CRS.from_epsg(4326), src.crs, *bbox_wgs84)
        win = window_from_bounds(*bbox_nativo, transform=src.transform)

        data = src.read(
            1,
            window=win,
            out_shape=(window_size, window_size),
            resampling=rasterio.enums.Resampling.bilinear,
        ).astype(np.float32)

        meta = {
            "transform": src.window_transform(win),
            "crs": src.crs,
        }
    return data, meta


def main():
    t0 = time.perf_counter()

    # Zona agrícola pura — Hermoso Campo / General Pinedo, Chaco.
    # Campos de soja, algodón, maíz y sorgo. Sin ciudad.
    # Bbox elegido dentro del tile S2B_20JQR (0.005% nubes, 2026-08-03)
    # cuyo footprint cubre [-60.97,-27.20,-59.87,-26.19].
    bbox = "-60.85,-27.15,-60.25,-26.65"

    print("Consultando Earth Search (AWS STAC API)...")
    print(f"  Área: Chaco, Argentina — {bbox}")
    try:
        item = consultar_stac(bbox)
    except Exception as e:
        print(f"ERROR consultando STAC: {e}")
        print("Verificá que el worker tenga acceso a internet.")
        return

    print(f"  Escena: {item['id']}")
    print(f"  Fecha:  {item['properties']['datetime'][:10]}")
    print(f"  Nubes:  {item['properties'].get('eo:cloud_cover', '?')}%")

    assets = item["assets"]
    arrays: dict[int, np.ndarray] = {}
    meta_ref: dict | None = None

    # Configurar GDAL para leer COGs remotos vía HTTPS
    bbox_wgs84 = tuple(float(x) for x in bbox.split(","))  # (xmin, ymin, xmax, ymax)

    with Env(GDAL_HTTP_TIMEOUT="30", GDAL_HTTP_CONNECTTIMEOUT="10", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif"):
        for band_s2, pos_out in BANDAS.items():
            asset = assets.get(band_s2, {})
            url = asset.get("href", "")
            if not url:
                print(f"  {band_s2}: no encontrada en assets")
                continue

            print(f"  Descargando {band_s2} → posición {pos_out}... ", end="", flush=True)
            tb = time.perf_counter()
            try:
                data, meta = leer_banda_remota(url, bbox_wgs84, WINDOW_SIZE)
                # Reflectancia L2A: dividir por 10000 (escala estándar Sentinel-2)
                data = np.clip(data / 10_000.0, 0.0, 1.0).astype(np.float32)
                arrays[pos_out] = data
                if meta_ref is None:
                    meta_ref = meta
                print(f"OK ({time.perf_counter()-tb:.1f}s) — rango [{data.min():.3f}, {data.max():.3f}]")
            except Exception as e:
                print(f"ERROR: {e}")

    if not arrays or meta_ref is None:
        print("No se pudo descargar ninguna banda. Verificá conectividad.")
        return

    # Crear GeoTIFF de 8 bandas (posiciones sin datos quedan en cero)
    out = np.zeros((8, WINDOW_SIZE, WINDOW_SIZE), dtype=np.float32)
    for pos, arr in arrays.items():
        out[pos - 1] = arr

    print(f"\nEscribiendo GeoTIFF ({WINDOW_SIZE}×{WINDOW_SIZE} px, 8 bandas)...")
    with rasterio.open(
        OUTPUT, "w",
        driver="GTiff",
        dtype="float32",
        width=WINDOW_SIZE,
        height=WINDOW_SIZE,
        count=8,
        crs=meta_ref["crs"],
        transform=meta_ref["transform"],
        compress="lzw",
        tiled=True,
        blockxsize=512,
        blockysize=512,
    ) as dst:
        for i in range(8):
            dst.write(out[i], i + 1)

    size_mb = OUTPUT.stat().st_size / 1_048_576
    res_km = WINDOW_SIZE * 10 / 1000
    print(f"\n✓ Archivo: {OUTPUT}")
    print(f"  Tamaño:  {size_mb:.1f} MB")
    print(f"  Área:    ~{res_km:.0f} km × {res_km:.0f} km a resolución 10m")
    print(f"  Tiempo:  {time.perf_counter()-t0:.1f}s")
    print(f"\nCopiar a Windows:")
    print(f"  docker compose cp worker:{OUTPUT} .")
    print(f"\nSubir con sensor: sentinel2")


if __name__ == "__main__":
    main()
