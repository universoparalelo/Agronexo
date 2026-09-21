"""
Tests del pipeline GIS: índices, mapeo de bandas y reproyección.
Correr en el contenedor worker:
    docker compose exec worker env PYTHONPATH=/app python3 tests/test_indices_worker.py
"""

import io

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_bounds


# ── Fixtures ─────────────────────────────────────────────────────────

def _geotiff_multibanda(n_bandas: int, crs: CRS, dtype: str = "float32") -> bytes:
    """GeoTIFF sintético con n bandas, valores secuenciales controlados."""
    buf = io.BytesIO()
    transform = from_bounds(-60.68, -27.48, -60.67, -27.47, 20, 20)
    with rasterio.open(
        buf, "w", driver="GTiff",
        height=20, width=20, count=n_bandas, dtype=dtype,
        crs=crs, transform=transform,
    ) as dst:
        for i in range(1, n_bandas + 1):
            # Valores distintos por banda para poder detectar errores de mapeo
            dst.write(np.full((20, 20), fill_value=0.1 * i, dtype=dtype), i)
    return buf.getvalue()


def _geotiff_grande_con_nodata(n: int, n_bandas: int = 4) -> bytes:
    """
    GeoTIFF sintético NxN con un borde de nodata, para probar la lectura
    decimada de rasters grandes (ver _leer_banda) sin necesitar un archivo
    de varios GB real en CI. n=3100 cruza _UMBRAL_DOWNSAMPLE_PX (9M px).
    """
    buf = io.BytesIO()
    transform = from_bounds(-60.70, -27.50, -60.60, -27.40, n, n)
    with rasterio.open(
        buf, "w", driver="GTiff", height=n, width=n, count=n_bandas,
        dtype="float32", crs=CRS.from_epsg(4326), transform=transform, nodata=-9999.0,
    ) as dst:
        for i in range(1, n_bandas + 1):
            arr = np.full((n, n), fill_value=0.1 * i, dtype="float32")
            borde = 5
            arr[:borde, :] = -9999.0
            arr[-borde:, :] = -9999.0
            arr[:, :borde] = -9999.0
            arr[:, -borde:] = -9999.0
            dst.write(arr, i)
    return buf.getvalue()


def _geotiff_utm() -> bytes:
    """GeoTIFF con CRS UTM zona 21 Sur (EPSG:32721) para probar reproyección."""
    buf = io.BytesIO()
    from rasterio.transform import from_origin
    transform = from_origin(3_500_000, 7_000_000, 10, 10)  # metros
    with rasterio.open(
        buf, "w", driver="GTiff",
        height=20, width=20, count=2, dtype="float32",
        crs=CRS.from_epsg(32721), transform=transform,
    ) as dst:
        dst.write(np.full((20, 20), 0.8, dtype="float32"), 1)  # NIR
        dst.write(np.full((20, 20), 0.2, dtype="float32"), 2)  # RED
    return buf.getvalue()


# ── Tests de índices ──────────────────────────────────────────────────

def test_ndvi_valor_conocido():
    from workers.gis.indices import calcular_ndvi

    nir = np.full((5, 5), 0.8, dtype=np.float32)
    red = np.full((5, 5), 0.2, dtype=np.float32)
    resultado = calcular_ndvi(nir, red)
    esperado = (0.8 - 0.2) / (0.8 + 0.2)  # 0.6
    assert np.allclose(resultado, esperado, atol=1e-5), f"NDVI esperado {esperado:.4f}, got {resultado[0,0]:.4f}"
    print(f"✓ NDVI valor conocido → {resultado[0,0]:.4f} (esperado {esperado:.4f})")


def test_ndvi_division_por_cero():
    from workers.gis.indices import calcular_ndvi

    nir = np.zeros((3, 3), dtype=np.float32)
    red = np.zeros((3, 3), dtype=np.float32)
    resultado = calcular_ndvi(nir, red)
    assert np.all(np.isnan(resultado)), "Píxeles nir+red=0 deben ser NaN"
    print("✓ NDVI denominador cero → NaN (sin excepción)")


def test_ndre_rango_valido():
    from workers.gis.indices import calcular_ndre

    nir = np.random.rand(10, 10).astype(np.float32)
    re  = np.random.rand(10, 10).astype(np.float32)
    resultado = calcular_ndre(nir, re)
    validos = resultado[~np.isnan(resultado)]
    assert validos.min() >= -1.0 and validos.max() <= 1.0, "NDRE fuera de rango [-1, 1]"
    print(f"✓ NDRE rango válido → [{validos.min():.3f}, {validos.max():.3f}]")


