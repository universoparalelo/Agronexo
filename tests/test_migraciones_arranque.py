"""
Tests de app/core/migraciones.py::aplicar_migraciones(), que lleva la base al
último esquema al arrancar la app de escritorio.

Necesitan un Postgres con PostGIS donde el usuario pueda crear bases y
extensiones (el de CI y el de desarrollo lo permiten). Cada test crea una base
nueva y vacía y la borra al terminar, sin tocar la base de trabajo.

Correr en el contenedor api:
    docker compose exec api python3 -m pytest tests/test_migraciones_arranque.py -v

Correr en CI o local (con DB levantada):
    PYTHONPATH=$(pwd) python3 -m pytest tests/test_migraciones_arranque.py -v
"""
import sys
import uuid

import psycopg2
import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.core import migraciones
from app.core.config import settings
from app.core.migraciones import aplicar_migraciones


def _conectar(base: str):
    return psycopg2.connect(
        host=settings.postgres_host, port=settings.postgres_port,
        user=settings.postgres_user, password=settings.postgres_password, dbname=base,
    )


@pytest.fixture
def base_vacia(monkeypatch):
    nombre = f"agronexo_mig_{uuid.uuid4().hex[:8]}"
    admin = _conectar("postgres")
    admin.autocommit = True
    admin.cursor().execute(f'CREATE DATABASE "{nombre}"')
    monkeypatch.setattr(settings, "postgres_db", nombre)
    yield nombre
    admin.cursor().execute(f'DROP DATABASE IF EXISTS "{nombre}" WITH (FORCE)')
    admin.close()


def _consultar(base: str, sql: str):
    con = _conectar(base)
    try:
        cur = con.cursor()
        cur.execute(sql)
        return cur.fetchall()
    finally:
        con.close()


def _ultima_revision() -> str:
    config = Config()
    config.set_main_option("script_location", str(migraciones._raiz() / "migrations"))
    return ScriptDirectory.from_config(config).get_current_head()


def test_una_base_vacia_queda_con_todo_el_esquema(base_vacia):
    aplicar_migraciones()

    assert _consultar(base_vacia, "select version_num from alembic_version") == [(_ultima_revision(),)]
    extensiones = {fila[0] for fila in _consultar(base_vacia, "select extname from pg_extension")}
    assert {"postgis", "uuid-ossp"} <= extensiones
    tablas = {fila[0] for fila in _consultar(
        base_vacia, "select tablename from pg_tables where schemaname = 'public'")}
    assert {"usuarios", "lotes", "vuelos", "cultivos", "diagnosticos", "productos_fitosanitarios"} <= tablas
    assert _consultar(base_vacia, "select count(*) from usuarios") == [(1,)]
    print("✓ aplicar_migraciones() sobre una base vacía deja el esquema completo y el usuario inicial")


def test_aplicarlas_otra_vez_no_cambia_nada(base_vacia):
    aplicar_migraciones()
    antes = _consultar(base_vacia, "select count(*) from pg_tables where schemaname = 'public'")

    aplicar_migraciones()

    assert _consultar(base_vacia, "select version_num from alembic_version") == [(_ultima_revision(),)]
    assert _consultar(base_vacia, "select count(*) from pg_tables where schemaname = 'public'") == antes
    assert _consultar(base_vacia, "select count(*) from usuarios") == [(1,)]
    print("✓ aplicar_migraciones() sobre una base al día no hace nada")


def test_empaquetado_las_migraciones_se_buscan_dentro_del_paquete(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    assert migraciones._raiz() == tmp_path


def test_sin_empaquetar_las_migraciones_se_buscan_en_el_repo():
    assert (migraciones._raiz() / "migrations" / "env.py").is_file()
