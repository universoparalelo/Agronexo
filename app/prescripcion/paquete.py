"""
Arma el .zip del paquete de prescripción: un mapa por producto (Shapefile),
el TASKDATA ISO-XML con una tarea por producto, el recorrido sugerido
(GeoJSON y KML), un resumen.json con las verificaciones y un LEEME.txt.
"""

from __future__ import annotations

import io
import json
import math
import re
import unicodedata
import zipfile
from datetime import datetime, timezone
from xml.sax.saxutils import escape

import shapefile
from shapely.geometry import mapping

from app.prescripcion.isoxml import generar_taskdata, validar_taskdata
from app.prescripcion.mapa import MapaPrescripcion, PrescripcionProducto, partes_poligonales
from app.prescripcion.maquinas import PerfilMaquina
from app.prescripcion.ruta import APLICACION, Ruta, generar_ruta, simular_cobertura
from app.reportes.exportacion import _WGS84_ESRI_WKT, _partes_shapefile

# Campos DBF clásicos: nombres de hasta 10 caracteres.
_CAMPOS_SHP = [
    ("unidad_id", "N", 10, 0),
    ("producto", "C", 60, 0),
    ("dosis", "F", 14, 4),
    ("unidad", "C", 10, 0),
    ("sup_ha", "F", 12, 4),
    ("cantidad", "F", 14, 3),
    ("severidad", "C", 20, 0),
    ("causa", "C", 40, 0),
    ("provisor", "C", 2, 0),
]


def generar_paquete_prescripcion(
    mapa: MapaPrescripcion,
    perfil: PerfilMaquina,
    metadata: dict,
    version_software: str,
) -> tuple[bytes, dict]:
    """Devuelve (bytes del .zip, resumen)."""
    lote_nombre = metadata.get("lote_nombre") or "Lote"
    taskdata, advertencias_iso = generar_taskdata(mapa, lote_nombre, version_software)
    errores_iso = validar_taskdata(taskdata)

    carpetas = _carpetas_unicas([p.producto for p in mapa.productos])
    resumen_productos = []
    archivos: dict[str, bytes | str] = {"TASKDATA/TASKDATA.XML": taskdata}

    for producto, carpeta in zip(mapa.productos, carpetas):
        zonas = [(z.geom_local, z.dosis_por_ha) for z in producto.zonas]
        ruta = generar_ruta(mapa.campo_local, zonas, perfil.ancho_labor_m, perfil.solo_pasadas_con_aplicacion)
        simulacion = simular_cobertura(ruta, zonas)

        for extension, contenido in _shapefile_producto(mapa, producto).items():
            archivos[f"{carpeta}/prescripcion.{extension}"] = contenido
        archivos[f"{carpeta}/recorrido.geojson"] = _ruta_geojson(mapa, ruta, producto)
        archivos[f"{carpeta}/recorrido.kml"] = _ruta_kml(mapa, ruta, producto, lote_nombre)

        resumen_productos.append(_resumen_producto(producto, carpeta, ruta, simulacion, perfil))

    resumen = {
        "generado_en": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "software": f"AgroNexo {version_software}",
        "lote": lote_nombre,
        "cultivo": metadata.get("cultivo"),
        "fecha_vuelo": metadata.get("fecha_vuelo"),
        "maquina": {
            "tipo": perfil.nombre,
            "ancho_labor_m": perfil.ancho_labor_m,
            "margen_m": perfil.margen_m,
            "caldo_l_ha": perfil.caldo_l_ha,
            "tanque_l": perfil.tanque_l,
        },
        "limite_lote": "real" if mapa.campo_es_limite_lote else "estimado (el lote no tiene límite cargado)",
        "productos": resumen_productos,
        "unidades_sin_prescripcion": mapa.sin_prescripcion,
        "iso_xml": {
            "version": "ISO 11783-10 v3.3",
            "advertencias": advertencias_iso,
            "errores_validacion": errores_iso,
        },
    }
    archivos["resumen.json"] = json.dumps(resumen, ensure_ascii=False, indent=2)
    archivos["LEEME.txt"] = _leeme(resumen, carpetas)

    zip_io = io.BytesIO()
    with zipfile.ZipFile(zip_io, "w", zipfile.ZIP_DEFLATED) as zf:
        for nombre, contenido in archivos.items():
            zf.writestr(nombre, contenido.encode("utf-8") if isinstance(contenido, str) else contenido)
    return zip_io.getvalue(), resumen


