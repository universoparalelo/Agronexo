"""
Tests de PUT /lotes/{id}/vuelos/{id} (editar fecha, estadio y cultivo de un vuelo).

Los vuelos se insertan directamente en la BD, igual que test_vuelos_estado.py.

    docker compose exec api python3 -m pytest tests/test_vuelos_editar.py -v
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine, text
from starlette.testclient import TestClient

from app.core.config import settings
from app.main import app

_EMAIL = f"vuelos_editar_{uuid.uuid4().hex[:8]}@agronexo-test.com"
_PASS = "vuelos_pass_789"
_GEOM = {
    "type": "Polygon",
    "coordinates": [[
        [-60.6753, -27.4693], [-60.6701, -27.4693], [-60.6701, -27.4741],
        [-60.6753, -27.4741], [-60.6753, -27.4693],
    ]],
}

_tc = TestClient(app)
_token: str = ""
_lote_id: str = ""
_cultivo_soja: str = ""
_cultivo_maiz: str = ""


def setup_module(module):
    global _token, _lote_id, _cultivo_soja, _cultivo_maiz
    from app.core.database import engine as _engine
    _engine.sync_engine.dispose(close=False)
    _tc.__enter__()
    _tc.post("/api/v1/auth/register", json={"email": _EMAIL, "nombre": "Test Editar", "password": _PASS})
    r = _tc.post("/api/v1/auth/login", json={"email": _EMAIL, "password": _PASS})
    assert r.status_code == 200, r.text
    _token = r.json()["access_token"]
    r = _tc.post("/api/v1/lotes", json={"nombre": "Lote Editar Vuelos", "geometry": _GEOM}, headers=_auth())
    assert r.status_code == 201, r.text
    _lote_id = r.json()["id"]
    r = _tc.post(f"/api/v1/lotes/{_lote_id}/cultivos", json={"tipo_cultivo": "soja"}, headers=_auth())
    assert r.status_code == 201, r.text
    _cultivo_soja = r.json()["id"]
    r = _tc.post(f"/api/v1/lotes/{_lote_id}/cultivos", json={"tipo_cultivo": "maiz"}, headers=_auth())
    assert r.status_code == 201, r.text
    _cultivo_maiz = r.json()["id"]


def teardown_module(module):
    _tc.__exit__(None, None, None)


def _auth() -> dict:
    return {"Authorization": f"Bearer {_token}"}


def _insertar_vuelo(lote_id: str) -> str:
    vuelo_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    engine = create_engine(settings.database_url_sync)
    with engine.connect() as conn:
        conn.execute(text(
            "INSERT INTO vuelos (id, lote_id, cultivo_id, sensor, fecha_vuelo, estadio_fenologico, estado, created_at) "
            "VALUES (CAST(:id AS uuid), CAST(:lote_id AS uuid), CAST(:cultivo AS uuid), 'dji_mavic3', :fecha, 'V4', 'completado', :ahora)"
        ), {"id": vuelo_id, "lote_id": lote_id, "cultivo": _cultivo_soja, "fecha": now, "ahora": now})
        conn.commit()
    engine.dispose()
    return vuelo_id


def _put(vuelo_id: str, cuerpo: dict, lote_id: str | None = None):
    return _tc.put(f"/api/v1/lotes/{lote_id or _lote_id}/vuelos/{vuelo_id}", json=cuerpo, headers=_auth())


def test_editar_fecha_no_invalida_el_diagnostico():
    vuelo_id = _insertar_vuelo(_lote_id)
    r = _put(vuelo_id, {"fecha_vuelo": "2026-03-15T12:00:00Z"})
    assert r.status_code == 200, r.text
    assert r.json()["fecha_vuelo"].startswith("2026-03-15")
    assert r.json()["diagnostico_desactualizado"] is False


def test_editar_estadio_marca_diagnostico_desactualizado():
    vuelo_id = _insertar_vuelo(_lote_id)
    r = _put(vuelo_id, {"estadio_fenologico": "  R3 "})
    assert r.status_code == 200, r.text
    assert r.json()["estadio_fenologico"] == "R3"
    assert r.json()["diagnostico_desactualizado"] is True


def test_editar_estadio_igual_no_marca_desactualizado():
    vuelo_id = _insertar_vuelo(_lote_id)
    r = _put(vuelo_id, {"estadio_fenologico": "V4"})
    assert r.status_code == 200
    assert r.json()["diagnostico_desactualizado"] is False


def test_cambiar_cultivo_del_lote():
    vuelo_id = _insertar_vuelo(_lote_id)
    r = _put(vuelo_id, {"cultivo_id": _cultivo_maiz})
    assert r.status_code == 200, r.text
    assert r.json()["cultivo_id"] == _cultivo_maiz
    assert r.json()["cultivo"]["tipo_cultivo"] == "maiz"
    assert r.json()["diagnostico_desactualizado"] is True


def test_cultivo_de_otro_lote_es_404():
    vuelo_id = _insertar_vuelo(_lote_id)
    r = _put(vuelo_id, {"cultivo_id": str(uuid.uuid4())})
    assert r.status_code == 404


def test_estadio_vacio_es_422():
    vuelo_id = _insertar_vuelo(_lote_id)
    assert _put(vuelo_id, {"estadio_fenologico": "   "}).status_code == 422


def test_vuelo_inexistente_es_404():
    assert _put(str(uuid.uuid4()), {"estadio_fenologico": "R1"}).status_code == 404


def test_lote_inexistente_es_404():
    vuelo_id = _insertar_vuelo(_lote_id)
    assert _put(vuelo_id, {"estadio_fenologico": "R1"}, lote_id=str(uuid.uuid4())).status_code == 404


def test_sin_auth_es_401():
    vuelo_id = _insertar_vuelo(_lote_id)
    r = _tc.put(f"/api/v1/lotes/{_lote_id}/vuelos/{vuelo_id}", json={"estadio_fenologico": "R1"})
    assert r.status_code in (401, 403)
