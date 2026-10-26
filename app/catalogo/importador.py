"""
Importa dosis, unidad, confiabilidad de la dosis y precio de referencia del
Excel del catálogo (docs/catalogo_productos_fitosanitarios.xlsx) a la base.

Alcance de la tanda 1: solo las filas con Estado "Recomendado por el motor",
emparejadas por nombre exacto con productos_fitosanitarios. No crea
productos ni toca restricciones/seguridad (ya vienen de las migraciones
0018/0019). Las demás filas esperan al modelo de marcas/presentaciones.

Es idempotente: sin --aplicar solo muestra qué cambiaría.

Uso (dentro del contenedor api, con el Excel copiado adentro):
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
from app.diagnostico.models import PrecioProducto, ProductoFitosanitario
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


def leer_catalogo(ruta: str | Path) -> tuple[list[FilaCatalogo], list[str]]:
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

    def celda(fila, campo):
        posicion = indice[campo]
        return fila[posicion] if posicion < len(fila) else None

    filas: list[FilaCatalogo] = []
    errores: list[str] = []
    vistos: set[str] = set()

    for numero, fila in enumerate(filas_excel[1:], start=2):
        if str(celda(fila, "estado") or "").strip() != ESTADO_MOTOR:
            continue
        nombre = str(celda(fila, "nombre") or "").strip()
        if not nombre:
            errores.append(f"Fila {numero}: sin nombre")
            continue
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

        fuente = celda(fila, "fuente")
        filas.append(FilaCatalogo(
            fila=numero,
            nombre=nombre,
            dosis=dosis,
            unidad=unidad,
            precio_usd=precio,
            fuente_precio=str(fuente).strip() if fuente else None,
            confiabilidad=normalizar_confiabilidad(celda(fila, "confiabilidad")),
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Importa el catálogo de fitosanitarios desde Excel")
    parser.add_argument("ruta", help="Ruta del .xlsx")
    parser.add_argument("--aplicar", action="store_true", help="Guarda los cambios (sin esto es solo simulación)")
    args = parser.parse_args(argv)

    if not Path(args.ruta).is_file():
        print(f"No existe el archivo: {args.ruta}")
        return 1

    filas, errores = leer_catalogo(args.ruta)
    if errores:
        print("La planilla tiene errores, no se importó nada:")
        for error in errores:
            print(f"  - {error}")
        return 1

    engine = create_engine(settings.database_url_sync)
    with Session(engine) as session:
        resumen = aplicar(session, filas)
        if args.aplicar:
            session.commit()
        else:
            session.rollback()

    print(f"Productos del motor en la planilla: {len(filas)}")
    for cambio in resumen.cambios:
        print(f"  * {cambio}")
    print(f"Sin cambios: {resumen.sin_cambios}")
    if resumen.no_encontrados:
        print(f"No están en la base (no se crean): {', '.join(resumen.no_encontrados)}")
    if resumen.ambiguos:
        print(f"Nombre repetido en la base (se omiten): {', '.join(resumen.ambiguos)}")
    print("Guardado." if args.aplicar else "Simulación: no se guardó nada. Usá --aplicar para confirmar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
