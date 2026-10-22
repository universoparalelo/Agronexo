"""crear tabla ndvi_esperado_estadio con curva genérica placeholder

Revision ID: 0025
Revises: 0024
Create Date: 2026-10-15

Tabla de referencia para el gráfico "Tendencia del índice": NDVI
esperado y rango normal por cultivo + estadio fenológico. Los valores que
carga esta migración son una curva genérica placeholder (sube en vegetativo,
mesetea y declina hacia madurez) — NO son una curva agronómica validada.
Se actualizará con estadísticas reales cuando haya suficientes vuelos
cargados por cultivo/estadio (ver docs/release-v4.0.0.md).

Los estadios y su orden están duplicados de
app/diagnostico/estadios.py::ESTADIOS_POR_CULTIVO a propósito — las
migraciones no importan código de la app porque éste puede cambiar después
y rompería la reproducibilidad histórica (mismo criterio que 0015).
"""

import re
import unicodedata

from alembic import op
import sqlalchemy as sa

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None

ESTADIOS_POR_CULTIVO = {
    "soja": ["VE", "VC"] + [f"V{n}" for n in range(1, 11)] + [f"R{n}" for n in range(1, 9)],
    "maiz": ["VE"] + [f"V{n}" for n in range(1, 19)] + ["VT"] + [f"R{n}" for n in range(1, 7)],
    "algodon": (
        ["VE"] + [f"V{n}" for n in range(1, 9)]
        + ["Botón floral", "Floración"]
        + [f"R{n}" for n in range(1, 6)]
        + ["Apertura de cápsulas"]
    ),
    "sorgo": (
        ["VE"] + [f"V{n}" for n in range(1, 13)]
        + ["VT", "Espigado", "Floración", "Llenado de grano"]
    ),
}

BANDA = 0.12


def _normalizar(texto: str) -> str:
    sin_acentos = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", "_", sin_acentos.strip().lower())


def _ndvi_esperado(progreso: float) -> float:
    """Curva genérica 0..1 del ciclo: sube hasta ~70% del ciclo, luego declina
    hacia senescencia/madurez. Puramente ilustrativa (ver docstring del módulo)."""
    import math
    if progreso <= 0.7:
        return 0.15 + 0.65 * math.sin(progreso / 0.7 * math.pi / 2)
    return 0.80 - 0.45 * ((progreso - 0.7) / 0.3)


def _filas_seed():
    filas = []
    for cultivo, estadios in ESTADIOS_POR_CULTIVO.items():
        n = len(estadios)
        for i, etiqueta in enumerate(estadios):
            progreso = i / (n - 1) if n > 1 else 0.0
            esperado = round(_ndvi_esperado(progreso), 3)
            ndvi_min = round(max(0.0, esperado - BANDA), 3)
            ndvi_max = round(min(1.0, esperado + BANDA), 3)
            filas.append((cultivo, _normalizar(etiqueta), etiqueta, i, esperado, ndvi_min, ndvi_max))
    return filas


def upgrade() -> None:
    bind = op.get_bind()

    op.execute("""
        CREATE TABLE ndvi_esperado_estadio (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            tipo_cultivo cultivoenum NOT NULL,
            estadio_normalizado VARCHAR(30) NOT NULL,
            etiqueta VARCHAR(30) NOT NULL,
            orden INTEGER NOT NULL,
            ndvi_esperado FLOAT NOT NULL,
            ndvi_min FLOAT NOT NULL,
            ndvi_max FLOAT NOT NULL,
            UNIQUE (tipo_cultivo, estadio_normalizado)
        )
    """)
    op.create_index("ix_ndvi_esperado_cultivo_orden", "ndvi_esperado_estadio", ["tipo_cultivo", "orden"])

    filas = _filas_seed()
    values = ", ".join(
        f"('{cultivo}'::cultivoenum, '{estadio}', '{etiqueta}', {orden}, {esperado}, {ndvi_min}, {ndvi_max})"
        for cultivo, estadio, etiqueta, orden, esperado, ndvi_min, ndvi_max in filas
    )
    bind.execute(sa.text(f"""
        INSERT INTO ndvi_esperado_estadio
            (tipo_cultivo, estadio_normalizado, etiqueta, orden, ndvi_esperado, ndvi_min, ndvi_max)
        VALUES {values}
    """))


def downgrade() -> None:
    op.drop_table("ndvi_esperado_estadio")