def _resumen_producto(
    producto: PrescripcionProducto, carpeta: str, ruta: Ruta, simulacion: dict, perfil: PerfilMaquina,
) -> dict:
    ha_por_carga = perfil.tanque_l / perfil.caldo_l_ha
    cargas = math.ceil(simulacion["superficie_aplicada_ha"] / ha_por_carga) if simulacion["superficie_aplicada_ha"] else 0
    return {
        "producto": producto.producto,
        "marca": producto.marca,
        "carpeta": carpeta,
        "unidad_dosis": producto.unidad_dosis,
        "provisorio": producto.provisorio,
        "zonas": [
            {
                "unidad_id": z.unidad_id,
                "dosis_por_ha": z.dosis_por_ha,
                "superficie_ha": round(z.area_ha, 4),
                "superficie_orden_ha": z.area_ha_orden,
                "cantidad": round(z.cantidad, 3),
            }
            for z in producto.zonas
        ],
        "orden_de_trabajo": {
            "superficie_ha": round(producto.area_ha_orden, 4),
            "cantidad": round(producto.cantidad_orden, 3),
        },
        "mapa_con_margen": {
            "superficie_ha": round(producto.area_ha, 4),
            "cantidad": round(producto.cantidad, 3),
        },
        "recorrido": {
            "pasadas": ruta.n_pasadas,
            "orientacion_grados": round(ruta.angulo_grados, 1),
            "aplicando_km": round(ruta.longitud_m(APLICACION) / 1000, 3),
            "traslado_km": round(ruta.longitud_m("traslado") / 1000, 3),
        },
        "simulacion": simulacion,
        "cargas": {
            "ha_por_carga": round(ha_por_carga, 2),
            "producto_por_carga_completa": round(ha_por_carga * producto.dosis_maxima, 3),
            "cantidad_de_cargas": cargas,
        },
        "unidad_cantidad": producto.unidad_cantidad,
    }


def _shapefile_producto(mapa: MapaPrescripcion, producto: PrescripcionProducto) -> dict[str, bytes | str]:
    shp_io, shx_io, dbf_io = io.BytesIO(), io.BytesIO(), io.BytesIO()
    writer = shapefile.Writer(shp=shp_io, shx=shx_io, dbf=dbf_io, shapeType=shapefile.POLYGON, encoding="utf-8")
    for nombre, tipo, largo, decimales in _CAMPOS_SHP:
        writer.field(nombre, tipo, largo, decimales)

    nombre = f"{producto.producto} ({producto.marca})" if producto.marca else producto.producto
    for zona in producto.zonas:
        writer.poly(_partes_shapefile(mapa.a_wgs84(zona.geom_local)))
        writer.record(
            unidad_id=zona.unidad_id,
            producto=nombre,
            dosis=zona.dosis_por_ha,
            unidad=producto.unidad_dosis,
            sup_ha=round(zona.area_ha, 4),
            cantidad=round(zona.cantidad, 3),
            severidad=zona.severidad,
            causa=zona.causa_indice,
            provisor="si" if zona.provisorio else "no",
        )

    # El resto del lote va explícito con dosis 0: hay monitores que, sin
    # polígono, aplican la "dosis por defecto" que tenga cargada el operador.
    tratado = None
    for zona in producto.zonas:
        tratado = zona.geom_local if tratado is None else tratado.union(zona.geom_local)
    resto = mapa.campo_local.difference(tratado) if tratado is not None else mapa.campo_local
    if partes_poligonales(resto):
        writer.poly(_partes_shapefile(mapa.a_wgs84(resto)))
        writer.record(
            unidad_id=0, producto=nombre, dosis=0.0, unidad=producto.unidad_dosis,
            sup_ha=round(resto.area / 10_000, 4), cantidad=0.0, severidad="", causa="sin_aplicacion",
            provisor="no",
        )
    writer.close()

    return {
        "shp": shp_io.getvalue(),
        "shx": shx_io.getvalue(),
        "dbf": dbf_io.getvalue(),
        "prj": _WGS84_ESRI_WKT,
        "cpg": "UTF-8",
    }


