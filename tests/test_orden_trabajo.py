"""
Tests de app/diagnostico/orden_trabajo.py — cálculo de dosis/volumen de la
orden de trabajo (RFSA-04) a partir de unidades de manejo. Puro: sin I/O,
sin DB.

Correr:
    docker compose exec api python3 -m pytest tests/test_orden_trabajo.py -v
"""
import pytest

from app.diagnostico.orden_trabajo import generar_orden_trabajo


def _unidad(unidad_id, causa="estres_hidrico", severidad="moderada",
            area_ha=2.0, zona_ids=None, producto="Urea 46% N"):
    productos_sugeridos = [{"nombre": producto, "tipo": "fertilizante"}] if producto else []
    return {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": []},
        "properties": {
            "unidad_id": unidad_id,
            "causa_indice": causa,
            "severidad": severidad,
            "area_total_ha": area_ha,
            "zona_ids": zona_ids or [0],
            "productos_sugeridos": productos_sugeridos,
        },
    }


CATALOGO_BASE = {
    "Urea 46% N": {
        "dosis_referencia": 100.0,
        "unidad": "kg/ha",
        "restricciones_ambientales": "No aplicar a menos de 50 m de cursos de agua.",
        "instrucciones_seguridad": "Usar guantes y protección respiratoria.",
    },
    "Glifosato": {
        "dosis_referencia": 3.0,
        "unidad": "l/ha",
        "restricciones_ambientales": None,
        "instrucciones_seguridad": None,
    },
}


class TestGenerarOrdenTrabajo:
    def test_sin_unidades_retorna_vacio(self):
        orden = generar_orden_trabajo([], CATALOGO_BASE)
        assert orden["items"] == []
        assert orden["totales_por_producto"] == []
        assert orden["area_total_tratada_ha"] == 0

    def test_una_unidad_calcula_volumen(self):
        orden = generar_orden_trabajo([_unidad(1, area_ha=2.0)], CATALOGO_BASE)
        item = orden["items"][0]
        assert item["producto"] == "Urea 46% N"
        assert item["dosis_por_ha"] == 100.0
        assert item["unidad_dosis"] == "kg/ha"
        assert item["volumen_total"] == 200.0
        assert item["sin_dosis_referencia"] is False

    def test_incluye_restricciones_e_instrucciones(self):
        orden = generar_orden_trabajo([_unidad(1)], CATALOGO_BASE)
        item = orden["items"][0]
        assert item["restricciones_ambientales"] == "No aplicar a menos de 50 m de cursos de agua."
        assert item["instrucciones_seguridad"] == "Usar guantes y protección respiratoria."

    def test_producto_sin_dosis_referencia_marca_flag(self):
        catalogo = {"Producto Sin Dosis": {"dosis_referencia": None, "unidad": None}}
        orden = generar_orden_trabajo([_unidad(1, producto="Producto Sin Dosis")], catalogo)
        item = orden["items"][0]
        assert item["sin_dosis_referencia"] is True
        assert item["volumen_total"] is None

    def test_producto_fuera_de_catalogo_marca_flag(self):
        orden = generar_orden_trabajo([_unidad(1, producto="Producto Desconocido")], CATALOGO_BASE)
        item = orden["items"][0]
        assert item["sin_dosis_referencia"] is True
        assert item["volumen_total"] is None
        assert item["producto"] == "Producto Desconocido"

    def test_unidad_sin_productos_sugeridos(self):
        orden = generar_orden_trabajo([_unidad(1, producto=None)], CATALOGO_BASE)
        item = orden["items"][0]
        assert item["producto"] is None
        assert item["sin_dosis_referencia"] is True
        assert item["volumen_total"] is None

    def test_totales_agrupan_por_producto(self):
        unidades = [
            _unidad(1, area_ha=2.0, producto="Urea 46% N"),
            _unidad(2, area_ha=3.0, producto="Urea 46% N"),
        ]
        orden = generar_orden_trabajo(unidades, CATALOGO_BASE)
        assert len(orden["totales_por_producto"]) == 1
        total = orden["totales_por_producto"][0]
        assert total["producto"] == "Urea 46% N"
        assert total["area_ha"] == 5.0
        assert total["volumen_total"] == 500.0

    def test_totales_separan_productos_distintos(self):
        unidades = [
            _unidad(1, area_ha=2.0, producto="Urea 46% N"),
            _unidad(2, area_ha=1.0, producto="Glifosato"),
        ]
        orden = generar_orden_trabajo(unidades, CATALOGO_BASE)
        productos = sorted(t["producto"] for t in orden["totales_por_producto"])
        assert productos == ["Glifosato", "Urea 46% N"]

    def test_totales_excluyen_unidades_sin_producto(self):
        unidades = [_unidad(1, producto=None)]
        orden = generar_orden_trabajo(unidades, CATALOGO_BASE)
        assert orden["totales_por_producto"] == []

    def test_totales_ignoran_volumen_none_pero_suman_area(self):
        unidades = [
            _unidad(1, area_ha=2.0, producto="Producto Desconocido"),
            _unidad(2, area_ha=1.0, producto="Producto Desconocido"),
        ]
        orden = generar_orden_trabajo(unidades, CATALOGO_BASE)
        total = orden["totales_por_producto"][0]
        assert total["area_ha"] == 3.0
        assert total["volumen_total"] == 0.0

    def test_area_total_tratada_suma_todas_las_unidades(self):
        unidades = [
            _unidad(1, area_ha=2.0, producto="Urea 46% N"),
            _unidad(2, area_ha=1.5, producto="Glifosato"),
        ]
        orden = generar_orden_trabajo(unidades, CATALOGO_BASE)
        assert orden["area_total_tratada_ha"] == 3.5

    def test_conserva_causa_severidad_y_zona_ids(self):
        orden = generar_orden_trabajo(
            [_unidad(1, causa="estres_biotico_fungico", severidad="critica", zona_ids=[3, 4])],
            CATALOGO_BASE,
        )
        item = orden["items"][0]
        assert item["causa_indice"] == "estres_biotico_fungico"
        assert item["severidad"] == "critica"
        assert item["zona_ids"] == [3, 4]


