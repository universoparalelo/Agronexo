"""Paso de filas de la base a JSON y de vuelta, tabla por tabla.

El backup guarda los datos como JSON (una línea por fila) y no como volcado de
Postgres: la API empaquetada no trae pg_dump y "sumar" necesita leer registro
por registro. Los tipos se resuelven con las columnas del modelo, así que una
columna nueva se exporta sin tocar este archivo.
"""
import enum
import json
import uuid
from datetime import date, datetime, time
from decimal import Decimal

from geoalchemy2 import Geometry
from sqlalchemy import Date, DateTime, Table, Time, func, select

from app.core.database import Base
import app.auth.models  # noqa: F401  (registra las tablas en Base.metadata)
import app.diagnostico.models  # noqa: F401
import app.lotes.models  # noqa: F401

FORMATO = 1

# Orden de inserción: cada tabla va después de aquellas a las que apunta.
TABLAS = [
    "lotes",
    "cultivos",
    "vuelos",
    "analisis_indices",
    "diagnosticos",
    "revisiones_diagnostico",
    "precios_productos",
]

COLUMNAS_USUARIO = {"usuario_id", "subido_por_id"}
COLUMNAS_CLAVE_ARCHIVO = {"archivo_original", "geojson_key"}

# El perfil (tabla usuarios) viaja aparte: el correo, la contraseña y el id son
# de la instalación y no se tocan al importar.
CAMPOS_PERFIL = [
    "nombre", "descripcion", "cuit", "telefono_contacto", "matricula_aplicador",
    "nombre_empresa", "avatar_key", "logo_empresa_key", "indice_preferido",
    "unidad_area_preferida",
]


def tabla(nombre: str) -> Table:
    return Base.metadata.tables[nombre]


def columnas_select(t: Table, nombres=None):
    cols = []
    for c in t.columns:
        if nombres is not None and c.name not in nombres:
            continue
        if isinstance(c.type, Geometry):
            cols.append(func.ST_AsEWKT(c).label(c.name))
        else:
            cols.append(c)
    return cols


def _a_json(valor):
    if isinstance(valor, enum.Enum):
        return valor.name
    if isinstance(valor, uuid.UUID):
        return str(valor)
    if isinstance(valor, (datetime, date, time)):
        return valor.isoformat()
    if isinstance(valor, Decimal):
        return float(valor)
    raise TypeError(f"No se puede guardar un {type(valor).__name__} en el backup")


def a_linea(fila: dict) -> str:
    return json.dumps(fila, default=_a_json, ensure_ascii=False)


def fila_a_dict(mapping) -> dict:
    return {k: (_a_json(v) if isinstance(v, (enum.Enum, uuid.UUID, datetime, date, time, Decimal)) else v)
            for k, v in mapping.items()}


def _a_python(columna, valor):
    if valor is None:
        return None
    tipo = columna.type
    if isinstance(tipo, Geometry):
        return func.ST_GeomFromEWKT(valor)
    if hasattr(tipo, "as_uuid"):
        return uuid.UUID(valor) if tipo.as_uuid else str(valor)
    if isinstance(tipo, DateTime):
        return datetime.fromisoformat(valor)
    if isinstance(tipo, Date):
        return date.fromisoformat(valor)
    if isinstance(tipo, Time):
        return time.fromisoformat(valor)
    return valor


def valores_para_insertar(t: Table, fila: dict, extra=None):
    """Devuelve (valores, columnas_desconocidas).

    Las columnas que la fila no trae se omiten: Postgres usa el valor por
    defecto. Las que la fila trae y esta versión no conoce se ignoran.
    """
    valores = {}
    for c in t.columns:
        if c.name in fila:
            valores[c.name] = _a_python(c, fila[c.name])
    if extra:
        valores.update(extra)
    desconocidas = sorted(set(fila) - {c.name for c in t.columns})
    return valores, desconocidas
