"""
Tests CRUD de lotes + soft delete.

Correr en el contenedor api:
    docker compose exec api python3 -m pytest tests/test_lotes.py -v

Correr en CI o local (con DB levantada):
    PYTHONPATH=$(pwd) python3 -m pytest tests/test_lotes.py -v
"""
import uuid

from starlette.testclient import TestClient

from app.main import app

_EMAIL = f"lotes_{uuid.uuid4().hex[:8]}@agronexo-test.com"
_PASS = "lotes_pass_456"
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
_suelo_id: str = ""


def setup_module(module):
    global _token, _suelo_id
    from app.core.database import engine as _engine
    _engine.sync_engine.dispose(close=False)
    _tc.__enter__()
    _tc.post("/api/v1/auth/register", json={
        "email": _EMAIL, "nombre": "Test Lotes", "password": _PASS,
    })
    r = _tc.post("/api/v1/auth/login", json={"email": _EMAIL, "password": _PASS})
    assert r.status_code == 200, f"setup_module login falló: {r.status_code} {r.text}"
    _token = r.json()["access_token"]

    suelos = _tc.get("/api/v1/lotes/suelos", headers={"Authorization": f"Bearer {_token}"}).json()
    assert suelos, "setup_module: catálogo de suelos vacío (falta correr migración 0014)"
    _suelo_id = suelos[0]["id"]
    print(f"\nUsuario de prueba: {_EMAIL}")


def teardown_module(module):
    _tc.__exit__(None, None, None)


def _auth() -> dict:
    return {"Authorization": f"Bearer {_token}"}


def _crear_lote(nombre: str = "Lote Test") -> dict:
    r = _tc.post("/api/v1/lotes", json={
        "nombre": nombre, "suelo_id": _suelo_id,
    }, headers=_auth())
    assert r.status_code == 201, f"No se pudo crear lote auxiliar: {r.text}"
    return r.json()


# ── Crear ─────────────────────────────────────────────────────────────

def test_crear_lote():
    r = _tc.post("/api/v1/lotes", json={
        "nombre": "Lote Norte Principal",
        "suelo_id": _suelo_id,
    }, headers=_auth())
    assert r.status_code == 201
    body = r.json()
    assert body["nombre"] == "Lote Norte Principal"
    assert body["suelo_id"] == _suelo_id
    # El límite geográfico no se pide al crear — lo deriva el worker del primer GeoTIFF.
    assert body["geometry"] is None
    assert body["area_ha"] is None
    # Ubicación es opcional — sin especificarla, el lote queda sin ubicacion_id.
    assert body["ubicacion_id"] is None
    print("✓ POST /lotes → 201, sin geometry/area_ha/ubicacion (opcionales)")


def test_crear_lote_con_ubicacion():
    r = _tc.post("/api/v1/lotes", json={
        "nombre": "Lote Con Ubicación",
        "suelo_id": _suelo_id,
        "provincia": "chaco",
        "departamento": " Presidencia Roque Sáenz Peña ",
        "localidad": " Colonia Elisa ",
    }, headers=_auth())
    assert r.status_code == 201
    body = r.json()
    assert body["ubicacion_id"] is not None
    assert body["ubicacion"]["provincia"] == "chaco"
    assert body["ubicacion"]["departamento"] == "Presidencia Roque Sáenz Peña"
    assert body["ubicacion"]["localidad"] == "Colonia Elisa"

    # Misma provincia/departamento/localidad (case-insensitive) en otro lote -> reusa la ubicación.
    r2 = _tc.post("/api/v1/lotes", json={
        "nombre": "Lote Con Ubicación 2",
        "suelo_id": _suelo_id,
        "provincia": "chaco",
        "departamento": "presidencia roque sáenz peña",
        "localidad": "colonia elisa",
    }, headers=_auth())
    assert r2.status_code == 201
    assert r2.json()["ubicacion_id"] == body["ubicacion_id"]
    print("✓ POST /lotes con provincia/departamento/localidad → 201, ubicación creada y reusada")


def test_crear_lote_ubicacion_incompleta():
    r = _tc.post("/api/v1/lotes", json={
        "nombre": "Lote Ubicación Incompleta",
        "suelo_id": _suelo_id,
        "departamento": "Resistencia",
        # sin provincia -> 422
    }, headers=_auth())
    assert r.status_code == 422
    print("✓ POST /lotes con departamento sin provincia → 422")


