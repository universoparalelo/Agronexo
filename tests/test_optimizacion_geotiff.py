"""
Tests de workers/gis/tasks.py::_optimizar_si_necesario, que reescribe un GeoTIFF
por líneas y sin compresión a tiles de 512×512 con DEFLATE.

Lo que importa es que el resultado tenga exactamente los mismos píxeles que el
original: leer por franjas y comprimir con varios hilos solo cambia la velocidad.

Correr en el contenedor worker:
    docker compose exec worker python3 -m pytest tests/test_optimizacion_geotiff.py -v

Correr en CI o local (con las dependencias del worker):
    PYTHONPATH=$(pwd) python3 -m pytest tests/test_optimizacion_geotiff.py -v
"""
import os

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from workers.gis import tasks

_FORMAS = [(1300, 1100), (300, 100), (512, 512), (513, 513), (1024, 70)]


def _datos(ancho, alto, bandas, dtype):
    rng = np.random.default_rng(42)
    if np.dtype(dtype).kind == "f":
        return rng.random((bandas, alto, ancho), dtype=np.float32).astype(dtype)
    maximo = np.iinfo(dtype).max
    return rng.integers(0, maximo, size=(bandas, alto, ancho), dtype=dtype)


def _crear(ruta, datos, **perfil):
    bandas, alto, ancho = datos.shape
    base = dict(
        driver="GTiff", width=ancho, height=alto, count=bandas, dtype=datos.dtype,
        crs="EPSG:4326", transform=from_origin(-60.0, -27.0, 0.0001, 0.0001),
    )
    base.update(perfil)
    with rasterio.open(ruta, "w", **base) as dst:
        dst.write(datos)


def _por_lineas(ruta, datos):
    _crear(ruta, datos, tiled=False, blockysize=1)


@pytest.mark.parametrize("dtype", ["uint8", "uint16", "float32"])
@pytest.mark.parametrize("ancho,alto", _FORMAS)
def test_el_resultado_tiene_los_mismos_pixeles(tmp_path, dtype, ancho, alto):
    ruta = str(tmp_path / "entrada.tif")
    datos = _datos(ancho, alto, 4, dtype)
    _por_lineas(ruta, datos)
    with rasterio.open(ruta) as src:
        crs, transform = src.crs, src.transform

    resultado = tasks._optimizar_si_necesario(ruta)

    with rasterio.open(resultado) as dst:
        assert np.array_equal(dst.read(), datos)
        assert dst.crs == crs
        assert dst.transform == transform
        assert (dst.count, dst.width, dst.height) == (4, ancho, alto)
        assert dst.dtypes[0] == dtype
    print(f"✓ {dtype} {ancho}x{alto}: mismos píxeles, mismo CRS y misma georreferencia")


def test_el_destino_queda_tileado_y_comprimido(tmp_path):
    ruta = str(tmp_path / "entrada.tif")
    _por_lineas(ruta, _datos(700, 600, 4, "uint8"))

    resultado = tasks._optimizar_si_necesario(ruta)

    with rasterio.open(resultado) as dst:
        assert dst.profile["tiled"] is True
        assert dst.profile["compress"].lower() == "deflate"
        assert dst.block_shapes[0] == (512, 512)


def test_borra_el_original_y_devuelve_el_archivo_nuevo(tmp_path):
    ruta = str(tmp_path / "entrada.tif")
    _por_lineas(ruta, _datos(600, 600, 4, "uint8"))

    resultado = tasks._optimizar_si_necesario(ruta)

    assert resultado == ruta + ".opt.tif"
    assert os.path.exists(resultado)
    assert not os.path.exists(ruta)


def test_un_archivo_ya_tileado_y_comprimido_no_se_toca(tmp_path):
    ruta = str(tmp_path / "entrada.tif")
    _crear(ruta, _datos(600, 600, 4, "uint8"), tiled=True, blockxsize=256, blockysize=256, compress="deflate")

    resultado = tasks._optimizar_si_necesario(ruta)

    assert resultado == ruta
    assert os.path.exists(ruta)
    assert not os.path.exists(ruta + ".opt.tif")


def test_lee_por_franjas_y_si_la_franja_es_enorme_vuelve_a_leer_por_mosaicos(tmp_path, monkeypatch):
    llamadas = []
    ventana_real = tasks.Window
    monkeypatch.setattr(tasks, "Window", lambda *a, **kw: llamadas.append(a) or ventana_real(*a, **kw))
    datos = _datos(1300, 1100, 4, "uint8")

    ruta = str(tmp_path / "a.tif")
    _por_lineas(ruta, datos)
    resultado = tasks._optimizar_si_necesario(ruta)
    with rasterio.open(resultado) as dst:
        assert np.array_equal(dst.read(), datos)
    assert len(llamadas) == 3   # 1100 líneas = franjas de 512, 512 y 76

    llamadas.clear()
    monkeypatch.setattr(tasks, "_OPT_FRANJA_MAX_BYTES", 1)
    ruta = str(tmp_path / "b.tif")
    _por_lineas(ruta, datos)
    resultado = tasks._optimizar_si_necesario(ruta)
    with rasterio.open(resultado) as dst:
        assert np.array_equal(dst.read(), datos)
    assert llamadas == []       # no se armaron franjas: se leyó mosaico por mosaico
    print("✓ por franjas con memoria normal; por mosaicos si la franja supera el tope")


def test_pide_a_gdal_comprimir_con_los_hilos_configurados(tmp_path, monkeypatch):
    abrir = rasterio.open
    creaciones = []

    def espia(*args, **kwargs):
        if (len(args) > 1 and args[1] == "w") or kwargs.get("mode") == "w":
            creaciones.append(kwargs)
        return abrir(*args, **kwargs)

    monkeypatch.setattr(rasterio, "open", espia)
    ruta = str(tmp_path / "entrada.tif")
    _por_lineas(ruta, _datos(600, 600, 4, "uint8"))
    creaciones.clear()   # descarta la creación del archivo de prueba

    tasks._optimizar_si_necesario(ruta)

    assert [c.get("num_threads") for c in creaciones] == [str(tasks._OPT_NUM_THREADS)]
    assert tasks._OPT_NUM_THREADS == 2
    print("✓ la compresión usa _OPT_NUM_THREADS (2) hilos")
