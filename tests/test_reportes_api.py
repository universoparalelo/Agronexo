"""
Tests del endpoint GET /lotes/{id}/vuelos/{id}/reporte/pdf.

Mismo criterio que test_diagnostico_api.py: los vuelos se insertan
directamente en la BD (sin MinIO ni Celery) para testear la capa HTTP sin
depender del stack completo. El camino feliz (PDF real generado a partir
de un GeoJSON real en MinIO) se verificó manualmente con
scripts/poc_reporte_pdf.py y contra el endpoint corriendo — acá se cubren
los 404 y la integración de la capa HTTP/ownership, igual que en
test_diagnostico_api.py, del que este endpoint depende directamente
(reutiliza generar_diagnostico()).

Correr en el contenedor api:
    docker compose exec api python3 -m pytest tests/test_reportes_api.py -v

Correr en CI o local (con DB levantada):
    PYTHONPATH=$(pwd) python3 -m pytest tests/test_reportes_api.py -v
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine, text
from starlette.testclient import TestClient

from app.core.config import settings
from app.main import app

_EMAIL = f"reportes_{uuid.uuid4().hex[:8]}@agronexo-test.com"
_PASS = "reportes_pass_123"
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


def setup_module(module):
    global _token, _lote_id
    from app.core.database import engine as _engine
    _engine.sync_engine.dispose(close=False)
    _tc.__enter__()
    _tc.post("/api/v1/auth/register", json={
        "email": _EMAIL, "nombre": "Test Reportes", "password": _PASS,
    })
    r = _tc.post("/api/v1/auth/login", json={"email": _EMAIL, "password": _PASS})
    assert r.status_code == 200, f"setup_module login falló: {r.status_code} {r.text}"
    _token = r.json()["access_token"]

    r = _tc.post("/api/v1/lotes", json={
        "nombre": "Lote Para Tests de Reportes",
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


def _url(lote_id: str, vuelo_id: str) -> str:
    return f"/api/v1/lotes/{lote_id}/vuelos/{vuelo_id}/reporte/pdf"


# ── 404 por estado del vuelo ─────────────────────────────────────────

def test_reporte_pdf_vuelo_pendiente_es_404():
    vuelo_id = _insertar_vuelo(_lote_id, "pendiente")
    r = _tc.get(_url(_lote_id, vuelo_id), headers=_auth())
    assert r.status_code == 404
    print("✓ GET /reporte/pdf vuelo pendiente → 404")


def test_reporte_pdf_vuelo_procesando_es_404():
    vuelo_id = _insertar_vuelo(_lote_id, "procesando")
    r = _tc.get(_url(_lote_id, vuelo_id), headers=_auth())
    assert r.status_code == 404
    print("✓ GET /reporte/pdf vuelo procesando → 404")


def test_reporte_pdf_vuelo_completado_sin_geojson_es_404():
    vuelo_id = _insertar_vuelo(_lote_id, "completado", geojson_key=None)
    r = _tc.get(_url(_lote_id, vuelo_id), headers=_auth())
    assert r.status_code == 404
    print("✓ GET /reporte/pdf vuelo completado sin geojson_key → 404")


# ── 404 por lote/vuelo inexistente o ajeno ───────────────────────────

def test_reporte_pdf_vuelo_inexistente():
    r = _tc.get(_url(_lote_id, str(uuid.uuid4())), headers=_auth())
    assert r.status_code == 404
    print("✓ GET /reporte/pdf vuelo inexistente → 404")


def test_reporte_pdf_lote_inexistente():
    r = _tc.get(_url(str(uuid.uuid4()), str(uuid.uuid4())), headers=_auth())
    assert r.status_code == 404
    print("✓ GET /reporte/pdf lote inexistente → 404")


def test_reporte_pdf_vuelo_de_otro_lote_es_404():
    vuelo_id = _insertar_vuelo(_lote_id, "completado", geojson_key="alguna/key.geojson")
    r = _tc.get(_url(str(uuid.uuid4()), vuelo_id), headers=_auth())
    assert r.status_code == 404
    print("✓ GET /reporte/pdf vuelo con lote_id ajeno → 404")


# ── Auth ──────────────────────────────────────────────────────────────

def test_reporte_pdf_sin_auth():
    r = _tc.get(_url(_lote_id, str(uuid.uuid4())))
    assert r.status_code == 401
    print("✓ GET /reporte/pdf sin token → 401")


if __name__ == "__main__":
    setup_module(None)
    try:
        print("\n── Reporte PDF: casos 404 y auth ────────────────────")
        test_reporte_pdf_vuelo_pendiente_es_404()
        test_reporte_pdf_vuelo_procesando_es_404()
        test_reporte_pdf_vuelo_completado_sin_geojson_es_404()
        test_reporte_pdf_vuelo_inexistente()
        test_reporte_pdf_lote_inexistente()
        test_reporte_pdf_vuelo_de_otro_lote_es_404()
        test_reporte_pdf_sin_auth()
        print("\nTodos los tests de reporte PDF pasaron.\n")
    finally:
        teardown_module(None)
