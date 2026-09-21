"""
Tests del endpoint GET /lotes/{id}/vuelos/{id}/orden-trabajo/pdf.

Mismo criterio que test_reportes_api.py: los vuelos se insertan
directamente en la BD (sin MinIO ni Celery) para testear la capa HTTP sin
depender del stack completo. El camino feliz (PDF real con dosis
calculadas) se cubre acá mockeando generar_diagnostico() y
cargar_catalogo_dosis() — la lógica de cálculo en sí (generar_orden_trabajo)
ya tiene su propia suite en tests/test_orden_trabajo.py, así que acá solo
se verifica que el endpoint arme el PDF a partir de esos dos mocks (sin
volver a probar el cálculo) y los casos 404/401 de ownership.

Correr en el contenedor api:
    docker compose exec api python3 -m pytest tests/test_orden_trabajo_pdf_api.py -v

Correr en CI o local (con DB levantada):
    PYTHONPATH=$(pwd) python3 -m pytest tests/test_orden_trabajo_pdf_api.py -v
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

from sqlalchemy import create_engine, text
from starlette.testclient import TestClient

from app.core.config import settings
from app.main import app

_EMAIL = f"orden_trabajo_{uuid.uuid4().hex[:8]}@agronexo-test.com"
_PASS = "orden_trabajo_pass_123"
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

_DIAGNOSTICO_CON_UNIDADES = {
    "metadata": {
        "lote_nombre": "Lote Para Tests de Orden de Trabajo",
        "cultivo": "soja",
        "estadio_fenologico": "R2",
        "fecha_vuelo": "2026-09-10T00:00:00+00:00",
        "calculado_en": "2026-09-17T00:00:00+00:00",
    },
    "unidades_manejo": [
        {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]},
            "properties": {
                "unidad_id": 1,
                "causa_indice": "estres_hidrico",
                "severidad": "critica",
                "regla_nombre": "Estrés hídrico crítico",
                "accion_recomendada": "Riego suplementario",
                "productos_sugeridos": [{"nombre": "Producto Test", "tipo": "fertilizante_foliar"}],
                "area_total_ha": 5.0,
                "ndvi_promedio": 0.3,
                "n_zonas": 1,
                "zona_ids": [1],
                "texto_unidad": "Unidad de prueba.",
            },
        },
    ],
}

_DIAGNOSTICO_SIN_UNIDADES = {
    "metadata": _DIAGNOSTICO_CON_UNIDADES["metadata"],
    "unidades_manejo": [],
}

_CATALOGO_DOSIS_FAKE = {
    "Producto Test": {
        "dosis_referencia": 2.0,
        "unidad": "L/ha",
        "restricciones_ambientales": "No aplicar cerca de cursos de agua.",
        "instrucciones_seguridad": "Usar equipo de protección personal completo.",
    },
}


def setup_module(module):
    global _token, _lote_id
    from app.core.database import engine as _engine
    _engine.sync_engine.dispose(close=False)
    _tc.__enter__()
    _tc.post("/api/v1/auth/register", json={
        "email": _EMAIL, "nombre": "Test Orden Trabajo", "password": _PASS,
    })
    r = _tc.post("/api/v1/auth/login", json={"email": _EMAIL, "password": _PASS})
    assert r.status_code == 200, f"setup_module login falló: {r.status_code} {r.text}"
    _token = r.json()["access_token"]

    r = _tc.post("/api/v1/lotes", json={
        "nombre": "Lote Para Tests de Orden de Trabajo",
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
    return f"/api/v1/lotes/{lote_id}/vuelos/{vuelo_id}/orden-trabajo/pdf"


# ── Camino feliz (mockeado) ──────────────────────────────────────────

def test_orden_trabajo_pdf_genera_documento():
    vuelo_id = _insertar_vuelo(_lote_id, "completado", geojson_key="alguna/key.geojson")
    with (
        patch("app.ordenes_trabajo.router.generar_diagnostico", return_value=_DIAGNOSTICO_CON_UNIDADES),
        patch("app.ordenes_trabajo.router.cargar_catalogo_dosis", return_value=_CATALOGO_DOSIS_FAKE),
    ):
        r = _tc.get(_url(_lote_id, vuelo_id), headers=_auth())

    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"
    assert f'orden_trabajo_{vuelo_id}.pdf' in r.headers["content-disposition"]
    print("✓ GET /orden-trabajo/pdf con unidades de manejo → 200, PDF válido")


def test_orden_trabajo_pdf_sin_unidades_de_manejo_es_404():
    vuelo_id = _insertar_vuelo(_lote_id, "completado", geojson_key="alguna/key.geojson")
    with patch("app.ordenes_trabajo.router.generar_diagnostico", return_value=_DIAGNOSTICO_SIN_UNIDADES):
        r = _tc.get(_url(_lote_id, vuelo_id), headers=_auth())
    assert r.status_code == 404
    print("✓ GET /orden-trabajo/pdf sin unidades de manejo → 404")


# ── 404 por estado del vuelo ─────────────────────────────────────────

def test_orden_trabajo_pdf_vuelo_pendiente_es_404():
    vuelo_id = _insertar_vuelo(_lote_id, "pendiente")
    r = _tc.get(_url(_lote_id, vuelo_id), headers=_auth())
    assert r.status_code == 404
    print("✓ GET /orden-trabajo/pdf vuelo pendiente → 404")


def test_orden_trabajo_pdf_vuelo_completado_sin_geojson_es_404():
    vuelo_id = _insertar_vuelo(_lote_id, "completado", geojson_key=None)
    r = _tc.get(_url(_lote_id, vuelo_id), headers=_auth())
    assert r.status_code == 404
    print("✓ GET /orden-trabajo/pdf vuelo completado sin geojson_key → 404")


# ── 404 por lote/vuelo inexistente o ajeno ───────────────────────────

def test_orden_trabajo_pdf_vuelo_inexistente():
    r = _tc.get(_url(_lote_id, str(uuid.uuid4())), headers=_auth())
    assert r.status_code == 404
    print("✓ GET /orden-trabajo/pdf vuelo inexistente → 404")


def test_orden_trabajo_pdf_lote_inexistente():
    r = _tc.get(_url(str(uuid.uuid4()), str(uuid.uuid4())), headers=_auth())
    assert r.status_code == 404
    print("✓ GET /orden-trabajo/pdf lote inexistente → 404")


def test_orden_trabajo_pdf_vuelo_de_otro_lote_es_404():
    vuelo_id = _insertar_vuelo(_lote_id, "completado", geojson_key="alguna/key.geojson")
    r = _tc.get(_url(str(uuid.uuid4()), vuelo_id), headers=_auth())
    assert r.status_code == 404
    print("✓ GET /orden-trabajo/pdf vuelo con lote_id ajeno → 404")


# ── Auth ──────────────────────────────────────────────────────────────

def test_orden_trabajo_pdf_sin_auth():
    r = _tc.get(_url(_lote_id, str(uuid.uuid4())))
    assert r.status_code == 401
    print("✓ GET /orden-trabajo/pdf sin token → 401")
