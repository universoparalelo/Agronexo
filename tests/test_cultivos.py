"""
Tests de cultivos de un lote y de la regla "todo análisis lleva un cultivo".

Correr en el contenedor api:
    docker compose exec api python3 -m pytest tests/test_cultivos.py -v

Correr en CI o local (con DB levantada):
    PYTHONPATH=$(pwd) python3 -m pytest tests/test_cultivos.py -v

Los rechazos (400/404/422) ocurren antes de tocar MinIO o Celery; los
caminos felices los simulan con monkeypatch. El diagnóstico con cultivo está
en test_diagnostico_api.py.
"""
import uuid

from starlette.testclient import TestClient

from app.main import app

_EMAIL = f"cultivos_{uuid.uuid4().hex[:8]}@agronexo-test.com"
_EMAIL_OTRO = f"cultivos_otro_{uuid.uuid4().hex[:8]}@agronexo-test.com"
_PASS = "cultivos_pass_123"
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
_TIFF_MINIMO = b"II*\x00" + b"\x00" * 64

_tc = TestClient(app)
_token: str = ""
_token_otro: str = ""
_lote_id: str = ""


def _login(email: str) -> str:
    _tc.post("/api/v1/auth/register", json={"email": email, "nombre": "Test Cultivos", "password": _PASS})
    r = _tc.post("/api/v1/auth/login", json={"email": email, "password": _PASS})
    assert r.status_code == 200, f"login falló: {r.status_code} {r.text}"
    return r.json()["access_token"]


def setup_module(module):
    global _token, _token_otro, _lote_id
    from app.core.database import engine as _engine
    _engine.sync_engine.dispose(close=False)
    _tc.__enter__()
    _token = _login(_EMAIL)
    _token_otro = _login(_EMAIL_OTRO)

    r = _tc.post("/api/v1/lotes", json={"nombre": "Lote Para Tests de Cultivos", "geometry": _GEOM}, headers=_auth())
    assert r.status_code == 201, f"setup_module crear lote falló: {r.text}"
    _lote_id = r.json()["id"]


def teardown_module(module):
    _tc.__exit__(None, None, None)


def _auth(token: str | None = None) -> dict:
    return {"Authorization": f"Bearer {token or _token}"}


def _crear_cultivo(**extra) -> dict:
    body = {"tipo_cultivo": "soja", **extra}
    r = _tc.post(f"/api/v1/lotes/{_lote_id}/cultivos", json=body, headers=_auth())
    assert r.status_code == 201, r.text
    return r.json()


# ── CRUD de cultivos ─────────────────────────────────────────────────

def test_crear_cultivo():
    body = _crear_cultivo(
        variedad="DM 46i17", fecha_siembra="2026-11-15T00:00:00Z", fecha_cosecha="2027-04-20T00:00:00Z",
    )
    assert body["tipo_cultivo"] == "soja"
    assert body["variedad"] == "DM 46i17"
    assert body["lote_id"] == _lote_id
    assert body["fecha_siembra"].startswith("2026-11-15")
    assert body["fecha_cosecha"].startswith("2027-04-20")
    print("✓ POST /lotes/{id}/cultivos → 201")


def test_crear_cultivo_solo_tipo():
    body = _crear_cultivo(tipo_cultivo="algodon")
    assert body["variedad"] is None and body["fecha_siembra"] is None and body["fecha_cosecha"] is None
    print("✓ POST /cultivos con solo tipo_cultivo → 201")


def test_crear_cultivo_tipo_invalido():
    r = _tc.post(f"/api/v1/lotes/{_lote_id}/cultivos", json={"tipo_cultivo": "trigo"}, headers=_auth())
    assert r.status_code == 422
    print("✓ POST /cultivos con tipo inválido → 422")


def test_crear_cultivo_cosecha_antes_de_siembra():
    r = _tc.post(f"/api/v1/lotes/{_lote_id}/cultivos", json={
        "tipo_cultivo": "maiz", "fecha_siembra": "2026-11-15T00:00:00Z", "fecha_cosecha": "2026-10-01T00:00:00Z",
    }, headers=_auth())
    assert r.status_code == 422
    print("✓ POST /cultivos con cosecha < siembra → 422")


