"""
Tests de endpoints /estado y /resultado de vuelos.

Los vuelos se insertan directamente en la BD (sin MinIO ni Celery)
para testear la capa HTTP sin depender del stack completo.

Correr en el contenedor api:
    docker compose exec api python3 -m pytest tests/test_vuelos_estado.py -v

Correr en CI o local (con DB levantada):
    PYTHONPATH=$(pwd) python3 -m pytest tests/test_vuelos_estado.py -v
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine, text
from starlette.testclient import TestClient

from app.core.config import settings
from app.main import app

_EMAIL = f"vuelos_{uuid.uuid4().hex[:8]}@agronexo-test.com"
_PASS = "vuelos_pass_789"
_GEOM = {
    "type": "Polygon",
    "coordinates": [[
        [-60.6753, -27.4693],
        [-60.6701, -27.4693],
        [-60.6701, -27.4741],
        [-60.6753, -27.4741],
        [-60.6753, -27.4693],
    ]],
}

# El TestClient se abre en setup_module y se cierra en teardown_module para
# mantener el mismo event loop de anyio en todas las llamadas del módulo.
_tc = TestClient(app)
_token: str = ""
_lote_id: str = ""


def setup_module(module):
    global _token, _lote_id
    from app.core.database import engine as _engine
    _engine.sync_engine.dispose(close=False)
    _tc.__enter__()
    _tc.post("/api/v1/auth/register", json={
        "email": _EMAIL, "nombre": "Test Vuelos", "password": _PASS,
    })
    r = _tc.post("/api/v1/auth/login", json={"email": _EMAIL, "password": _PASS})
    assert r.status_code == 200, f"setup_module login falló: {r.status_code} {r.text}"
    _token = r.json()["access_token"]

    r = _tc.post("/api/v1/lotes", json={
        "nombre": "Lote Para Tests de Vuelos",
        "cultivo": "soja",
        "geometry": _GEOM,
    }, headers={"Authorization": f"Bearer {_token}"})
    assert r.status_code == 201, f"setup_module crear lote falló: {r.text}"
    _lote_id = r.json()["id"]
    print(f"\nLote base creado: {_lote_id}")


def teardown_module(module):
    _tc.__exit__(None, None, None)


def _auth() -> dict:
    return {"Authorization": f"Bearer {_token}"}


def _insertar_vuelo(lote_id: str, estado: str = "pendiente") -> str:
    """Inserta un vuelo directamente en la BD, sin pasar por MinIO ni Celery."""
    vuelo_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    engine = create_engine(settings.database_url_sync)
    with engine.connect() as conn:
        # psycopg2 usa %s params — evitar :: que colisiona con el parser de text()
        conn.execute(text(
            "INSERT INTO vuelos (id, lote_id, sensor, fecha_vuelo, estado, created_at) "
            "VALUES (CAST(:id AS uuid), CAST(:lote_id AS uuid), :sensor, :fecha, :estado, :created_at)"
        ), {
            "id": vuelo_id,
            "lote_id": lote_id,
            "sensor": "dji_mavic3",
            "fecha": now,
            "estado": estado,
            "created_at": now,
        })
        conn.commit()
    engine.dispose()
    return vuelo_id


# ── /estado ───────────────────────────────────────────────────────────

def test_estado_vuelo_pendiente():
    vuelo_id = _insertar_vuelo(_lote_id, "pendiente")
    r = _tc.get(f"/api/v1/lotes/{_lote_id}/vuelos/{vuelo_id}/estado", headers=_auth())
    assert r.status_code == 200
    body = r.json()
    assert body["estado"] == "pendiente"
    assert body["vuelo_id"] == vuelo_id
    assert body["task_id"] is None
    print("✓ GET /estado vuelo pendiente → 200, estado=pendiente")


def test_estado_vuelo_completado():
    vuelo_id = _insertar_vuelo(_lote_id, "completado")
    r = _tc.get(f"/api/v1/lotes/{_lote_id}/vuelos/{vuelo_id}/estado", headers=_auth())
    assert r.status_code == 200
    assert r.json()["estado"] == "completado"
    print("✓ GET /estado vuelo completado → 200, estado=completado")


def test_estado_vuelo_error():
    vuelo_id = _insertar_vuelo(_lote_id, "error")
    r = _tc.get(f"/api/v1/lotes/{_lote_id}/vuelos/{vuelo_id}/estado", headers=_auth())
    assert r.status_code == 200
    assert r.json()["estado"] == "error"
    print("✓ GET /estado vuelo con error → 200, estado=error")


def test_estado_vuelo_inexistente():
    r = _tc.get(f"/api/v1/lotes/{_lote_id}/vuelos/{uuid.uuid4()}/estado", headers=_auth())
    assert r.status_code == 404
    print("✓ GET /estado vuelo inexistente → 404")


def test_estado_lote_inexistente():
    r = _tc.get(f"/api/v1/lotes/{uuid.uuid4()}/vuelos/{uuid.uuid4()}/estado", headers=_auth())
    assert r.status_code == 404
    print("✓ GET /estado lote inexistente → 404")


def test_estado_sin_auth():
    r = _tc.get(f"/api/v1/lotes/{_lote_id}/vuelos/{uuid.uuid4()}/estado")
    assert r.status_code == 401
    print("✓ GET /estado sin token → 401")


# ── /resultado ────────────────────────────────────────────────────────

def test_resultado_vuelo_pendiente_es_404():
    vuelo_id = _insertar_vuelo(_lote_id, "pendiente")
    r = _tc.get(f"/api/v1/lotes/{_lote_id}/vuelos/{vuelo_id}/resultado", headers=_auth())
    assert r.status_code == 404
    print("✓ GET /resultado vuelo pendiente → 404 (no completado)")


def test_resultado_vuelo_procesando_es_404():
    vuelo_id = _insertar_vuelo(_lote_id, "procesando")
    r = _tc.get(f"/api/v1/lotes/{_lote_id}/vuelos/{vuelo_id}/resultado", headers=_auth())
    assert r.status_code == 404
    print("✓ GET /resultado vuelo procesando → 404")


def test_resultado_vuelo_error_es_404():
    vuelo_id = _insertar_vuelo(_lote_id, "error")
    r = _tc.get(f"/api/v1/lotes/{_lote_id}/vuelos/{vuelo_id}/resultado", headers=_auth())
    assert r.status_code == 404
    print("✓ GET /resultado vuelo en error → 404")


def test_resultado_vuelo_inexistente():
    r = _tc.get(f"/api/v1/lotes/{_lote_id}/vuelos/{uuid.uuid4()}/resultado", headers=_auth())
    assert r.status_code == 404
    print("✓ GET /resultado vuelo inexistente → 404")


def test_resultado_sin_auth():
    r = _tc.get(f"/api/v1/lotes/{_lote_id}/vuelos/{uuid.uuid4()}/resultado")
    assert r.status_code == 401
    print("✓ GET /resultado sin token → 401")


# ── Listar vuelos ─────────────────────────────────────────────────────

def test_listar_vuelos_de_lote():
    vuelo_id = _insertar_vuelo(_lote_id, "pendiente")
    r = _tc.get(f"/api/v1/lotes/{_lote_id}/vuelos", headers=_auth())
    assert r.status_code == 200
    vuelos = r.json()
    assert isinstance(vuelos, list)
    assert len(vuelos) >= 1
    # El endpoint del router de lotes devuelve VueloResponse con campo "id"
    ids = [v["id"] for v in vuelos]
    assert vuelo_id in ids
    for v in vuelos:
        assert "estado" in v
        assert "sensor" in v
        assert "id" in v
    print(f"✓ GET /lotes/{{id}}/vuelos → {len(vuelos)} vuelo(s)")


def test_listar_vuelos_lote_inexistente():
    r = _tc.get(f"/api/v1/lotes/{uuid.uuid4()}/vuelos", headers=_auth())
    assert r.status_code == 404
    print("✓ GET vuelos de lote inexistente → 404")


if __name__ == "__main__":
    setup_module(None)
    try:
        print("\n── Vuelos: /estado y /resultado ────────────────────")
        test_estado_vuelo_pendiente()
        test_estado_vuelo_completado()
        test_estado_vuelo_error()
        test_estado_vuelo_inexistente()
        test_estado_lote_inexistente()
        test_estado_sin_auth()
        test_resultado_vuelo_pendiente_es_404()
        test_resultado_vuelo_procesando_es_404()
        test_resultado_vuelo_error_es_404()
        test_resultado_vuelo_inexistente()
        test_resultado_sin_auth()
        test_listar_vuelos_de_lote()
        test_listar_vuelos_lote_inexistente()
        print("\nTodos los tests de vuelos pasaron.\n")
    finally:
        teardown_module(None)