def test_savi_difiere_de_ndvi():
    """SAVI debe ser diferente a NDVI porque tiene el factor L."""
    from workers.gis.indices import calcular_ndvi, calcular_savi

    nir = np.full((5, 5), 0.6, dtype=np.float32)
    red = np.full((5, 5), 0.2, dtype=np.float32)
    assert not np.allclose(calcular_ndvi(nir, red), calcular_savi(nir, red))
    print("✓ SAVI produce valores distintos a NDVI (factor L aplicado)")


def test_exg_no_requiere_nir():
    from workers.gis.indices import calcular_exg

    green = np.full((5, 5), 0.4, dtype=np.float32)
    red   = np.full((5, 5), 0.2, dtype=np.float32)
    blue  = np.full((5, 5), 0.1, dtype=np.float32)
    resultado = calcular_exg(green, red, blue)
    # normalizado: 2g − r − b = (2G − R − B) / (R + G + B) = 0.5 / 0.7
    esperado = (2 * 0.4 - 0.2 - 0.1) / (0.4 + 0.2 + 0.1)
    assert np.allclose(resultado, esperado, atol=1e-5)
    print(f"✓ ExG normalizado → {resultado[0,0]:.4f} (esperado {esperado:.4f})")


def test_exg_no_depende_del_brillo_ni_de_las_unidades():
    from workers.gis.indices import calcular_exg

    green = np.full((3, 3), 0.07, dtype=np.float32)
    red   = np.full((3, 3), 0.05, dtype=np.float32)
    blue  = np.full((3, 3), 0.04, dtype=np.float32)
    base = calcular_exg(green, red, blue)
    doble_brillo = calcular_exg(green * 2, red * 2, blue * 2)
    dn_8bit = calcular_exg(green * 3600, red * 3600, blue * 3600)   # otra escala de la cámara
    assert np.allclose(base, doble_brillo, atol=1e-5)
    assert np.allclose(base, dn_8bit, atol=1e-4)
    assert 0.05 < base[0, 0] < 0.45   # rango típico de vegetación
    print(f"✓ ExG igual con el doble de brillo y con otras unidades ({base[0,0]:.3f})")


def test_exg_suma_cero_es_nan_y_respeta_nodata():
    from workers.gis.indices import calcular_exg

    verde = np.array([[0.0, 0.07]], dtype=np.float32)
    rojo  = np.array([[0.0, 0.05]], dtype=np.float32)
    azul  = np.array([[0.0, 0.04]], dtype=np.float32)
    resultado = calcular_exg(verde, rojo, azul)
    assert np.isnan(resultado[0, 0]) and not np.isnan(resultado[0, 1])
    con_nodata = calcular_exg(verde, rojo, azul, nodata=0.07)
    assert np.isnan(con_nodata[0, 1])
    print("✓ ExG: R+G+B = 0 → NaN, y nodata enmascarado")


def test_gndvi_valor_conocido():
    from workers.gis.indices import calcular_gndvi

    nir = np.full((5, 5), 0.7, dtype=np.float32)
    green = np.full((5, 5), 0.3, dtype=np.float32)
    resultado = calcular_gndvi(nir, green)
    esperado = (0.7 - 0.3) / (0.7 + 0.3)  # 0.4
    assert np.allclose(resultado, esperado, atol=1e-5), f"GNDVI esperado {esperado:.4f}, got {resultado[0,0]:.4f}"
    print(f"✓ GNDVI valor conocido → {resultado[0,0]:.4f} (esperado {esperado:.4f})")


def test_nodata_se_convierte_en_nan():
    from workers.gis.indices import calcular_ndvi

    nir = np.array([[0.8, -9999.0]], dtype=np.float32)
    red = np.array([[0.2, -9999.0]], dtype=np.float32)
    resultado = calcular_ndvi(nir, red, nodata=-9999.0)
    assert not np.isnan(resultado[0, 0]), "Píxel válido no debe ser NaN"
    assert np.isnan(resultado[0, 1]), "Píxel nodata debe ser NaN"
    print("✓ nodata → NaN correctamente")


# ── Tests de mapeo de bandas ──────────────────────────────────────────

def test_mapeo_sentinel2():
    from workers.gis.band_mapping import numero_banda
    assert numero_banda("sentinel2", "NIR") == 8
    assert numero_banda("sentinel2", "RED") == 4
    assert numero_banda("sentinel2", "RE")  == 5
    print("✓ Mapeo Sentinel-2: NIR=8, RED=4, RE=5")


