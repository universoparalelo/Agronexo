import enum
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.auth.models import Usuario
from app.backup import archivos
from app.backup.exportar import claves_de_archivos, revision_actual
from app.backup.filas import (
    CAMPOS_PERFIL, COLUMNAS_CLAVE_ARCHIVO, COLUMNAS_USUARIO, FORMATO, TABLAS, tabla,
    valores_para_insertar,
)

MODOS = ("reemplazar", "sumar")

# Qué columnas identifican "el mismo registro" en cada tabla y cuáles se comparan
# para decidir cuál versión gana al sumar. Los diagnósticos y las revisiones se
# reconocen por vuelo (y zona) y no por id: recalcular o revisar la misma zona en
# otra PC crea un registro con id distinto.
CLAVES = {
    "lotes": (("id",), ("updated_at", "deleted_at")),
    "cultivos": (("id",), ("deleted_at",)),
    "vuelos": (("id",), ("deleted_at",)),
    "analisis_indices": (("vuelo_id", "indice"), ()),
    "diagnosticos": (("vuelo_id",), ("calculado_en",)),
    "revisiones_diagnostico": (("vuelo_id", "zona_id"), ("updated_at",)),
    "precios_productos": (("id",), ()),
}


class BackupInvalido(Exception):
    """El archivo no es un backup de AgroNexo que esta versión pueda leer."""


class Leido:
    def __init__(self, manifiesto: dict, datos: dict[str, list[dict]], perfil: dict):
        self.manifiesto = manifiesto
        self.datos = datos
        self.perfil = perfil


def leer(ruta: Path) -> Leido:
    try:
        with zipfile.ZipFile(ruta) as zf:
            manifiesto = json.loads(zf.read("manifiesto.json"))
            datos = {}
            for nombre in TABLAS:
                texto = zf.read(f"datos/{nombre}.jsonl").decode("utf-8")
                datos[nombre] = [json.loads(linea) for linea in texto.split("\n") if linea.strip()]
            perfil = json.loads(zf.read("datos/perfil.json"))
    except (zipfile.BadZipFile, KeyError, ValueError) as error:
        raise BackupInvalido("El archivo no es un backup de AgroNexo.") from error
    if manifiesto.get("formato", 0) > FORMATO:
        raise BackupInvalido("El backup usa un formato más nuevo que esta versión de AgroNexo. Actualizá la aplicación.")
    return Leido(manifiesto, datos, perfil)


def _numero_revision(revision: str | None) -> int | None:
    m = re.match(r"\d+", revision or "")
    return int(m.group()) if m else None


def _fecha(valor) -> datetime | None:
    if valor is None:
        return None
    if isinstance(valor, str):
        valor = datetime.fromisoformat(valor)
    return valor if valor.tzinfo else valor.replace(tzinfo=timezone.utc)


def _texto(valor) -> str:
    return str(valor.name if isinstance(valor, enum.Enum) else valor).lower()


def _columnas_desconocidas(leido: Leido) -> dict[str, list[str]]:
    resultado = {}
    for nombre, filas in leido.datos.items():
        if not filas:
            continue
        conocidas = {c.name for c in tabla(nombre).columns} | {"producto_ref"}
        extra = sorted(set().union(*(set(f) for f in filas)) - conocidas)
        if extra:
            resultado[nombre] = extra
    return resultado


async def analizar(db: AsyncSession, leido: Leido) -> dict:
    m = leido.manifiesto
    advertencias = []
    local, origen = _numero_revision(await revision_actual(db)), _numero_revision(m.get("revision_base"))
    if local is not None and origen is not None and origen > local:
        advertencias.append({
            "codigo": "version_mas_nueva",
            "mensaje": "El backup es de una versión más nueva de AgroNexo. Lo que esta versión no conoce se va a ignorar y se pierde al importar.",
        })
    for nombre, columnas in _columnas_desconocidas(leido).items():
        advertencias.append({
            "codigo": "columnas_desconocidas",
            "mensaje": f"En «{nombre}» se ignoran los campos: {', '.join(columnas)}.",
        })
    if m.get("archivos_faltantes"):
        advertencias.append({
            "codigo": "archivos_faltantes",
            "mensaje": f"Al crear el backup faltaban {len(m['archivos_faltantes'])} archivos; esos no se pueden recuperar.",
        })
    actuales = {
        nombre: (await db.execute(select(func.count()).select_from(tabla(nombre)))).scalar_one()
        for nombre in ("lotes", "vuelos")
    }
    return {
        "creado_en": m.get("creado_en"),
        "app_version": m.get("app_version"),
        "conteos": m.get("conteos", {}),
        "archivos": m.get("archivos", 0),
        "advertencias": advertencias,
        "datos_actuales": actuales,
    }


