"""
Tests del endpoint GET /lotes/{id}/vuelos/{id}/diagnostico.

Mismo criterio que test_vuelos_estado.py: los vuelos se insertan
directamente en la BD (sin MinIO ni Celery) para testear la capa HTTP sin
depender del stack completo. El camino feliz (regla que efectivamente
matchea sobre un GeoJSON real) está cubierto por test_diagnostico_engine.py
(motor puro) y test_forma.py (patrón espacial) — acá se cubren los 404 y
la integración de la capa HTTP/ownership.

Correr en el contenedor api:
    docker compose exec api python3 -m pytest tests/test_diagnostico_api.py -v

Correr en CI o local (con DB levantada):
    PYTHONPATH=$(pwd) python3 -m pytest tests/test_diagnostico_api.py -v
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine, text
from starlette.testclient import TestClient

from app.core.config import settings
from app.main import app

_EMAIL = f"diagnostico_{uuid.uuid4().hex[:8]}@agronexo-test.com"
_PASS = "diagnostico_pass_123"
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
        "email": _EMAIL, "nombre": "Test Diagnostico", "password": _PASS,
    })
    r = _tc.post("/api/v1/auth/login", json={"email": _EMAIL, "password": _PASS})
    assert r.status_code == 200, f"setup_module login falló: {r.status_code} {r.text}"
    _token = r.json()["access_token"]

    r = _tc.post("/api/v1/lotes", json={
        "nombre": "Lote Para Tests de Diagnostico",
        "geometry": _GEOM,
    }, headers={"Authorization": f"Bearer {_token}"})
    assert r.status_code == 201, f"setup_module crear lote falló: {r.text}"
    _lote_id = r.json()["id"]


def teardown_module(module):
    _tc.__exit__(None, None, None)


def _auth() -> dict:
    return {"Authorization": f"Bearer {_token}"}


def _insertar_vuelo(
    lote_id: str, estado: str = "pendiente", geojson_key: str | None = None,
    cultivo_id: str | None = None, estadio_fenologico: str | None = None,
    archivo_original: str | None = None, subido_por_id: str | None = None,
    metodo_umbral: str | None = None, mapeo_bandas: str | None = None,
) -> str:
    """Inserta un vuelo directamente en la BD, sin pasar por MinIO ni Celery.

    mapeo_bandas se recibe ya como JSON string (json.dumps) para el CAST —
    igual que hace el worker real en _actualizar_vuelo."""
    vuelo_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    engine = create_engine(settings.database_url_sync)
    with engine.connect() as conn:
        conn.execute(text(
            "INSERT INTO vuelos (id, lote_id, cultivo_id, estadio_fenologico, sensor, fecha_vuelo, estado, "
            "geojson_key, archivo_original, subido_por_id, metodo_umbral, mapeo_bandas, created_at) "
            "VALUES (CAST(:id AS uuid), CAST(:lote_id AS uuid), CAST(:cultivo_id AS uuid), :estadio, :sensor, "
            ":fecha, :estado, :geojson_key, :archivo_original, CAST(:subido_por_id AS uuid), :metodo_umbral, "
            "CAST(:mapeo_bandas AS JSONB), :created_at)"
        ), {
            "id": vuelo_id,
            "lote_id": lote_id,
            "cultivo_id": cultivo_id,
            "estadio": estadio_fenologico,
            "sensor": "dji_mavic3",
            "fecha": now,
            "estado": estado,
            "geojson_key": geojson_key,
            "archivo_original": archivo_original,
            "subido_por_id": subido_por_id,
            "metodo_umbral": metodo_umbral,
            "mapeo_bandas": mapeo_bandas,
            "created_at": now,
        })
        conn.commit()
    engine.dispose()
    return vuelo_id


# ── 404 por estado del vuelo ─────────────────────────────────────────

def test_diagnostico_vuelo_pendiente_es_404():
    vuelo_id = _insertar_vuelo(_lote_id, "pendiente")
    r = _tc.get(f"/api/v1/lotes/{_lote_id}/vuelos/{vuelo_id}/diagnostico", headers=_auth())
    assert r.status_code == 404
    print("✓ GET /diagnostico vuelo pendiente → 404")


def test_diagnostico_vuelo_procesando_es_404():
    vuelo_id = _insertar_vuelo(_lote_id, "procesando")
    r = _tc.get(f"/api/v1/lotes/{_lote_id}/vuelos/{vuelo_id}/diagnostico", headers=_auth())
    assert r.status_code == 404
    print("✓ GET /diagnostico vuelo procesando → 404")


def test_diagnostico_vuelo_error_es_404():
    vuelo_id = _insertar_vuelo(_lote_id, "error")
    r = _tc.get(f"/api/v1/lotes/{_lote_id}/vuelos/{vuelo_id}/diagnostico", headers=_auth())
    assert r.status_code == 404
    print("✓ GET /diagnostico vuelo en error → 404")


def test_diagnostico_vuelo_completado_sin_geojson_es_404():
    # completado pero sin geojson_key (worker no llegó a guardar el resultado)
    vuelo_id = _insertar_vuelo(_lote_id, "completado", geojson_key=None)
    r = _tc.get(f"/api/v1/lotes/{_lote_id}/vuelos/{vuelo_id}/diagnostico", headers=_auth())
    assert r.status_code == 404
    print("✓ GET /diagnostico vuelo completado sin geojson_key → 404")


# ── 404 por lote/vuelo inexistente o ajeno ───────────────────────────

def test_diagnostico_vuelo_inexistente():
    r = _tc.get(f"/api/v1/lotes/{_lote_id}/vuelos/{uuid.uuid4()}/diagnostico", headers=_auth())
    assert r.status_code == 404
    print("✓ GET /diagnostico vuelo inexistente → 404")


def test_diagnostico_lote_inexistente():
    r = _tc.get(f"/api/v1/lotes/{uuid.uuid4()}/vuelos/{uuid.uuid4()}/diagnostico", headers=_auth())
    assert r.status_code == 404
    print("✓ GET /diagnostico lote inexistente → 404")


def test_diagnostico_vuelo_de_otro_lote_es_404():
    # Un vuelo real, pero consultado con un lote_id que no es el suyo —
    # nunca debe filtrar existencia con 403.
    vuelo_id = _insertar_vuelo(_lote_id, "completado", geojson_key="alguna/key.geojson")
    r = _tc.get(f"/api/v1/lotes/{uuid.uuid4()}/vuelos/{vuelo_id}/diagnostico", headers=_auth())
    assert r.status_code == 404
    print("✓ GET /diagnostico vuelo con lote_id ajeno → 404")


# ── Cultivo del análisis ─────────────────────────────────────────────

def _crear_cultivo(tipo: str = "maiz", variedad: str | None = "DK 72-10") -> str:
    r = _tc.post(f"/api/v1/lotes/{_lote_id}/cultivos", json={
        "tipo_cultivo": tipo, "variedad": variedad, "fecha_siembra": "2026-09-01T00:00:00Z",
    }, headers=_auth())
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _geojson_ndvi_fixture() -> dict:
    import json
    from pathlib import Path
    return json.loads((Path(__file__).parent / "fixtures" / "resultado_ndvi.geojson").read_text(encoding="utf-8"))


def test_diagnostico_usa_el_cultivo_del_vuelo(monkeypatch):
    # El cultivo sale del análisis (vuelo.cultivo), no del lote: dos vuelos del
    # mismo lote con cultivos distintos deben diagnosticarse con el suyo.
    from app.diagnostico import service as diag_service

    async def _fake_geojson(db, lote_id, vuelo_id):
        return _geojson_ndvi_fixture()

    monkeypatch.setattr(diag_service, "obtener_resultado_geojson", _fake_geojson)

    cultivo_maiz = _crear_cultivo("maiz", "DK 72-10")
    vuelo_id = _insertar_vuelo(
        _lote_id, "completado", geojson_key="x.geojson", cultivo_id=cultivo_maiz, estadio_fenologico="R2",
    )
    r = _tc.get(f"/api/v1/lotes/{_lote_id}/vuelos/{vuelo_id}/diagnostico", headers=_auth())
    assert r.status_code == 200, r.text
    meta = r.json()["metadata"]
    assert meta["cultivo"] == "maiz"
    assert meta["variedad"] == "DK 72-10"
    assert meta["cultivo_id"] == cultivo_maiz
    assert meta["estadio_fenologico"] == "R2"

    cultivo_soja = _crear_cultivo("soja", None)
    vuelo_soja = _insertar_vuelo(
        _lote_id, "completado", geojson_key="x.geojson", cultivo_id=cultivo_soja, estadio_fenologico="R2",
    )
    r = _tc.get(f"/api/v1/lotes/{_lote_id}/vuelos/{vuelo_soja}/diagnostico", headers=_auth())
    assert r.status_code == 200, r.text
    assert r.json()["metadata"]["cultivo"] == "soja"
    print("✓ GET /diagnostico usa el cultivo asociado a cada vuelo")


def test_diagnostico_vuelo_sin_cultivo_es_409(monkeypatch):
    from app.diagnostico import service as diag_service

    async def _fake_geojson(db, lote_id, vuelo_id):
        return _geojson_ndvi_fixture()

    monkeypatch.setattr(diag_service, "obtener_resultado_geojson", _fake_geojson)

    vuelo_id = _insertar_vuelo(_lote_id, "completado", geojson_key="x.geojson", cultivo_id=None)
    r = _tc.get(f"/api/v1/lotes/{_lote_id}/vuelos/{vuelo_id}/diagnostico", headers=_auth())
    assert r.status_code == 409
    assert "cultivo" in r.json()["detail"].lower()
    print("✓ GET /diagnostico vuelo sin cultivo → 409")


# ── Trazabilidad (HU-R4-02) ──────────────────────────────────────────

def test_diagnostico_incluye_trazabilidad_completa(monkeypatch):
    import json

    from app.diagnostico.reglas import MOTOR_VERSION

    from app.diagnostico import service as diag_service

    async def _fake_geojson(db, lote_id, vuelo_id):
        return _geojson_ndvi_fixture()

    monkeypatch.setattr(diag_service, "obtener_resultado_geojson", _fake_geojson)

    engine = create_engine(settings.database_url_sync)
    with engine.connect() as conn:
        usuario_id = conn.execute(
            text("SELECT id FROM usuarios WHERE email = :email"), {"email": _EMAIL},
        ).scalar_one()
    engine.dispose()

    cultivo = _crear_cultivo("soja", None)
    vuelo_id = _insertar_vuelo(
        _lote_id, "completado", geojson_key="x.geojson", cultivo_id=cultivo, estadio_fenologico="R2",
        archivo_original=f"{usuario_id}/{_lote_id}/vuelo/original.tif",
        subido_por_id=str(usuario_id),
        metodo_umbral="otsu",
        mapeo_bandas=json.dumps({"NIR": 4, "RED": 2, "RE": 3, "GREEN": 1, "BLUE": None}),
    )
    r = _tc.get(f"/api/v1/lotes/{_lote_id}/vuelos/{vuelo_id}/diagnostico", headers=_auth())
    assert r.status_code == 200, r.text
    meta = r.json()["metadata"]
    assert meta["motor_version"] == MOTOR_VERSION
    assert meta["archivo_original"] == f"{usuario_id}/{_lote_id}/vuelo/original.tif"
    assert meta["subido_por"] == f"Test Diagnostico ({_EMAIL})"
    assert meta["metodo_umbral"] == "otsu"
    assert meta["mapeo_bandas"] == {"NIR": 4, "RED": 2, "RE": 3, "GREEN": 1, "BLUE": None}
    print("✓ GET /diagnostico incluye archivo, uploader, umbral, mapeo de bandas y versión del motor")


# ── Auth ──────────────────────────────────────────────────────────────

def test_diagnostico_sin_auth():
    r = _tc.get(f"/api/v1/lotes/{_lote_id}/vuelos/{uuid.uuid4()}/diagnostico")
    assert r.status_code == 401
    print("✓ GET /diagnostico sin token → 401")


if __name__ == "__main__":
    setup_module(None)
    try:
        print("\n── Diagnóstico: casos 404 y auth ────────────────────")
        test_diagnostico_vuelo_pendiente_es_404()
        test_diagnostico_vuelo_procesando_es_404()
        test_diagnostico_vuelo_error_es_404()
        test_diagnostico_vuelo_completado_sin_geojson_es_404()
        test_diagnostico_vuelo_inexistente()
        test_diagnostico_lote_inexistente()
        test_diagnostico_vuelo_de_otro_lote_es_404()
        test_diagnostico_sin_auth()
        print("\nTodos los tests de diagnóstico pasaron.\n")
    finally:
        teardown_module(None)


# ── Recálculo automático (firma de datos) ────────────────────────────

def _calculado_en(vuelo_id: str) -> str:
    r = _tc.get(f"/api/v1/lotes/{_lote_id}/vuelos/{vuelo_id}/diagnostico", headers=_auth())
    assert r.status_code == 200, r.text
    return r.json()["metadata"]["calculado_en"], r.json()["metadata"]


def test_diagnostico_guardado_se_reutiliza_si_nada_cambio(monkeypatch):
    from app.diagnostico import service as diag_service

    async def _fake_geojson(db, lote_id, vuelo_id):
        return _geojson_ndvi_fixture()

    monkeypatch.setattr(diag_service, "obtener_resultado_geojson", _fake_geojson)
    cultivo = _crear_cultivo("soja", None)
    vuelo_id = _insertar_vuelo(_lote_id, "completado", geojson_key="x.geojson", cultivo_id=cultivo, estadio_fenologico="R2")

    primero, meta = _calculado_en(vuelo_id)
    segundo, _ = _calculado_en(vuelo_id)
    assert meta["firma_datos"]
    assert primero == segundo


def test_diagnostico_se_recalcula_solo_al_cambiar_el_estadio(monkeypatch):
    from app.diagnostico import service as diag_service

    async def _fake_geojson(db, lote_id, vuelo_id):
        return _geojson_ndvi_fixture()

    monkeypatch.setattr(diag_service, "obtener_resultado_geojson", _fake_geojson)
    cultivo = _crear_cultivo("soja", None)
    vuelo_id = _insertar_vuelo(_lote_id, "completado", geojson_key="x.geojson", cultivo_id=cultivo, estadio_fenologico="R2")

    primero, _ = _calculado_en(vuelo_id)
    r = _tc.put(f"/api/v1/lotes/{_lote_id}/vuelos/{vuelo_id}", json={"estadio_fenologico": "R3"}, headers=_auth())
    assert r.status_code == 200, r.text

    segundo, meta = _calculado_en(vuelo_id)
    assert segundo != primero
    assert meta["estadio_fenologico"] == "R3"


def test_diagnostico_se_recalcula_solo_al_cambiar_el_cultivo(monkeypatch):
    from app.diagnostico import service as diag_service

    async def _fake_geojson(db, lote_id, vuelo_id):
        return _geojson_ndvi_fixture()

    monkeypatch.setattr(diag_service, "obtener_resultado_geojson", _fake_geojson)
    soja = _crear_cultivo("soja", None)
    maiz = _crear_cultivo("maiz", None)
    vuelo_id = _insertar_vuelo(_lote_id, "completado", geojson_key="x.geojson", cultivo_id=soja, estadio_fenologico="R2")

    _, meta = _calculado_en(vuelo_id)
    assert meta["cultivo"] == "soja"
    r = _tc.put(f"/api/v1/lotes/{_lote_id}/vuelos/{vuelo_id}", json={"cultivo_id": maiz}, headers=_auth())
    assert r.status_code == 200, r.text
    _, meta = _calculado_en(vuelo_id)
    assert meta["cultivo"] == "maiz"


def test_diagnostico_se_recalcula_solo_al_cambiar_la_fecha(monkeypatch):
    from app.diagnostico import service as diag_service

    async def _fake_geojson(db, lote_id, vuelo_id):
        return _geojson_ndvi_fixture()

    monkeypatch.setattr(diag_service, "obtener_resultado_geojson", _fake_geojson)
    cultivo = _crear_cultivo("soja", None)
    vuelo_id = _insertar_vuelo(_lote_id, "completado", geojson_key="x.geojson", cultivo_id=cultivo, estadio_fenologico="R2")

    primero, _ = _calculado_en(vuelo_id)
    r = _tc.put(f"/api/v1/lotes/{_lote_id}/vuelos/{vuelo_id}", json={"fecha_vuelo": "2026-03-15T12:00:00Z"}, headers=_auth())
    assert r.status_code == 200, r.text
    segundo, meta = _calculado_en(vuelo_id)
    assert segundo != primero
    assert meta["fecha_vuelo"].startswith("2026-03-15")


def test_diagnostico_se_recalcula_solo_si_cambia_el_catalogo(monkeypatch):
    from app.diagnostico import service as diag_service

    async def _fake_geojson(db, lote_id, vuelo_id):
        return _geojson_ndvi_fixture()

    monkeypatch.setattr(diag_service, "obtener_resultado_geojson", _fake_geojson)
    cultivo = _crear_cultivo("soja", None)
    vuelo_id = _insertar_vuelo(_lote_id, "completado", geojson_key="x.geojson", cultivo_id=cultivo, estadio_fenologico="R2")

    primero, _ = _calculado_en(vuelo_id)

    async def _catalogo_distinto(db, cultivo=None):
        return {"interferencia_vegetacion": [{"nombre": "Producto Nuevo", "tipo": "herbicida"}]}

    monkeypatch.setattr(diag_service, "_cargar_catalogo_productos", _catalogo_distinto)
    segundo, _ = _calculado_en(vuelo_id)
    assert segundo != primero
