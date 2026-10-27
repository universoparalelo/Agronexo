"""
Importa dosis, unidad, confiabilidad de la dosis y precio de referencia del
Excel del catálogo (docs/catalogo_productos_fitosanitarios.xlsx) a la base.

Dos pasos en cada corrida:
1. Filas con Estado "Recomendado por el motor": actualizan dosis, unidad,
   confiabilidad y precio del producto existente (emparejado por nombre exacto).
   No tocan restricciones/seguridad (ya vienen de las migraciones 0018/0019).
2. Todas las filas: se cargan como presentaciones (marca/concentración) del
   principio activo. Un activo que no existe solo se crea con
   --crear-activos-nuevos, porque al entrar a productos_fitosanitarios el
   motor puede empezar a sugerirlo.

Es idempotente: sin --aplicar solo muestra qué cambiaría.

Uso (dentro del contenedor api, con el Excel copiado adentro; en Git Bash
anteponer MSYS_NO_PATHCONV=1 para que no convierta /tmp):
    docker compose cp docs/catalogo_productos_fitosanitarios.xlsx api:/tmp/catalogo.xlsx
    docker compose exec api python -m app.catalogo.importador /tmp/catalogo.xlsx
    docker compose exec api python -m app.catalogo.importador /tmp/catalogo.xlsx --aplicar
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import openpyxl
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.auth import models as _auth_models  # noqa: F401
from app.core.config import settings
from app.diagnostico.models import (
    CausaIndiceEnum,
    PrecioProducto,
    PresentacionProducto,
    ProductoFitosanitario,
    TipoProductoEnum,
)
from app.lotes import models as _lotes_models  # noqa: F401

# Los dos imports de arriba solo registran modelos: fuera de FastAPI nadie más
# los importa y SQLAlchemy no puede resolver las relaciones entre ellos
# (Lote -> Usuario) al usar cualquier modelo.

ESTADO_MOTOR = "Recomendado por el motor"
UNIDAD_PRECIO_POR_UNIDAD_DOSIS = {"L/ha": "L", "kg/ha": "kg"}

# Prefijos normalizados de cabecera -> campo. Se busca por prefijo porque la
# planilla se edita a mano (ej. "Confiabilidad " con espacio final).
_COLUMNAS = {
    "nombre": "nombre",
    "dosis de referencia": "dosis",
    "unidad de dosis": "unidad",
    "precio aproximado": "precio",
    "fecha / fuente": "fuente",
    "confiabilidad": "confiabilidad",
    "estado": "estado",
}

# Solo las usa la carga de presentaciones; una planilla sin ellas sigue
# sirviendo para actualizar los 21 productos del motor.
_COLUMNAS_OPCIONALES = {
    "tipo": "tipo",
    "causa asociada": "causa",
    "marca": "marca",
    "variante": "variante",
    "cultivos asociados": "cultivos",
    "observaciones del marbete": "observaciones",
    "restricciones ambientales": "restricciones",
    "instrucciones de seguridad": "seguridad",
}

_FECHA_COMPLETA = re.compile(r"(?<!\d)(\d{1,2})/(\d{1,2})/(\d{4})")
_FECHA_MES_ANIO = re.compile(r"(?<!\d)(\d{1,2})/(\d{4})")
_FECHA_ISO_MES = re.compile(r"(\d{4})-(\d{2})")


@dataclass
class FilaCatalogo:
    fila: int
    nombre: str
    dosis: float
    unidad: str
    precio_usd: float
    fuente_precio: str | None
    confiabilidad: str | None
    estado: str = ESTADO_MOTOR
    tipo: str = ""
    causa: str = ""
    marca: str = ""
    concentracion: str = ""
    variante: str = ""
    cultivos: str | None = None
    observaciones: str | None = None
    restricciones: str | None = None
    seguridad: str | None = None


@dataclass
class ResumenPresentaciones:
    creadas: int = 0
    actualizadas: int = 0
    sin_cambios: int = 0
    activos_creados: list[str] = field(default_factory=list)
    activos_pendientes: dict[str, int] = field(default_factory=dict)


@dataclass
class ResumenImportacion:
    cambios: list[str] = field(default_factory=list)
    no_encontrados: list[str] = field(default_factory=list)
    ambiguos: list[str] = field(default_factory=list)
    sin_cambios: int = 0


def _norm(texto) -> str:
    sin_acentos = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return sin_acentos.strip().lower()


def _a_float(valor) -> float | None:
    if valor is None or valor == "":
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    return float(str(valor).replace("$", "").replace(" ", "").replace(",", "."))


def normalizar_confiabilidad(texto) -> str | None:
    normalizado = _norm(texto)
    if "marbete" in normalizado:
        return "marbete"
    if "web" in normalizado:
        return "web"
    return None


def parsear_fuente_y_fecha(texto, hoy: date | None = None) -> tuple[str | None, date]:
    """La planilla junta fuente y fecha en una sola celda; la base las guarda
    separadas y `fecha` es obligatoria. Sin fecha reconocible usa `hoy`."""
    hoy = hoy or date.today()
    if not texto:
        return None, hoy
    fuente = str(texto).strip()[:200]
    for patron, armar in (
        (_FECHA_COMPLETA, lambda g: date(int(g[2]), int(g[1]), int(g[0]))),
        (_FECHA_MES_ANIO, lambda g: date(int(g[1]), int(g[0]), 1)),
        (_FECHA_ISO_MES, lambda g: date(int(g[0]), int(g[1]), 1)),
    ):
        coincidencia = patron.search(fuente)
        if coincidencia:
            try:
                return fuente, armar(coincidencia.groups())
            except ValueError:
                continue
    return fuente, hoy


def leer_catalogo(ruta: str | Path, solo_motor: bool = True) -> tuple[list[FilaCatalogo], list[str]]:
    """solo_motor=True: únicamente las filas "Recomendado por el motor" (tanda 1).
    solo_motor=False: todas las filas con producto, para cargar presentaciones."""
    libro = openpyxl.load_workbook(ruta, data_only=True, read_only=True)
    filas_excel = list(libro.worksheets[0].iter_rows(values_only=True))
    if not filas_excel:
        return [], ["La planilla está vacía"]

    indice: dict[str, int] = {}
    for posicion, cabecera in enumerate(filas_excel[0]):
        normalizada = _norm(cabecera)
        for prefijo, campo in _COLUMNAS.items():
            if normalizada.startswith(prefijo) and campo not in indice:
                indice[campo] = posicion
    faltantes = sorted(set(_COLUMNAS.values()) - set(indice))
    if faltantes:
        return [], [f"Faltan columnas en la planilla: {', '.join(faltantes)}"]

    for posicion, cabecera in enumerate(filas_excel[0]):
        normalizada = _norm(cabecera)
        for prefijo, campo in _COLUMNAS_OPCIONALES.items():
            if normalizada.startswith(prefijo) and campo not in indice:
                indice[campo] = posicion
    # La concentración está en una columna sin título, justo a la derecha de "Marca".
    marca = indice.get("marca")
    if marca is not None and marca + 1 < len(filas_excel[0]) and not _norm(filas_excel[0][marca + 1]):
        indice["concentracion"] = marca + 1

    def celda(fila, campo):
        posicion = indice.get(campo)
        return fila[posicion] if posicion is not None and posicion < len(fila) else None

    def texto(fila, campo) -> str:
        return str(celda(fila, campo) or "").strip()

    filas: list[FilaCatalogo] = []
    errores: list[str] = []
    vistos: set[str] = set()
    claves_presentacion: set[tuple[str, str, str, str]] = set()

    if not solo_motor:
        faltan_para_presentaciones = sorted({"tipo", "causa", "marca"} - set(indice))
        if faltan_para_presentaciones:
            return [], [f"Faltan columnas para cargar presentaciones: {', '.join(faltan_para_presentaciones)}"]

    for numero, fila in enumerate(filas_excel[1:], start=2):
        estado = texto(fila, "estado")
        es_del_motor = estado == ESTADO_MOTOR
        if solo_motor and not es_del_motor:
            continue
        if not solo_motor and not texto(fila, "tipo"):
            continue
        nombre = texto(fila, "nombre")
        if not nombre:
            errores.append(f"Fila {numero}: sin nombre")
            continue
        if es_del_motor:
            if nombre in vistos:
                errores.append(f"Fila {numero}: '{nombre}' está repetido entre los productos del motor")
                continue
            vistos.add(nombre)

        try:
            dosis = _a_float(celda(fila, "dosis"))
            precio = _a_float(celda(fila, "precio"))
        except ValueError:
            errores.append(f"Fila {numero} ({nombre}): dosis o precio no es un número")
            continue
        unidad = str(celda(fila, "unidad") or "").strip()

        if dosis is None or dosis <= 0:
            errores.append(f"Fila {numero} ({nombre}): dosis vacía o no positiva")
        if precio is None or precio <= 0:
            errores.append(f"Fila {numero} ({nombre}): precio vacío o no positivo")
        if unidad not in UNIDAD_PRECIO_POR_UNIDAD_DOSIS:
            errores.append(f"Fila {numero} ({nombre}): unidad '{unidad}' no es L/ha ni kg/ha")
        if dosis is None or dosis <= 0 or precio is None or precio <= 0 or unidad not in UNIDAD_PRECIO_POR_UNIDAD_DOSIS:
            continue

        tipo, causa = texto(fila, "tipo"), texto(fila, "causa")
        marca, concentracion, variante = texto(fila, "marca"), texto(fila, "concentracion"), texto(fila, "variante")
        if not solo_motor:
            if tipo not in {t.value for t in TipoProductoEnum}:
                errores.append(f"Fila {numero} ({nombre}): tipo '{tipo}' no existe en el sistema")
            if causa not in {c.value for c in CausaIndiceEnum}:
                errores.append(f"Fila {numero} ({nombre}): causa '{causa}' no existe en el sistema")
            if not marca:
                errores.append(f"Fila {numero} ({nombre}): sin marca")
            clave = (nombre, marca, concentracion, variante)
            if clave in claves_presentacion:
                errores.append(f"Fila {numero} ({nombre}): marca, concentración y variante repetidas")
            claves_presentacion.add(clave)

        fuente = celda(fila, "fuente")
        filas.append(FilaCatalogo(
            fila=numero,
            nombre=nombre,
            dosis=dosis,
            unidad=unidad,
            precio_usd=precio,
            fuente_precio=str(fuente).strip() if fuente else None,
            confiabilidad=normalizar_confiabilidad(celda(fila, "confiabilidad")),
            estado=estado,
            tipo=tipo,
            causa=causa,
            marca=marca,
            concentracion=concentracion,
            variante=variante,
            cultivos=texto(fila, "cultivos")[:200] or None,
            observaciones=texto(fila, "observaciones") or None,
            restricciones=texto(fila, "restricciones") or None,
            seguridad=texto(fila, "seguridad") or None,
        ))
    return filas, errores


def _distinto(a: float | None, b: float | None) -> bool:
    return a is None or b is None or abs(a - b) > 1e-9


def aplicar(session: Session, filas: list[FilaCatalogo], hoy: date | None = None) -> ResumenImportacion:
    """No hace commit: lo decide quien llama (--aplicar o rollback en dry-run)."""
    resumen = ResumenImportacion()

    for fila in filas:
        productos = session.scalars(
            select(ProductoFitosanitario).where(ProductoFitosanitario.nombre == fila.nombre)
        ).all()
        if not productos:
            resumen.no_encontrados.append(fila.nombre)
            continue
        if len(productos) > 1:
            resumen.ambiguos.append(fila.nombre)
            continue
        producto = productos[0]
        hubo_cambio = False

        if _distinto(producto.dosis_referencia, fila.dosis):
            resumen.cambios.append(f"{fila.nombre}: dosis {producto.dosis_referencia} -> {fila.dosis}")
            producto.dosis_referencia = fila.dosis
            hubo_cambio = True
        if producto.unidad != fila.unidad:
            resumen.cambios.append(f"{fila.nombre}: unidad {producto.unidad} -> {fila.unidad}")
            producto.unidad = fila.unidad
            hubo_cambio = True
        if producto.confiabilidad_dosis != fila.confiabilidad:
            resumen.cambios.append(
                f"{fila.nombre}: confiabilidad {producto.confiabilidad_dosis} -> {fila.confiabilidad}"
            )
            producto.confiabilidad_dosis = fila.confiabilidad
            hubo_cambio = True

        unidad_precio = UNIDAD_PRECIO_POR_UNIDAD_DOSIS[fila.unidad]
        precio = session.scalars(
            select(PrecioProducto)
            .where(PrecioProducto.producto_id == producto.id, PrecioProducto.tipo == "referencia")
            .order_by(PrecioProducto.fecha.desc())
        ).first()
        fuente, fecha = parsear_fuente_y_fecha(fila.fuente_precio, hoy)

        if precio is None:
            session.add(PrecioProducto(
                producto_id=producto.id, precio_usd=fila.precio_usd, unidad=unidad_precio,
                fuente=fuente, fecha=fecha, tipo="referencia",
            ))
            resumen.cambios.append(f"{fila.nombre}: precio nuevo {fila.precio_usd}/{unidad_precio}")
            hubo_cambio = True
        elif _distinto(precio.precio_usd, fila.precio_usd) or precio.unidad != unidad_precio:
            resumen.cambios.append(
                f"{fila.nombre}: precio {precio.precio_usd}/{precio.unidad} -> {fila.precio_usd}/{unidad_precio}"
            )
            precio.precio_usd = fila.precio_usd
            precio.unidad = unidad_precio
            precio.fuente = fuente
            precio.fecha = fecha
            hubo_cambio = True

        if not hubo_cambio:
            resumen.sin_cambios += 1

    session.flush()
    return resumen


def aplicar_presentaciones(
    session: Session,
    filas: list[FilaCatalogo],
    crear_activos_nuevos: bool = False,
    hoy: date | None = None,
) -> ResumenPresentaciones:
    """Carga cada fila como presentación de su principio activo (emparejado por
    nombre). Si el activo no existe, solo se crea con crear_activos_nuevos: al
    entrar a productos_fitosanitarios el motor puede empezar a sugerirlo.
    Un activo nuevo toma dosis, restricciones y seguridad de su primera fila.
    No hace commit."""
    resumen = ResumenPresentaciones()

    for fila in filas:
        producto = session.scalars(
            select(ProductoFitosanitario).where(ProductoFitosanitario.nombre == fila.nombre)
        ).first()
        if producto is None:
            if not crear_activos_nuevos:
                resumen.activos_pendientes[fila.nombre] = resumen.activos_pendientes.get(fila.nombre, 0) + 1
                continue
            producto = ProductoFitosanitario(
                nombre=fila.nombre,
                tipo=TipoProductoEnum(fila.tipo),
                causa_indice=CausaIndiceEnum(fila.causa),
                dosis_referencia=fila.dosis,
                unidad=fila.unidad,
                confiabilidad_dosis=fila.confiabilidad,
                restricciones_ambientales=fila.restricciones,
                instrucciones_seguridad=fila.seguridad,
            )
            session.add(producto)
            session.flush()
            resumen.activos_creados.append(fila.nombre)

        fuente, fecha = parsear_fuente_y_fecha(fila.fuente_precio, hoy)
        datos = dict(
            dosis_referencia=fila.dosis,
            unidad=fila.unidad,
            confiabilidad_dosis=fila.confiabilidad,
            precio_usd=fila.precio_usd,
            unidad_precio=UNIDAD_PRECIO_POR_UNIDAD_DOSIS[fila.unidad],
            fuente_precio=fuente,
            fecha_precio=fecha,
            cultivos=fila.cultivos,
            observaciones_marbete=fila.observaciones,
        )
        presentacion = session.scalars(
            select(PresentacionProducto).where(
                PresentacionProducto.producto_id == producto.id,
                PresentacionProducto.marca == fila.marca,
                PresentacionProducto.concentracion == fila.concentracion,
                PresentacionProducto.variante == fila.variante,
            )
        ).first()

        if presentacion is None:
            session.add(PresentacionProducto(
                producto_id=producto.id, marca=fila.marca,
                concentracion=fila.concentracion, variante=fila.variante, **datos,
            ))
            resumen.creadas += 1
        elif any(getattr(presentacion, campo) != valor for campo, valor in datos.items()):
            for campo, valor in datos.items():
                setattr(presentacion, campo, valor)
            resumen.actualizadas += 1
        else:
            resumen.sin_cambios += 1

    session.flush()
    return resumen


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Importa el catálogo de fitosanitarios desde Excel")
    parser.add_argument("ruta", help="Ruta del .xlsx")
    parser.add_argument("--aplicar", action="store_true", help="Guarda los cambios (sin esto es solo simulación)")
    parser.add_argument(
        "--crear-activos-nuevos", action="store_true",
        help="Crea los principios activos que no existen, para poder cargar sus marcas",
    )
    args = parser.parse_args(argv)

    if not Path(args.ruta).is_file():
        print(f"No existe el archivo: {args.ruta}")
        return 1

    filas_todas, errores = leer_catalogo(args.ruta, solo_motor=False)
    if errores:
        print("La planilla tiene errores, no se importó nada:")
        for error in errores:
            print(f"  - {error}")
        return 1
    filas_motor = [f for f in filas_todas if f.estado == ESTADO_MOTOR]

    engine = create_engine(settings.database_url_sync)
    with Session(engine) as session:
        resumen = aplicar(session, filas_motor)
        presentaciones = aplicar_presentaciones(session, filas_todas, args.crear_activos_nuevos)
        if args.aplicar:
            session.commit()
        else:
            session.rollback()

    print(f"Productos del motor en la planilla: {len(filas_motor)}")
    for cambio in resumen.cambios:
        print(f"  * {cambio}")
    print(f"Sin cambios: {resumen.sin_cambios}")
    if resumen.no_encontrados:
        print(f"No están en la base (no se crean): {', '.join(resumen.no_encontrados)}")
    if resumen.ambiguos:
        print(f"Nombre repetido en la base (se omiten): {', '.join(resumen.ambiguos)}")

    print(f"Presentaciones en la planilla: {len(filas_todas)}")
    print(f"  creadas: {presentaciones.creadas} | actualizadas: {presentaciones.actualizadas} | sin cambios: {presentaciones.sin_cambios}")
    if presentaciones.activos_creados:
        print(f"  activos nuevos creados: {', '.join(presentaciones.activos_creados)}")
    if presentaciones.activos_pendientes:
        detalle = ", ".join(f"{n} ({c})" for n, c in presentaciones.activos_pendientes.items())
        print(f"  no cargadas, su activo no existe (usá --crear-activos-nuevos): {detalle}")
    print("Guardado." if args.aplicar else "Simulación: no se guardó nada. Usá --aplicar para confirmar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
