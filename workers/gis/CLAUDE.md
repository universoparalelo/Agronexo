# Procesamiento GIS — pipeline

```
GeoTIFF (Sentinel-2 / DJI Mavic 3 Multispectral)
    ↓ Rasterio (windowed reading para archivos > 500 MB)
Extracción de bandas → matrices NumPy
    ↓ NumPy
Cálculo de índice (NDVI, SAVI, GNDVI, etc.)
    ↓ scipy.ndimage.gaussian_filter (sigma=1px, NaN-safe) — `suavizar_indice()`
Suavizado espacial → evita fragmentación "sal y pimienta" al clasificar gradientes continuos
    ↓ scikit-image (Otsu)
Umbralización → máscara de píxeles (las estadísticas reportadas usan el valor SIN suavizar)
    ↓ cast a float32 / uint8 (shapes() rechaza float64 e int8)
    ↓ rasterio.features.shapes()  — para archivos > 500 MB usar rasterio.band(src, n) en lugar de src.read() para evitar cargar el array completo en memoria
Vectorización → polígonos
    ↓ GeoPandas + Shapely
gdf.explode() ANTES de filtrar por área — si no, un buffer(0) que fusiona fragmentos en un MultiPolygon deja pasar ruido cuya área total agregada supera el mínimo
    ↓
Filtrado por área mínima (por fragmento individual), simplificación Douglas-Peucker
    ↓
Exportación: GeoJSON (API) / SHP.zip (maquinaria) / ISO-XML (ISOBUS)
```

**Limitación técnica documentada:** DJI Mavic 3 Multispectral no tiene banda SWIR → NDWI convencional (NIR − SWIR) no es calculable. Usar NDWI de McFeeters (Verde − NIR) / (Verde + NIR) como proxy de agua superficial. NDRE como proxy de estrés hídrico foliar.

**Ojo con el DJI Mavic 3 Multispectral real:** captura solo 4 bandas (Green, Red, RedEdge, NIR) — **no tiene banda Blue**. `workers/gis/band_mapping.py` refleja esto (`GREEN=1, RED=2, RE=3, NIR=4`, sin `BLUE`). Por eso el índice `ExG` (que necesita RGB) no está disponible para `sensor="dji_mavic3"` — es una limitación real del sensor, no un bug.

Reglas de índices, umbrales y patrones espaciales: ver `app/diagnostico/CLAUDE.md`.