def test_mapeo_dji():
    from workers.gis.band_mapping import numero_banda
    assert numero_banda("dji_mavic3", "NIR") == 4
    assert numero_banda("dji_mavic3", "RED") == 2
    assert numero_banda("dji_mavic3", "RE")  == 3
    print("✓ Mapeo DJI Mavic 3: NIR=4, RED=2, RE=3 (4 bandas, sin Blue)")


def test_sensor_invalido():
    from workers.gis.band_mapping import obtener_mapeo
    try:
        obtener_mapeo("phantom4")
        assert False, "Debería lanzar ValueError"
    except ValueError as e:
        print(f"✓ Sensor inválido → ValueError: {e}")


def test_bandas_insuficientes():
    from workers.gis.band_mapping import validar_bandas_disponibles
    try:
        # sentinel2 necesita banda NIR=8 para NDVI pero el archivo solo tiene 2
        validar_bandas_disponibles("sentinel2", "ndvi", n_bandas_archivo=2)
        assert False, "Debería lanzar ValueError"
    except ValueError as e:
        assert "banda" in str(e).lower()
        print(f"✓ Bandas insuficientes → ValueError: {e}")


# ── Tests de reproyección ─────────────────────────────────────────────

def test_reproyeccion_utm_a_4326():
    from workers.gis.reproyeccion import reproyectar_a_4326

    data_utm = _geotiff_utm()
    data_4326 = reproyectar_a_4326(data_utm)

    with rasterio.open(io.BytesIO(data_4326)) as src:
        assert src.crs == CRS.from_epsg(4326), f"CRS esperado EPSG:4326, got {src.crs}"
        assert src.count == 2
    print("✓ Reproyección UTM→4326 correcta, bandas preservadas")


def test_4326_no_reproyecta():
    from workers.gis.reproyeccion import reproyectar_a_4326

    data = _geotiff_multibanda(2, CRS.from_epsg(4326))
    resultado = reproyectar_a_4326(data)
    assert resultado == data, "GeoTIFF ya en 4326 no debe modificarse"
    print("✓ GeoTIFF ya en EPSG:4326 → devuelve bytes originales sin modificar")


# ── Tests del pipeline completo ───────────────────────────────────────

def test_pipeline_ndvi_dji():
    import tempfile
    from workers.gis.pipeline import ejecutar_pipeline

    # DJI Mavic3 real: 4 bandas, sin Blue — G=1, R=2, RE=3, NIR=4
    data = _geotiff_multibanda(4, CRS.from_epsg(4326))
    with tempfile.NamedTemporaryFile(suffix=".geojson", delete=False) as tmp:
        stats = ejecutar_pipeline(data, sensor="dji_mavic3", indice="ndvi", geojson_destino=tmp.name)

    assert stats["indice"] == "ndvi"
    assert stats["sensor"] == "dji_mavic3"
    assert "ndvi_promedio_lote" in stats
    print(f"✓ Pipeline NDVI DJI → {stats['total_poligonos']} polígonos, NDVI prom={stats['ndvi_promedio_lote']}")


def test_pipeline_savi_sentinel2():
    import tempfile
    from workers.gis.pipeline import ejecutar_pipeline

    # Sentinel-2 tiene 8+ bandas; usamos 8 para cubrir NIR=8
    data = _geotiff_multibanda(8, CRS.from_epsg(4326))
    with tempfile.NamedTemporaryFile(suffix=".geojson", delete=False) as tmp:
        stats = ejecutar_pipeline(data, sensor="sentinel2", indice="savi", geojson_destino=tmp.name)

    assert stats["indice"] == "savi"
    print(f"✓ Pipeline SAVI Sentinel-2 → {stats['total_poligonos']} polígonos")


def _archivo_temporal(data: bytes) -> str:
    import tempfile
    tmp = tempfile.NamedTemporaryFile(suffix=".tif", delete=False)
    tmp.write(data)
    tmp.close()
    return tmp.name


