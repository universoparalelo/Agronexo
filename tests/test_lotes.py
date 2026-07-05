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


def setup_module(module):
    global _token
    from app.core.database import engine as _engine
    _engine.sync_engine.dispose(close=False)
    _tc.__enter__()
    _tc.post("/api/v1/auth/register", json={
        "email": _EMAIL, "nombre": "Test Lotes", "password": _PASS,
    })
    r = _tc.post("/api/v1/auth/login", json={"email": _EMAIL, "password": _PASS})
    assert r.status_code == 200, f"setup_module login falló: {r.status_code} {r.text}"
    _token = r.json()["access_token"]
    print(f"\nUsuario de prueba: {_EMAIL}")


def teardown_module(module):
    _tc.__exit__(None, None, None)


def _auth() -> dict:
    return {"Authorization": f"Bearer {_token}"}


def _crear_lote(nombre: str = "Lote Test", cultivo: str = "soja") -> dict:
    r = _tc.post("/api/v1/lotes", json={
        "nombre": nombre, "cultivo": cultivo, "geometry": _GEOM,
    }, headers=_auth())
    assert r.status_code == 201, f"No se pudo crear lote auxiliar: {r.text}"
    return r.json()


# ── Crear ─────────────────────────────────────────────────────────────

def test_crear_lote():
    r = _tc.post("/api/v1/lotes", json={
        "nombre": "Lote Norte Principal",
        "cultivo": "soja",
        "geometry": _GEOM,
    }, headers=_auth())
    assert r.status_code == 201
    body = r.json()
    assert body["nombre"] == "Lote Norte Principal"
    assert body["cultivo"] == "soja"
    assert body["geometry"] is not None
    assert body["area_ha"] is not None
    assert body["area_ha"] > 0
    print(f"✓ POST /lotes → 201, área={body['area_ha']:.2f} ha")


def test_crear_lote_sin_auth():
    r = _tc.post("/api/v1/lotes", json={
        "nombre": "Sin Auth", "cultivo": "maiz", "geometry": _GEOM,
    })
    assert r.status_code == 401
    print("✓ POST /lotes sin token → 401")


def test_crear_lote_geometry_invalida():
    geom_invalida = {"type": "Polygon", "coordinates": [[[0, 0], [1, 1]]]}
    r = _tc.post("/api/v1/lotes", json={
        "nombre": "Lote Geom Rota", "cultivo": "soja", "geometry": geom_invalida,
    }, headers=_auth())
    assert r.status_code == 422
    print("✓ POST /lotes con geometry inválida → 422")


def test_crear_lote_cultivo_invalido():
    r = _tc.post("/api/v1/lotes", json={
        "nombre": "Lote Cultivo Raro",
        "cultivo": "trigo",
        "geometry": _GEOM,
    }, headers=_auth())
    assert r.status_code == 422
    print("✓ POST /lotes con cultivo inválido → 422")


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

def test_actualizar_lote_nombre_y_cultivo():
    lote = _crear_lote("Lote Original", "soja")
    r = _tc.put(f"/api/v1/lotes/{lote['id']}", json={
        "nombre": "Lote Actualizado",
        "cultivo": "maiz",
    }, headers=_auth())
    assert r.status_code == 200
    body = r.json()
    assert body["nombre"] == "Lote Actualizado"
    assert body["cultivo"] == "maiz"
    print("✓ PUT /lotes/{id} → 200 con nombre y cultivo actualizados")


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
        "nombre": "Lote de Otro", "cultivo": "soja", "geometry": _GEOM,
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
        "nombre": "Lote Privado", "cultivo": "maiz", "geometry": _GEOM,
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
        test_crear_lote_sin_auth()
        test_crear_lote_geometry_invalida()
        test_crear_lote_cultivo_invalido()
        test_listar_lotes()
        test_listar_lotes_sin_auth()
        test_obtener_lote_por_id()
        test_obtener_lote_inexistente()
        test_actualizar_lote_nombre_y_cultivo()
        test_actualizar_lote_inexistente()
        test_soft_delete_devuelve_204()
        test_lote_borrado_no_accesible_por_get()
        test_lote_borrado_no_aparece_en_lista()
        test_delete_lote_inexistente()
        test_lote_de_otro_usuario_no_accesible()
        test_lote_de_otro_usuario_no_aparece_en_lista()
        print("\nTodos los tests de lotes pasaron.\n")
    finally:
        teardown_module(None)
