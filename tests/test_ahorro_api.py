"""
Tests de los endpoints de HU-R4-11 (precios de productos + ahorro
comparativo). Mismo criterio que tests/test_orden_trabajo_pdf_api.py: los
vuelos se insertan directo en la BD (sin MinIO ni Celery), y
generar_diagnostico()/cargar_catalogo_dosis() se mockean para el camino
feliz — la resolución de PRECIO sí corre real contra la BD, usando el
precio de referencia sembrado por la migración 0023 (Glifosato, 3.50
USD/L) para verificar la pieza nueva de esta tarjeta sin duplicar la
suite de tests/test_orden_trabajo.py (cálculo de dosis, ya cubierto).

Correr en el contenedor api:
    docker compose exec api python3 -m pytest tests/test_ahorro_api.py -v

Correr en CI o local (con DB levantada):
    PYTHONPATH=$(pwd) python3 -m pytest tests/test_ahorro_api.py -v
"""
import uuid
from datetime import date, datetime, timezone
from unittest.mock import patch

from sqlalchemy import create_engine, text
from starlette.testclient import TestClient

from app.core.config import settings
from app.main import app

_EMAIL = f"ahorro_{uuid.uuid4().hex[:8]}@agronexo-test.com"
_PASS = "ahorro_pass_123"
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
_area_ha: float = 0.0
_cultivo_id: str = ""
_producto_glifosato_id: str = ""

# "Atrazina" (no "Glifosato") a propósito: los tests de precio-CRUD de más
# abajo cargan un precio "usuario" para Glifosato, y precios_productos es
# una tabla global (no por test) — usar un producto distinto evita que el
# orden de ejecución de los tests cambie qué precio se resuelve acá.
_CATALOGO_DOSIS_FAKE = {
    "Atrazina": {
        "dosis_referencia": 3.0,
        "unidad": "L",
        "restricciones_ambientales": None,
        "instrucciones_seguridad": None,
    },
}


def _diagnostico_con_unidades(area_tratada_ha: float) -> dict:
    return {
        "unidades_manejo": [
            {
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]},
                "properties": {
                    "unidad_id": 1,
                    "causa_indice": "interferencia_vegetacion",
                    "severidad": "critica",
                    "productos_sugeridos": [{"nombre": "Atrazina", "tipo": "herbicida"}],
                    "area_total_ha": area_tratada_ha,
                    "zona_ids": [1],
                },
            },
        ],
    }


_DIAGNOSTICO_SIN_UNIDADES = {"unidades_manejo": []}


def setup_module(module):
    global _token, _lote_id, _area_ha, _cultivo_id, _producto_glifosato_id
    from app.core.database import engine as _engine
    _engine.sync_engine.dispose(close=False)
    _tc.__enter__()
    _tc.post("/api/v1/auth/register", json={"email": _EMAIL, "nombre": "Test Ahorro", "password": _PASS})
    r = _tc.post("/api/v1/auth/login", json={"email": _EMAIL, "password": _PASS})
    assert r.status_code == 200, f"setup_module login falló: {r.status_code} {r.text}"
    _token = r.json()["access_token"]

    r = _tc.post("/api/v1/lotes", json={"nombre": "Lote Para Tests de Ahorro", "geometry": _GEOM}, headers=_auth())
    assert r.status_code == 201, f"setup_module crear lote falló: {r.text}"
    _lote_id = r.json()["id"]
    _area_ha = r.json()["area_ha"]

    r = _tc.post(f"/api/v1/lotes/{_lote_id}/cultivos", json={"tipo_cultivo": "soja"}, headers=_auth())
    assert r.status_code == 201, f"setup_module crear cultivo falló: {r.text}"
    _cultivo_id = r.json()["id"]

    r = _tc.get("/api/v1/productos-fitosanitarios", headers=_auth())
    assert r.status_code == 200
    _producto_glifosato_id = next(p["id"] for p in r.json()["items"] if p["nombre"] == "Glifosato")


def teardown_module(module):
    _tc.__exit__(None, None, None)


def _auth() -> dict:
    return {"Authorization": f"Bearer {_token}"}


def _precio_referencia_de_bd(nombre_producto: str) -> float:
    engine = create_engine(settings.database_url_sync)
    with engine.connect() as conn:
        return conn.execute(text(
            "SELECT pr.precio_usd FROM precios_productos pr "
            "JOIN productos_fitosanitarios p ON p.id = pr.producto_id "
            "WHERE p.nombre = :nombre AND pr.tipo = 'referencia' ORDER BY pr.fecha DESC LIMIT 1"
        ), {"nombre": nombre_producto}).scalar_one()


