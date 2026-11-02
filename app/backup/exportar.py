import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.auth.models import Usuario
from app.backup import archivos
from app.backup.filas import (
    CAMPOS_PERFIL, COLUMNAS_CLAVE_ARCHIVO, FORMATO, TABLAS, a_linea, columnas_select,
    fila_a_dict, tabla,
)

APP_VERSION = "4.0.0"


async def revision_actual(db: AsyncSession) -> str | None:
    return (await db.execute(text("SELECT version_num FROM alembic_version"))).scalar_one_or_none()


async def referencia_producto(db: AsyncSession, producto_id) -> dict | None:
    """Los productos del catálogo se siembran con ids aleatorios en cada instalación,
    así que lo que apunta a uno viaja con su nombre, tipo y causa para reubicarlo."""
    if producto_id is None:
        return None
    productos = tabla("productos_fitosanitarios")
    fila = (await db.execute(
        select(productos.c.nombre, productos.c.tipo, productos.c.causa_indice)
        .where(productos.c.id == producto_id)
    )).first()
    return fila_a_dict(fila._mapping) if fila else None


async def _filas(db: AsyncSession, nombre: str) -> list[dict]:
    t = tabla(nombre)
    consulta = select(*columnas_select(t))
    if nombre == "precios_productos":
        consulta = consulta.where(t.c.tipo == "usuario")
    filas = [fila_a_dict(f._mapping) for f in (await db.execute(consulta)).all()]
    if nombre == "precios_productos":
        for fila in filas:
            fila["producto_ref"] = await referencia_producto(db, fila["producto_id"])
    return filas


async def _perfil(db: AsyncSession, usuario: Usuario) -> dict:
    fila = (await db.execute(
        select(*columnas_select(tabla("usuarios"), set(CAMPOS_PERFIL) | {"id", "producto_habitual_id"}))
        .where(tabla("usuarios").c.id == usuario.id)
    )).first()
    perfil = fila_a_dict(fila._mapping)
    perfil["producto_habitual_ref"] = await referencia_producto(db, perfil.pop("producto_habitual_id"))
    return perfil


def claves_de_archivos(filas_por_tabla: dict[str, list[dict]], perfil: dict) -> list[str]:
    claves = set()
    for filas in filas_por_tabla.values():
        for fila in filas:
            for columna in COLUMNAS_CLAVE_ARCHIVO:
                if fila.get(columna):
                    claves.add(fila[columna])
    for campo in ("avatar_key", "logo_empresa_key"):
        if perfil.get(campo):
            claves.add(perfil[campo])
    return sorted(claves)


async def exportar(db: AsyncSession, usuario: Usuario, destino: Path) -> dict:
    """Escribe en `destino` un .zip con los datos del usuario y sus archivos."""
    datos = {nombre: await _filas(db, nombre) for nombre in TABLAS}
    perfil = await _perfil(db, usuario)
    claves = claves_de_archivos(datos, perfil)
    revision = await revision_actual(db)

    incluidos, faltantes = [], []
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
        for nombre, filas in datos.items():
            zf.writestr(f"datos/{nombre}.jsonl", "\n".join(a_linea(f) for f in filas))
        zf.writestr("datos/perfil.json", json.dumps(perfil, ensure_ascii=False))
        for clave in claves:
            (incluidos if await run_in_threadpool(archivos.agregar_al_zip, zf, clave) else faltantes).append(clave)
        manifiesto = {
            "formato": FORMATO,
            "app_version": APP_VERSION,
            "revision_base": revision,
            "creado_en": datetime.now(timezone.utc).isoformat(),
            "conteos": {nombre: len(filas) for nombre, filas in datos.items()},
            "archivos": len(incluidos),
            "archivos_faltantes": faltantes,
        }
        zf.writestr("manifiesto.json", json.dumps(manifiesto, ensure_ascii=False))
    return manifiesto