def _ruta_geojson(mapa: MapaPrescripcion, ruta: Ruta, producto: PrescripcionProducto) -> str:
    features = [
        {
            "type": "Feature",
            "geometry": mapping(mapa.a_wgs84(tramo.linea_local)),
            "properties": {
                "orden": orden,
                "pasada": tramo.pasada + 1,
                "tipo": tramo.tipo,
                "dosis_por_ha": tramo.dosis_por_ha,
                "unidad_dosis": producto.unidad_dosis,
                "largo_m": round(tramo.linea_local.length, 1),
            },
        }
        for orden, tramo in enumerate(ruta.tramos, start=1)
    ]
    return json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False)


def _ruta_kml(mapa: MapaPrescripcion, ruta: Ruta, producto: PrescripcionProducto, lote_nombre: str) -> str:
    def coords(geom) -> str:
        return " ".join(f"{x:.8f},{y:.8f},0" for x, y, *_ in geom.coords)

    zonas_kml = []
    for zona in producto.zonas:
        for poligono in partes_poligonales(mapa.a_wgs84(zona.geom_local)):
            interiores = "".join(
                f"<innerBoundaryIs><LinearRing><coordinates>{coords(i)}</coordinates></LinearRing></innerBoundaryIs>"
                for i in poligono.interiors
            )
            zonas_kml.append(
                f"<Placemark><name>Unidad {zona.unidad_id}</name>"
                f"<description>{escape(f'{zona.dosis_por_ha} {producto.unidad_dosis}')}</description>"
                f"<styleUrl>#zona</styleUrl><Polygon><outerBoundaryIs><LinearRing>"
                f"<coordinates>{coords(poligono.exterior)}</coordinates></LinearRing></outerBoundaryIs>"
                f"{interiores}</Polygon></Placemark>"
            )

    tramos_kml = []
    for orden, tramo in enumerate(ruta.tramos, start=1):
        aplica = tramo.tipo == APLICACION
        descripcion = f"{tramo.dosis_por_ha} {producto.unidad_dosis}" if aplica else "Barra cerrada"
        tramos_kml.append(
            f"<Placemark><name>{orden}. Pasada {tramo.pasada + 1} - {'aplicar' if aplica else 'traslado'}</name>"
            f"<description>{escape(descripcion)}</description>"
            f"<styleUrl>#{'aplicacion' if aplica else 'traslado'}</styleUrl>"
            f"<LineString><tessellate>1</tessellate><coordinates>{coords(mapa.a_wgs84(tramo.linea_local))}"
            f"</coordinates></LineString></Placemark>"
        )

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
        f"<name>{escape(f'{lote_nombre} - {producto.producto}')}</name>"
        '<Style id="zona"><LineStyle><color>ff0000ff</color><width>2</width></LineStyle>'
        "<PolyStyle><color>440000ff</color></PolyStyle></Style>"
        '<Style id="aplicacion"><LineStyle><color>ff00a5ff</color><width>3</width></LineStyle></Style>'
        '<Style id="traslado"><LineStyle><color>ff9e9e9e</color><width>1</width></LineStyle></Style>'
        f"<Folder><name>Zonas a aplicar</name>{''.join(zonas_kml)}</Folder>"
        f"<Folder><name>Recorrido</name>{''.join(tramos_kml)}</Folder>"
        "</Document></kml>"
    )


def _carpetas_unicas(nombres: list[str]) -> list[str]:
    usadas: set[str] = set()
    carpetas = []
    for nombre in nombres:
        base = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
        base = re.sub(r"[^a-zA-Z0-9]+", "_", base).strip("_").lower()[:40] or "producto"
        carpeta, n = base, 2
        while carpeta in usadas:
            carpeta, n = f"{base}_{n}", n + 1
        usadas.add(carpeta)
        carpetas.append(carpeta)
    return carpetas


