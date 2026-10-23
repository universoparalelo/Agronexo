"""
Tests del evaluador en cascada (app/diagnostico/engine.py) y del catálogo
de reglas (app/diagnostico/reglas.py). Puro — ContextoZona construidos a
mano, sin base de datos ni GeoJSON real.
"""
import pytest

from app.diagnostico.engine import ContextoZona, evaluar_zona
from app.diagnostico.estadios import normalizar_estadio
from app.diagnostico.reglas import REGLAS
from app.lotes.models import CultivoEnum


def _contexto(**overrides) -> ContextoZona:
    base = dict(
        zona_id=0,
        valores={"ndvi": 0.60},
        patron_espacial="manchas_irregulares",
        area_ha=1.0,
        ndvi_promedio_lote=0.60,
        cultivo=CultivoEnum.soja,
        estadio_normalizado=None,
    )
    base.update(overrides)
    return ContextoZona(**base)


# ── Integridad del catálogo ───────────────────────────────────────────

def test_ids_de_reglas_son_unicos_y_en_orden_documentado():
    ids = [r.id for r in REGLAS]
    assert len(ids) == len(set(ids)) == 22
    assert ids == [
        "R00", "R60", "R01", "R20", "R21", "R22", "R23", "R24",
        "R30", "R31", "R32", "R45", "R10", "R40", "R41", "R42", "R43", "R44",
        "R50", "R70", "R80", "R99",
    ]


def test_r99_no_tiene_requisitos_y_siempre_matchea():
    contexto = _contexto(valores={}, patron_espacial="cualquiera", cultivo=CultivoEnum.maiz)
    resultado = evaluar_zona(contexto)
    assert resultado.regla_id == "R99"


# ── Orden de cascada y prioridad ──────────────────────────────────────

def test_r00_antes_que_r01_zona_pequena_circular_ndvi_bajo():
    contexto = _contexto(valores={"ndvi": 0.10}, patron_espacial="circular", area_ha=0.02)
    resultado = evaluar_zona(contexto)
    assert resultado.regla_id == "R00"
    assert resultado.excluida is True


def test_r01_cuando_ndvi_bajo_pero_no_circular_o_zona_grande():
    contexto = _contexto(valores={"ndvi": 0.10}, patron_espacial="manchas_irregulares", area_ha=2.0)
    resultado = evaluar_zona(contexto)
    assert resultado.regla_id == "R01"


def test_r20_fungica_tiene_prioridad_sobre_r10_malezas():
    # v1.1.0: con ExG disponible, R10 tapaba toda mancha circular en
    # reproductivo — ahora el patrón de enfermedad se evalúa primero.
    contexto = _contexto(
        valores={"ndvi": 0.35, "exg": 0.25},
        patron_espacial="circular",
        cultivo=CultivoEnum.soja,
        estadio_normalizado="r2",
    )
    resultado = evaluar_zona(contexto)
    assert resultado.regla_id == "R20"


def test_r10_malezas_cuando_ningun_patron_biotico_aplica():
    contexto = _contexto(
        valores={"ndvi": 0.35, "exg": 0.25},
        patron_espacial="por_sectores",
        cultivo=CultivoEnum.soja,
        estadio_normalizado="r2",
    )
    assert evaluar_zona(contexto).regla_id == "R10"


def test_r20_matchea_cuando_no_hay_dato_de_exg():
    # Sin "exg" en valores, R10 no puede evaluarse (requiere_indices no
    # está contenido en las claves disponibles) y se salta sin excepción.
    contexto = _contexto(
        valores={"ndvi": 0.35},
        patron_espacial="circular",
        cultivo=CultivoEnum.soja,
        estadio_normalizado="r2",
    )
    resultado = evaluar_zona(contexto)
    assert resultado.regla_id == "R20"


# ── Filtro por cultivo y estadio ───────────────────────────────────────

def test_regla_de_soja_no_matchea_en_maiz():
    contexto = _contexto(
        valores={"ndvi": 0.35},
        patron_espacial="circular",
        cultivo=CultivoEnum.maiz,       # R20 es solo para soja
        estadio_normalizado="r2",
    )
    resultado = evaluar_zona(contexto)
    assert resultado.regla_id != "R20"
    assert resultado.regla_id == "R99"  # maíz+R2 no matchea ninguna otra regla de este contexto


def test_zona_sin_estadio_no_matchea_reglas_con_estadio_especifico():
    contexto = _contexto(
        valores={"ndvi": 0.35},
        patron_espacial="circular",
        cultivo=CultivoEnum.soja,
        estadio_normalizado=None,       # lote sin estadio cargado
    )
    resultado = evaluar_zona(contexto)
    assert resultado.regla_id == "R99"


