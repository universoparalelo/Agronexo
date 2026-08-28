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
    assert len(ids) == len(set(ids)) == 20
    assert ids == [
        "R00", "R01", "R10", "R20", "R21", "R22", "R23", "R24",
        "R30", "R31", "R32", "R40", "R41", "R42", "R43", "R44",
        "R50", "R60", "R70", "R99",
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


def test_r10_malezas_tiene_prioridad_sobre_r20_fungica():
    contexto = _contexto(
        valores={"ndvi": 0.35, "exg": 0.25},
        patron_espacial="circular",
        cultivo=CultivoEnum.soja,
        estadio_normalizado="r2",
    )
    resultado = evaluar_zona(contexto)
    assert resultado.regla_id == "R10"


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
