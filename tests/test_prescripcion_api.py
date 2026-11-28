"""
Tests del endpoint GET /lotes/{id}/vuelos/{id}/prescripcion.

Mismo criterio que test_orden_trabajo_pdf_api.py: los vuelos se insertan en
la BD sin MinIO ni Celery, y el camino feliz mockea generar_diagnostico() y
cargar_catalogo_dosis(). El cálculo del paquete tiene su propia suite en
tests/test_prescripcion.py.

    docker compose exec api python3 -m pytest tests/test_prescripcion_api.py -v
    PYTHONPATH=$(pwd) python3 -m pytest tests/test_prescripcion_api.py -v   (con DB levantada)
"""
import io
import json
import uuid
import zipfile
from datetime import datetime, timezone
from unittest.mock import patch

from sqlalchemy import create_engine, text
from starlette.testclient import TestClient

from app.core.config import settings
from app.main import app

_EMAIL = f"prescripcion_{uuid.uuid4().hex[:8]}@agronexo-test.com"
_PASS = "prescripcion_pass_123"
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


def _unidad(uid: int, producto: str, coords: list) -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [coords]},
        "properties": {
            "unidad_id": uid,
            "causa_indice": "estres_biotico_insecto",
            "severidad": "moderada",
            "productos_sugeridos": [{"nombre": producto, "tipo": "insecticida"}],
            "area_total_ha": 1.0,
            "zona_ids": [uid],
        },
    }


_DIAGNOSTICO = {
    "metadata": {"lote_nombre": "Lote Prescripcion", "cultivo": "soja"},
    "unidades_manejo": [
        _unidad(1, "Producto Test", [
            [-60.6740, -27.4700], [-60.6730, -27.4700], [-60.6730, -27.4710],
            [-60.6740, -27.4710], [-60.6740, -27.4700],
        ]),
    ],
}

_CATALOGO = {"Producto Test": {"dosis_referencia": 0.5, "unidad": "L/ha"}}


def setup_module(module):
    global _token, _lote_id
    from app.core.database import engine as _engine
    _engine.sync_engine.dispose(close=False)
    _tc.__enter__()
    _tc.post("/api/v1/auth/register", json={"email": _EMAIL, "nombre": "Test Prescripcion", "password": _PASS})
    r = _tc.post("/api/v1/auth/login", json={"email": _EMAIL, "password": _PASS})
    assert r.status_code == 200, r.text
    _token = r.json()["access_token"]
    r = _tc.post(
        "/api/v1/lotes", json={"nombre": "Lote Prescripcion", "geometry": _GEOM},
        headers={"Authorization": f"Bearer {_token}"},
    )
    assert r.status_code == 201, r.text
    _lote_id = r.json()["id"]


def teardown_module(module):
    _tc.__exit__(None, None, None)


def _auth() -> dict:
    return {"Authorization": f"Bearer {_token}"}


def _insertar_vuelo(lote_id: str, estado: str = "completado", geojson_key: str | None = "alguna/key.geojson") -> str:
    vuelo_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    engine = create_engine(settings.database_url_sync)
    with engine.connect() as conn:
        conn.execute(text(
            "INSERT INTO vuelos (id, lote_id, sensor, fecha_vuelo, estado, geojson_key, created_at) "
            "VALUES (CAST(:id AS uuid), CAST(:lote_id AS uuid), :sensor, :fecha, :estado, :geojson_key, :created_at)"
        ), {
            "id": vuelo_id, "lote_id": lote_id, "sensor": "dji_mavic3", "fecha": now,
            "estado": estado, "geojson_key": geojson_key, "created_at": now,
        })
        conn.commit()
    engine.dispose()
    return vuelo_id


def _url(lote_id: str, vuelo_id: str) -> str:
    return f"/api/v1/lotes/{lote_id}/vuelos/{vuelo_id}/prescripcion"


def _get(vuelo_id: str, diagnostico: dict, catalogo: dict, **params):
    with (
        patch("app.prescripcion.router.generar_diagnostico", return_value=diagnostico),
        patch("app.prescripcion.router.cargar_catalogo_dosis", return_value=catalogo),
    ):
        return _tc.get(_url(_lote_id, vuelo_id), headers=_auth(), params=params)


def test_prescripcion_devuelve_zip_completo():
    vuelo_id = _insertar_vuelo(_lote_id)
    r = _get(vuelo_id, _DIAGNOSTICO, _CATALOGO, maquina="dron")

    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/zip"
    assert f"prescripcion_dron_{vuelo_id}.zip" in r.headers["content-disposition"]

    zf = zipfile.ZipFile(io.BytesIO(r.content))
    nombres = set(zf.namelist())
    assert {"TASKDATA/TASKDATA.XML", "resumen.json", "LEEME.txt", "producto_test/prescripcion.shp"} <= nombres
    resumen = json.loads(zf.read("resumen.json"))
    assert resumen["limite_lote"] == "real"
    assert resumen["maquina"]["ancho_labor_m"] == 7.0
    assert resumen["iso_xml"]["errores_validacion"] == []
    assert resumen["productos"][0]["simulacion"]["cobertura_pct"] >= 99.9


def test_prescripcion_respeta_ancho_y_margen_pedidos():
    vuelo_id = _insertar_vuelo(_lote_id)
    r = _get(vuelo_id, _DIAGNOSTICO, _CATALOGO, maquina="mosquito", ancho_labor_m=36, margen_m=0)
    assert r.status_code == 200, r.text
    resumen = json.loads(zipfile.ZipFile(io.BytesIO(r.content)).read("resumen.json"))
    assert resumen["maquina"]["ancho_labor_m"] == 36
    assert resumen["maquina"]["margen_m"] == 0


def test_prescripcion_parametros_fuera_de_rango_es_422():
    vuelo_id = _insertar_vuelo(_lote_id)
    assert _get(vuelo_id, _DIAGNOSTICO, _CATALOGO, ancho_labor_m=0).status_code == 422
    assert _get(vuelo_id, _DIAGNOSTICO, _CATALOGO, margen_m=-1).status_code == 422
    assert _get(vuelo_id, _DIAGNOSTICO, _CATALOGO, maquina="avion").status_code == 422


def test_prescripcion_sin_dosis_es_404():
    vuelo_id = _insertar_vuelo(_lote_id)
    r = _get(vuelo_id, _DIAGNOSTICO, {})
    assert r.status_code == 404
    assert "nada que prescribir" in r.json()["detail"]


def test_prescripcion_sin_unidades_es_404():
    vuelo_id = _insertar_vuelo(_lote_id)
    r = _get(vuelo_id, {**_DIAGNOSTICO, "unidades_manejo": []}, _CATALOGO)
    assert r.status_code == 404


def test_prescripcion_vuelo_pendiente_es_404():
    vuelo_id = _insertar_vuelo(_lote_id, estado="pendiente", geojson_key=None)
    r = _tc.get(_url(_lote_id, vuelo_id), headers=_auth())
    assert r.status_code == 404


def test_prescripcion_lote_ajeno_es_404():
    vuelo_id = _insertar_vuelo(_lote_id)
    r = _tc.get(_url(str(uuid.uuid4()), vuelo_id), headers=_auth())
    assert r.status_code == 404


def test_prescripcion_sin_auth_es_401():
    r = _tc.get(_url(_lote_id, str(uuid.uuid4())))
    assert r.status_code == 401