def test_estadio_fuera_de_rango_no_matchea():
    contexto = _contexto(
        valores={"ndvi": 0.35},
        patron_espacial="circular",
        cultivo=CultivoEnum.soja,
        estadio_normalizado="v1",       # R20 exige R1-R5
    )
    resultado = evaluar_zona(contexto)
    assert resultado.regla_id == "R99"


# ── Multi-índice: R44 requiere NDVI y NDRE simultáneos ─────────────────

def test_r44_requiere_ambos_indices_simultaneos():
    contexto_completo = _contexto(
        valores={"ndvi": 0.40, "ndre": 0.15},
        patron_espacial="difuso_homogeneo",
        cultivo=CultivoEnum.soja,
        estadio_normalizado="v3",
    )
    assert evaluar_zona(contexto_completo).regla_id == "R44"

    contexto_sin_ndre = _contexto(
        valores={"ndvi": 0.40},
        patron_espacial="difuso_homogeneo",
        cultivo=CultivoEnum.soja,
        estadio_normalizado="v3",
    )
    resultado = evaluar_zona(contexto_sin_ndre)
    assert resultado.regla_id != "R44"


# ── R60: comparación contra el promedio del lote ───────────────────────

def test_r60_madurez_diferencial_algodon():
    # ndvi=0.22: por encima de 0.20 (no dispara R01 "suelo desnudo") pero
    # por debajo de 0.25 y de 0.40*0.60=0.24 (condiciones de R60).
    contexto = _contexto(
        valores={"ndvi": 0.22},
        patron_espacial="focos_aislados",
        area_ha=0.3,
        ndvi_promedio_lote=0.60,
        cultivo=CultivoEnum.algodon,
        estadio_normalizado="r4",
    )
    resultado = evaluar_zona(contexto)
    assert resultado.regla_id == "R60"


def test_r60_no_matchea_si_no_esta_suficientemente_por_debajo_del_promedio():
    contexto = _contexto(
        valores={"ndvi": 0.23},         # < 0.25 pero NO < 0.40 * 0.30 = 0.12
        patron_espacial="focos_aislados",
        ndvi_promedio_lote=0.30,
        cultivo=CultivoEnum.algodon,
        estadio_normalizado="r4",
    )
    resultado = evaluar_zona(contexto)
    assert resultado.regla_id != "R60"


# ── Zona neutra ─────────────────────────────────────────────────────────

def test_zona_sana_resuelve_en_r99():
    contexto = _contexto(valores={"ndvi": 0.65}, patron_espacial="manchas_irregulares")
    resultado = evaluar_zona(contexto)
    assert resultado.regla_id == "R99"
    assert resultado.excluida is False


# ── normalizar_estadio ───────────────────────────────────────────────

@pytest.mark.parametrize("crudo,esperado", [
    ("R3", "r3"),
    (" v4 ", "v4"),
    ("Botón floral", "boton_floral"),
    ("apertura de cápsulas", "apertura_de_capsulas"),
    (None, None),
    ("", None),
])
def test_normalizar_estadio(crudo, esperado):
    assert normalizar_estadio(crudo) == esperado


if __name__ == "__main__":
    import sys
    raise SystemExit(pytest.main([__file__, "-v"]))


# ── v1.1.0: NDVI bajo relativo al estadio ──────────────────────────────

def test_ndvi_bajo_en_estadio_temprano_no_es_alarma_si_esta_en_rango():
    # Soja V3 con NDVI 0.35: dentro del rango normal (mín 0.33) — antes salía
    # "estrés hídrico" por el corte fijo de 0.50.
    contexto = _contexto(
        valores={"ndvi": 0.35}, patron_espacial="difuso_homogeneo", ndvi_promedio_lote=0.35,
        estadio_normalizado="v3", ndvi_esperado=0.446, ndvi_esperado_min=0.326,
    )
    assert evaluar_zona(contexto).regla_id == "R99"


def test_lote_parejo_bajo_para_el_estadio_ya_no_es_sin_problema():
    contexto = _contexto(
        valores={"ndvi": 0.30}, patron_espacial="por_sectores", ndvi_promedio_lote=0.32,
        estadio_normalizado="r5", ndvi_esperado=0.587, ndvi_esperado_min=0.467,
    )
    resultado = evaluar_zona(contexto)
    assert resultado.regla_id == "R80"
    assert resultado.causa_indice == "bajo_vigor_estadio"


def test_ndvi_sobre_el_corte_fijo_pero_bajo_para_el_estadio_dispara_regla():
    contexto = _contexto(
        valores={"ndvi": 0.55}, patron_espacial="circular",
        estadio_normalizado="r3", ndvi_esperado=0.745, ndvi_esperado_min=0.625,
    )
    assert evaluar_zona(contexto).regla_id == "R20"


