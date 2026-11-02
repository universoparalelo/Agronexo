"""
Tests de la pantalla de bienvenida de la app de escritorio (POST /auth/me/bienvenida).

Trabajan en una base de datos propia que se crea y se borra en el módulo, porque
la bienvenida modifica el usuario que siembra la migración 0006.

Necesitan Postgres con PostGIS (crean la base y corren alembic):
    docker compose exec api python3 -m pytest tests/test_bienvenida.py -v

Correr en CI o local (con DB levantada):
    PYTHONPATH=$(pwd) python3 -m pytest tests/test_bienvenida.py -v
"""
import os
import subprocess
import sys
import uuid
from pathlib import Path
from unittest import mock

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from starlette.testclient import TestClient

from app.auth.service import EMAIL_PROVISORIO
from app.core.config import settings
from app.core.database import get_db
from app.main import app

_BD = f"agronexo_bv_{uuid.uuid4().hex[:8]}"
_PASS = "bienvenida_pass_123"
_RAIZ = Path(__file__).resolve().parent.parent

_tc = TestClient(app)
_estado: dict = {}


def _url_bd(nombre: str, sincrona: bool = False) -> str:
    base = settings.database_url_sync if sincrona else settings.database_url
    return base.rsplit("/", 1)[0] + f"/{nombre}"


def setup_module(module):
    admin = create_engine(settings.database_url_sync, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{_BD}"'))
    admin.dispose()
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=_RAIZ,
        env={**os.environ, "POSTGRES_DB": _BD, "ADMIN_EMAIL": EMAIL_PROVISORIO, "ADMIN_PASSWORD": _PASS},
        check=True, capture_output=True,
    )

    _estado["motor"] = create_async_engine(_url_bd(_BD), poolclass=NullPool)
    _estado["sync"] = create_engine(_url_bd(_BD, sincrona=True))

    async def _get_db():
        async with AsyncSession(_estado["motor"], expire_on_commit=False) as sesion:
            try:
                yield sesion
                await sesion.commit()
            except Exception:
                await sesion.rollback()
                raise

    app.dependency_overrides[get_db] = _get_db
    _tc.__enter__()
    with _estado["sync"].connect() as conn:
        _estado["admin_id"] = conn.execute(
            text("SELECT id FROM usuarios WHERE email = :e"), {"e": EMAIL_PROVISORIO}
        ).scalar_one()


