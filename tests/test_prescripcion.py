"""
Tests del paquete de prescripción (app/prescripcion/): mapa por producto,
recorrido sugerido, ISO-XML y armado del .zip.

Son la verificación de la entrega sin máquina real:
- las cantidades del mapa coinciden con la orden de trabajo;
- el recorrido simulado cubre todas las zonas a tratar;
- el TASKDATA.XML pasa el control estructural y lleva las dosis bien escaladas;
- el Shapefile se vuelve a leer con la misma geometría y los mismos datos.

Puros: sin DB ni MinIO.
    PYTHONPATH=$(pwd) python3 -m pytest tests/test_prescripcion.py -v
"""
import io
import json
import math
import xml.etree.ElementTree as ET
import zipfile

import numpy as np
import pytest
import shapefile
import shapely
from shapely.geometry import Polygon, box, mapping, shape
from shapely.ops import unary_union

from app.diagnostico.forma import proyectar_a_metros_locales
from app.diagnostico.orden_trabajo import generar_orden_trabajo
from app.prescripcion.isoxml import generar_taskdata, validar_taskdata
from app.prescripcion.mapa import armar_mapa_prescripcion
from app.prescripcion.maquinas import MaquinaEnum, resolver_perfil
from app.prescripcion.paquete import generar_paquete_prescripcion
from app.prescripcion.ruta import APLICACION, generar_ruta, simular_cobertura

LON0, LAT0 = -60.67, -27.47

# Lote de 400 x 200 m, girado 20° para que el recorrido no quede alineado a los ejes.
_CAMPO_LOCAL = Polygon([(-200, -100), (200, -100), (200, 100), (-200, 100)])


def _rotar(geom, grados=20.0):
    from shapely.affinity import rotate
    return rotate(geom, grados, origin=(0, 0))


def _a_wgs84(geom_local):
    cos_lat0 = math.cos(math.radians(LAT0))
    return shapely.transform(
        geom_local, lambda c: np.column_stack((c[:, 0] / (111_320.0 * cos_lat0) + LON0, c[:, 1] / 110_540.0 + LAT0)),
    )


LIMITE_4326 = _a_wgs84(_rotar(_CAMPO_LOCAL))

_CATALOGO = {
    "Thiametoxam": {"dosis_referencia": 0.2, "unidad": "L/ha"},
    "Azoxistrobina": {"dosis_referencia": 0.3, "unidad": "kg/ha"},
    "Sin Dosis": {"dosis_referencia": None, "unidad": "L/ha"},
}


def _unidad(uid, geom_local, producto, severidad="moderada", causa="estres_biotico_insecto", provisorio=False):
    geom_local = _rotar(geom_local)
    return {
        "type": "Feature",
        "geometry": mapping(_a_wgs84(geom_local)),
        "properties": {
            "unidad_id": uid,
            "causa_indice": causa,
            "severidad": severidad,
            "productos_sugeridos": [{"nombre": producto, "tipo": "x"}],
            "provisorio": provisorio,
            "area_total_ha": geom_local.area / 10_000,
            "zona_ids": [uid],
        },
    }


def _unidades():
    con_hueco = Polygon(
        [(20, 20), (120, 20), (120, 80), (20, 80)],
        [[(50, 40), (80, 40), (80, 60), (50, 60)]],
    )
    return [
        _unidad(1, box(-180, -80, -120, -20), "Thiametoxam", severidad="critica"),
        # Pegada a la unidad 1: con margen, se superponen.
        _unidad(2, box(-118, -80, -60, 0), "Thiametoxam"),
        _unidad(3, con_hueco, "Azoxistrobina", causa="estres_biotico_fungico", provisorio=True),
        _unidad(4, box(150, -90, 190, -50), "Sin Dosis"),
    ]


def _mapa(margen_m=0.0, unidades=None):
    unidades = unidades or _unidades()
    orden = generar_orden_trabajo(unidades, _CATALOGO)
    return armar_mapa_prescripcion(unidades, orden, LIMITE_4326, margen_m), orden


def _producto(mapa, nombre):
    return next(p for p in mapa.productos if p.producto == nombre)


# ── Mapa ──────────────────────────────────────────────────────────────

