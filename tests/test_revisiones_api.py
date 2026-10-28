"""
Tests de la revisión del diagnóstico por el agrónomo (RFDR-04):
PUT/DELETE /lotes/{id}/vuelos/{id}/diagnostico/zonas/{zona_id}/revision y
su aparición en GET .../diagnostico.

El diagnóstico se inserta ya guardado en `diagnosticos` (sin MinIO ni
Celery), mismo criterio que test_reportes_api.py.

    docker compose exec api python3 -m pytest tests/test_revisiones_api.py -v
"""
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine, text
from starlette.testclient import TestClient

from app.core.config import settings
from app.main import app

_EMAIL = f"revisiones_{uuid.uuid4().hex[:8]}@agronexo-test.com"
_PASS = "revisiones_pass_123"
_GEOM = {
    "type": "Polygon",
    "coordinates": [[
        [-60.6753, -27.4693], [-60.6701, -27.4693], [-60.6701, -27.4741],
        [-60.6753, -27.4741], [-60.6753, -27.4693],
    ]],
}

_tc = TestClient(app)
_token = ""
_lote_id = ""


def setup_module(module):
    global _token, _lote_id
    from app.core.database import engine as _engine
    _engine.sync_engine.dispose(close=False)
    _tc.__enter__()
    _tc.post("/api/v1/auth/register", json={"email": _EMAIL, "nombre": "Test Revisiones", "password": _PASS})
    r = _tc.post("/api/v1/auth/login", json={"email": _EMAIL, "password": _PASS})
    assert r.status_code == 200, r.text
    _token = r.json()["access_token"]
    r = _tc.post("/api/v1/lotes", json={"nombre": "Lote Revisiones", "geometry": _GEOM}, headers=_auth())
    assert r.status_code == 201, r.text
    _lote_id = r.json()["id"]


def teardown_module(module):
    # Las revisiones son casos de entrenamiento del motor bayesiano: si
    # quedaran, los tests contaminarían el modelo de la base de desarrollo.
    engine = create_engine(settings.database_url_sync)
    with engine.connect() as conn:
        conn.execute(text(
            "DELETE FROM revisiones_diagnostico WHERE vuelo_id IN "
            "(SELECT id FROM vuelos WHERE lote_id = CAST(:l AS uuid))"
        ), {"l": _lote_id})
        conn.commit()
    engine.dispose()
    _tc.__exit__(None, None, None)


def _auth() -> dict:
    return {"Authorization": f"Bearer {_token}"}


def _diagnostico(lote_id: str, vuelo_id: str) -> dict:
    zona = lambda zid, regla, causa: {
        "type": "Feature", "geometry": _GEOM,
        "properties": {
            "zona_id": zid, "regla_id": regla, "causa_indice": causa, "patron_espacial": "circular",
            "ndvi_promedio": 0.45, "area_ha": 2.0,
        },
    }
    return {
        "type": "FeatureCollection",
        "features": [zona(0, "R20", "estres_biotico_fungico"), zona(1, "R01", "sin_problema_detectado")],
        "unidades_manejo": [],
        "metadata": {
            "lote_id": lote_id, "vuelo_id": vuelo_id, "cultivo": "soja", "estadio_fenologico": "R3",
            "ndvi_promedio_lote": 0.6, "motor_version": "1.1.0",
        },
    }


def _vuelo_con_diagnostico(con_diagnostico: bool = True) -> str:
    vuelo_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    engine = create_engine(settings.database_url_sync)
    with engine.connect() as conn:
        conn.execute(text(
            "INSERT INTO vuelos (id, lote_id, sensor, fecha_vuelo, estado, geojson_key, created_at) "
            "VALUES (CAST(:id AS uuid), CAST(:lote AS uuid), 'dji_mavic3', :f, 'completado', 'x.geojson', :f)"
        ), {"id": vuelo_id, "lote": _lote_id, "f": now})
        if con_diagnostico:
            conn.execute(text(
                "INSERT INTO diagnosticos (vuelo_id, resultado, calculado_en, motor_version) "
                "VALUES (CAST(:v AS uuid), CAST(:r AS jsonb), :f, '1.1.0')"
            ), {"v": vuelo_id, "r": json.dumps(_diagnostico(_lote_id, vuelo_id)), "f": now})
        conn.commit()
    engine.dispose()
    return vuelo_id


