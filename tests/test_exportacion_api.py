"""
Tests de los endpoints GET /lotes/{id}/vuelos/{id}/zonas/geojson y
GET /lotes/{id}/vuelos/{id}/zonas/shapefile.

Mismo criterio que test_diagnostico_api.py y test_reportes_api.py: los
vuelos se insertan directamente en la BD (sin MinIO ni Celery) para
testear la capa HTTP sin depender del stack completo. El camino feliz
(GeoJSON/Shapefile real a partir de un vuelo con datos en MinIO) se
verificó manualmente contra el endpoint corriendo — acá se cubren los
404 y la integración de la capa HTTP/ownership, que ambos endpoints
comparten vía _resolver_diagnostico_o_404() en app/reportes/router.py.

Correr en el contenedor api:
    docker compose exec api python3 -m pytest tests/test_exportacion_api.py -v

Correr en CI o local (con DB levantada):
    PYTHONPATH=$(pwd) python3 -m pytest tests/test_exportacion_api.py -v
"""
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, text
from starlette.testclient import TestClient

from app.core.config import settings
from app.main import app

_EMAIL = f"exportacion_{uuid.uuid4().hex[:8]}@agronexo-test.com"
_PASS = "exportacion_pass_123"
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

_tc = TestClient(app)
_token: str = ""
_lote_id: str = ""

# Ambos endpoints comparten la misma resolución de lote/diagnóstico —
# se parametriza el sufijo de ruta para no duplicar cada test dos veces.
_ENDPOINTS = ["zonas/geojson", "zonas/shapefile"]


def setup_module(module):
    global _token, _lote_id
    from app.core.database import engine as _engine
    _engine.sync_engine.dispose(close=False)
    _tc.__enter__()
    _tc.post("/api/v1/auth/register", json={
        "email": _EMAIL, "nombre": "Test Exportacion", "password": _PASS,
    })
    r = _tc.post("/api/v1/auth/login", json={"email": _EMAIL, "password": _PASS})
    assert r.status_code == 200, f"setup_module login falló: {r.status_code} {r.text}"
    _token = r.json()["access_token"]

    r = _tc.post("/api/v1/lotes", json={
        "nombre": "Lote Para Tests de Exportacion",
        "cultivo": "soja",
        "estadio_fenologico": "R2",
        "geometry": _GEOM,
    }, headers={"Authorization": f"Bearer {_token}"})
    assert r.status_code == 201, f"setup_module crear lote falló: {r.text}"
    _lote_id = r.json()["id"]


def teardown_module(module):
    _tc.__exit__(None, None, None)


def _auth() -> dict:
    return {"Authorization": f"Bearer {_token}"}


def _insertar_vuelo(lote_id: str, estado: str = "pendiente", geojson_key: str | None = None) -> str:
    """Inserta un vuelo directamente en la BD, sin pasar por MinIO ni Celery."""
    vuelo_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    engine = create_engine(settings.database_url_sync)
    with engine.connect() as conn:
        conn.execute(text(
            "INSERT INTO vuelos (id, lote_id, sensor, fecha_vuelo, estado, geojson_key, created_at) "
            "VALUES (CAST(:id AS uuid), CAST(:lote_id AS uuid), :sensor, :fecha, :estado, :geojson_key, :created_at)"
        ), {
            "id": vuelo_id,
            "lote_id": lote_id,
            "sensor": "dji_mavic3",
            "fecha": now,
            "estado": estado,
            "geojson_key": geojson_key,
            "created_at": now,
        })
        conn.commit()
    engine.dispose()
    return vuelo_id


def _url(lote_id: str, vuelo_id: str, sufijo: str) -> str:
    return f"/api/v1/lotes/{lote_id}/vuelos/{vuelo_id}/{sufijo}"


# ── 404 por estado del vuelo ─────────────────────────────────────────

@pytest.mark.parametrize("sufijo", _ENDPOINTS)
def test_export_vuelo_pendiente_es_404(sufijo):
    vuelo_id = _insertar_vuelo(_lote_id, "pendiente")
    r = _tc.get(_url(_lote_id, vuelo_id, sufijo), headers=_auth())
    assert r.status_code == 404
    print(f"✓ GET /{sufijo} vuelo pendiente → 404")


@pytest.mark.parametrize("sufijo", _ENDPOINTS)
def test_export_vuelo_completado_sin_geojson_es_404(sufijo):
    vuelo_id = _insertar_vuelo(_lote_id, "completado", geojson_key=None)
    r = _tc.get(_url(_lote_id, vuelo_id, sufijo), headers=_auth())
    assert r.status_code == 404
    print(f"✓ GET /{sufijo} vuelo completado sin geojson_key → 404")


# ── 404 por lote/vuelo inexistente o ajeno ───────────────────────────

@pytest.mark.parametrize("sufijo", _ENDPOINTS)
def test_export_vuelo_inexistente(sufijo):
    r = _tc.get(_url(_lote_id, str(uuid.uuid4()), sufijo), headers=_auth())
    assert r.status_code == 404
    print(f"✓ GET /{sufijo} vuelo inexistente → 404")


@pytest.mark.parametrize("sufijo", _ENDPOINTS)
def test_export_lote_inexistente(sufijo):
    r = _tc.get(_url(str(uuid.uuid4()), str(uuid.uuid4()), sufijo), headers=_auth())
    assert r.status_code == 404
    print(f"✓ GET /{sufijo} lote inexistente → 404")


@pytest.mark.parametrize("sufijo", _ENDPOINTS)
def test_export_vuelo_de_otro_lote_es_404(sufijo):
    vuelo_id = _insertar_vuelo(_lote_id, "completado", geojson_key="alguna/key.geojson")
    r = _tc.get(_url(str(uuid.uuid4()), vuelo_id, sufijo), headers=_auth())
    assert r.status_code == 404
    print(f"✓ GET /{sufijo} vuelo con lote_id ajeno → 404")


# ── Auth ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("sufijo", _ENDPOINTS)
def test_export_sin_auth(sufijo):
    r = _tc.get(_url(_lote_id, str(uuid.uuid4()), sufijo))
    assert r.status_code == 401
    print(f"✓ GET /{sufijo} sin token → 401")
