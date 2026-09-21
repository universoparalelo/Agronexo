"""
Tests de los endpoints GET /lotes/{id}/vuelos/{id}/zonas/geojson,
GET /lotes/{id}/vuelos/{id}/zonas/shapefile y GET .../zonas/export
(genérico, con caché en MinIO y URL firmada).

Mismo criterio que test_diagnostico_api.py y test_reportes_api.py: los
vuelos se insertan directamente en la BD (sin MinIO ni Celery) para
testear la capa HTTP sin depender del stack completo. El camino feliz
de /zonas/geojson y /zonas/shapefile (archivo real a partir de un vuelo
con datos en MinIO) se verificó manualmente contra el endpoint
corriendo — acá se cubren los 404 y la integración de la capa
HTTP/ownership, que los tres endpoints comparten vía
_resolver_lote_o_404()/_generar_diagnostico_o_404() en
app/reportes/router.py.

/zonas/export sí tiene su camino feliz cubierto acá (cache miss y cache
hit) porque la lógica nueva que agrega — decidir regenerar o servir
cacheado, y pedir la URL firmada — no la ejerce ningún otro test; se
mockean generar_diagnostico() y las funciones de app/core/storage.py
para no depender de un MinIO real.

Correr en el contenedor api:
    docker compose exec api python3 -m pytest tests/test_exportacion_api.py -v

Correr en CI o local (con DB levantada):
    PYTHONPATH=$(pwd) python3 -m pytest tests/test_exportacion_api.py -v
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

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


# ── /zonas/export (genérico, caché + URL firmada) ─────────────────────

_DIAGNOSTICO_FAKE = {
    "features": [
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-60.6740, -27.4700],
                    [-60.6730, -27.4700],
                    [-60.6730, -27.4710],
                    [-60.6740, -27.4710],
                    [-60.6740, -27.4700],
                ]],
            },
            "properties": {
                "zona_id": 1,
                "clase": "estres",
                "severidad": "media",
                "causa_indice": "Deficit hidrico",
                "ndvi_promedio": 0.35,
                "area_ha": 1.2,
                "confianza": "alta",
                "regla_id": "R01",
            },
        },
    ],
}


def _export_url(lote_id: str, vuelo_id: str, formato: str = "geojson", indice: str | None = None) -> str:
    qs = f"formato={formato}"
    if indice is not None:
        qs += f"&indice={indice}"
    return f"/api/v1/lotes/{lote_id}/vuelos/{vuelo_id}/zonas/export?{qs}"


@pytest.mark.parametrize("formato", ["geojson", "shapefile"])
def test_export_generico_cache_miss_genera_sube_y_firma(formato):
    vuelo_id = _insertar_vuelo(_lote_id, "completado", geojson_key="alguna/key.geojson")
    with (
        patch("app.reportes.router.generar_diagnostico", return_value=_DIAGNOSTICO_FAKE) as mock_diag,
        patch("app.reportes.router.object_exists", return_value=False),
        patch("app.reportes.router.upload_bytes") as mock_upload,
        patch("app.reportes.router.presigned_url", return_value="https://minio.local/fake-url") as mock_presigned,
    ):
        r = _tc.get(_export_url(_lote_id, vuelo_id, formato), headers=_auth())

    assert r.status_code == 200, r.text
    body = r.json()
    assert body == {
        "vuelo_id": vuelo_id,
        "formato": formato,
        "indice": "ndvi",
        "url": "https://minio.local/fake-url",
        "expira_en_segundos": settings.minio_presigned_url_expiry,
    }
    mock_diag.assert_called_once()
    mock_upload.assert_called_once()
    mock_presigned.assert_called_once()
    print(f"✓ GET /zonas/export?formato={formato} cache miss → genera, sube y devuelve URL firmada")


@pytest.mark.parametrize("formato", ["geojson", "shapefile"])
def test_export_generico_cache_hit_no_regenera(formato):
    vuelo_id = _insertar_vuelo(_lote_id, "completado", geojson_key="alguna/key.geojson")
    with (
        patch("app.reportes.router.generar_diagnostico") as mock_diag,
        patch("app.reportes.router.object_exists", return_value=True),
        patch("app.reportes.router.upload_bytes") as mock_upload,
        patch("app.reportes.router.presigned_url", return_value="https://minio.local/cached-url") as mock_presigned,
    ):
        r = _tc.get(_export_url(_lote_id, vuelo_id, formato), headers=_auth())

    assert r.status_code == 200, r.text
    assert r.json()["url"] == "https://minio.local/cached-url"
    mock_diag.assert_not_called()
    mock_upload.assert_not_called()
    mock_presigned.assert_called_once()
    print(f"✓ GET /zonas/export?formato={formato} cache hit → no regenera, sirve URL cacheada")


def test_export_generico_indice_no_ndvi_es_501():
    vuelo_id = _insertar_vuelo(_lote_id, "completado", geojson_key="alguna/key.geojson")
    r = _tc.get(_export_url(_lote_id, vuelo_id, indice="ndre"), headers=_auth())
    assert r.status_code == 501
    print("✓ GET /zonas/export?indice=ndre (no soportado aún) → 501")


def test_export_generico_sin_formato_es_422():
    vuelo_id = _insertar_vuelo(_lote_id, "completado", geojson_key="alguna/key.geojson")
    r = _tc.get(f"/api/v1/lotes/{_lote_id}/vuelos/{vuelo_id}/zonas/export", headers=_auth())
    assert r.status_code == 422
    print("✓ GET /zonas/export sin formato → 422")


def test_export_generico_vuelo_pendiente_es_404():
    vuelo_id = _insertar_vuelo(_lote_id, "pendiente")
    with patch("app.reportes.router.object_exists", return_value=False):
        r = _tc.get(_export_url(_lote_id, vuelo_id), headers=_auth())
    assert r.status_code == 404
    print("✓ GET /zonas/export vuelo pendiente → 404")


def test_export_generico_lote_ajeno_es_404():
    vuelo_id = _insertar_vuelo(_lote_id, "completado", geojson_key="alguna/key.geojson")
    r = _tc.get(_export_url(str(uuid.uuid4()), vuelo_id), headers=_auth())
    assert r.status_code == 404
    print("✓ GET /zonas/export lote_id ajeno → 404")


def test_export_generico_sin_auth():
    r = _tc.get(_export_url(_lote_id, str(uuid.uuid4())))
    assert r.status_code == 401
    print("✓ GET /zonas/export sin token → 401")
