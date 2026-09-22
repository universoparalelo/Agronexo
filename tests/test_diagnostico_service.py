"""
Tests de _resolver_estadio (app/diagnostico/service.py). Puro — objetos
mínimos armados a mano, sin base de datos, siguiendo el mismo criterio que
test_diagnostico_engine.py.

El estadio fenológico es siempre el del vuelo: ni el lote ni el cultivo lo
guardan (migración 0020).
"""
from types import SimpleNamespace

from app.diagnostico.service import _resolver_estadio


def _vuelo(estadio_fenologico=None):
    return SimpleNamespace(estadio_fenologico=estadio_fenologico)


def test_usa_el_estadio_del_vuelo():
    assert _resolver_estadio(_vuelo(estadio_fenologico="R2")) == "R2"


def test_devuelve_none_si_el_vuelo_no_lo_tiene():
    assert _resolver_estadio(_vuelo(estadio_fenologico=None)) is None
