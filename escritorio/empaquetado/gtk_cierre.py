"""
Calcula qué DLL de GTK necesitan WeasyPrint y Pango y las copia a una carpeta propia.

Recorre las importaciones de cada DLL (formato PE) a partir de las que WeasyPrint carga
(gobject, pango, harfbuzz, fontconfig) y se queda solo con las que existen en la
instalación de GTK; las demás son de Windows. Uso: gtk_cierre.py <carpeta bin de GTK> <destino>
"""
import os
import shutil
import struct
import sys

RAICES = ["libgobject-2.0-0", "libpango-1.0-0", "libharfbuzz-0", "libharfbuzz-subset-0",
          "libfontconfig-1", "libpangoft2-1.0-0"]


def importadas(ruta):
    with open(ruta, "rb") as f:
        datos = f.read()
    pe = struct.unpack_from("<I", datos, 0x3C)[0]
    nsec = struct.unpack_from("<H", datos, pe + 6)[0]
    tam_opt = struct.unpack_from("<H", datos, pe + 20)[0]
    opt = pe + 24
    magia = struct.unpack_from("<H", datos, opt)[0]
    dir_import = opt + (112 if magia == 0x20B else 96) + 8
    rva = struct.unpack_from("<I", datos, dir_import)[0]
    secciones = []
    for i in range(nsec):
        s = opt + tam_opt + i * 40
        vtam, vdir, rtam, rdir = struct.unpack_from("<IIII", datos, s + 8)
        secciones.append((vdir, max(vtam, rtam), rdir))

    def a_archivo(r):
        for vdir, tam, rdir in secciones:
            if vdir <= r < vdir + tam:
                return r - vdir + rdir
        return None

    nombres = []
    pos = a_archivo(rva)
    while pos is not None:
        _, _, _, nombre_rva, _ = struct.unpack_from("<IIIII", datos, pos)
        if nombre_rva == 0:
            break
        ini = a_archivo(nombre_rva)
        nombres.append(datos[ini:datos.index(b"\0", ini)].decode().lower())
        pos += 20
    return nombres


def main(bin_gtk, destino):
    locales = {f.lower(): f for f in os.listdir(bin_gtk) if f.lower().endswith(".dll")}
    vistas, pendientes = {}, [r.lower() + ".dll" for r in RAICES]
    while pendientes:
        nombre = pendientes.pop()
        if nombre in vistas or nombre not in locales:
            continue
        vistas[nombre] = locales[nombre]
        pendientes.extend(importadas(os.path.join(bin_gtk, locales[nombre])))
    os.makedirs(destino, exist_ok=True)
    for original in vistas.values():
        shutil.copy2(os.path.join(bin_gtk, original), os.path.join(destino, original))
    print(f"{len(vistas)} DLL copiadas a {destino}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