def test_crear_lote_provincia_y_localidad_sin_departamento():
    """Departamento es opcional — provincia + localidad alcanza (caso típico: el
    usuario sabe la ciudad, no el departamento administrativo)."""
    r = _tc.post("/api/v1/lotes", json={
        "nombre": "Lote Sin Departamento",
        "suelo_id": _suelo_id,
        "provincia": "chaco",
        "localidad": "Resistencia",
    }, headers=_auth())
    assert r.status_code == 201
    body = r.json()
    assert body["ubicacion"]["provincia"] == "chaco"
    assert body["ubicacion"]["departamento"] is None
    assert body["ubicacion"]["localidad"] == "Resistencia"
    print("✓ POST /lotes con provincia + localidad, sin departamento → 201")


def test_crear_lote_sin_auth():
    r = _tc.post("/api/v1/lotes", json={
        "nombre": "Sin Auth", "suelo_id": _suelo_id,
    })
    assert r.status_code == 401
    print("✓ POST /lotes sin token → 401")


def test_crear_lote_suelo_id_faltante():
    r = _tc.post("/api/v1/lotes", json={
        "nombre": "Lote Sin Suelo",
    }, headers=_auth())
    assert r.status_code == 422
    print("✓ POST /lotes sin suelo_id → 422")


def test_crear_lote_suelo_inexistente():
    r = _tc.post("/api/v1/lotes", json={
        "nombre": "Lote Suelo Falso", "suelo_id": str(uuid.uuid4()),
    }, headers=_auth())
    assert r.status_code == 404
    print("✓ POST /lotes con suelo_id inexistente → 404")


# ── Listar ────────────────────────────────────────────────────────────

def test_listar_lotes():
    lote = _crear_lote("Lote Para Listar")
    r = _tc.get("/api/v1/lotes", headers=_auth())
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert "total" in body
    assert body["total"] >= 1
    ids = [it["id"] for it in body["items"]]
    assert lote["id"] in ids
    print(f"✓ GET /lotes → 200, {body['total']} lote(s) en total")


def test_listar_lotes_sin_auth():
    r = _tc.get("/api/v1/lotes")
    assert r.status_code == 401
    print("✓ GET /lotes sin token → 401")


# ── Obtener ───────────────────────────────────────────────────────────

def test_obtener_lote_por_id():
    lote = _crear_lote("Lote Para GET")
    r = _tc.get(f"/api/v1/lotes/{lote['id']}", headers=_auth())
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == lote["id"]
    assert body["nombre"] == "Lote Para GET"
    print("✓ GET /lotes/{id} → 200")


def test_obtener_lote_inexistente():
    r = _tc.get(f"/api/v1/lotes/{uuid.uuid4()}", headers=_auth())
    assert r.status_code == 404
    print("✓ GET /lotes/{uuid_random} → 404")


# ── Actualizar ────────────────────────────────────────────────────────

def test_actualizar_lote_nombre():
    lote = _crear_lote("Lote Original")
    r = _tc.put(f"/api/v1/lotes/{lote['id']}", json={
        "nombre": "Lote Actualizado",
    }, headers=_auth())
    assert r.status_code == 200
    body = r.json()
    assert body["nombre"] == "Lote Actualizado"
    print("✓ PUT /lotes/{id} → 200 con nombre actualizado")


def test_actualizar_lote_geometry():
    """PUT /lotes/{id} sigue aceptando geometry manual (ModalLimites) — solo
    se sacó de la creación, no de la actualización."""
    lote = _crear_lote("Lote Sin Límites")
    assert lote["geometry"] is None
    r = _tc.put(f"/api/v1/lotes/{lote['id']}", json={"geometry": _GEOM}, headers=_auth())
    assert r.status_code == 200
    body = r.json()
    assert body["geometry"] is not None
    assert body["area_ha"] is not None and body["area_ha"] > 0
    print(f"✓ PUT /lotes/{{id}} con geometry → 200, área={body['area_ha']:.2f} ha")


def test_actualizar_lote_inexistente():
    r = _tc.put(f"/api/v1/lotes/{uuid.uuid4()}", json={"nombre": "X"}, headers=_auth())
    assert r.status_code == 404
    print("✓ PUT /lotes/{uuid_random} → 404")


# ── Eliminar (soft delete) ────────────────────────────────────────────

def test_soft_delete_devuelve_204():
    lote = _crear_lote("Lote Para Borrar")
    r = _tc.delete(f"/api/v1/lotes/{lote['id']}", headers=_auth())
    assert r.status_code == 204
    print("✓ DELETE /lotes/{id} → 204")


def test_lote_borrado_no_accesible_por_get():
    lote = _crear_lote("Lote Borrado GET")
    _tc.delete(f"/api/v1/lotes/{lote['id']}", headers=_auth())

    r = _tc.get(f"/api/v1/lotes/{lote['id']}", headers=_auth())
    assert r.status_code == 404
    print("✓ GET lote eliminado → 404 (soft delete verificado)")