def test_sin_curva_esperada_se_mantiene_el_corte_fijo():
    contexto = _contexto(valores={"ndvi": 0.45}, patron_espacial="difuso_homogeneo", estadio_normalizado=None)
    assert evaluar_zona(contexto).regla_id == "R50"
    contexto = _contexto(valores={"ndvi": 0.55}, patron_espacial="por_sectores", estadio_normalizado=None)
    assert evaluar_zona(contexto).regla_id == "R99"


def test_r01_no_marca_suelo_desnudo_en_emergencia():
    contexto = _contexto(
        valores={"ndvi": 0.15}, patron_espacial="manchas_irregulares", area_ha=2.0,
        estadio_normalizado="ve", ndvi_esperado=0.15, ndvi_esperado_min=0.03,
    )
    assert evaluar_zona(contexto).regla_id == "R99"


def test_r45_patron_lineal_bajo():
    contexto = _contexto(valores={"ndvi": 0.35}, patron_espacial="lineal", estadio_normalizado="r3")
    resultado = evaluar_zona(contexto)
    assert resultado.regla_id == "R45"
    assert resultado.causa_indice == "compactacion_falla_siembra"


def test_r60_alcanzable_con_ndvi_menor_a_020():
    contexto = _contexto(
        valores={"ndvi": 0.15}, patron_espacial="manchas_irregulares", area_ha=2.0,
        ndvi_promedio_lote=0.60, cultivo=CultivoEnum.algodon, estadio_normalizado="r5",
    )
    assert evaluar_zona(contexto).regla_id == "R60"


# ── v1.2.0: R80 se precisa con el motor probabilístico ─────────────────

from app.diagnostico.engine import precisar_con_bayes  # noqa: E402


def _r80():
    return evaluar_zona(_contexto(
        valores={"ndvi": 0.26}, patron_espacial="por_sectores", ndvi_promedio_lote=0.30,
        estadio_normalizado="v6", ndvi_esperado=0.628, ndvi_esperado_min=0.508,
    ))


def _bayes(*ranking):
    return {"ranking": [{"causa": c, "probabilidad": p} for c, p in ranking]}


def test_r80_adopta_la_causa_probabilistica_cuando_es_clara():
    r = precisar_con_bayes(_r80(), _bayes(("estres_hidrico", 0.55), ("estres_nutricional_nitrogeno", 0.20)),
                           CultivoEnum.soja, {"ndvi", "ndre"})
    assert r.regla_id == "R80"
    assert r.causa_indice == "estres_hidrico"
    assert "probable estrés hídrico" in r.regla_nombre
    assert r.confianza.value == "baja"
    # 0.55 / (0.55 + 0.20): renormalizado sin "sin problema"
    assert "73%" in r.accion_recomendada


def test_r80_con_empate_da_diferencial_y_pide_el_indice_que_falta():
    r = precisar_con_bayes(_r80(), _bayes(("estres_hidrico", 0.26), ("estres_nutricional_nitrogeno", 0.25),
                                          ("estres_nutricional_fosforo", 0.14)),
                           CultivoEnum.soja, {"ndvi"})
    assert r.causa_indice == "bajo_vigor_estadio"
    assert r.regla_nombre == "Vigor bajo para el estadio — estrés hídrico o déficit de nitrógeno"
    assert "Calcular NDRE" in r.accion_recomendada
    assert "Para confirmar estrés hídrico:" in r.como_confirmar_campo
    assert "Para confirmar déficit de nitrógeno:" in r.como_confirmar_campo


def test_r80_ignora_sin_problema_como_candidata():
    r = precisar_con_bayes(_r80(), _bayes(("sin_problema_detectado", 0.6), ("estres_biotico_insecto", 0.3),
                                          ("estres_hidrico", 0.05)),
                           CultivoEnum.soja, {"ndvi"})
    assert r.causa_indice == "estres_biotico_insecto"


def test_precisar_no_toca_otras_reglas():
    r = evaluar_zona(_contexto(valores={"ndvi": 0.35}, patron_espacial="lineal"))
    assert precisar_con_bayes(r, _bayes(("estres_hidrico", 0.9)), CultivoEnum.soja, {"ndvi"}) is r


def test_r80_no_repite_probable_en_el_nombre():
    r = precisar_con_bayes(_r80(), _bayes(("estres_biotico_insecto", 0.6), ("estres_hidrico", 0.1)),
                           CultivoEnum.soja, {"ndvi"})
    assert r.regla_nombre == "Vigor bajo para el estadio — probable ataque de insectos"
