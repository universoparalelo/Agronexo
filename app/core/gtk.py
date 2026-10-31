import os
import sys
from pathlib import Path

_preparado = False


def preparar_gtk_empaquetado() -> None:
    """Deja a WeasyPrint encontrar las DLL de GTK cuando la API corre empaquetada.

    En Windows las DLL viajan en la carpeta `gtk` junto al ejecutable. WeasyPrint
    registra sus carpetas de búsqueda solo si el programa no está congelado
    (weasyprint/text/ffi.py), y las carga sin mirar el PATH, así que acá se
    registra la carpeta a mano. Hay que llamarla antes de importar weasyprint.
    Fuera de un ejecutable de Windows no hace nada.
    """
    global _preparado
    if _preparado or os.name != "nt" or not getattr(sys, "frozen", False):
        return
    carpeta = Path(sys.executable).resolve().parent / "gtk"
    if not carpeta.is_dir():
        return
    os.add_dll_directory(str(carpeta))
    os.environ.setdefault("FONTCONFIG_PATH", str(carpeta / "etc" / "fonts"))
    _preparado = True