def test_lote_borrado_no_aparece_en_lista():
    lote = _crear_lote("Lote Efímero")
    lote_id = lote["id"]
    _tc.delete(f"/api/v1/lotes/{lote_id}", headers=_auth())

    items = _tc.get("/api/v1/lotes", headers=_auth()).json()["items"]
    ids = [it["id"] for it in items]
    assert lote_id not in ids
    print("✓ Lote eliminado no aparece en GET /lotes (soft delete)")


def test_delete_lote_inexistente():
    r = _tc.delete(f"/api/v1/lotes/{uuid.uuid4()}", headers=_auth())
    assert r.status_code == 404
    print("✓ DELETE /lotes/{uuid_random} → 404")


# ── Cultivos ────────────────────────────────────────────────────────

def test_listar_cultivos_lote_vacio():
    lote = _crear_lote("Lote Sin Cultivos")
    r = _tc.get(f"/api/v1/lotes/{lote['id']}/cultivos", headers=_auth())
    assert r.status_code == 200
    assert r.json() == []
    print("✓ GET /lotes/{id}/cultivos → 200, [] sin ciclos registrados")


def test_listar_cultivos_lote_inexistente():
    r = _tc.get(f"/api/v1/lotes/{uuid.uuid4()}/cultivos", headers=_auth())
    assert r.status_code == 404
    print("✓ GET /lotes/{uuid_random}/cultivos → 404")


# ── Aislamiento por usuario ───────────────────────────────────────────

def test_lote_de_otro_usuario_no_accesible():
    email2 = f"otro_{uuid.uuid4().hex[:8]}@agronexo-test.com"
    _tc.post("/api/v1/auth/register", json={
        "email": email2, "nombre": "Otro Usuario", "password": "pass_otro_456",
    })
    token2 = _tc.post("/api/v1/auth/login", json={
        "email": email2, "password": "pass_otro_456",
    }).json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    lote_ajeno = _tc.post("/api/v1/lotes", json={
        "nombre": "Lote de Otro", "suelo_id": _suelo_id,
    }, headers=headers2).json()

    r = _tc.get(f"/api/v1/lotes/{lote_ajeno['id']}", headers=_auth())
    assert r.status_code == 404
    print("✓ Lote de otro usuario no es accesible → 404")


def test_lote_de_otro_usuario_no_aparece_en_lista():
    email3 = f"tercero_{uuid.uuid4().hex[:8]}@agronexo-test.com"
    _tc.post("/api/v1/auth/register", json={
        "email": email3, "nombre": "Tercero", "password": "pass_ter_789",
    })
    token3 = _tc.post("/api/v1/auth/login", json={
        "email": email3, "password": "pass_ter_789",
    }).json()["access_token"]

    lote_ajeno = _tc.post("/api/v1/lotes", json={
        "nombre": "Lote Privado", "suelo_id": _suelo_id,
    }, headers={"Authorization": f"Bearer {token3}"}).json()

    items = _tc.get("/api/v1/lotes", headers=_auth()).json()["items"]
    ids = [it["id"] for it in items]
    assert lote_ajeno["id"] not in ids
    print("✓ Lote de otro usuario no aparece en GET /lotes del usuario actual")


if __name__ == "__main__":
    setup_module(None)
    try:
        print("\n── CRUD Lotes + Soft Delete ─────────────────────────")
        test_crear_lote()
        test_crear_lote_con_ubicacion()
        test_crear_lote_ubicacion_incompleta()
        test_crear_lote_provincia_y_localidad_sin_departamento()
        test_crear_lote_sin_auth()
        test_crear_lote_suelo_id_faltante()
        test_crear_lote_suelo_inexistente()
        test_listar_lotes()
        test_listar_lotes_sin_auth()
        test_obtener_lote_por_id()
        test_obtener_lote_inexistente()
        test_actualizar_lote_nombre()
        test_actualizar_lote_geometry()
        test_actualizar_lote_inexistente()
        test_soft_delete_devuelve_204()
        test_lote_borrado_no_accesible_por_get()
        test_lote_borrado_no_aparece_en_lista()
        test_delete_lote_inexistente()
        test_listar_cultivos_lote_vacio()
        test_listar_cultivos_lote_inexistente()
        test_lote_de_otro_usuario_no_accesible()
        test_lote_de_otro_usuario_no_aparece_en_lista()
        print("\nTodos los tests de lotes pasaron.\n")
    finally:
        teardown_module(None)