def test_listar_cultivos_y_aparecen_en_el_lote():
    cultivo = _crear_cultivo(tipo_cultivo="sorgo")
    r = _tc.get(f"/api/v1/lotes/{_lote_id}/cultivos", headers=_auth())
    assert r.status_code == 200
    assert cultivo["id"] in [c["id"] for c in r.json()]

    r = _tc.get(f"/api/v1/lotes/{_lote_id}", headers=_auth())
    assert r.status_code == 200
    assert cultivo["id"] in [c["id"] for c in r.json()["cultivos"]]
    print("✓ GET /cultivos y lote.cultivos incluyen el cultivo creado")


def test_actualizar_cultivo():
    cultivo = _crear_cultivo(fecha_siembra="2026-11-15T00:00:00Z")
    r = _tc.put(f"/api/v1/lotes/{_lote_id}/cultivos/{cultivo['id']}", json={
        "fecha_cosecha": "2027-04-20T00:00:00Z", "variedad": "Nueva",
    }, headers=_auth())
    assert r.status_code == 200
    assert r.json()["variedad"] == "Nueva"
    assert r.json()["fecha_cosecha"].startswith("2027-04-20")
    assert r.json()["fecha_siembra"].startswith("2026-11-15")
    print("✓ PUT /cultivos/{id} actualiza solo lo enviado")


def test_actualizar_cultivo_cosecha_antes_de_siembra_guardada():
    cultivo = _crear_cultivo(fecha_siembra="2026-11-15T00:00:00Z")
    r = _tc.put(f"/api/v1/lotes/{_lote_id}/cultivos/{cultivo['id']}", json={
        "fecha_cosecha": "2026-01-01T00:00:00Z",
    }, headers=_auth())
    assert r.status_code == 422
    print("✓ PUT /cultivos con cosecha anterior a la siembra guardada → 422")


def test_eliminar_cultivo_es_soft_delete():
    cultivo = _crear_cultivo(tipo_cultivo="maiz")
    r = _tc.delete(f"/api/v1/lotes/{_lote_id}/cultivos/{cultivo['id']}", headers=_auth())
    assert r.status_code == 204
    r = _tc.get(f"/api/v1/lotes/{_lote_id}/cultivos", headers=_auth())
    assert cultivo["id"] not in [c["id"] for c in r.json()]
    r = _tc.get(f"/api/v1/lotes/{_lote_id}", headers=_auth())
    assert cultivo["id"] not in [c["id"] for c in r.json()["cultivos"]]
    print("✓ DELETE /cultivos/{id} → 204 y deja de listarse")


def test_cultivo_de_otro_usuario_es_404():
    r = _tc.get(f"/api/v1/lotes/{_lote_id}/cultivos", headers=_auth(_token_otro))
    assert r.status_code == 404
    r = _tc.post(f"/api/v1/lotes/{_lote_id}/cultivos", json={"tipo_cultivo": "soja"}, headers=_auth(_token_otro))
    assert r.status_code == 404
    print("✓ cultivos de un lote ajeno → 404")


def test_cultivos_sin_auth():
    r = _tc.get(f"/api/v1/lotes/{_lote_id}/cultivos")
    assert r.status_code == 401
    print("✓ GET /cultivos sin token → 401")


# ── Un análisis siempre lleva cultivo ────────────────────────────────

def _post_geotiff(**form):
    return _tc.post(
        f"/api/v1/lotes/{_lote_id}/vuelos",
        data={"sensor": "sentinel2", "estadio_fenologico": "V6", **form},
        files={"archivo": ("prueba.tif", _TIFF_MINIMO, "image/tiff")},
        headers=_auth(),
    )


def test_subir_geotiff_sin_cultivo_es_400():
    r = _post_geotiff()
    assert r.status_code == 400
    assert "cultivo" in r.json()["detail"].lower()
    print("✓ POST /vuelos sin cultivo → 400")


