"""
Consistencia de la lista de estadios que ve el usuario (ESTADIOS_POR_CULTIVO)
con los tokens que usa el motor de reglas, y del endpoint que la expone.

Correr en el contenedor api:
    docker compose exec api python3 -m pytest tests/test_estadios.py -v
"""
import uuid

from starlette.testclient import TestClient

from app.diagnostico.estadios import ESTADIOS_POR_CULTIVO, ESTADIOS_VALIDOS_POR_CULTIVO, normalizar_estadio
from app.diagnostico.reglas import REGLAS
from app.lotes.models import CultivoEnum
from app.main import app


def test_toda_regla_puede_matchear_con_la_lista_de_su_cultivo():
    # Si una regla exige el estadio "boton_floral" y la lista del algodón no
    # ofrece nada que normalice a eso, esa regla nunca podría dispararse.
    for regla in REGLAS:
        if regla.estadios is None:
            continue
        cultivos = regla.cultivos or frozenset(CultivoEnum)
        for cultivo in cultivos:
            normalizados = {normalizar_estadio(e) for e in ESTADIOS_POR_CULTIVO[cultivo]}
            assert normalizados & regla.estadios, (
                f"{regla.id}: ningún estadio de {cultivo.value} normaliza a {sorted(regla.estadios)}"
            )


def test_la_lista_incluye_todo_el_catalogo_de_referencia():
    for cultivo, tokens in ESTADIOS_VALIDOS_POR_CULTIVO.items():
        normalizados = {normalizar_estadio(e) for e in ESTADIOS_POR_CULTIVO[cultivo]}
        assert tokens <= normalizados, f"{cultivo.value}: faltan {sorted(tokens - normalizados)}"


def test_todos_los_cultivos_tienen_lista_sin_repetidos():
    assert set(ESTADIOS_POR_CULTIVO) == set(CultivoEnum)
    for cultivo, estadios in ESTADIOS_POR_CULTIVO.items():
        assert estadios and len(estadios) == len(set(estadios)), cultivo.value
        assert all(len(e) <= 30 for e in estadios)  # límite de vuelos.estadio_fenologico


# ── Endpoint ─────────────────────────────────────────────────────────

_tc = TestClient(app)
_token = ""


def setup_module(module):
    global _token
    from app.core.database import engine as _engine
    _engine.sync_engine.dispose(close=False)
    _tc.__enter__()
    email = f"estadios_{uuid.uuid4().hex[:8]}@agronexo-test.com"
    _tc.post("/api/v1/auth/register", json={"email": email, "nombre": "Test Estadios", "password": "estadios_pass_1"})
    r = _tc.post("/api/v1/auth/login", json={"email": email, "password": "estadios_pass_1"})
    assert r.status_code == 200, r.text
    _token = r.json()["access_token"]


def teardown_module(module):
    _tc.__exit__(None, None, None)


def test_endpoint_devuelve_los_estadios_por_cultivo():
    r = _tc.get("/api/v1/estadios-fenologicos", headers={"Authorization": f"Bearer {_token}"})
    assert r.status_code == 200
    estadios = r.json()["estadios"]
    assert set(estadios) == {"soja", "maiz", "algodon", "sorgo"}
    assert estadios["soja"][:3] == ["VE", "VC", "V1"] and "R8" in estadios["soja"]
    assert "Botón floral" in estadios["algodon"]


def test_endpoint_sin_auth():
    assert _tc.get("/api/v1/estadios-fenologicos").status_code == 401
