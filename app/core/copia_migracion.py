"""
Copia de la base antes de actualizar el esquema (app de escritorio, D11).

Cuando se instala una versión nueva con cambios en la base, las migraciones
transforman los datos al abrir la app. Antes de eso se guarda una copia con
pg_dump; si la migración falla, se restaura sola y se deja un aviso para que el
lanzador le explique a la persona qué pasó.

Se guarda una sola copia: la de justo antes de la última actualización. Solo se
hace cuando hay migraciones pendientes sobre una base que ya tenía datos; abrir
la misma versión dos veces no pisa la copia buena.

Se activa con dos variables que pone el lanzador de Electron: AGRONEXO_PG_BIN
(carpeta con pg_dump y pg_restore) y AGRONEXO_COPIAS_DIR. Sin ellas (Docker,
desarrollo) las migraciones corren como siempre.
"""
import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.core import migraciones
from app.core.config import settings

log = logging.getLogger(__name__)

ARCHIVO_COPIA = "base-anterior.dump"
ARCHIVO_DATOS = "base-anterior.json"
ARCHIVO_AVISO = "actualizacion-fallida.json"
ESPERA_COPIA_S = 1800


class CopiaNoDisponible(Exception):
    """No se pudo hacer o restaurar la copia."""


def _conectar(base: str):
    return psycopg2.connect(
        host=settings.postgres_host, port=settings.postgres_port,
        user=settings.postgres_user, password=settings.postgres_password, dbname=base,
    )


def revision_de_la_base() -> str | None:
    """La revisión en la que está la base, o None si todavía no tiene el esquema."""
    con = _conectar(settings.postgres_db)
    try:
        cur = con.cursor()
        cur.execute("select to_regclass('public.alembic_version')")
        if cur.fetchone()[0] is None:
            return None
        cur.execute("select version_num from alembic_version")
        fila = cur.fetchone()
        return fila[0] if fila else None
    finally:
        con.close()


def ultima_revision() -> str:
    config = Config()
    config.set_main_option("script_location", str(migraciones._raiz() / "migrations"))
    return ScriptDirectory.from_config(config).get_current_head()


def _herramienta(pg_bin: Path, nombre: str) -> str:
    exe = pg_bin / f"{nombre}.exe"
    return str(exe if exe.exists() else pg_bin / nombre)


def _entorno_pg() -> dict:
    return {**os.environ, "PGPASSWORD": settings.postgres_password}


def _argumentos_conexion() -> list[str]:
    return ["-h", settings.postgres_host, "-p", str(settings.postgres_port), "-U", settings.postgres_user]


def hacer_copia(pg_bin: Path, carpeta: Path, revision: str) -> Path:
    """Guarda la copia de la base. Reemplaza a la anterior solo si esta salió bien."""
    carpeta.mkdir(parents=True, exist_ok=True)
    temporal = carpeta / f"{ARCHIVO_COPIA}.tmp"
    destino = carpeta / ARCHIVO_COPIA
    try:
        subprocess.run(
            [_herramienta(pg_bin, "pg_dump"), *_argumentos_conexion(), "-Fc", "-f", str(temporal), settings.postgres_db],
            env=_entorno_pg(), check=True, capture_output=True, timeout=ESPERA_COPIA_S,
        )
    except (subprocess.SubprocessError, OSError) as error:
        temporal.unlink(missing_ok=True)
        raise CopiaNoDisponible(f"No se pudo hacer la copia de la base: {_detalle(error)}") from error
    os.replace(temporal, destino)
    (carpeta / ARCHIVO_DATOS).write_text(json.dumps({
        "revision": revision,
        "creada_en": datetime.now(timezone.utc).isoformat(),
    }), encoding="utf-8")
    return destino


def restaurar_copia(pg_bin: Path, copia: Path) -> None:
    """Deja la base como estaba en la copia: se recrea vacía y se vuelca la copia."""
    nombre = settings.postgres_db
    admin = _conectar("postgres")
    admin.autocommit = True
    try:
        cur = admin.cursor()
        cur.execute(f'DROP DATABASE IF EXISTS "{nombre}" WITH (FORCE)')
        cur.execute(f'CREATE DATABASE "{nombre}"')
    finally:
        admin.close()
    try:
        subprocess.run(
            [_herramienta(pg_bin, "pg_restore"), *_argumentos_conexion(), "--no-owner", "-d", nombre, str(copia)],
            env=_entorno_pg(), check=True, capture_output=True, timeout=ESPERA_COPIA_S,
        )
    except (subprocess.SubprocessError, OSError) as error:
        raise CopiaNoDisponible(f"No se pudo restaurar la copia: {_detalle(error)}") from error


def _detalle(error: Exception) -> str:
    salida = getattr(error, "stderr", b"") or b""
    texto = salida.decode("utf-8", errors="replace").strip() if isinstance(salida, bytes) else str(salida)
    return texto or str(error)


def _escribir_aviso(carpeta: Path, **datos) -> None:
    carpeta.mkdir(parents=True, exist_ok=True)
    datos["fecha"] = datetime.now(timezone.utc).isoformat()
    (carpeta / ARCHIVO_AVISO).write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")


def actualizar_base() -> None:
    """Lleva la base al último esquema; si hay que actualizar datos existentes, con copia previa."""
    pg_bin, carpeta = os.environ.get("AGRONEXO_PG_BIN"), os.environ.get("AGRONEXO_COPIAS_DIR")
    if not (pg_bin and carpeta):
        migraciones.aplicar_migraciones()
        return

    pg_bin, carpeta = Path(pg_bin), Path(carpeta)
    actual = revision_de_la_base()
    if actual is None or actual == ultima_revision():
        migraciones.aplicar_migraciones()
        return

    # Sin copia no se toca la base: es preferible no abrir a arriesgar los datos.
    try:
        copia = hacer_copia(pg_bin, carpeta, actual)
    except CopiaNoDisponible as error:
        _escribir_aviso(carpeta, motivo="sin_copia", detalle=str(error), restaurada=False, revision_anterior=actual)
        raise
    log.info("Copia de la base guardada antes de actualizar: %s", copia)

    try:
        migraciones.aplicar_migraciones()
    except Exception as error:
        log.exception("La actualización de la base falló; se restaura la copia")
        restaurada = True
        try:
            restaurar_copia(pg_bin, copia)
        except CopiaNoDisponible as fallo:
            restaurada = False
            log.error("%s", fallo)
        _escribir_aviso(
            carpeta, motivo="migracion", detalle=str(error), restaurada=restaurada, revision_anterior=actual,
        )
        raise