def test_lectura_decimada_raster_grande_no_materializa_resolucion_completa():
    """
    Un raster por encima de _UMBRAL_DOWNSAMPLE_PX debe leerse ya decimado
    por GDAL (out_shape + Resampling.average) en vez de leerse completo y
    reducirse después en NumPy — así se evita materializar en RAM un array
    a resolución completa que, en un GeoTIFF real de varios GB, puede tirar
    el worker por out-of-memory. También verifica que el nodata del borde
    no contamine el promedio con el valor crudo del sentinel.
    """
    from workers.gis.pipeline import _UMBRAL_DOWNSAMPLE_PX, _factor_downsample, _leer_banda

    n = 3100  # 3100x3100 = 9.61M px > 9M -> factor=2
    assert n * n > _UMBRAL_DOWNSAMPLE_PX

    data = _geotiff_grande_con_nodata(n)
    path = _archivo_temporal(data)

    with rasterio.open(path) as src:
        factor = _factor_downsample((src.height, src.width))
        assert factor == 2, f"factor esperado 2, dio {factor}"
        banda = _leer_banda(src, 1, factor)  # banda 1 -> valor de relleno 0.1

    assert banda.shape == (n // factor, n // factor)
    assert not np.any(banda == -9999.0), "el nodata crudo no debe filtrarse en el promedio decimado"
    interior = banda[10:-10, 10:-10]
    assert np.allclose(interior, 0.1, atol=1e-4), f"interior esperado ~0.1, dio min={interior.min()} max={interior.max()}"
    print(f"✓ Lectura decimada x{factor}: {n}x{n} → {banda.shape}, sin materializar resolución completa ni filtrar nodata crudo")


def test_lectura_decimada_dtype_entero_no_falla():
    """
    Bandas con dtype entero (uint8/uint16 — DN crudo típico de dron/satélite
    sin calibrar a reflectancia) no deben fallar al decimar. Bug real
    encontrado con un archivo de producción: el cast a float32 tiene que
    pasar ANTES de rellenar con NaN, porque un array entero no puede
    representar NaN (`np.ma.filled` lanza TypeError si se hace al revés).
    """
    from workers.gis.pipeline import _factor_downsample, _leer_banda

    n = 3100  # cruza el umbral de downsample -> fuerza la lectura decimada
    buf = io.BytesIO()
    transform = from_bounds(-60.70, -27.50, -60.60, -27.40, n, n)
    with rasterio.open(
        buf, "w", driver="GTiff", height=n, width=n, count=1,
        dtype="uint8", crs=CRS.from_epsg(4326), transform=transform, nodata=0,
    ) as dst:
        arr = np.full((n, n), fill_value=100, dtype="uint8")
        arr[:5, :] = 0  # borde nodata
        dst.write(arr, 1)
    path = _archivo_temporal(buf.getvalue())

    with rasterio.open(path) as src:
        factor = _factor_downsample((src.height, src.width))
        banda = _leer_banda(src, 1, factor)  # no debe lanzar TypeError

    assert banda.dtype == np.float32
    interior = banda[10:-10, 10:-10]
    assert np.allclose(interior, 100, atol=1.0), f"interior esperado ~100, dio min={interior.min()} max={interior.max()}"
    print(f"✓ Lectura decimada con dtype entero (uint8) no falla → banda.dtype={banda.dtype}")


def test_pipeline_archivo_grande_completa_sin_cargar_resolucion_completa():
    """Pipeline completo end-to-end sobre un raster por encima del umbral —
    confirma que ejecutar_pipeline_archivo no intenta calcular el índice
    sobre la resolución original (fallaría/tardaría mucho en un raster real
    de varios GB) sino sobre la ya decimada."""
    import tempfile
    from workers.gis.pipeline import ejecutar_pipeline_archivo

    n = 3100
    data = _geotiff_grande_con_nodata(n, n_bandas=4)  # dji_mavic3: G=1,R=2,RE=3,NIR=4
    with tempfile.NamedTemporaryFile(suffix=".geojson", delete=False) as tmp:
        stats = ejecutar_pipeline_archivo(
            _archivo_temporal(data), sensor="dji_mavic3", indice="ndvi", geojson_destino=tmp.name,
        )

    # NIR=0.4, RED=0.2 -> ndvi = (0.4-0.2)/(0.4+0.2) = 0.3333
    assert abs(stats["ndvi_promedio_lote"] - 0.3333) < 0.01
    print(f"✓ Pipeline en raster grande ({n}x{n}) completó sin cargar resolución completa → NDVI prom={stats['ndvi_promedio_lote']}")


def test_pipeline_multi_indice_bandas_compartidas():
    """El modo batch (que comparte NIR/RED entre índices en vez de releerlas
    por cada uno) debe dar exactamente el mismo resultado que llamar al
    pipeline individual una vez por índice."""
    import tempfile
    from workers.gis.pipeline import ejecutar_pipeline_archivo, ejecutar_pipeline_multi_indice_archivo

    data = _geotiff_multibanda(8, CRS.from_epsg(4326))  # sentinel2: NIR=8, RED=4

    with tempfile.NamedTemporaryFile(suffix=".geojson", delete=False) as tmp:
        stats_ndvi_individual = ejecutar_pipeline_archivo(
            _archivo_temporal(data), sensor="sentinel2", indice="ndvi", geojson_destino=tmp.name,
        )
    with tempfile.NamedTemporaryFile(suffix=".geojson", delete=False) as tmp:
        stats_savi_individual = ejecutar_pipeline_archivo(
            _archivo_temporal(data), sensor="sentinel2", indice="savi", geojson_destino=tmp.name,
        )

    geojson_ndvi = tempfile.NamedTemporaryFile(suffix=".geojson", delete=False)
    geojson_ndvi.close()
    geojson_savi = tempfile.NamedTemporaryFile(suffix=".geojson", delete=False)
    geojson_savi.close()
    resultados = ejecutar_pipeline_multi_indice_archivo(
        _archivo_temporal(data), sensor="sentinel2", indices=["ndvi", "savi"],
        geojson_destino_por_indice={"ndvi": geojson_ndvi.name, "savi": geojson_savi.name},
    )

    assert resultados["ndvi"]["ndvi_promedio_lote"] == stats_ndvi_individual["ndvi_promedio_lote"]
    assert resultados["ndvi"]["total_poligonos"] == stats_ndvi_individual["total_poligonos"]
    assert resultados["savi"]["savi_promedio_lote"] == stats_savi_individual["savi_promedio_lote"]
    assert resultados["savi"]["total_poligonos"] == stats_savi_individual["total_poligonos"]
    print("✓ Batch multi-índice (bandas compartidas) → mismos resultados que pipeline individual por índice")


def test_pipeline_multi_indice_error_no_aborta_batch():
    """Un índice que falla dentro del batch (banda no disponible para el
    sensor) no debe impedir que los demás índices de la lista se calculen."""
    import tempfile
    from workers.gis.pipeline import ejecutar_pipeline_multi_indice_archivo

    # DJI Mavic3 real: 4 bandas, sin Blue — ExG la necesita y debe fallar,
    # NDVI no la necesita y debe completarse igual.
    data = _geotiff_multibanda(4, CRS.from_epsg(4326))

    geojson_ndvi = tempfile.NamedTemporaryFile(suffix=".geojson", delete=False)
    geojson_ndvi.close()
    geojson_exg = tempfile.NamedTemporaryFile(suffix=".geojson", delete=False)
    geojson_exg.close()

    completados, errores = [], []
    resultados = ejecutar_pipeline_multi_indice_archivo(
        _archivo_temporal(data), sensor="dji_mavic3", indices=["ndvi", "exg"],
        geojson_destino_por_indice={"ndvi": geojson_ndvi.name, "exg": geojson_exg.name},
        on_indice_completado=lambda i, s: completados.append(i),
        on_indice_error=lambda i, exc: errores.append(i),
    )

    assert "ndvi" in resultados and "exg" not in resultados
    assert completados == ["ndvi"]
    assert errores == ["exg"]
    print("✓ Batch multi-índice: ExG sin banda Blue falla sin abortar el resto — NDVI se calculó igual")


if __name__ == "__main__":
    print("\n── Índices ──────────────────────────────────────────")
    test_ndvi_valor_conocido()
    test_ndvi_division_por_cero()
    test_ndre_rango_valido()
    test_savi_difiere_de_ndvi()
    test_exg_no_requiere_nir()
    test_exg_no_depende_del_brillo_ni_de_las_unidades()
    test_exg_suma_cero_es_nan_y_respeta_nodata()
    test_gndvi_valor_conocido()
    test_nodata_se_convierte_en_nan()

    print("\n── Mapeo de bandas ──────────────────────────────────")
    test_mapeo_sentinel2()
    test_mapeo_dji()
    test_sensor_invalido()
    test_bandas_insuficientes()

    print("\n── Reproyección ─────────────────────────────────────")
    test_reproyeccion_utm_a_4326()
    test_4326_no_reproyecta()

    print("\n── Pipeline completo ────────────────────────────────")
    test_pipeline_ndvi_dji()
    test_pipeline_savi_sentinel2()

    print("\n── Lectura decimada (rasters grandes) ────────────────")
    test_lectura_decimada_raster_grande_no_materializa_resolucion_completa()
    test_lectura_decimada_dtype_entero_no_falla()
    test_pipeline_archivo_grande_completa_sin_cargar_resolucion_completa()

    print("\n── Pipeline batch multi-índice ───────────────────────")
    test_pipeline_multi_indice_bandas_compartidas()
    test_pipeline_multi_indice_error_no_aborta_batch()

    print("\nTodos los tests pasaron.\n")