class _Contexto:
    def __init__(self, usuario_local_id: str, usuarios_origen: set[str]):
        self.usuario_id = usuario_local_id
        self.usuarios_origen = usuarios_origen
        self.desconocidas: dict[str, set[str]] = {}
        self.sin_producto = 0

    def clave(self, clave: str | None) -> str | None:
        if not clave:
            return clave
        primero, _, resto = clave.partition("/")
        return f"{self.usuario_id}/{resto}" if resto and primero in self.usuarios_origen else clave

    def preparar(self, fila: dict) -> dict:
        fila = dict(fila)
        for columna in COLUMNAS_USUARIO & set(fila):
            if fila[columna] is not None:
                fila[columna] = self.usuario_id
        for columna in COLUMNAS_CLAVE_ARCHIVO & set(fila):
            fila[columna] = self.clave(fila[columna])
        return fila


def _usuarios_origen(leido: Leido) -> set[str]:
    ids = {leido.perfil.get("id")}
    ids.update(f.get("usuario_id") for f in leido.datos["lotes"])
    ids.update(f.get("subido_por_id") for f in leido.datos["vuelos"])
    ids.update(f.get("usuario_id") for f in leido.datos["revisiones_diagnostico"])
    return {str(i) for i in ids if i}


async def _insertar(db: AsyncSession, ctx: _Contexto, nombre: str, fila: dict, extra=None) -> None:
    t = tabla(nombre)
    valores, desconocidas = valores_para_insertar(t, ctx.preparar(fila), extra)
    ctx.desconocidas.setdefault(nombre, set()).update(set(desconocidas) - {"producto_ref"})
    await db.execute(t.insert().values(**valores))


async def _actualizar(db: AsyncSession, ctx: _Contexto, nombre: str, donde, fila: dict, excluir) -> None:
    t = tabla(nombre)
    valores, _ = valores_para_insertar(t, ctx.preparar(fila))
    for columna in excluir:
        valores.pop(columna, None)
    await db.execute(update(t).where(donde).values(**valores))


async def _id_de_producto(db: AsyncSession, ref: dict | None):
    if not ref:
        return None
    p = tabla("productos_fitosanitarios")
    return (await db.execute(
        select(p.c.id).where(p.c.nombre == ref["nombre"], p.c.tipo == ref["tipo"],
                             p.c.causa_indice == ref["causa_indice"]).limit(1)
    )).scalar_one_or_none()


async def _producto_para(db: AsyncSession, ctx: _Contexto, fila: dict, cuenta: dict):
    """Para precios_productos: devuelve el `extra` con el producto de esta instalación."""
    producto_id = await _id_de_producto(db, fila.get("producto_ref"))
    if producto_id is None:
        ctx.sin_producto += 1
        cuenta["omitidos"] += 1
        return None
    return {"producto_id": producto_id}


async def _claves_locales(db: AsyncSession) -> set[str]:
    claves = set()
    for nombre, columnas in (("vuelos", ("archivo_original", "geojson_key")), ("analisis_indices", ("geojson_key",)),
                             ("usuarios", ("avatar_key", "logo_empresa_key"))):
        t = tabla(nombre)
        for fila in (await db.execute(select(*[t.c[c] for c in columnas]))).all():
            claves.update(v for v in fila if v)
    return claves


def _conteo() -> dict:
    return {"insertados": 0, "actualizados": 0, "omitidos": 0}


async def _reemplazar(db: AsyncSession, ctx: _Contexto, leido: Leido, resumen: dict) -> None:
    for nombre in reversed(TABLAS):
        t = tabla(nombre)
        consulta = delete(t)
        if nombre == "precios_productos":
            consulta = consulta.where(t.c.tipo == "usuario")
        await db.execute(consulta)
    for nombre in TABLAS:
        cuenta = resumen["tablas"][nombre]
        for fila in leido.datos[nombre]:
            extra = None
            if nombre == "precios_productos":
                extra = await _producto_para(db, ctx, fila, cuenta)
                if extra is None:
                    continue
            await _insertar(db, ctx, nombre, fila, extra)
            cuenta["insertados"] += 1


def _donde(t, claves: tuple[str, ...], fila: dict):
    condicion = None
    for c in claves:
        valor, _ = valores_para_insertar(t, {c: fila[c]})
        parcial = t.c[c] == valor[c]
        condicion = parcial if condicion is None else condicion & parcial
    return condicion


