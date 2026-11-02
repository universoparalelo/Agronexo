"""
Tests de app/core/copia_migracion.py: la copia de la base que se hace antes de
actualizar el esquema y su restauración si la actualización falla.

Necesitan un Postgres con PostGIS donde se puedan crear bases (como los de
test_migraciones_arranque.py) y pg_dump/pg_restore de la misma versión. Se
buscan en AGRONEXO_PG_BIN, en el PATH y en /usr/lib/postgresql; si no están,
los tests se saltean.

Correr en CI o local (con DB levantada):
    PYTHONPATH=$(pwd) python3 -m pytest tests/test_copia_migracion.py -v
"""
import glob
import json
import os
import shutil
import uuid
from pathlib import Path

import psycopg2
import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.core import copia_migracion, migraciones
from app.core.config import settings
from app.core.copia_migracion import (
    ARCHIVO_AVISO, ARCHIVO_COPIA, ARCHIVO_DATOS, CopiaNoDisponible, actualizar_base,
)


def _carpeta_de_pg() -> Path | None:
    candidatos = [os.environ.get("AGRONEXO_PG_BIN")]
    en_path = shutil.which("pg_dump")
    if en_path:
        candidatos.append(str(Path(en_path).parent))
    candidatos += sorted(glob.glob("/usr/lib/postgresql/*/bin"), reverse=True)
    for carpeta in filter(None, candidatos):
        if shutil.which("pg_dump", path=carpeta) and shutil.which("pg_restore", path=carpeta):
            return Path(carpeta)
    return None


PG_BIN = _carpeta_de_pg()
pytestmark = pytest.mark.skipif(PG_BIN is None, reason="no se encontró pg_dump/pg_restore")


def _conectar(base: str):
    return psycopg2.connect(
        host=settings.postgres_host, port=settings.postgres_port,
        user=settings.postgres_user, password=settings.postgres_password, dbname=base,
    )


def _sql(base: str, sql: str):
    con = _conectar(base)
    con.autocommit = True
    try:
        cur = con.cursor()
        cur.execute(sql)
        return cur.fetchall() if cur.description else None
    finally:
        con.close()


def _config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(migraciones._raiz() / "migrations"))
    return config


def _revision_previa() -> str:
    cabeza = ScriptDirectory.from_config(_config()).get_current_head()
    return ScriptDirectory.from_config(_config()).get_revision(cabeza).down_revision


@pytest.fixture
def base(monkeypatch, tmp_path):
    nombre = f"agronexo_cop_{uuid.uuid4().hex[:8]}"
    _sql("postgres", f'CREATE DATABASE "{nombre}"')
    monkeypatch.setattr(settings, "postgres_db", nombre)
    monkeypatch.setenv("AGRONEXO_PG_BIN", str(PG_BIN))
    monkeypatch.setenv("AGRONEXO_COPIAS_DIR", str(tmp_path / "copias"))
    yield nombre
    _sql("postgres", f'DROP DATABASE IF EXISTS "{nombre}" WITH (FORCE)')


@pytest.fixture
def base_desactualizada(base):
    """Una base con datos, un paso antes de la última revisión."""
    command.upgrade(_config(), _revision_previa())
    _sql(base, "CREATE TABLE marcador (valor text)")
    _sql(base, "INSERT INTO marcador VALUES ('dato importante')")
    return base


def _carpeta() -> Path:
    return Path(os.environ["AGRONEXO_COPIAS_DIR"])


def _revision(base: str) -> str:
    return _sql(base, "select version_num from alembic_version")[0][0]


def test_una_base_nueva_se_migra_sin_hacer_copia(base):
    actualizar_base()

    assert _revision(base) == copia_migracion.ultima_revision()
    assert not (_carpeta() / ARCHIVO_COPIA).exists()


def test_actualizar_una_base_con_datos_guarda_la_copia_y_migra(base_desactualizada):
    actualizar_base()

    assert _revision(base_desactualizada) == copia_migracion.ultima_revision()
    assert (_carpeta() / ARCHIVO_COPIA).stat().st_size > 0
    datos = json.loads((_carpeta() / ARCHIVO_DATOS).read_text(encoding="utf-8"))
    assert datos["revision"] == _revision_previa()
    assert not (_carpeta() / ARCHIVO_AVISO).exists()


def test_abrir_la_misma_version_no_pisa_la_copia(base_desactualizada):
    actualizar_base()
    copia = _carpeta() / ARCHIVO_COPIA
    antes = (copia.stat().st_mtime_ns, copia.read_bytes())

    actualizar_base()

    assert (copia.stat().st_mtime_ns, copia.read_bytes()) == antes


def test_si_la_migracion_falla_se_restaura_la_base_como_estaba(base_desactualizada, monkeypatch):
    def migracion_rota():
        _sql(base_desactualizada, "DROP TABLE marcador")
        _sql(base_desactualizada, "UPDATE alembic_version SET version_num = 'otra_cosa'")
        raise RuntimeError("falló a la mitad")

    monkeypatch.setattr(migraciones, "aplicar_migraciones", migracion_rota)

    with pytest.raises(RuntimeError, match="falló a la mitad"):
        actualizar_base()

    assert _sql(base_desactualizada, "SELECT valor FROM marcador") == [("dato importante",)]
    assert _revision(base_desactualizada) == _revision_previa()
    aviso = json.loads((_carpeta() / ARCHIVO_AVISO).read_text(encoding="utf-8"))
    assert aviso["motivo"] == "migracion" and aviso["restaurada"] is True
    assert aviso["revision_anterior"] == _revision_previa()
    assert "falló a la mitad" in aviso["detalle"]


def test_si_no_se_puede_hacer_la_copia_no_se_toca_la_base(base_desactualizada, monkeypatch, tmp_path):
    monkeypatch.setenv("AGRONEXO_PG_BIN", str(tmp_path / "no_existe"))
    llamadas = []
    monkeypatch.setattr(migraciones, "aplicar_migraciones", lambda: llamadas.append(1))

    with pytest.raises(CopiaNoDisponible):
        actualizar_base()

    assert llamadas == []
    assert _revision(base_desactualizada) == _revision_previa()
    assert json.loads((_carpeta() / ARCHIVO_AVISO).read_text(encoding="utf-8"))["motivo"] == "sin_copia"


def test_una_copia_que_falla_no_pisa_la_anterior(base_desactualizada, monkeypatch, tmp_path):
    actualizar_base()
    copia = _carpeta() / ARCHIVO_COPIA
    anterior = copia.read_bytes()

    monkeypatch.setenv("AGRONEXO_PG_BIN", str(tmp_path / "no_existe"))
    with pytest.raises(CopiaNoDisponible):
        copia_migracion.hacer_copia(tmp_path / "no_existe", _carpeta(), "x")

    assert copia.read_bytes() == anterior
    assert not (_carpeta() / f"{ARCHIVO_COPIA}.tmp").exists()


def test_sin_las_variables_del_lanzador_las_migraciones_corren_como_siempre(base, monkeypatch):
    copias = _carpeta()
    monkeypatch.delenv("AGRONEXO_PG_BIN")
    monkeypatch.delenv("AGRONEXO_COPIAS_DIR")
    llamadas = []
    monkeypatch.setattr(migraciones, "aplicar_migraciones", lambda: llamadas.append(1))

    actualizar_base()

    assert llamadas == [1]
    assert not (copias / ARCHIVO_COPIA).exists()