def _insertar_vuelo(cultivo_id: str, estado: str = "completado") -> str:
    vuelo_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    engine = create_engine(settings.database_url_sync)
    with engine.connect() as conn:
        conn.execute(text(
            "INSERT INTO vuelos (id, lote_id, cultivo_id, sensor, fecha_vuelo, estado, geojson_key, created_at) "
            "VALUES (CAST(:id AS uuid), CAST(:lote_id AS uuid), CAST(:cultivo_id AS uuid), :sensor, :fecha, "
            ":estado, :geojson_key, :created_at)"
        ), {
            "id": vuelo_id, "lote_id": _lote_id, "cultivo_id": cultivo_id, "sensor": "dji_mavic3",
            "fecha": now, "estado": estado, "geojson_key": "alguna/key.geojson", "created_at": now,
        })
        conn.commit()
    engine.dispose()
    return vuelo_id


# ── Precios ───────────────────────────────────────────────────────────

def test_cargar_precio_usuario_y_listar_historico():
    r = _tc.post(
        f"/api/v1/productos-fitosanitarios/{_producto_glifosato_id}/precios",
        json={"precio_usd": 4.2, "unidad": "L", "fecha": date.today().isoformat()},
        headers=_auth(),
    )
    assert r.status_code == 201, r.text
    assert r.json()["tipo"] == "usuario"
    assert r.json()["precio_usd"] == 4.2

    r = _tc.get(f"/api/v1/productos-fitosanitarios/{_producto_glifosato_id}/precios", headers=_auth())
    assert r.status_code == 200
    tipos = [p["tipo"] for p in r.json()]
    assert "usuario" in tipos and "referencia" in tipos
    print("✓ POST precio de usuario + GET histórico incluye el nuevo y el de referencia sembrado")


def test_cargar_precio_fecha_futura_es_422():
    r = _tc.post(
        f"/api/v1/productos-fitosanitarios/{_producto_glifosato_id}/precios",
        json={"precio_usd": 4.2, "unidad": "L", "fecha": "2099-01-01"},
        headers=_auth(),
    )
    assert r.status_code == 422
    print("✓ POST precio con fecha futura → 422")


def test_cargar_precio_producto_inexistente_es_404():
    r = _tc.post(
        f"/api/v1/productos-fitosanitarios/{uuid.uuid4()}/precios",
        json={"precio_usd": 4.2, "unidad": "L", "fecha": date.today().isoformat()},
        headers=_auth(),
    )
    assert r.status_code == 404
    print("✓ POST precio de producto inexistente → 404")


# ── Ahorro de un vuelo ───────────────────────────────────────────────

def test_ahorro_vuelo_variable_vs_uniforme():
    vuelo_id = _insertar_vuelo(_cultivo_id)
    area_tratada = 2.0
    with (
        patch("app.ahorro.service.generar_diagnostico", return_value=_diagnostico_con_unidades(area_tratada)),
        patch("app.ahorro.service.cargar_catalogo_dosis", return_value=_CATALOGO_DOSIS_FAKE),
    ):
        r = _tc.get(f"/api/v1/lotes/{_lote_id}/vuelos/{vuelo_id}/ahorro", headers=_auth())

    assert r.status_code == 200, r.text
    data = r.json()
    assert data["area_total_lote_ha"] == _area_ha
    assert data["area_tratada_ha"] == area_tratada

    atrazina = next(p for p in data["productos"] if p["producto"] == "Atrazina")
    assert atrazina["cantidad_variable"] == area_tratada * 3.0
    assert atrazina["cantidad_uniforme"] == round(_area_ha * 3.0, 3)
    assert atrazina["ahorro_cantidad"] == round(atrazina["cantidad_uniforme"] - atrazina["cantidad_variable"], 3)
    # Se lee de la BD y no se fija en 5.2: el importador del catálogo (app/catalogo)
    # puede haber actualizado el precio de referencia sembrado por la migración 0023.
    precio_referencia = _precio_referencia_de_bd("Atrazina")
    assert atrazina["precio_tipo"] == "referencia"
    assert atrazina["precio_usd"] == precio_referencia
    assert data["ahorro_total_pesos"] == round(atrazina["ahorro_cantidad"] * precio_referencia, 2)
    print("✓ GET .../ahorro calcula variable vs. uniforme y resuelve el precio real de BD")


def test_ahorro_vuelo_sin_unidades_de_manejo_es_ahorro_cero():
    vuelo_id = _insertar_vuelo(_cultivo_id)
    with patch("app.ahorro.service.generar_diagnostico", return_value=_DIAGNOSTICO_SIN_UNIDADES):
        r = _tc.get(f"/api/v1/lotes/{_lote_id}/vuelos/{vuelo_id}/ahorro", headers=_auth())
    assert r.status_code == 200, r.text
    assert r.json()["productos"] == []
    assert r.json()["ahorro_total_pesos"] == 0.0
    print("✓ vuelo sin unidades de manejo → 200 con ahorro cero, no error")