if __name__ == "__main__":
    import sys
    raise SystemExit(pytest.main([__file__, "-v"]))


class TestProvisorio:
    def test_la_unidad_provisoria_entra_a_la_orden_y_marca_el_item_y_el_total(self):
        unidad = _unidad(1, area_ha=15.0)
        unidad["properties"]["provisorio"] = True
        orden = generar_orden_trabajo([unidad, _unidad(2, area_ha=1.0, producto="Glifosato")], CATALOGO_BASE)
        assert orden["items"][0]["provisorio"] is True
        assert orden["items"][0]["volumen_total"] == 1500.0
        assert orden["items"][1]["provisorio"] is False
        totales = {t["producto"]: t for t in orden["totales_por_producto"]}
        assert totales["Urea 46% N"]["provisorio"] is True
        assert totales["Glifosato"]["provisorio"] is False


class TestMarcaRecomendada:
    _MARCAS = {"Urea 46% N": [
        {"marca": "Barata", "concentracion": "46 %", "dosis_por_ha": 120.0, "unidad_dosis": "kg/ha",
         "precio_usd": 0.4, "costo_por_ha_usd": 48.0},
        {"marca": "Cara", "concentracion": "46 %", "dosis_por_ha": 100.0, "unidad_dosis": "kg/ha",
         "precio_usd": 0.55, "costo_por_ha_usd": 55.0},
    ]}

    def test_la_marca_recomendada_es_la_primera_alternativa(self):
        orden = generar_orden_trabajo([_unidad(1)], CATALOGO_BASE, self._MARCAS)
        assert orden["items"][0]["marca_recomendada"]["marca"] == "Barata"

    def test_dosis_y_volumen_salen_de_la_marca_recomendada(self):
        item = generar_orden_trabajo([_unidad(1, area_ha=2.0)], CATALOGO_BASE, self._MARCAS)["items"][0]
        # el activo dice 100 kg/ha; la marca recomendada, 120
        assert item["dosis_por_ha"] == 120.0
        assert item["volumen_total"] == 240.0
        assert item["producto"] == "Urea 46% N"

    def test_sin_marca_se_usa_la_dosis_del_activo(self):
        item = generar_orden_trabajo([_unidad(1, area_ha=2.0)], CATALOGO_BASE)["items"][0]
        assert (item["dosis_por_ha"], item["volumen_total"]) == (100.0, 200.0)

    def test_marca_sin_dosis_cae_a_la_del_activo(self):
        marcas = {"Urea 46% N": [{"marca": "Sin dosis", "dosis_por_ha": None}]}
        item = generar_orden_trabajo([_unidad(1, area_ha=2.0)], CATALOGO_BASE, marcas)["items"][0]
        assert item["dosis_por_ha"] == 100.0

    def test_el_total_por_activo_lleva_la_dosis_y_la_marca(self):
        total = generar_orden_trabajo([_unidad(1, area_ha=2.0), _unidad(2, area_ha=3.0)], CATALOGO_BASE, self._MARCAS)[
            "totales_por_producto"][0]
        assert total["volumen_total"] == 600.0
        assert total["dosis_por_ha"] == 120.0
        assert total["marca_recomendada"]["marca"] == "Barata"

    def test_sin_marcas_cargadas_no_hay_recomendada(self):
        assert generar_orden_trabajo([_unidad(1)], CATALOGO_BASE)["items"][0]["marca_recomendada"] is None
        assert generar_orden_trabajo([_unidad(1)], CATALOGO_BASE, {"Otro": []})["items"][0]["marca_recomendada"] is None

    def test_unidad_sin_producto_no_tiene_marca(self):
        orden = generar_orden_trabajo([_unidad(1, producto=None)], CATALOGO_BASE, self._MARCAS)
        assert orden["items"][0]["marca_recomendada"] is None


