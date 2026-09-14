"""
Tests de workers/gis/satelital_catalogo.py — búsqueda en el catálogo STAC
de Earth Search. Puro: mockea la llamada HTTP (_get_json), sin red real,
sin rasterio/numpy (ver docstring del módulo sobre por qué está separado
de satelital_descarga.py).

Correr:
    docker compose exec api python3 -m pytest tests/test_satelital_catalogo.py -v
"""
from unittest.mock import patch

import pytest

from workers.gis.satelital_catalogo import bbox_de_poligono, buscar_escenas, obtener_escena_por_id

POLIGONO = {
    "type": "Polygon",
    "coordinates": [[
        [-61.22, -27.23],
        [-61.21, -27.23],
        [-61.21, -27.22],
        [-61.22, -27.22],
        [-61.22, -27.23],
    ]],
}


def _feature_collection(items: list[dict]) -> dict:
    return {"type": "FeatureCollection", "features": items}


def _feature(item_id: str, fecha: str, nubes: float) -> dict:
    return {
        "type": "Feature",
        "id": item_id,
        "properties": {"datetime": f"{fecha}T13:00:00Z", "eo:cloud_cover": nubes},
        "assets": {},
    }


class TestBboxDePoligono:
    def test_extrae_min_max_del_anillo_exterior(self):
        bbox = bbox_de_poligono(POLIGONO)
        assert bbox == pytest.approx((-61.22, -27.23, -61.21, -27.22))


class TestBuscarEscenas:
    def test_ordena_por_cercania_a_la_fecha_elegida(self):
        catalogo = _feature_collection([
            _feature("lejos", "2026-08-20", 5.0),
            _feature("cerca", "2026-08-03", 10.0),
            _feature("medio", "2026-08-10", 0.0),
        ])
        with patch("workers.gis.satelital_catalogo._get_json", return_value=catalogo):
            escenas = buscar_escenas((-61.22, -27.23, -61.21, -27.22), "2026-08-03", ventana_dias=30)

        assert [e["id"] for e in escenas] == ["cerca", "medio", "lejos"]
        assert escenas[0]["_dias_de_diferencia"] == 0

    def test_calcula_dias_de_diferencia_correctamente(self):
        catalogo = _feature_collection([_feature("x", "2026-08-10", 0.0)])
        with patch("workers.gis.satelital_catalogo._get_json", return_value=catalogo):
            escenas = buscar_escenas((-61.22, -27.23, -61.21, -27.22), "2026-08-03", ventana_dias=30)
        assert escenas[0]["_dias_de_diferencia"] == 7

    def test_sin_escenas_lanza_runtime_error(self):
        with patch("workers.gis.satelital_catalogo._get_json", return_value=_feature_collection([])):
            with pytest.raises(RuntimeError):
                buscar_escenas((-61.22, -27.23, -61.21, -27.22), "2026-08-03", ventana_dias=15)

    def test_conserva_nubes_pct_de_cada_escena(self):
        catalogo = _feature_collection([_feature("a", "2026-08-01", 58.0), _feature("b", "2026-08-06", 0.004)])
        with patch("workers.gis.satelital_catalogo._get_json", return_value=catalogo):
            escenas = buscar_escenas((-61.22, -27.23, -61.21, -27.22), "2026-08-03", ventana_dias=15)
        nubes_por_id = {e["id"]: e["properties"]["eo:cloud_cover"] for e in escenas}
        assert nubes_por_id == {"a": 58.0, "b": 0.004}


class TestObtenerEscenaPorId:
    def test_devuelve_el_item_consultado(self):
        item = _feature("S2B_20JPQ_20260806_0_L2A", "2026-08-06", 0.004)
        with patch("workers.gis.satelital_catalogo._get_json", return_value=item) as mock_get:
            resultado = obtener_escena_por_id("S2B_20JPQ_20260806_0_L2A")
        assert resultado == item
        assert "S2B_20JPQ_20260806_0_L2A" in mock_get.call_args[0][0]


if __name__ == "__main__":
    import sys
    raise SystemExit(pytest.main([__file__, "-v"]))
