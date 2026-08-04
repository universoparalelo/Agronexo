"""
Genera un GeoTIFF multibanda sintético para probar el pipeline.

Simula un campo agrícola real con 4 zonas de vegetación y ruido espacial.
Formato: DJI Mavic 3 Multispectral (4 bandas: Green, Red, RedEdge, NIR).

Uso desde el contenedor worker:
    python3 scripts/generar_geotiff_prueba.py [tamaño_px]

Ejemplos:
    python3 scripts/generar_geotiff_prueba.py 500     # pequeño, ~1 MB
    python3 scripts/generar_geotiff_prueba.py 3000    # mediano, sin downsample
    python3 scripts/generar_geotiff_prueba.py 5000    # grande, activa downsample
    python3 scripts/generar_geotiff_prueba.py 10000   # muy grande, ~400 MB
"""
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_bounds

SIZE = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
OUTPUT = Path(f"/tmp/campo_prueba_{SIZE}px.tif")

print(f"Generando GeoTIFF {SIZE}×{SIZE} px (DJI Mavic 3, 4 bandas)...")
t0 = time.perf_counter()

rng = np.random.default_rng(42)

# --- Coordenadas: lote ficticio en el Chaco argentino ---
# Campo de ~1000 ha centrado en Roque Sáenz Peña, Chaco
lon_min, lat_min = -60.55, -26.85
lon_max, lat_max = -60.45, -26.75

transform = from_bounds(lon_min, lat_min, lon_max, lat_max, SIZE, SIZE)
crs = CRS.from_epsg(4326)

# --- Simular 4 zonas de vegetación con gradientes suaves ---
y, x = np.mgrid[0:SIZE, 0:SIZE]
yf = y / SIZE
xf = x / SIZE

# Zona 1: cultivo vigoroso (NDVI ~0.75) — mitad superior izquierda
vigor = np.clip(0.80 - 0.15 * ((xf - 0.2)**2 + (yf - 0.2)**2) * 10, 0.60, 0.85)

# Zona 2: cultivo normal (NDVI ~0.50) — mitad inferior derecha
normal = np.clip(0.55 - 0.10 * ((xf - 0.8)**2 + (yf - 0.8)**2) * 10, 0.40, 0.65)

# Zona 3: estrés hídrico (NDVI ~0.30) — franja central
estres = np.clip(0.30 - 0.08 * np.abs(xf - 0.5) * 5, 0.20, 0.40)

# Zona 4: suelo expuesto (NDVI ~0.10) — esquina inferior izquierda
suelo = np.clip(0.10 + 0.05 * xf, 0.05, 0.18)

# Combinar zonas según posición en el campo
ndvi_base = np.where(
    (xf < 0.45) & (yf < 0.45), vigor,
    np.where(
        (xf > 0.55) & (yf > 0.55), normal,
        np.where(
            np.abs(xf - 0.5) < 0.15, estres,
            suelo
        )
    )
).astype(np.float32)

# Agregar ruido espacial realista (gradiente continuo, no bloques)
ruido = rng.normal(0, 0.03, (SIZE, SIZE)).astype(np.float32)
ndvi = np.clip(ndvi_base + ruido, -0.1, 1.0)

# --- Convertir NDVI a reflectancias de bandas (DJI Mavic 3: G, R, RE, NIR) ---
# NDVI = (NIR - RED) / (NIR + RED)
# Asumimos reflectancia RED base + NIR derivada del NDVI objetivo
red = rng.uniform(0.05, 0.15, (SIZE, SIZE)).astype(np.float32)
# NIR = RED * (1 + NDVI) / (1 - NDVI)
with np.errstate(invalid="ignore", divide="ignore"):
    nir = np.where(ndvi < 0.99, red * (1 + ndvi) / (1 - ndvi), 0.9)
nir = np.clip(nir, 0.0, 1.0).astype(np.float32)

# Green y RedEdge correlacionados con NIR (valores realistas para Mavic 3)
green = np.clip(red * 1.2 + rng.normal(0, 0.02, (SIZE, SIZE)), 0.0, 1.0).astype(np.float32)
re = np.clip((red + nir) / 2 + rng.normal(0, 0.01, (SIZE, SIZE)), 0.0, 1.0).astype(np.float32)

print(f"  Arrays generados: {time.perf_counter()-t0:.1f}s")
print(f"  NDVI sintético — min: {float(ndvi.min()):.3f}, max: {float(ndvi.max()):.3f}, promedio: {float(ndvi.mean()):.3f}")

# --- Escribir GeoTIFF ---
perfil = {
    "driver": "GTiff",
    "dtype": "float32",
    "width": SIZE,
    "height": SIZE,
    "count": 4,           # Green=1, Red=2, RedEdge=3, NIR=4
    "crs": crs,
    "transform": transform,
    "compress": "lzw",    # compresión sin pérdida — reduce tamaño en disco
    "tiled": True,
    "blockxsize": 512,
    "blockysize": 512,
}

with rasterio.open(OUTPUT, "w", **perfil) as dst:
    dst.write(green, 1)   # Green
    dst.write(red,   2)   # Red
    dst.write(re,    3)   # RedEdge
    dst.write(nir,   4)   # NIR

size_mb = OUTPUT.stat().st_size / 1_048_576
print(f"  Archivo generado: {OUTPUT}")
print(f"  Tamaño en disco: {size_mb:.1f} MB")
print(f"  Tiempo total: {time.perf_counter()-t0:.1f}s")
print()
print("Para copiarlo a Windows:")
print(f"  docker compose cp worker:{OUTPUT} .")
