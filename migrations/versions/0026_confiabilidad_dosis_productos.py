"""confiabilidad de la dosis de referencia en productos_fitosanitarios

Revision ID: 0026
Revises: 0025
Create Date: 2026-10-26

Origen de cada dosis_referencia: "marbete" (etiqueta oficial del producto,
dosis autorizada) o "web" (valor genérico de internet, puede no coincidir
con la etiqueta). NULL = sin dato. Lo carga app/catalogo/importador.py
desde el Excel del catálogo; la columna no se completa en esta migración
porque ningún producto tiene todavía dosis_referencia en la base.
"""

from alembic import op
import sqlalchemy as sa

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "productos_fitosanitarios",
        sa.Column("confiabilidad_dosis", sa.String(20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("productos_fitosanitarios", "confiabilidad_dosis")