def _leeme(resumen: dict, carpetas: list[str]) -> str:
    maquina = resumen["maquina"]
    lineas = [
        f"PAQUETE DE PRESCRIPCION - {resumen['lote']}",
        f"Generado por {resumen['software']} el {resumen['generado_en']}",
        "",
        f"Maquina: {maquina['tipo']}",
        f"Ancho de labor: {maquina['ancho_labor_m']} m | Margen alrededor de cada zona: {maquina['margen_m']} m",
        f"Caldo: {maquina['caldo_l_ha']} L/ha | Tanque: {maquina['tanque_l']} L",
        f"Limite del lote: {resumen['limite_lote']}",
        "",
        "CONTENIDO",
        "  TASKDATA/TASKDATA.XML   Prescripcion ISO-XML (ISOBUS, ISO 11783-10 v3), una tarea por producto.",
        "                          Copiar la carpeta TASKDATA entera a la raiz de un pendrive.",
    ]
    for carpeta in carpetas:
        lineas += [
            f"  {carpeta}/prescripcion.shp (+ .shx .dbf .prj .cpg)",
            "                          Mapa de prescripcion en Shapefile: campo 'dosis' por zona;",
            "                          el resto del lote va con dosis 0.",
            f"  {carpeta}/recorrido.kml / recorrido.geojson",
            "                          Recorrido sugerido: tramos 'aplicacion' (barra abierta) y 'traslado'.",
        ]
    lineas += [
        "  resumen.json            Cantidades, recorrido, cargas y verificacion de cobertura.",
        "",
        "PRODUCTOS",
    ]
    for p in resumen["productos"]:
        u = p["unidad_cantidad"]
        lineas += [
            f"- {p['producto']}" + (f" ({p['marca']})" if p["marca"] else "") + f"  [carpeta {p['carpeta']}]",
            f"    Orden de trabajo: {p['orden_de_trabajo']['cantidad']} {u} en {p['orden_de_trabajo']['superficie_ha']} ha",
            f"    Mapa con margen:  {p['mapa_con_margen']['cantidad']} {u} en {p['mapa_con_margen']['superficie_ha']} ha",
            f"    Simulacion del recorrido: cobertura {p['simulacion']['cobertura_pct']} %, "
            f"{p['simulacion']['cantidad_aplicada']} {u} aplicados en {p['simulacion']['superficie_aplicada_ha']} ha",
            f"    Cargas: {p['cargas']['cantidad_de_cargas']} de hasta {p['cargas']['ha_por_carga']} ha; "
            f"{p['cargas']['producto_por_carga_completa']} {u} por tanque lleno",
        ]
        if p["provisorio"]:
            lineas.append("    ATENCION: diagnostico provisorio, confirmar la causa en el campo antes de aplicar.")
    if resumen["unidades_sin_prescripcion"]:
        lineas += ["", "UNIDADES SIN PRESCRIPCION (no estan en ningun mapa)"]
        lineas += [f"- Unidad {u['unidad_id']}: {u['motivo']}" for u in resumen["unidades_sin_prescripcion"]]
    if resumen["iso_xml"]["advertencias"]:
        lineas += ["", "ADVERTENCIAS ISO-XML"]
        lineas += [f"- {a}" for a in resumen["iso_xml"]["advertencias"]]
    lineas += [
        "",
        "COMO USARLO",
        "- Pulverizadora con monitor ISOBUS: cargar TASKDATA desde el pendrive en el Task Controller;",
        "  elegir la tarea del producto que lleva el tanque.",
        "- Monitor sin ISOBUS o software de dron: importar el Shapefile del producto como mapa de",
        "  prescripcion (aplicacion variable), indicando 'dosis' como campo de dosis.",
        "- El recorrido es una sugerencia para planificar y revisar en QGIS o Google Earth; los drones",
        "  y monitores con guiado calculan su propia ruta a partir del mapa.",
        "",
        "LIMITACIONES",
        "- La simulacion supone la barra entera abierta o cerrada. Con corte por secciones la",
        "  superficie aplicada fuera de las zonas es menor que la del resumen.",
        "- Los archivos siguen los formatos estandar, pero cada marca de monitor o dron puede pedir",
        "  ajustes (nombres de campo, unidades) que solo se confirman en el equipo real.",
        "- Las dosis salen del catalogo de AgroNexo: verificarlas contra el marbete del producto.",
        "- Toda aplicacion requiere receta agronomica firmada por un ingeniero agronomo matriculado.",
    ]
    return "\r\n".join(lineas) + "\r\n"
