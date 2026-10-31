"""
Tests de app/core/gtk.py: registro de las DLL de GTK cuando la API corre
empaquetada en Windows, y de la fuente del mapa del PDF.

No necesitan GTK ni WeasyPrint: se simula el entorno.
"""
import sys

import pytest

from app.core import gtk
from app.reportes import mapa


@pytest.fixture(autouse=True)
def estado_limpio(monkeypatch):
    monkeypatch.setattr(gtk, "_preparado", False)
    monkeypatch.delenv("FONTCONFIG_PATH", raising=False)


@pytest.fixture
def carpeta_gtk(tmp_path, monkeypatch):
    (tmp_path / "gtk" / "etc" / "fonts").mkdir(parents=True)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "agronexo-api.exe"))
    return tmp_path / "gtk"


@pytest.fixture
def registradas(monkeypatch):
    llamadas = []
    monkeypatch.setattr(gtk.os, "add_dll_directory", lambda ruta: llamadas.append(ruta), raising=False)
    return llamadas


def test_no_hace_nada_si_no_esta_empaquetado(carpeta_gtk, registradas, monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setattr(gtk.os, "name", "nt")

    gtk.preparar_gtk_empaquetado()

    assert registradas == []


def test_no_hace_nada_fuera_de_windows(carpeta_gtk, registradas, monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(gtk.os, "name", "posix")

    gtk.preparar_gtk_empaquetado()

    assert registradas == []


def test_no_hace_nada_si_falta_la_carpeta_gtk(tmp_path, registradas, monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "agronexo-api.exe"))
    monkeypatch.setattr(gtk.os, "name", "nt")

    gtk.preparar_gtk_empaquetado()

    assert registradas == []


def test_registra_las_dll_y_la_configuracion_de_fuentes(carpeta_gtk, registradas, monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(gtk.os, "name", "nt")

    gtk.preparar_gtk_empaquetado()

    assert registradas == [str(carpeta_gtk)]
    assert gtk.os.environ["FONTCONFIG_PATH"] == str(carpeta_gtk / "etc" / "fonts")


def test_registra_una_sola_vez(carpeta_gtk, registradas, monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(gtk.os, "name", "nt")

    gtk.preparar_gtk_empaquetado()
    gtk.preparar_gtk_empaquetado()

    assert len(registradas) == 1


def test_no_pisa_un_fontconfig_path_ya_definido(carpeta_gtk, registradas, monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(gtk.os, "name", "nt")
    monkeypatch.setenv("FONTCONFIG_PATH", "otra/carpeta")

    gtk.preparar_gtk_empaquetado()

    assert gtk.os.environ["FONTCONFIG_PATH"] == "otra/carpeta"


def test_fuente_del_mapa_usa_la_de_windows_si_no_hay_dejavu(tmp_path, monkeypatch):
    pedidas = []

    def truetype(ruta, size):
        pedidas.append(ruta)
        if ruta.endswith("segoeui.ttf"):
            return "fuente-segoe"
        raise OSError

    monkeypatch.setattr(mapa, "_FONT_PATH", str(tmp_path / "no-existe.ttf"))
    monkeypatch.setattr(mapa, "_FONTS_WINDOWS", (tmp_path / "segoeui.ttf", tmp_path / "arial.ttf"))
    monkeypatch.setattr(mapa.ImageFont, "truetype", truetype)

    assert mapa._cargar_fuente() == "fuente-segoe"
    assert len(pedidas) == 2


def test_fuente_del_mapa_cae_a_la_de_pillow_si_no_hay_ninguna(tmp_path, monkeypatch):
    monkeypatch.setattr(mapa, "_FONT_PATH", str(tmp_path / "a.ttf"))
    monkeypatch.setattr(mapa, "_FONTS_WINDOWS", (tmp_path / "b.ttf",))

    assert mapa._cargar_fuente() is not None
