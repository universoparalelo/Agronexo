"""
Tests de aislamiento multi-tenencia (HU-R4-01) para los endpoints de
índices adicionales sobre un vuelo (NDRE/SAVI/ExG/GNDVI).

Cubre el IDOR encontrado en la auditoría de esta historia: GET
.../indices/{indice}/estado y GET .../indices/{indice}/resultado
validaban que el lote_id de la URL fuera del usuario autenticado, pero
las funciones de servicio detrás (obtener_analisis_indice y las que
dependen de ella) filtraban AnalisisIndice solo por vuelo_id, sin
cruzar con el lote — un usuario dueño de CUALQUIER lote podía leer el
estado y el GeoJSON de índices de un vuelo ajeno pasando su propio
lote_id junto con un vuelo_id adivinado/enumerado. Fix en
app/ingesta/service.py: obtener_analisis_indice ahora hace join con
Vuelo y filtra por Vuelo.lote_id == lote_id.

Mismo criterio que test_exportacion_api.py: vuelos y análisis de
índice se insertan directo en la BD (sin MinIO ni Celery) para
testear la capa HTTP/ownership sin depender del stack completo.

Correr en el contenedor api:
    docker compose exec api python3 -m pytest tests/test_multi_tenant_indices.py -v

Correr en CI o local (con DB levantada):
    PYTHONPATH=$(pwd) python3 -m pytest tests/test_multi_tenant_indices.py -v
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

from sqlalchemy import create_engine, text
from starlette.testclient import TestClient

from app.core.config import settings
from app.main import app

_EMAIL_A = f"idor_a_{uuid.uuid4().hex[:8]}@agronexo-test.com"
_EMAIL_B = f"idor_b_{uuid.uuid4().hex[:8]}@agronexo-test.com"
_PASS = "idor_pass_123"
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
_token_a: str = ""
_token_b: str = ""
_lote_a: str = ""
_lote_b: str = ""


def setup_module(module):
    global _token_a, _token_b, _lote_a, _lote_b
    from app.core.database import engine as _engine
    _engine.sync_engine.dispose(close=False)
    _tc.__enter__()

    _tc.post("/api/v1/auth/register", json={"email": _EMAIL_A, "nombre": "Tenant A", "password": _PASS})
    r = _tc.post("/api/v1/auth/login", json={"email": _EMAIL_A, "password": _PASS})
    assert r.status_code == 200, f"setup_module login A falló: {r.status_code} {r.text}"
    _token_a = r.json()["access_token"]

    _tc.post("/api/v1/auth/register", json={"email": _EMAIL_B, "nombre": "Tenant B", "password": _PASS})
    r = _tc.post("/api/v1/auth/login", json={"email": _EMAIL_B, "password": _PASS})
    assert r.status_code == 200, f"setup_module login B falló: {r.status_code} {r.text}"
    _token_b = r.json()["access_token"]

    r = _tc.post("/api/v1/lotes", json={"nombre": "Lote de A", "geometry": _GEOM}, headers=_auth(_token_a))
    assert r.status_code == 201, f"setup_module crear lote A falló: {r.text}"
    _lote_a = r.json()["id"]

    r = _tc.post("/api/v1/lotes", json={"nombre": "Lote de B", "geometry": _GEOM}, headers=_auth(_token_b))
    assert r.status_code == 201, f"setup_module crear lote B falló: {r.text}"
    _lote_b = r.json()["id"]


def teardown_module(module):
    _tc.__exit__(None, None, None)


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _insertar_vuelo(lote_id: str, estado: str = "completado") -> str:
    """Inserta un vuelo directamente en la BD, sin pasar por MinIO ni Celery."""
    vuelo_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    engine = create_engine(settings.database_url_sync)
    with engine.connect() as conn:
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


def _insertar_analisis_indice(
    vuelo_id: str,
    indice: str = "ndre",
    estado: str = "completado",
    geojson_key: str | None = "alguna/key.geojson",
) -> str:
    """Inserta un AnalisisIndice directamente en la BD, sin pasar por Celery."""
    analisis_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    engine = create_engine(settings.database_url_sync)
    with engine.connect() as conn:
        conn.execute(text(
            "INSERT INTO analisis_indices (id, vuelo_id, indice, estado, geojson_key, created_at) "
            "VALUES (CAST(:id AS uuid), CAST(:vuelo_id AS uuid), :indice, :estado, :geojson_key, :created_at)"
        ), {
            "id": analisis_id,
            "vuelo_id": vuelo_id,
            "indice": indice,
            "estado": estado,
            "geojson_key": geojson_key,
            "created_at": now,
        })
        conn.commit()
    engine.dispose()
    return analisis_id


def _estado_url(lote_id: str, vuelo_id: str, indice: str = "ndre") -> str:
    return f"/api/v1/lotes/{lote_id}/vuelos/{vuelo_id}/indices/{indice}/estado"


def _resultado_url(lote_id: str, vuelo_id: str, indice: str = "ndre") -> str:
    return f"/api/v1/lotes/{lote_id}/vuelos/{vuelo_id}/indices/{indice}/resultado"


# ── IDOR: lote propio (válido) + vuelo_id ajeno (adivinado/enumerado) ──

def test_estado_indice_con_vuelo_de_otro_tenant_es_404():
    vuelo_a = _insertar_vuelo(_lote_a)
    _insertar_analisis_indice(vuelo_a)
    # B pasa SU PROPIO lote_id (pasa el chequeo de obtener_lote) pero el
    # vuelo_id le pertenece a A — antes del fix esto devolvía 200 con el
    # estado del análisis de A.
    r = _tc.get(_estado_url(_lote_b, vuelo_a), headers=_auth(_token_b))
    assert r.status_code == 404
    print("✓ GET /indices/{indice}/estado con lote propio + vuelo ajeno → 404")


def test_resultado_indice_con_vuelo_de_otro_tenant_es_404():
    vuelo_a = _insertar_vuelo(_lote_a)
    _insertar_analisis_indice(vuelo_a)
    r = _tc.get(_resultado_url(_lote_b, vuelo_a), headers=_auth(_token_b))
    assert r.status_code == 404
    print("✓ GET /indices/{indice}/resultado con lote propio + vuelo ajeno → 404")


# ── Control: lote ajeno (ya lo bloqueaba obtener_lote antes del fix) ───

def test_estado_indice_con_lote_ajeno_es_404():
    vuelo_a = _insertar_vuelo(_lote_a)
    _insertar_analisis_indice(vuelo_a)
    r = _tc.get(_estado_url(_lote_a, vuelo_a), headers=_auth(_token_b))
    assert r.status_code == 404
    print("✓ GET /indices/{indice}/estado con lote ajeno → 404")


def test_resultado_indice_con_lote_ajeno_es_404():
    vuelo_a = _insertar_vuelo(_lote_a)
    _insertar_analisis_indice(vuelo_a)
    r = _tc.get(_resultado_url(_lote_a, vuelo_a), headers=_auth(_token_b))
    assert r.status_code == 404
    print("✓ GET /indices/{indice}/resultado con lote ajeno → 404")


# ── Camino propio: el fix no debe romper el acceso legítimo ────────────

def test_estado_indice_propio_sigue_funcionando():
    vuelo_a = _insertar_vuelo(_lote_a)
    _insertar_analisis_indice(vuelo_a, estado="procesando", geojson_key=None)
    r = _tc.get(_estado_url(_lote_a, vuelo_a), headers=_auth(_token_a))
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "procesando"
    print("✓ GET /indices/{indice}/estado propio → 200")


def test_resultado_indice_propio_sigue_funcionando():
    vuelo_a = _insertar_vuelo(_lote_a)
    _insertar_analisis_indice(vuelo_a, geojson_key="alguna/key.geojson")
    with patch(
        "app.ingesta.service.download_bytes",
        return_value=b'{"type": "FeatureCollection", "features": []}',
    ):
        r = _tc.get(_resultado_url(_lote_a, vuelo_a), headers=_auth(_token_a))
    assert r.status_code == 200, r.text
    assert r.json() == {"type": "FeatureCollection", "features": []}
    print("✓ GET /indices/{indice}/resultado propio → 200")


# ── Auth ─────────────────────────────────────────────────────────────

def test_estado_indice_sin_auth():
    vuelo_a = _insertar_vuelo(_lote_a)
    r = _tc.get(_estado_url(_lote_a, vuelo_a))
    assert r.status_code == 401
    print("✓ GET /indices/{indice}/estado sin token → 401")
