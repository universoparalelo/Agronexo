"""
Tests del motor probabilístico (app/diagnostico/bayes.py). Puro, sin DB.

    docker compose exec api python3 -m pytest tests/test_bayes.py -v
"""
import pytest

from app.diagnostico.bayes import (
    CAUSAS, VALORES_EVIDENCIA, EvidenciaZona, causa_efectiva, construir_modelo,
    discretizar, evaluar_bayes, fase_fenologica, nivel_certeza,
)
from app.lotes.models import CultivoEnum


def _ev(**kw):
    base = dict(cultivo=CultivoEnum.soja, estadio="R3", patron="circular", ndvi=0.45,
                ndvi_promedio_lote=0.70, ndvi_esperado=0.745, ndvi_esperado_min=0.625)
    base.update(kw)
    return EvidenciaZona(**base)


def test_tablas_expertas_suman_uno():
    modelo = construir_modelo()
    for fase, dist in modelo.prior.items():
        assert sum(dist.values()) == pytest.approx(1.0), fase
    for nombre, por_causa in modelo.verosimilitud.items():
        for causa in CAUSAS:
            assert sum(por_causa[causa].values()) == pytest.approx(1.0), (nombre, causa)
            assert set(por_causa[causa]) == set(VALORES_EVIDENCIA[nombre])


@pytest.mark.parametrize("cultivo,estadio,fase", [
    (CultivoEnum.soja, "V2", "temprana"),
    (CultivoEnum.soja, "V6", "vegetativa"),
    (CultivoEnum.soja, "R3", "reproductiva"),
    (CultivoEnum.soja, "R7", "madurez"),
    (CultivoEnum.algodon, "Botón floral", "reproductiva"),
    (CultivoEnum.algodon, "Apertura de cápsulas", "madurez"),
    (CultivoEnum.maiz, None, "desconocida"),
])
def test_fase_fenologica(cultivo, estadio, fase):
    assert fase_fenologica(cultivo, estadio) == fase


def test_desvio_usa_lo_esperado_para_el_estadio():
    assert discretizar(_ev(ndvi=0.35, estadio="V3", ndvi_esperado=0.446, ndvi_esperado_min=0.326))["desvio"] == "normal"
    assert discretizar(_ev(ndvi=0.55))["desvio"] == "bajo"
    assert discretizar(_ev(ndvi=0.40))["desvio"] == "muy_bajo"


def test_sin_curva_el_desvio_es_contra_el_lote():
    d = discretizar(_ev(ndvi=0.40, ndvi_esperado=None, ndvi_esperado_min=None, ndvi_promedio_lote=0.70))
    assert d["desvio"] == "muy_bajo"


def test_indices_sin_dato_no_entran_como_evidencia():
    d = discretizar(_ev())
    assert "ndre" not in d and "exg" not in d


def test_mancha_circular_baja_en_reproductivo_es_hongo():
    r = evaluar_bayes(_ev(), construir_modelo())
    assert r["ranking"][0]["causa"] == "estres_biotico_fungico"
    assert sum(x["probabilidad"] for x in r["ranking"]) <= 1.0


def test_lineal_bajo_es_compactacion():
    r = evaluar_bayes(_ev(patron="lineal"), construir_modelo())
    assert r["ranking"][0]["causa"] == "compactacion_falla_siembra"


def test_zona_normal_es_sin_problema():
    r = evaluar_bayes(_ev(ndvi=0.74, patron="por_sectores"), construir_modelo())
    assert r["ranking"][0]["causa"] == "sin_problema_detectado"


def test_ndre_bajo_difuso_en_vegetativo_favorece_nitrogeno():
    r = evaluar_bayes(_ev(estadio="V6", patron="difuso_homogeneo", ndvi=0.45, ndre=0.12,
                          ndvi_esperado=0.62, ndvi_esperado_min=0.50), construir_modelo())
    assert r["ranking"][0]["causa"] == "estres_nutricional_nitrogeno"


def test_madurez_temprana_casi_nula_fuera_de_algodon():
    ev = dict(estadio="R7", patron="manchas_irregulares", ndvi=0.15, ndvi_esperado=0.45, ndvi_esperado_min=0.33)
    soja = evaluar_bayes(_ev(**ev), construir_modelo())
    algodon = evaluar_bayes(_ev(cultivo=CultivoEnum.algodon, **{**ev, "estadio": "R5"}), construir_modelo())
    p = lambda r: next((x["probabilidad"] for x in r["ranking"] if x["causa"] == "madurez_temprana_diferencial"), 0)
    assert p(algodon) > p(soja)


def test_nivel_certeza():
    assert nivel_certeza([("a", 0.80), ("b", 0.10)]) == "alta"
    assert nivel_certeza([("a", 0.45), ("b", 0.20)]) == "media"
    assert nivel_certeza([("a", 0.40), ("b", 0.35)]) == "ambigua"


def test_revisiones_del_agronomo_mueven_el_modelo():
    # Caso ambiguo de por sí: manchas irregulares bajas en vegetativo.
    ev = _ev(estadio="V6", patron="manchas_irregulares", ndvi=0.48, ndvi_esperado=0.62, ndvi_esperado_min=0.50)
    antes = evaluar_bayes(ev, construir_modelo())
    modelo = construir_modelo([(ev, "estres_nutricional_micro")] * 30)
    despues = evaluar_bayes(ev, modelo)
    assert modelo.n_casos == 30
    assert despues["ranking"][0]["causa"] == "estres_nutricional_micro"
    assert antes["ranking"][0]["causa"] != "estres_nutricional_micro"


def test_casos_con_causa_desconocida_se_ignoran():
    assert construir_modelo([(_ev(), "bajo_vigor_estadio")]).n_casos == 0


def test_causa_efectiva():
    assert causa_efectiva("R01", "sin_problema_detectado") == "suelo_desnudo"
    assert causa_efectiva("R99", "sin_problema_detectado") == "sin_problema_detectado"
    assert causa_efectiva("R80", "bajo_vigor_estadio") is None


def test_evidencia_ida_y_vuelta_por_dict():
    ev = _ev(ndre=0.1)
    assert EvidenciaZona.desde_dict(ev.a_dict()) == ev
