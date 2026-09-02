"""
Tests de app/diagnostico/zonificacion.py — agrupación de zonas contiguas
en unidades de manejo (RFDR-02). Puro: geometrías Shapely sintéticas,
sin I/O, sin DB.

Correr:
    docker compose exec api python3 -m pytest tests/test_zonificacion.py -v
"""
import pytest
from shapely.geometry import mapping, Point, box

from app.diagnostico.zonificacion import (
    BUFFER_CONTIGUIDAD_M,
    _componentes_conexos,
    generar_unidades_manejo,
)

LON0, LAT0 = -60.70, -27.10


def _feature(zona_id, lon, lat, radius_deg=0.001, causa="estres_hidrico",
             severidad="moderada", regla_id="R40", ndvi=0.35, area_ha=1.0):
    geom = Point(lon, lat).buffer(radius_deg)
    return {
        "type": "Feature",
        "geometry": mapping(geom),
        "properties": {
            "zona_id": zona_id,
            "causa_indice": causa,
            "severidad": severidad,
            "regla_id": regla_id,
            "ndvi_promedio": ndvi,
            "area_ha": area_ha,
            "regla_nombre": f"Regla {regla_id}",
            "accion_recomendada": "Acción test",
            "productos_sugeridos": [{"nombre": "Producto Test"}],
        },
    }


# ── _componentes_conexos ────────────────────────────────────────────────

class TestComponentesConexos:
    def test_sin_nodos(self):
        assert _componentes_conexos([], {}) == []

    def test_nodos_aislados(self):
        result = _componentes_conexos([0, 1, 2], {0: set(), 1: set(), 2: set()})
        assert len(result) == 3
        assert all(len(c) == 1 for c in result)

    def test_un_componente_conectado(self):
        adj = {0: {1}, 1: {0, 2}, 2: {1}}
        result = _componentes_conexos([0, 1, 2], adj)
        assert len(result) == 1
        assert sorted(result[0]) == [0, 1, 2]

    def test_dos_componentes(self):
        adj = {0: {1}, 1: {0}, 2: {3}, 3: {2}}
        result = _componentes_conexos([0, 1, 2, 3], adj)
        assert len(result) == 2
        componentes_sorted = [sorted(c) for c in result]
        assert [0, 1] in componentes_sorted
        assert [2, 3] in componentes_sorted


# ── generar_unidades_manejo ─────────────────────────────────────────────