def test_sin_margen_las_cantidades_coinciden_con_la_orden_de_trabajo():
    mapa, orden = _mapa(margen_m=0.0)
    totales = {t["producto"]: t["volumen_total"] for t in orden["totales_por_producto"]}

    assert {p.producto for p in mapa.productos} == {"Thiametoxam", "Azoxistrobina"}
    for producto in mapa.productos:
        # La orden redondea el volumen de cada unidad a 3 decimales.
        tolerancia = 0.0005 * len(producto.zonas) + 1e-9
        assert producto.cantidad == pytest.approx(producto.cantidad_orden, abs=tolerancia)
        assert producto.cantidad == pytest.approx(totales[producto.producto], abs=tolerancia)


def test_un_mapa_por_producto_con_sus_unidades():
    mapa, _ = _mapa()
    assert [z.unidad_id for z in _producto(mapa, "Thiametoxam").zonas] == [1, 2]
    assert [z.unidad_id for z in _producto(mapa, "Azoxistrobina").zonas] == [3]


def test_unidad_sin_dosis_queda_fuera_y_avisada():
    mapa, _ = _mapa()
    assert all(z.unidad_id != 4 for p in mapa.productos for z in p.zonas)
    assert [s["unidad_id"] for s in mapa.sin_prescripcion] == [4]
    assert "sin dosis" in mapa.sin_prescripcion[0]["motivo"]


def test_margen_agranda_sin_superponer_ni_salir_del_lote():
    sin, _ = _mapa(margen_m=0.0)
    con, _ = _mapa(margen_m=5.0)
    thia_sin, thia_con = _producto(sin, "Thiametoxam"), _producto(con, "Thiametoxam")

    assert thia_con.area_ha > thia_sin.area_ha
    union = unary_union([z.geom_local for z in thia_con.zonas])
    assert union.area == pytest.approx(sum(z.geom_local.area for z in thia_con.zonas), rel=1e-6)
    assert union.difference(con.campo_local.buffer(1e-6)).area == pytest.approx(0.0, abs=1e-3)


def test_el_hueco_de_la_zona_se_conserva():
    mapa, _ = _mapa()
    geom = _producto(mapa, "Azoxistrobina").zonas[0].geom_local
    assert geom.geom_type == "Polygon" and len(geom.interiors) == 1


def test_sin_limite_de_lote_se_estima_el_campo():
    unidades = _unidades()
    orden = generar_orden_trabajo(unidades, _CATALOGO)
    mapa = armar_mapa_prescripcion(unidades, orden, None, 3.0)
    assert not mapa.campo_es_limite_lote
    for producto in mapa.productos:
        for zona in producto.zonas:
            assert mapa.campo_local.buffer(1e-6).contains(zona.geom_local)


def test_a_wgs84_es_la_inversa_de_la_proyeccion_local():
    mapa, _ = _mapa()
    ida_y_vuelta = mapa.a_wgs84(proyectar_a_metros_locales(LIMITE_4326, mapa.lon0, mapa.lat0))
    assert ida_y_vuelta.symmetric_difference(LIMITE_4326).area < 1e-14


# ── Recorrido ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("maquina", list(MaquinaEnum))
def test_recorrido_simulado_cubre_todas_las_zonas(maquina):
    perfil = resolver_perfil(maquina)
    mapa, _ = _mapa(margen_m=perfil.margen_m)
    for producto in mapa.productos:
        zonas = [(z.geom_local, z.dosis_por_ha) for z in producto.zonas]
        ruta = generar_ruta(mapa.campo_local, zonas, perfil.ancho_labor_m, perfil.solo_pasadas_con_aplicacion)
        sim = simular_cobertura(ruta, zonas)

        assert sim["cobertura_pct"] >= 99.9
        # Barra completa abierta o cerrada: se aplica al menos lo que pide el mapa.
        assert sim["cantidad_aplicada"] >= producto.cantidad * 0.999


def test_recorrido_sigue_el_lado_mas_largo_del_lote():
    mapa, _ = _mapa()
    zonas = [(z.geom_local, z.dosis_por_ha) for z in mapa.productos[0].zonas]
    ruta = generar_ruta(mapa.campo_local, zonas, 28.0, False)
    assert ruta.angulo_grados % 180 == pytest.approx(20.0, abs=0.5)