def test_subir_geotiff_con_cultivo_inexistente_es_404():
    r = _post_geotiff(cultivo_id=str(uuid.uuid4()))
    assert r.status_code == 404
    print("✓ POST /vuelos con cultivo_id inexistente → 404")


def test_subir_geotiff_con_cultivo_de_otro_lote_es_404():
    r = _tc.post("/api/v1/lotes", json={"nombre": "Otro Lote", "geometry": _GEOM}, headers=_auth())
    otro_lote = r.json()["id"]
    r = _tc.post(f"/api/v1/lotes/{otro_lote}/cultivos", json={"tipo_cultivo": "soja"}, headers=_auth())
    cultivo_ajeno = r.json()["id"]
    r = _post_geotiff(cultivo_id=cultivo_ajeno)
    assert r.status_code == 404
    print("✓ POST /vuelos con cultivo de otro lote → 404")


def test_subir_geotiff_con_cultivo_existente_y_nuevo_es_400():
    cultivo = _crear_cultivo()
    r = _post_geotiff(cultivo_id=cultivo["id"], cultivo_tipo="maiz")
    assert r.status_code == 400
    print("✓ POST /vuelos con cultivo existente Y nuevo → 400")


def test_subir_geotiff_cultivo_nuevo_con_fechas_incoherentes_es_422():
    r = _post_geotiff(
        cultivo_tipo="maiz",
        cultivo_fecha_siembra="2026-11-15T00:00:00Z", cultivo_fecha_cosecha="2026-10-01T00:00:00Z",
    )
    assert r.status_code == 422
    print("✓ POST /vuelos con cultivo nuevo de fechas incoherentes → 422")


def test_satelite_sin_cultivo_es_400():
    r = _tc.post(f"/api/v1/lotes/{_lote_id}/vuelos/desde-satelite", json={
        "escena_id": "S2B_21JTK_20260902_0_L2A", "fecha_vuelo": "2026-09-02T00:00:00Z", "estadio_fenologico": "V6",
    }, headers=_auth())
    assert r.status_code == 400
    print("✓ POST /vuelos/desde-satelite sin cultivo → 400")


def test_satelite_con_cultivo_inexistente_es_404():
    r = _tc.post(f"/api/v1/lotes/{_lote_id}/vuelos/desde-satelite", json={
        "escena_id": "S2B_21JTK_20260902_0_L2A", "fecha_vuelo": "2026-09-02T00:00:00Z", "estadio_fenologico": "V6",
        "cultivo_id": str(uuid.uuid4()),
    }, headers=_auth())
    assert r.status_code == 404
    print("✓ POST /vuelos/desde-satelite con cultivo inexistente → 404")


def test_rechazo_no_deja_cultivos_huerfanos():
    antes = len(_tc.get(f"/api/v1/lotes/{_lote_id}/cultivos", headers=_auth()).json())
    # cultivo nuevo + cultivo existente → se rechaza; no debe crearse el nuevo
    cultivo = _crear_cultivo()
    _post_geotiff(cultivo_id=cultivo["id"], cultivo_tipo="maiz")
    despues = len(_tc.get(f"/api/v1/lotes/{_lote_id}/cultivos", headers=_auth()).json())
    assert despues == antes + 1
    print("✓ un análisis rechazado no crea cultivos huérfanos")


# ── Camino feliz (MinIO y Celery simulados) ──────────────────────────

class _TareaFalsa:
    id = "tarea-falsa"


def _simular_infraestructura(monkeypatch):
    from app.core import storage
    from app.ingesta import service as ingesta_service

    monkeypatch.setattr(storage, "upload_geotiff_stream", lambda **kw: "usuario/lote/vuelo/original.tif")
    monkeypatch.setattr(ingesta_service.celery_app, "send_task", lambda *a, **kw: _TareaFalsa())