class TestGenerarUnidadesManejo:
    def test_sin_features_retorna_vacio(self):
        assert generar_unidades_manejo([], LON0, LAT0) == []

    def test_solo_r99_retorna_vacio(self):
        features = [
            _feature(0, -60.700, -27.100, regla_id="R99", causa="sin_problema_detectado", severidad="normal"),
            _feature(1, -60.695, -27.100, regla_id="R99", causa="sin_problema_detectado", severidad="normal"),
        ]
        assert generar_unidades_manejo(features, LON0, LAT0) == []

    def test_solo_r00_retorna_vacio(self):
        features = [
            _feature(0, -60.700, -27.100, regla_id="R00", causa="obstaculo", severidad="normal"),
        ]
        assert generar_unidades_manejo(features, LON0, LAT0) == []

    def test_severidad_normal_excluida(self):
        features = [
            _feature(0, -60.700, -27.100, severidad="normal"),
        ]
        assert generar_unidades_manejo(features, LON0, LAT0) == []

    def test_una_zona_genera_una_unidad(self):
        features = [
            _feature(0, -60.700, -27.100, severidad="moderada"),
        ]
        unidades = generar_unidades_manejo(features, LON0, LAT0)
        assert len(unidades) == 1
        u = unidades[0]
        assert u["type"] == "Feature"
        assert u["properties"]["n_zonas"] == 1
        assert u["properties"]["causa_indice"] == "estres_hidrico"
        assert u["properties"]["severidad"] == "moderada"
        assert u["properties"]["texto_unidad"]  # no vacío

    def test_zonas_contiguas_misma_causa_se_agrupan(self):
        features = [
            _feature(0, -60.700, -27.100, causa="estres_hidrico", severidad="moderada"),
            _feature(1, -60.7015, -27.100, causa="estres_hidrico", severidad="moderada"),
        ]
        unidades = generar_unidades_manejo(features, LON0, LAT0)
        assert len(unidades) == 1
        assert unidades[0]["properties"]["n_zonas"] == 2
        assert sorted(unidades[0]["properties"]["zona_ids"]) == [0, 1]

    def test_zonas_distantes_misma_causa_no_se_agrupan(self):
        features = [
            _feature(0, -60.700, -27.100, causa="estres_hidrico", severidad="moderada"),
            _feature(1, -60.650, -27.050, causa="estres_hidrico", severidad="moderada"),
        ]
        unidades = generar_unidades_manejo(features, LON0, LAT0)
        assert len(unidades) == 2
        assert all(u["properties"]["n_zonas"] == 1 for u in unidades)

    def test_distinta_causa_no_se_agrupan(self):
        features = [
            _feature(0, -60.700, -27.100, causa="estres_hidrico", severidad="moderada"),
            _feature(1, -60.7015, -27.100, causa="estres_biotico_fungico", severidad="moderada"),
        ]
        unidades = generar_unidades_manejo(features, LON0, LAT0)
        assert len(unidades) == 2

    def test_distinta_severidad_no_se_agrupan(self):
        features = [
            _feature(0, -60.700, -27.100, causa="estres_hidrico", severidad="moderada"),
            _feature(1, -60.7015, -27.100, causa="estres_hidrico", severidad="critica"),
        ]
        unidades = generar_unidades_manejo(features, LON0, LAT0)
        assert len(unidades) == 2

    def test_ndvi_promedio_ponderado_por_area(self):
        features = [
            _feature(0, -60.700, -27.100, ndvi=0.30, area_ha=2.0, severidad="moderada"),
            _feature(1, -60.7015, -27.100, ndvi=0.50, area_ha=3.0, severidad="moderada"),
        ]
        unidades = generar_unidades_manejo(features, LON0, LAT0)
        assert len(unidades) == 1
        # (0.30*2 + 0.50*3) / (2+3) = 2.10/5 = 0.42
        assert unidades[0]["properties"]["ndvi_promedio"] == 0.420

    def test_area_total_es_suma(self):
        features = [
            _feature(0, -60.700, -27.100, area_ha=1.5, severidad="moderada"),
            _feature(1, -60.7015, -27.100, area_ha=2.5, severidad="moderada"),
        ]
        unidades = generar_unidades_manejo(features, LON0, LAT0)
        assert unidades[0]["properties"]["area_total_ha"] == 4.0

    def test_unidades_ordenadas_critica_primero(self):
        features = [
            _feature(0, -60.700, -27.100, severidad="leve"),
            _feature(1, -60.650, -27.050, severidad="critica"),
            _feature(2, -60.600, -27.000, severidad="moderada"),
        ]
        unidades = generar_unidades_manejo(features, LON0, LAT0)
        severidades = [u["properties"]["severidad"] for u in unidades]
        assert severidades == ["critica", "moderada", "leve"]

    def test_mezcla_r99_y_problemas(self):
        features = [
            _feature(0, -60.700, -27.100, regla_id="R99", causa="sin_problema_detectado", severidad="normal"),
            _feature(1, -60.695, -27.100, causa="estres_hidrico", severidad="moderada"),
            _feature(2, -60.690, -27.100, regla_id="R99", causa="sin_problema_detectado", severidad="normal"),
        ]
        unidades = generar_unidades_manejo(features, LON0, LAT0)
        assert len(unidades) == 1
        assert unidades[0]["properties"]["zona_ids"] == [1]

    def test_geometria_unidad_es_geojson_valido(self):
        features = [
            _feature(0, -60.700, -27.100, severidad="moderada"),
        ]
        unidades = generar_unidades_manejo(features, LON0, LAT0)
        geom = unidades[0]["geometry"]
        assert geom["type"] in ("Polygon", "MultiPolygon")
        assert "coordinates" in geom

    def test_tres_zonas_dos_contiguas_una_distante(self):
        features = [
            _feature(0, -60.700, -27.100, severidad="moderada"),
            _feature(1, -60.7015, -27.100, severidad="moderada"),
            _feature(2, -60.650, -27.050, severidad="moderada"),
        ]
        unidades = generar_unidades_manejo(features, LON0, LAT0)
        assert len(unidades) == 2
        n_zonas_list = sorted([u["properties"]["n_zonas"] for u in unidades])
        assert n_zonas_list == [1, 2]


if __name__ == "__main__":
    import sys
    raise SystemExit(pytest.main([__file__, "-v"]))
