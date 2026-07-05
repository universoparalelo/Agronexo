"""
Tests de endpoints de autenticación JWT.

Correr en el contenedor api:
    docker compose exec api python3 -m pytest tests/test_auth.py -v

Correr en CI o local (con DB levantada):
    PYTHONPATH=$(pwd) python3 -m pytest tests/test_auth.py -v
"""
import uuid

from starlette.testclient import TestClient

from app.main import app

_EMAIL = f"auth_{uuid.uuid4().hex[:8]}@agronexo-test.com"
_PASS = "test_secure_123"
_NOMBRE = "Usuario Test Auth"

# El TestClient se abre en setup_module y se cierra en teardown_module para
# mantener el mismo event loop de anyio en todas las llamadas del módulo.
# asyncpg asocia el connection pool al primer loop; cambiar de loop entre
# requests causa "Future attached to a different loop".
_tc = TestClient(app)


def setup_module(module):
    from app.core.database import engine as _engine
    _engine.sync_engine.dispose(close=False)
    _tc.__enter__()
    r = _tc.post("/api/v1/auth/register", json={
        "email": _EMAIL, "nombre": _NOMBRE, "password": _PASS,
    })
    assert r.status_code == 201, f"setup_module falló: {r.status_code} {r.text}"
    print(f"\nUsuario de prueba creado: {_EMAIL}")


def teardown_module(module):
    _tc.__exit__(None, None, None)


# ── Register ──────────────────────────────────────────────────────────

def test_register_nuevo_usuario():
    email = f"nuevo_{uuid.uuid4().hex[:8]}@agronexo-test.com"
    r = _tc.post("/api/v1/auth/register", json={
        "email": email,
        "nombre": "Nuevo Usuario",
        "password": "seguro_pass_abc",
    })
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == email
    assert "id" in body
    assert "password" not in body
    assert body["is_active"] is True
    print(f"✓ register nuevo → 201, id={body['id'][:8]}...")


def test_register_email_duplicado():
    r = _tc.post("/api/v1/auth/register", json={
        "email": _EMAIL,
        "nombre": "Duplicado",
        "password": _PASS,
    })
    assert r.status_code == 409
    print("✓ register email duplicado → 409")


def test_register_password_corta():
    r = _tc.post("/api/v1/auth/register", json={
        "email": f"short_{uuid.uuid4().hex[:4]}@test.com",
        "nombre": "Test",
        "password": "abc",
    })
    assert r.status_code == 422
    print("✓ register password < 8 chars → 422")


def test_register_email_invalido():
    r = _tc.post("/api/v1/auth/register", json={
        "email": "no-es-un-email",
        "nombre": "Test",
        "password": "password123",
    })
    assert r.status_code == 422
    print("✓ register email inválido → 422")


# ── Login ─────────────────────────────────────────────────────────────

def test_login_credenciales_validas():
    r = _tc.post("/api/v1/auth/login", json={"email": _EMAIL, "password": _PASS})
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"
    print("✓ login → 200 con access_token y refresh_token")


def test_login_password_incorrecta():
    r = _tc.post("/api/v1/auth/login", json={
        "email": _EMAIL, "password": "password_incorrecta",
    })
    assert r.status_code == 401
    print("✓ login password incorrecta → 401")


def test_login_email_inexistente():
    r = _tc.post("/api/v1/auth/login", json={
        "email": "noexiste_jamas@agronexo.com", "password": "cualquiera",
    })
    assert r.status_code == 401
    print("✓ login email inexistente → 401")


# ── /me ───────────────────────────────────────────────────────────────

def test_me_con_token_valido():
    token = _tc.post("/api/v1/auth/login", json={
        "email": _EMAIL, "password": _PASS,
    }).json()["access_token"]

    r = _tc.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == _EMAIL
    assert body["nombre"] == _NOMBRE
    print("✓ GET /me con token → 200 con datos del usuario")


def test_me_sin_token():
    r = _tc.get("/api/v1/auth/me")
    assert r.status_code == 401
    print("✓ GET /me sin token → 401")


def test_me_token_invalido():
    r = _tc.get("/api/v1/auth/me", headers={"Authorization": "Bearer esto_no_es_un_jwt"})
    assert r.status_code == 401
    print("✓ GET /me con token malformado → 401")


def test_me_token_con_firma_incorrecta():
    import base64
    import json as _json
    header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(
        _json.dumps({"sub": "00000000-0000-0000-0000-000000000000"}).encode()
    ).rstrip(b"=").decode()
    token = f"{header}.{payload}.firma_invalida"
    r = _tc.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
    print("✓ GET /me con firma inválida → 401")


# ── Refresh ───────────────────────────────────────────────────────────

def test_refresh_token_valido():
    tokens = _tc.post("/api/v1/auth/login", json={
        "email": _EMAIL, "password": _PASS,
    }).json()

    r = _tc.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert "refresh_token" in body
    print("✓ POST /refresh con refresh_token válido → 200 con nuevos tokens")


def test_refresh_token_invalido():
    r = _tc.post("/api/v1/auth/refresh", json={"refresh_token": "token_completamente_invalido"})
    assert r.status_code == 401
    print("✓ POST /refresh con token inválido → 401")


def test_refresh_usando_access_token():
    tokens = _tc.post("/api/v1/auth/login", json={
        "email": _EMAIL, "password": _PASS,
    }).json()

    r = _tc.post("/api/v1/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert r.status_code == 401
    print("✓ POST /refresh con access_token (tipo incorrecto) → 401")


# ── Logout ────────────────────────────────────────────────────────────

def test_logout():
    r = _tc.post("/api/v1/auth/logout")
    assert r.status_code == 204
    print("✓ POST /logout → 204")


if __name__ == "__main__":
    setup_module(None)
    try:
        print("\n── Auth JWT ─────────────────────────────────────────")
        test_register_nuevo_usuario()
        test_register_email_duplicado()
        test_register_password_corta()
        test_register_email_invalido()
        test_login_credenciales_validas()
        test_login_password_incorrecta()
        test_login_email_inexistente()
        test_me_con_token_valido()
        test_me_sin_token()
        test_me_token_invalido()
        test_me_token_con_firma_incorrecta()
        test_refresh_token_valido()
        test_refresh_token_invalido()
        test_refresh_usando_access_token()
        test_logout()
        print("\nTodos los tests de auth pasaron.\n")
    finally:
        teardown_module(None)
