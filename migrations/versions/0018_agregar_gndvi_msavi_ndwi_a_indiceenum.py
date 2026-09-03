"""agregar gndvi, msavi y ndwi a indiceenum

Revision ID: 0018
Revises: 0017
Create Date: 2026-08-17

Se suman 3 índices al sistema multi-índice existente (NDVI/NDRE/SAVI/ExG):
GNDVI, MSAVI y NDWI (proxy McFeeters, sin banda SWIR). No requiere tocar
la tabla analisis_indices — solo ampliar los valores válidos del enum
Postgres `indiceenum` que ya usa esa columna.

ALTER TYPE ... ADD VALUE no puede usarse dentro de la misma transacción en
la que se inserta una fila con el valor nuevo (restricción de Postgres) —
como acá solo agregamos los valores sin usarlos, no hay problema corriendo
dentro de la transacción de Alembic.
"""

from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None

_NUEVOS_VALORES = ["gndvi", "msavi", "ndwi"]


def upgrade() -> None:
    for valor in _NUEVOS_VALORES:
        op.execute(f"ALTER TYPE indiceenum ADD VALUE IF NOT EXISTS '{valor}'")


def downgrade() -> None:
    # Postgres no soporta quitar valores de un enum directamente — habría que
    # recrear el tipo. No se implementa downgrade: si se necesita revertir,
    # borrar manualmente las filas con esos índices y recrear el enum.
    pass