def test_analisis_con_cultivo_existente(monkeypatch):
    _simular_infraestructura(monkeypatch)
    cultivo = _crear_cultivo(tipo_cultivo="maiz", variedad="DK 72-10")
    r = _post_geotiff(cultivo_id=cultivo["id"])
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["cultivo_id"] == cultivo["id"]
    assert body["cultivo"]["tipo_cultivo"] == "maiz"
    assert body["estadio_fenologico"] == "V6"

    r = _tc.get(f"/api/v1/lotes/{_lote_id}/vuelos", headers=_auth())
    vuelo = next(v for v in r.json() if v["vuelo_id"] == body["vuelo_id"])
    assert vuelo["cultivo_id"] == cultivo["id"]
    assert vuelo["cultivo"]["variedad"] == "DK 72-10"
    print("✓ análisis sobre un cultivo ya cargado → 202 y el vuelo queda asociado")


def test_analisis_creando_cultivo_nuevo(monkeypatch):
    _simular_infraestructura(monkeypatch)
    antes = len(_tc.get(f"/api/v1/lotes/{_lote_id}/cultivos", headers=_auth()).json())
    r = _post_geotiff(
        cultivo_tipo="algodon", cultivo_variedad="Guazuncho", cultivo_fecha_siembra="2026-10-01T00:00:00Z",
    )
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["cultivo"]["tipo_cultivo"] == "algodon"
    assert body["cultivo"]["variedad"] == "Guazuncho"

    cultivos = _tc.get(f"/api/v1/lotes/{_lote_id}/cultivos", headers=_auth()).json()
    assert len(cultivos) == antes + 1
    assert body["cultivo_id"] in [c["id"] for c in cultivos]
    print("✓ análisis creando un cultivo nuevo → 202 y el cultivo queda en el lote")


def test_satelite_con_cultivo_nuevo(monkeypatch):
    _simular_infraestructura(monkeypatch)
    r = _tc.post(f"/api/v1/lotes/{_lote_id}/vuelos/desde-satelite", json={
        "escena_id": "S2B_21JTK_20260902_0_L2A", "fecha_vuelo": "2026-09-02T00:00:00Z", "estadio_fenologico": "V6",
        "cultivo": {"tipo_cultivo": "sorgo", "variedad": "Sureño"},
    }, headers=_auth())
    assert r.status_code == 202, r.text
    assert r.json()["cultivo"]["tipo_cultivo"] == "sorgo"
    print("✓ imagen satelital creando un cultivo nuevo → 202")


# ── El estadio fenológico es obligatorio ─────────────────────────────

def test_subir_geotiff_sin_estadio_es_422():
    cultivo = _crear_cultivo()
    r = _tc.post(
        f"/api/v1/lotes/{_lote_id}/vuelos",
        data={"sensor": "sentinel2", "cultivo_id": cultivo["id"]},
        files={"archivo": ("prueba.tif", _TIFF_MINIMO, "image/tiff")},
        headers=_auth(),
    )
    assert r.status_code == 422
    print("✓ POST /vuelos sin estadio fenológico → 422")


def test_subir_geotiff_con_estadio_en_blanco_es_422():
    cultivo = _crear_cultivo()
    r = _post_geotiff(cultivo_id=cultivo["id"], estadio_fenologico="   ")
    assert r.status_code == 422
    print("✓ POST /vuelos con estadio en blanco → 422")


def test_satelite_sin_estadio_es_422():
    cultivo = _crear_cultivo()
    r = _tc.post(f"/api/v1/lotes/{_lote_id}/vuelos/desde-satelite", json={
        "escena_id": "S2B_21JTK_20260902_0_L2A", "fecha_vuelo": "2026-09-02T00:00:00Z",
        "cultivo_id": cultivo["id"],
    }, headers=_auth())
    assert r.status_code == 422
    print("✓ POST /desde-satelite sin estadio fenológico → 422")


def test_satelite_con_estadio_en_blanco_es_422():
    cultivo = _crear_cultivo()
    r = _tc.post(f"/api/v1/lotes/{_lote_id}/vuelos/desde-satelite", json={
        "escena_id": "S2B_21JTK_20260902_0_L2A", "fecha_vuelo": "2026-09-02T00:00:00Z",
        "estadio_fenologico": "  ", "cultivo_id": cultivo["id"],
    }, headers=_auth())
    assert r.status_code == 422
    print("✓ POST /desde-satelite con estadio en blanco → 422")
