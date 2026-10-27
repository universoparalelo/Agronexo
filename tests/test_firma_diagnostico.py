"""
Tests de la firma de datos del diagnóstico (app/diagnostico/service.py::calcular_firma_datos).

El diagnóstico guardado se recalcula solo cuando cambia la firma: cualquier dato
que usa el cálculo tiene que alterarla, y el orden de las claves no.

    docker compose exec api python3 -m pytest tests/test_firma_diagnostico.py -v
"""
import copy

import pytest

from app.diagnostico.service import calcular_firma_datos

_BASE = dict(
    motor_version="1.0.0",
    lote={"nombre": "Lote Norte", "actualizado": "2026-10-27T10:00:00"},
    vuelo={
        "fecha": "2026-10-26T12:00:00", "estadio": "R3", "geojson_key": "a/b.geojson",
        "task_id": "t1", "metodo_umbral": "fijo", "mapeo_bandas": {"NIR": 4, "RED": 2},
    },
    cultivo={"id": "c1", "tipo": "soja", "variedad": None, "siembra": None, "cosecha": None},
    catalogo={"interferencia_vegetacion": [{"nombre": "Glifosato", "tipo": "herbicida"}]},
    alternativas_marca={"Glifosato": [{"marca": "Roundup", "dosis_por_ha": 2.5, "precio_usd": 6.7}]},
    indices={"ndre": "k1:t1"},
)


def _firma(**cambios):
    datos = copy.deepcopy(_BASE)
    for clave, valor in cambios.items():
        datos[clave] = valor
    return calcular_firma_datos(**datos)


def test_mismos_datos_misma_firma():
    assert _firma() == _firma()


def test_el_orden_de_las_claves_no_cambia_la_firma():
    invertido = {k: v for k, v in reversed(list(_BASE["vuelo"].items()))}
    assert _firma(vuelo=invertido) == _firma()


@pytest.mark.parametrize("campo,valor", [
    ("motor_version", "2.0.0"),
    ("lote", {"nombre": "Otro nombre", "actualizado": "2026-10-27T10:00:00"}),
    ("lote", {"nombre": "Lote Norte", "actualizado": "2026-10-28T10:00:00"}),
    ("vuelo", {**_BASE["vuelo"], "estadio": "R5"}),
    ("vuelo", {**_BASE["vuelo"], "fecha": "2026-10-27T12:00:00"}),
    ("vuelo", {**_BASE["vuelo"], "task_id": "t2"}),
    ("vuelo", {**_BASE["vuelo"], "geojson_key": "otro.geojson"}),
    ("cultivo", {**_BASE["cultivo"], "id": "c2", "tipo": "maiz"}),
    ("cultivo", {**_BASE["cultivo"], "variedad": "DK 72-10"}),
    ("catalogo", {"interferencia_vegetacion": []}),
    ("alternativas_marca", {"Glifosato": [{"marca": "Roundup", "dosis_por_ha": 2.5, "precio_usd": 7.1}]}),
    ("indices", {}),
    ("indices", {"ndre": "k1:t2"}),
    ("indices", {"ndre": "k1:t1", "savi": "k2:t3"}),
])
def test_cualquier_dato_que_cambie_altera_la_firma(campo, valor):
    assert _firma(**{campo: valor}) != _firma()
