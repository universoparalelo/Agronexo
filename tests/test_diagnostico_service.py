"""
Tests de _resolver_estadio (app/diagnostico/service.py). Puro — objetos
mínimos armados a mano, sin base de datos, siguiendo el mismo criterio que
test_diagnostico_engine.py.
"""
from types import SimpleNamespace

from app.diagnostico.service import _resolver_estadio


def _lote(estadio_fenologico=None):
    return SimpleNamespace(estadio_fenologico=estadio_fenologico)


def _vuelo(estadio_fenologico=None):
    return SimpleNamespace(estadio_fenologico=estadio_fenologico)


def test_estadio_del_vuelo_tiene_prioridad_sobre_el_del_lote():
    lote = _lote(estadio_fenologico="V3")
    vuelo = _vuelo(estadio_fenologico="R2")
    assert _resolver_estadio(lote, vuelo) == "R2"


def test_cae_al_estadio_del_lote_si_el_vuelo_no_lo_tiene():
    lote = _lote(estadio_fenologico="V3")
    vuelo = _vuelo(estadio_fenologico=None)
    assert _resolver_estadio(lote, vuelo) == "V3"


def test_devuelve_none_si_ninguno_lo_tiene():
    lote = _lote(estadio_fenologico=None)
    vuelo = _vuelo(estadio_fenologico=None)
    assert _resolver_estadio(lote, vuelo) is None