def teardown_module(module):
    _tc.__exit__(None, None, None)
    app.dependency_overrides.pop(get_db, None)
    _estado["sync"].dispose()
    admin = create_engine(settings.database_url_sync, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{_BD}" WITH (FORCE)'))
    admin.dispose()


@pytest.fixture(autouse=True)
def _usuario_provisorio():
    with _estado["sync"].begin() as conn:
        conn.execute(text("DELETE FROM usuarios WHERE id <> :id"), {"id": _estado["admin_id"]})
        conn.execute(
            text("UPDATE usuarios SET email = :e, nombre = 'Administrador' WHERE id = :id"),
            {"e": EMAIL_PROVISORIO, "id": _estado["admin_id"]},
        )
    yield


@pytest.fixture
def modo_escritorio():
    with mock.patch.object(settings, "modo_escritorio", True):
        yield


def _login(email: str, password: str = _PASS):
    return _tc.post("/api/v1/auth/login", json={"email": email, "password": password})


def _auth(email: str = EMAIL_PROVISORIO) -> dict:
    return {"Authorization": f"Bearer {_login(email).json()['access_token']}"}


def test_fuera_del_modo_escritorio_no_hay_bienvenida_pendiente():
    cabeceras = _auth()
    assert _tc.get("/api/v1/auth/me", headers=cabeceras).json()["bienvenida_pendiente"] is False
    r = _tc.post("/api/v1/auth/me/bienvenida", headers=cabeceras, json={"nombre": "Ana", "email": "ana@campo.com"})
    assert r.status_code == 409


def test_primer_arranque_tiene_bienvenida_pendiente(modo_escritorio):
    assert _tc.get("/api/v1/auth/me", headers=_auth()).json()["bienvenida_pendiente"] is True


def test_completar_bienvenida_guarda_nombre_y_correo(modo_escritorio):
    cabeceras = _auth()
    r = _tc.post(
        "/api/v1/auth/me/bienvenida", headers=cabeceras,
        json={"nombre": "  Ana Pérez  ", "email": "Ana@Campo.com"},
    )
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["email"] == "ana@campo.com"
    assert cuerpo["nombre"] == "Ana Pérez"
    assert cuerpo["bienvenida_pendiente"] is False


def test_el_token_anterior_sigue_valiendo_y_el_login_pasa_al_correo_nuevo():
    cabeceras = _auth()
    with mock.patch.object(settings, "modo_escritorio", True):
        _tc.post("/api/v1/auth/me/bienvenida", headers=cabeceras, json={"nombre": "Ana", "email": "ana@campo.com"})
    assert _tc.get("/api/v1/auth/me", headers=cabeceras).json()["email"] == "ana@campo.com"
    assert _login("ana@campo.com").status_code == 200
    assert _login(EMAIL_PROVISORIO).status_code == 401  # fuera del modo escritorio no hay alias


def test_el_lanzador_sigue_entrando_con_el_correo_provisorio(modo_escritorio):
    cabeceras = _auth()
    _tc.post("/api/v1/auth/me/bienvenida", headers=cabeceras, json={"nombre": "Ana", "email": "ana@campo.com"})
    r = _login(EMAIL_PROVISORIO)
    assert r.status_code == 200
    assert _tc.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"}).json()["email"] == "ana@campo.com"
    assert _login(EMAIL_PROVISORIO, "contraseña-incorrecta").status_code == 401


def test_no_se_puede_completar_dos_veces(modo_escritorio):
    cabeceras = _auth()
    datos = {"nombre": "Ana", "email": "ana@campo.com"}
    assert _tc.post("/api/v1/auth/me/bienvenida", headers=cabeceras, json=datos).status_code == 200
    r = _tc.post("/api/v1/auth/me/bienvenida", headers=cabeceras, json={"nombre": "Otra", "email": "otra@campo.com"})
    assert r.status_code == 409
    assert _tc.get("/api/v1/auth/me", headers=cabeceras).json()["email"] == "ana@campo.com"


def test_rechaza_un_correo_que_ya_usa_otra_cuenta(modo_escritorio):
    _tc.post("/api/v1/auth/register", json={"email": "ocupado@campo.com", "nombre": "Otro", "password": _PASS})
    cabeceras = _auth()
    r = _tc.post("/api/v1/auth/me/bienvenida", headers=cabeceras, json={"nombre": "Ana", "email": "ocupado@campo.com"})
    assert r.status_code == 409
    assert _tc.get("/api/v1/auth/me", headers=cabeceras).json()["email"] == EMAIL_PROVISORIO


def test_rechaza_dejar_el_correo_provisorio(modo_escritorio):
    r = _tc.post(
        "/api/v1/auth/me/bienvenida", headers=_auth(),
        json={"nombre": "Ana", "email": EMAIL_PROVISORIO},
    )
    assert r.status_code == 409


@pytest.mark.parametrize("cuerpo", [
    {"nombre": "Ana", "email": "no-es-un-correo"},
    {"nombre": "   ", "email": "ana@campo.com"},
    {"email": "ana@campo.com"},
])
def test_valida_los_datos(modo_escritorio, cuerpo):
    r = _tc.post("/api/v1/auth/me/bienvenida", headers=_auth(), json=cuerpo)
    assert r.status_code == 422


def test_exige_sesion(modo_escritorio):
    r = _tc.post("/api/v1/auth/me/bienvenida", json={"nombre": "Ana", "email": "ana@campo.com"})
    assert r.status_code in (401, 403)