def _marca(nombre, costo, dosis=1.0):
    return [{"marca": f"Marca {nombre}", "concentracion": "10 %", "dosis_por_ha": dosis, "unidad_dosis": "L/ha",
             "precio_usd": costo / dosis, "costo_por_ha_usd": costo}]


def _unidad_con(*activos):
    u = _unidad(1, area_ha=2.0)
    u["properties"]["productos_sugeridos"] = [{"nombre": a, "tipo": "insecticida"} for a in activos]
    return u


class TestAlternativas:
    _MARCAS = {"A": _marca("A", 9.0), "B": _marca("B", 3.0), "C": _marca("C", 5.0), "D": _marca("D", 7.0), "E": _marca("E", 8.0)}

    def test_el_recomendado_es_el_de_menor_costo_por_ha_y_no_el_primero_de_la_lista(self):
        item = generar_orden_trabajo([_unidad_con("A", "B", "C")], {}, self._MARCAS)["items"][0]
        assert item["producto"] == "B"
        assert item["marca_recomendada"]["marca"] == "Marca B"

    def test_hasta_tres_alternativas_de_menor_a_mayor_costo(self):
        item = generar_orden_trabajo([_unidad_con("A", "B", "C", "D", "E")], {}, self._MARCAS)["items"][0]
        assert item["producto"] == "B"
        assert [a["producto"] for a in item["alternativas"]] == ["C", "D", "E"]
        assert [a["costo_por_ha_usd"] for a in item["alternativas"]] == [5.0, 7.0, 8.0]

    def test_con_dos_activos_hay_una_sola_alternativa(self):
        item = generar_orden_trabajo([_unidad_con("A", "B")], {}, self._MARCAS)["items"][0]
        assert [a["producto"] for a in item["alternativas"]] == ["A"]

    def test_los_totales_y_el_volumen_son_solo_del_recomendado(self):
        orden = generar_orden_trabajo([_unidad_con("A", "B", "C")], {}, self._MARCAS)
        assert [t["producto"] for t in orden["totales_por_producto"]] == ["B"]
        assert orden["items"][0]["volumen_total"] == 2.0   # 2 ha x 1.0 L/ha de la marca B

    def test_los_sin_costo_conocido_van_despues_de_los_que_tienen(self):
        marcas = {"B": _marca("B", 3.0)}
        item = generar_orden_trabajo([_unidad_con("X", "B", "Y")], {}, marcas)["items"][0]
        assert item["producto"] == "B"
        assert [a["producto"] for a in item["alternativas"]] == ["X", "Y"]   # conservan su orden
        assert item["alternativas"][0]["costo_por_ha_usd"] is None

    def test_sin_marcas_cargadas_se_mantiene_el_primero_de_la_lista(self):
        item = generar_orden_trabajo([_unidad_con("A", "B")], {})["items"][0]
        assert item["producto"] == "A"
        assert [a["producto"] for a in item["alternativas"]] == ["B"]

    def test_la_alternativa_toma_la_dosis_del_catalogo_si_no_tiene_marca(self):
        catalogo = {"Y": {"dosis_referencia": 0.3, "unidad": "kg/ha"}}
        item = generar_orden_trabajo([_unidad_con("B", "Y")], catalogo, {"B": _marca("B", 3.0)})["items"][0]
        assert (item["alternativas"][0]["dosis_por_ha"], item["alternativas"][0]["unidad_dosis"]) == (0.3, "kg/ha")

    def test_unidad_con_un_solo_activo_no_tiene_alternativas(self):
        assert generar_orden_trabajo([_unidad_con("A")], {}, self._MARCAS)["items"][0]["alternativas"] == []