def _url(vuelo_id: str, zona_id: int, lote_id: str | None = None) -> str:
    return f"/api/v1/lotes/{lote_id or _lote_id}/vuelos/{vuelo_id}/diagnostico/zonas/{zona_id}/revision"


def test_aceptar_y_verla_en_el_diagnostico():
    vuelo_id = _vuelo_con_diagnostico()
    r = _tc.put(_url(vuelo_id, 0), json={"decision": "aceptado", "comentario": "Vi esclerotos"}, headers=_auth())
    assert r.status_code == 200, r.text
    assert r.json()["causa_sugerida"] == "estres_biotico_fungico"

    d = _tc.get(f"/api/v1/lotes/{_lote_id}/vuelos/{vuelo_id}/diagnostico", headers=_auth()).json()
    rev = d["features"][0]["properties"]["revision"]
    assert rev["decision"] == "aceptado" and rev["comentario"] == "Vi esclerotos"
    assert d["features"][1]["properties"]["revision"] is None
    assert d["metadata"]["n_zonas_revisadas"] == 1


def test_r01_se_guarda_como_suelo_desnudo():
    vuelo_id = _vuelo_con_diagnostico()
    r = _tc.put(_url(vuelo_id, 1), json={"decision": "aceptado"}, headers=_auth())
    assert r.json()["causa_sugerida"] == "suelo_desnudo"


def test_modificar_valida_la_causa_y_sobrescribe():
    vuelo_id = _vuelo_con_diagnostico()
    assert _tc.put(_url(vuelo_id, 0), json={"decision": "modificado"}, headers=_auth()).status_code == 422
    assert _tc.put(_url(vuelo_id, 0), json={"decision": "modificado", "causa_confirmada": "estres_biotico_fungico"},
                   headers=_auth()).status_code == 422
    assert _tc.put(_url(vuelo_id, 0), json={"decision": "modificado", "causa_confirmada": "inventada"},
                   headers=_auth()).status_code == 422

    r = _tc.put(_url(vuelo_id, 0), json={"decision": "modificado", "causa_confirmada": "estres_biotico_insecto"},
                headers=_auth())
    assert r.status_code == 200 and r.json()["causa_confirmada"] == "estres_biotico_insecto"
    r = _tc.put(_url(vuelo_id, 0), json={"decision": "rechazado"}, headers=_auth())
    assert r.status_code == 200 and r.json()["decision"] == "rechazado"

    engine = create_engine(settings.database_url_sync)
    with engine.connect() as conn:
        filas = conn.execute(text(
            "SELECT decision, evidencia->>'patron' FROM revisiones_diagnostico WHERE vuelo_id = CAST(:v AS uuid)"
        ), {"v": vuelo_id}).all()
    engine.dispose()
    assert len(filas) == 1
    assert filas[0][0] == "rechazado" and filas[0][1] == "circular"


def test_borrar_revision():
    vuelo_id = _vuelo_con_diagnostico()
    _tc.put(_url(vuelo_id, 0), json={"decision": "aceptado"}, headers=_auth())
    assert _tc.delete(_url(vuelo_id, 0), headers=_auth()).status_code == 204
    assert _tc.delete(_url(vuelo_id, 0), headers=_auth()).status_code == 404


def test_zona_inexistente_o_sin_diagnostico_es_404():
    vuelo_id = _vuelo_con_diagnostico()
    assert _tc.put(_url(vuelo_id, 99), json={"decision": "aceptado"}, headers=_auth()).status_code == 404
    sin_diag = _vuelo_con_diagnostico(con_diagnostico=False)
    assert _tc.put(_url(sin_diag, 0), json={"decision": "aceptado"}, headers=_auth()).status_code == 404


def test_lote_ajeno_es_404():
    vuelo_id = _vuelo_con_diagnostico()
    r = _tc.put(_url(vuelo_id, 0, lote_id=str(uuid.uuid4())), json={"decision": "aceptado"}, headers=_auth())
    assert r.status_code == 404