def test_mosquito_recorre_todo_el_lote_y_dron_solo_donde_aplica():
    mapa, _ = _mapa()
    zonas = [(z.geom_local, z.dosis_por_ha) for z in _producto(mapa, "Thiametoxam").zonas]

    mosquito = generar_ruta(mapa.campo_local, zonas, 28.0, False)
    assert mosquito.n_pasadas == math.ceil(200 / 28.0)

    dron = generar_ruta(mapa.campo_local, zonas, 7.0, True)
    for pasada in range(dron.n_pasadas):
        tramos = [t for t in dron.tramos if t.pasada == pasada]
        assert any(t.tipo == APLICACION for t in tramos)
    assert dron.longitud_m(APLICACION) + dron.longitud_m("traslado") < (
        mosquito.longitud_m(APLICACION) + mosquito.longitud_m("traslado")
    ) * 200 / 7  # vuela mucho menos que si barriera el lote con su ancho


def test_franja_angosta_entre_dos_pasadas_no_queda_sin_aplicar():
    campo = box(0, 0, 200, 100)
    # Franja de 2 m entre las líneas centrales y = 14 y y = 42 de un ancho de 28 m.
    franja = box(50, 27, 150, 29)
    ruta = generar_ruta(campo, [(franja, 1.0)], 28.0, False)
    assert simular_cobertura(ruta, [(franja, 1.0)])["cobertura_pct"] >= 99.9


def test_pasadas_alternan_sentido_y_se_conectan():
    campo = box(0, 0, 200, 100)
    ruta = generar_ruta(campo, [(box(20, 0, 180, 100), 1.0)], 25.0, False)
    finales = {}
    for t in ruta.tramos:
        finales.setdefault(t.pasada, []).append(t)
    for i in range(1, ruta.n_pasadas):
        fin_anterior = finales[i - 1][-1].linea_local.coords[-1]
        inicio = finales[i][0].linea_local.coords[0]
        assert fin_anterior == pytest.approx(inicio)


# ── ISO-XML ───────────────────────────────────────────────────────────

def test_taskdata_valido_con_una_tarea_por_producto_y_dosis_escaladas():
    mapa, _ = _mapa(margen_m=3.0)
    xml, advertencias = generar_taskdata(mapa, "Lote Norte", "4.0.0")
    assert validar_taskdata(xml) == []
    assert advertencias == []

    raiz = ET.fromstring(xml)
    tareas = raiz.findall("TSK")
    assert len(tareas) == 2

    valores = {}
    for tsk in tareas:
        for tzn in tsk.findall("TZN"):
            pdv = tzn.find("PDV")
            valores.setdefault(tsk.get("B"), []).append((pdv.get("A"), int(pdv.get("B"))))
    thia = next(v for k, v in valores.items() if "Thiametoxam" in k)
    azox = next(v for k, v in valores.items() if "Azoxistrobina" in k)
    # 0,2 L/ha -> DDI 1 (mm³/m², resolución 0,01) = 2000; zona por defecto en 0.
    assert thia == [("0001", 0), ("0001", 2000), ("0001", 2000)]
    # 0,3 kg/ha -> DDI 6 (mg/m², resolución 1) = 30.
    assert azox == [("0006", 0), ("0006", 30)]


def test_taskdata_conserva_coordenadas_y_huecos():
    mapa, _ = _mapa()
    xml, _ = generar_taskdata(mapa, "Lote", "4.0.0")
    raiz = ET.fromstring(xml)
    tzn = next(t for t in raiz.iter("TZN") if t.get("B") == "Unidad 3")
    anillos = tzn.find("PLN").findall("LSG")
    assert [a.get("A") for a in anillos] == ["1", "2"]

    exterior = Polygon([(float(p.get("D")), float(p.get("C"))) for p in anillos[0].findall("PNT")])
    esperado = shape(_unidades()[2]["geometry"])
    assert exterior.symmetric_difference(Polygon(esperado.exterior)).area < 1e-12


def test_taskdata_avisa_redondeo_y_unidad_desconocida():
    catalogo = dict(_CATALOGO)
    catalogo["Azoxistrobina"] = {"dosis_referencia": 0.045, "unidad": "kg/ha"}
    catalogo["Thiametoxam"] = {"dosis_referencia": 150, "unidad": "cc/ha"}
    unidades = _unidades()
    orden = generar_orden_trabajo(unidades, catalogo)
    mapa = armar_mapa_prescripcion(unidades, orden, LIMITE_4326, 0.0)

    xml, advertencias = generar_taskdata(mapa, "Lote", "4.0.0")
    assert validar_taskdata(xml) == []
    assert len(ET.fromstring(xml).findall("TSK")) == 1
    assert any("cc/ha" in a for a in advertencias)
    assert any("se redondea" in a for a in advertencias)