async def _sumar(db: AsyncSession, ctx: _Contexto, leido: Leido, resumen: dict) -> None:
    for nombre in TABLAS:
        t = tabla(nombre)
        cuenta = resumen["tablas"][nombre]
        claves, comparadas = CLAVES[nombre]
        filas = (await db.execute(select(*[t.c[c] for c in claves + comparadas]))).all()
        locales = {tuple(_texto(f._mapping[c]) for c in claves): f._mapping for f in filas}

        for fila in leido.datos[nombre]:
            local = locales.get(tuple(_texto(fila[c]) for c in claves))
            if local is None:
                extra = None
                if nombre == "precios_productos":
                    extra = await _producto_para(db, ctx, fila, cuenta)
                    if extra is None:
                        continue
                await _insertar(db, ctx, nombre, fila, extra)
                cuenta["insertados"] += 1
                continue

            donde = _donde(t, claves, fila)
            comparar = next((c for c in ("updated_at", "calculado_en") if c in comparadas), None)
            gana_el_backup = comparar and _fecha(fila.get(comparar)) > _fecha(local[comparar])
            if gana_el_backup:
                await _actualizar(db, ctx, nombre, donde, fila, excluir=("id",) + claves)
                cuenta["actualizados"] += 1
            elif "deleted_at" in comparadas and fila.get("deleted_at") and local["deleted_at"] is None:
                # Algo dado de baja en el backup se da de baja acá también.
                await db.execute(update(t).where(donde).values(deleted_at=_fecha(fila["deleted_at"])))
                cuenta["actualizados"] += 1
            else:
                cuenta["omitidos"] += 1


async def _aplicar_perfil(db: AsyncSession, ctx: _Contexto, leido: Leido, modo: str) -> None:
    t = tabla("usuarios")
    actual = (await db.execute(select(t).where(t.c.id == ctx.usuario_id))).first()._mapping
    perfil = dict(leido.perfil)
    perfil["avatar_key"] = ctx.clave(perfil.get("avatar_key"))
    perfil["logo_empresa_key"] = ctx.clave(perfil.get("logo_empresa_key"))
    cambios = {
        campo: perfil[campo] for campo in CAMPOS_PERFIL
        if perfil.get(campo) is not None and (modo == "reemplazar" or actual[campo] in (None, ""))
    }
    valores, _ = valores_para_insertar(t, cambios)
    producto_id = await _id_de_producto(db, perfil.get("producto_habitual_ref"))
    if producto_id is not None and (modo == "reemplazar" or actual["producto_habitual_id"] is None):
        valores["producto_habitual_id"] = producto_id
    if valores:
        await db.execute(update(t).where(t.c.id == ctx.usuario_id).values(**valores))


async def importar(db: AsyncSession, usuario: Usuario, ruta: Path, leido: Leido, modo: str) -> dict:
    """Aplica el backup. No hace commit: lo hace quien llama, y recién entonces
    puede borrar los archivos viejos que devuelve en `claves_a_borrar`."""
    if modo not in MODOS:
        raise ValueError(f"Modo de importación desconocido: {modo!r}")
    ctx = _Contexto(str(usuario.id), _usuarios_origen(leido))
    resumen = {"modo": modo, "tablas": {nombre: _conteo() for nombre in TABLAS}}
    claves_viejas = await _claves_locales(db) if modo == "reemplazar" else set()

    if modo == "reemplazar":
        await _reemplazar(db, ctx, leido, resumen)
    else:
        await _sumar(db, ctx, leido, resumen)
    await _aplicar_perfil(db, ctx, leido, modo)

    copiados = omitidos = faltantes = 0
    claves = claves_de_archivos(leido.datos, leido.perfil)
    with zipfile.ZipFile(ruta) as zf:
        for origen in claves:
            destino = ctx.clave(origen)
            if modo == "sumar" and await run_in_threadpool(archivos.existe, destino):
                omitidos += 1
            elif await run_in_threadpool(archivos.extraer_del_zip, zf, origen, destino):
                copiados += 1
            else:
                faltantes += 1
    resumen["archivos"] = {"copiados": copiados, "omitidos": omitidos, "faltantes": faltantes}
    resumen["columnas_desconocidas"] = {n: sorted(c) for n, c in ctx.desconocidas.items() if c}
    resumen["productos_no_encontrados"] = ctx.sin_producto
    resumen["claves_a_borrar"] = sorted(claves_viejas - {ctx.clave(c) for c in claves})
    return resumen
