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