def test_ahorro_vuelo_pendiente_es_404():
    vuelo_id = _insertar_vuelo(_cultivo_id, estado="pendiente")
    with patch("app.ahorro.service.generar_diagnostico", return_value=None):
        r = _tc.get(f"/api/v1/lotes/{_lote_id}/vuelos/{vuelo_id}/ahorro", headers=_auth())
    assert r.status_code == 404
    print("✓ GET .../ahorro vuelo sin diagnóstico disponible → 404")


def test_ahorro_vuelo_inexistente_es_404():
    r = _tc.get(f"/api/v1/lotes/{_lote_id}/vuelos/{uuid.uuid4()}/ahorro", headers=_auth())
    assert r.status_code == 404
    print("✓ GET .../ahorro vuelo inexistente → 404")


def test_ahorro_vuelo_sin_auth():
    r = _tc.get(f"/api/v1/lotes/{_lote_id}/vuelos/{uuid.uuid4()}/ahorro")
    assert r.status_code == 401
    print("✓ GET .../ahorro sin token → 401")


# ── Ahorro comparativo entre campañas ────────────────────────────────

def test_ahorro_comparativo_acumula_varios_vuelos_de_la_campana():
    vuelo_1 = _insertar_vuelo(_cultivo_id)
    vuelo_2 = _insertar_vuelo(_cultivo_id)
    with (
        patch("app.ahorro.service.generar_diagnostico", return_value=_diagnostico_con_unidades(2.0)),
        patch("app.ahorro.service.cargar_catalogo_dosis", return_value=_CATALOGO_DOSIS_FAKE),
    ):
        r = _tc.get(
            f"/api/v1/lotes/{_lote_id}/ahorro-comparativo", params={"cultivo_a": _cultivo_id}, headers=_auth(),
        )

    assert r.status_code == 200, r.text
    data = r.json()
    assert data["campana_a"]["n_vuelos_considerados"] >= 2  # al menos los 2 insertados en este test
    assert data["campana_b"] is None
    atrazina = next(p for p in data["campana_a"]["productos"] if p["producto"] == "Atrazina")
    # N vuelos, cada uno aporta la misma cantidad variable/uniforme (mismo mock)
    assert atrazina["cantidad_variable"] == round(2.0 * 3.0 * data["campana_a"]["n_vuelos_considerados"], 3)
    print("✓ ahorro-comparativo con un solo cultivo_a acumula todos sus vuelos completados")


def test_ahorro_comparativo_cultivo_inexistente_es_404():
    r = _tc.get(
        f"/api/v1/lotes/{_lote_id}/ahorro-comparativo", params={"cultivo_a": str(uuid.uuid4())}, headers=_auth(),
    )
    assert r.status_code == 404
    print("✓ ahorro-comparativo cultivo_a inexistente → 404")


def test_ahorro_comparativo_cultivo_b_inexistente_es_404():
    r = _tc.get(
        f"/api/v1/lotes/{_lote_id}/ahorro-comparativo",
        params={"cultivo_a": _cultivo_id, "cultivo_b": str(uuid.uuid4())},
        headers=_auth(),
    )
    assert r.status_code == 404
    print("✓ ahorro-comparativo cultivo_b inexistente → 404")


def test_ahorro_comparativo_lote_sin_area_es_409():
    r = _tc.post("/api/v1/lotes", json={"nombre": "Lote Sin Limites"}, headers=_auth())
    assert r.status_code == 201
    lote_sin_area_id = r.json()["id"]
    assert r.json()["area_ha"] is None

    r = _tc.post(f"/api/v1/lotes/{lote_sin_area_id}/cultivos", json={"tipo_cultivo": "soja"}, headers=_auth())
    cultivo_id = r.json()["id"]

    r = _tc.get(
        f"/api/v1/lotes/{lote_sin_area_id}/ahorro-comparativo", params={"cultivo_a": cultivo_id}, headers=_auth(),
    )
    assert r.status_code == 409
    print("✓ ahorro-comparativo en un lote sin límites (area_ha=None) → 409")


def test_ahorro_comparativo_lote_inexistente_es_404():
    r = _tc.get(
        f"/api/v1/lotes/{uuid.uuid4()}/ahorro-comparativo", params={"cultivo_a": str(uuid.uuid4())}, headers=_auth(),
    )
    assert r.status_code == 404
    print("✓ ahorro-comparativo lote inexistente → 404")


def test_ahorro_comparativo_sin_auth():
    r = _tc.get(f"/api/v1/lotes/{_lote_id}/ahorro-comparativo", params={"cultivo_a": _cultivo_id})
    assert r.status_code == 401
    print("✓ ahorro-comparativo sin token → 401")