def test_validar_taskdata_detecta_errores():
    mapa, _ = _mapa()
    xml, _ = generar_taskdata(mapa, "Lote", "4.0.0")
    raiz = ET.fromstring(xml)
    tsk = raiz.find("TSK")
    tsk.set("E", "PFD9")
    tsk.set("I", "77")
    lsg = next(raiz.iter("LSG"))
    lsg.remove(lsg.findall("PNT")[-1])
    errores = validar_taskdata(ET.tostring(raiz))
    assert any("PFD inexistente" in e for e in errores)
    assert any("TZN inexistente" in e for e in errores)
    assert any("sin cerrar" in e for e in errores)


# ── Paquete .zip ──────────────────────────────────────────────────────

def _paquete(maquina=MaquinaEnum.mosquito):
    perfil = resolver_perfil(maquina)
    mapa, orden = _mapa(margen_m=perfil.margen_m)
    contenido, resumen = generar_paquete_prescripcion(
        mapa, perfil, {"lote_nombre": "Lote Norte", "cultivo": "soja"}, "4.0.0",
    )
    return zipfile.ZipFile(io.BytesIO(contenido)), resumen, mapa


def test_paquete_trae_todos_los_archivos():
    zf, _, _ = _paquete()
    nombres = set(zf.namelist())
    assert {"TASKDATA/TASKDATA.XML", "resumen.json", "LEEME.txt"} <= nombres
    for carpeta in ("thiametoxam", "azoxistrobina"):
        for ext in ("shp", "shx", "dbf", "prj", "cpg"):
            assert f"{carpeta}/prescripcion.{ext}" in nombres
        assert f"{carpeta}/recorrido.geojson" in nombres
        assert f"{carpeta}/recorrido.kml" in nombres


def test_shapefile_se_relee_con_dosis_y_resto_del_lote_en_cero():
    zf, _, mapa = _paquete()
    lector = shapefile.Reader(
        shp=io.BytesIO(zf.read("thiametoxam/prescripcion.shp")),
        shx=io.BytesIO(zf.read("thiametoxam/prescripcion.shx")),
        dbf=io.BytesIO(zf.read("thiametoxam/prescripcion.dbf")),
    )
    registros = lector.records()
    assert [r["unidad_id"] for r in registros] == [1, 2, 0]
    assert [r["dosis"] for r in registros] == [0.2, 0.2, 0.0]

    producto = _producto(mapa, "Thiametoxam")
    assert sum(r["cantidad"] for r in registros) == pytest.approx(producto.cantidad, abs=0.002)

    # Zonas + resto cubren el lote completo.
    geoms = [shape(s.__geo_interface__) for s in lector.shapes()]
    assert unary_union(geoms).symmetric_difference(LIMITE_4326).area < 1e-12


def test_resumen_y_leeme_coherentes():
    zf, resumen, _ = _paquete()
    en_zip = json.loads(zf.read("resumen.json"))
    assert en_zip["iso_xml"]["errores_validacion"] == []
    assert [s["unidad_id"] for s in en_zip["unidades_sin_prescripcion"]] == [4]
    for p in en_zip["productos"]:
        assert p["simulacion"]["cobertura_pct"] >= 99.9
        assert p["mapa_con_margen"]["cantidad"] >= p["orden_de_trabajo"]["cantidad"]
        assert p["cargas"]["cantidad_de_cargas"] >= 1
    azox = next(p for p in en_zip["productos"] if p["producto"] == "Azoxistrobina")
    assert azox["provisorio"] is True

    leeme = zf.read("LEEME.txt").decode("utf-8")
    assert "Unidad 4" in leeme and "confirmar la causa" in leeme
    assert resumen["productos"] == en_zip["productos"]


def test_recorrido_kml_y_geojson_son_legibles():
    zf, _, _ = _paquete(MaquinaEnum.dron)
    kml = ET.fromstring(zf.read("thiametoxam/recorrido.kml"))
    placemarks = kml.findall(".//{http://www.opengis.net/kml/2.2}Placemark")
    assert placemarks

    geojson = json.loads(zf.read("thiametoxam/recorrido.geojson"))
    tipos = {f["properties"]["tipo"] for f in geojson["features"]}
    assert APLICACION in tipos
    assert [f["properties"]["orden"] for f in geojson["features"]] == list(range(1, len(geojson["features"]) + 1))
