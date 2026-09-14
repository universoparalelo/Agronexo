"""agregar restricciones_ambientales e instrucciones_seguridad a productos_fitosanitarios

Revision ID: 0018
Revises: 0017
Create Date: 2026-09-14

RFSA-04 (orden de trabajo) requiere restricciones ambientales e
instrucciones de seguridad por producto aplicado — el catálogo actual
(migración 0015) solo tenía nombre/tipo/causa/dosis_referencia/unidad.
Columnas nullable: los 21 productos seed no tienen estos datos cargados
todavía, se completan manualmente por producto según ficha técnica/hoja
de seguridad.
"""

from alembic import op
import sqlalchemy as sa

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "productos_fitosanitarios",
        sa.Column("restricciones_ambientales", sa.Text(), nullable=True),
    )
    op.add_column(
        "productos_fitosanitarios",
        sa.Column("instrucciones_seguridad", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("productos_fitosanitarios", "instrucciones_seguridad")
    op.drop_column("productos_fitosanitarios", "restricciones_ambientales")
