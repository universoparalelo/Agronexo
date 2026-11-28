"""
Prescripción en ISO-XML (ISO 11783-10, "TASKDATA"), el formato ISOBUS que
leen los monitores de pulverizadoras de distintas marcas.

Una tarea (TSK) por producto, con zonas de tratamiento poligonales (TZN +
PLN): cada unidad de manejo es una zona con su dosis, y la zona por defecto
(fuera de toda unidad, fuera del lote o sin señal GPS) va con dosis 0 para
que la máquina cierre. Se escribe la versión 3 de la norma, que leen tanto
los monitores viejos como los nuevos.

Con xml.etree de la librería estándar: no suma dependencias al empaquetado
de escritorio.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from shapely.geometry.base import BaseGeometry

from app.prescripcion.mapa import MapaPrescripcion, partes_poligonales

VERSION_MAYOR = "3"
VERSION_MENOR = "3"

# Base de DDIs de ISOBUS (isobus.net, consultada 2026-11): el valor de PDV es
# un entero en la resolución del DDI.
#   DDI 1 Setpoint Volume Per Area Application Rate: mm³/m², resolución 0,01
#         -> 1 L/ha = 100 mm³/m² = 10000 unidades
#   DDI 6 Setpoint Mass Per Area Application Rate: mg/m², resolución 1
#         -> 1 kg/ha = 100 mg/m² = 100 unidades
DDI_POR_UNIDAD: dict[str, tuple[str, int]] = {
    "l/ha": ("0001", 10_000),
    "kg/ha": ("0006", 100),
}

# Redondear la dosis al entero del DDI cambia la cantidad; por encima de esto se avisa.
ERROR_REDONDEO_MAX = 0.01

_LARGO_DESIGNADOR = 32
_TZN_POR_DEFECTO = 0
_PLN_LIMITE = "1"
_PLN_ZONA_TRATAMIENTO = "2"
_LSG_EXTERIOR = "1"
_LSG_INTERIOR = "2"
_PNT_OTRO = "2"
_TSK_PLANIFICADA = "1"


def generar_taskdata(mapa: MapaPrescripcion, lote_nombre: str, version_software: str) -> tuple[bytes, list[str]]:
    """Devuelve (TASKDATA.XML, advertencias)."""
    advertencias: list[str] = []
    raiz = ET.Element("ISO11783_TaskData", {
        "VersionMajor": VERSION_MAYOR,
        "VersionMinor": VERSION_MENOR,
        "ManagementSoftwareManufacturer": "AgroNexo",
        "ManagementSoftwareVersion": version_software,
    })

    pfd = ET.SubElement(raiz, "PFD", {
        "A": "PFD1",
        "C": _designador(lote_nombre or "Lote"),
        "D": str(int(round(mapa.campo_local.area))),
    })
    if mapa.campo_es_limite_lote:
        _agregar_poligonos(pfd, mapa, mapa.campo_local, _PLN_LIMITE)

    numero = 0
    for producto in mapa.productos:
        unidad = producto.unidad_dosis.strip().lower()
        if unidad not in DDI_POR_UNIDAD:
            advertencias.append(
                f"{producto.producto}: la unidad '{producto.unidad_dosis}' no tiene DDI ISOBUS conocido; "
                "no se incluye en TASKDATA.XML (usar el Shapefile)."
            )
            continue
        numero += 1
        ddi, factor = DDI_POR_UNIDAD[unidad]
        pdt_id, vpn_id = f"PDT{numero}", f"VPN{numero}"

        ET.SubElement(raiz, "PDT", {"A": pdt_id, "B": _designador(_nombre_producto(producto))})
        ET.SubElement(raiz, "VPN", {
            "A": vpn_id,
            "B": "0",
            "C": f"{1 / factor:.6f}".rstrip("0"),
            "D": "2",
            "E": producto.unidad_dosis,
        })

        tsk = ET.SubElement(raiz, "TSK", {
            "A": f"TSK{numero}",
            "B": _designador(f"{lote_nombre or 'Lote'} - {producto.producto}"),
            "E": "PFD1",
            "G": _TSK_PLANIFICADA,
            "I": str(_TZN_POR_DEFECTO),
            "J": str(_TZN_POR_DEFECTO),
            "K": str(_TZN_POR_DEFECTO),
        })
        tzn = ET.SubElement(tsk, "TZN", {"A": str(_TZN_POR_DEFECTO), "B": "Sin aplicacion"})
        ET.SubElement(tzn, "PDV", {"A": ddi, "B": "0", "C": pdt_id, "E": vpn_id})

        for codigo, zona in enumerate(producto.zonas, start=1):
            valor = int(round(zona.dosis_por_ha * factor))
            if zona.dosis_por_ha > 0 and abs(valor / factor - zona.dosis_por_ha) / zona.dosis_por_ha > ERROR_REDONDEO_MAX:
                advertencias.append(
                    f"{producto.producto}, unidad {zona.unidad_id}: la dosis {zona.dosis_por_ha} "
                    f"{producto.unidad_dosis} se redondea a {valor / factor} en ISO-XML."
                )
            tzn = ET.SubElement(tsk, "TZN", {"A": str(codigo), "B": f"Unidad {zona.unidad_id}"})
            ET.SubElement(tzn, "PDV", {"A": ddi, "B": str(valor), "C": pdt_id, "E": vpn_id})
            _agregar_poligonos(tzn, mapa, zona.geom_local, _PLN_ZONA_TRATAMIENTO)

    ET.indent(raiz)
    return ET.tostring(raiz, encoding="UTF-8", xml_declaration=True), advertencias


def _nombre_producto(producto) -> str:
    return f"{producto.producto} ({producto.marca})" if producto.marca else producto.producto


def _designador(texto: str) -> str:
    return texto[:_LARGO_DESIGNADOR]


def _agregar_poligonos(padre: ET.Element, mapa: MapaPrescripcion, geom_local: BaseGeometry, tipo: str) -> None:
    for poligono in partes_poligonales(mapa.a_wgs84(geom_local)):
        pln = ET.SubElement(padre, "PLN", {"A": tipo})
        _agregar_anillo(pln, poligono.exterior.coords, _LSG_EXTERIOR)
        for interior in poligono.interiors:
            _agregar_anillo(pln, interior.coords, _LSG_INTERIOR)


def _agregar_anillo(pln: ET.Element, coords, tipo: str) -> None:
    lsg = ET.SubElement(pln, "LSG", {"A": tipo})
    for lon, lat, *_ in coords:
        ET.SubElement(lsg, "PNT", {"A": _PNT_OTRO, "C": f"{lat:.9f}", "D": f"{lon:.9f}"})


_ID = {
    "PFD": re.compile(r"^PFD\d+$"),
    "PDT": re.compile(r"^PDT\d+$"),
    "VPN": re.compile(r"^VPN\d+$"),
    "TSK": re.compile(r"^TSK\d+$"),
}


def validar_taskdata(xml_bytes: bytes) -> list[str]:
    """
    Control estructural de lo que escribe generar_taskdata(): atributos
    obligatorios, formato de IDs, referencias que existen, códigos de zona
    coherentes, anillos cerrados y coordenadas en rango. No reemplaza al XSD
    oficial de la norma; sirve para que un cambio en el exportador no rompa
    el archivo sin que un test lo note.
    """
    errores: list[str] = []
    raiz = ET.fromstring(xml_bytes)
    if raiz.tag != "ISO11783_TaskData":
        return [f"Raíz inesperada: {raiz.tag}"]
    for attr in ("VersionMajor", "VersionMinor", "ManagementSoftwareManufacturer", "ManagementSoftwareVersion"):
        if not raiz.get(attr):
            errores.append(f"ISO11783_TaskData sin {attr}")

    ids: dict[str, set[str]] = {tag: set() for tag in _ID}
    for tag, patron in _ID.items():
        for elem in raiz.iter(tag):
            ident = elem.get("A", "")
            if not patron.match(ident):
                errores.append(f"{tag} con ID inválido: {ident!r}")
            if ident in ids[tag]:
                errores.append(f"{tag} con ID repetido: {ident}")
            ids[tag].add(ident)

    for pfd in raiz.iter("PFD"):
        if not pfd.get("C"):
            errores.append(f"{pfd.get('A')} sin designador (C)")
        if not (pfd.get("D") or "").isdigit():
            errores.append(f"{pfd.get('A')} sin superficie en m² (D)")

    for tsk in raiz.iter("TSK"):
        nombre = tsk.get("A")
        if tsk.get("E") not in ids["PFD"]:
            errores.append(f"{nombre} referencia un PFD inexistente: {tsk.get('E')}")
        codigos = [tzn.get("A") for tzn in tsk.findall("TZN")]
        if len(codigos) != len(set(codigos)):
            errores.append(f"{nombre} tiene códigos de TZN repetidos")
        for attr in ("I", "J", "K"):
            if tsk.get(attr) is not None and tsk.get(attr) not in codigos:
                errores.append(f"{nombre}.{attr} apunta a una TZN inexistente: {tsk.get(attr)}")
        for tzn in tsk.findall("TZN"):
            codigo = tzn.get("A", "")
            if not codigo.isdigit() or not 0 <= int(codigo) <= 254:
                errores.append(f"{nombre} TZN con código fuera de rango: {codigo!r}")
            pdvs = tzn.findall("PDV")
            if not pdvs:
                errores.append(f"{nombre} TZN {codigo} sin PDV")
            for pdv in pdvs:
                if not re.fullmatch(r"[0-9A-F]{4}", pdv.get("A", "")):
                    errores.append(f"{nombre} TZN {codigo}: DDI inválido {pdv.get('A')!r}")
                if not (pdv.get("B") or "").isdigit():
                    errores.append(f"{nombre} TZN {codigo}: valor no entero {pdv.get('B')!r}")
                if pdv.get("C") not in ids["PDT"]:
                    errores.append(f"{nombre} TZN {codigo}: producto inexistente {pdv.get('C')}")
                if pdv.get("E") is not None and pdv.get("E") not in ids["VPN"]:
                    errores.append(f"{nombre} TZN {codigo}: VPN inexistente {pdv.get('E')}")
            if codigo != str(_TZN_POR_DEFECTO) and not tzn.findall("PLN"):
                errores.append(f"{nombre} TZN {codigo} sin polígono")

    for pln in raiz.iter("PLN"):
        for lsg in pln.findall("LSG"):
            pnts = lsg.findall("PNT")
            if len(pnts) < 4:
                errores.append("LSG con menos de 4 puntos")
                continue
            coords = [(p.get("C"), p.get("D")) for p in pnts]
            if coords[0] != coords[-1]:
                errores.append("LSG de polígono sin cerrar")
            for lat, lon in coords:
                if not (-90 <= float(lat) <= 90 and -180 <= float(lon) <= 180):
                    errores.append(f"PNT fuera de rango: {lat}, {lon}")
                    break

    return errores
