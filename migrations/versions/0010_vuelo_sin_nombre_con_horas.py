"""quitar nombre de vuelos, agregar hora_inicio y hora_fin

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-04

Se decidió que un vuelo no se identifica por nombre propio, sino por su
lote y fecha (fecha_vuelo). La columna nombre agregada en 0009 se revierte.
Se agregan hora_inicio/hora_fin (nullable, no se muestran en el dashboard
todavía) para registrar la ventana horaria real del vuelo cuando se cargue.
"""

from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("vuelos", "nombre")
    op.add_column("vuelos", sa.Column("hora_inicio", sa.Time(), nullable=True))
    op.add_column("vuelos", sa.Column("hora_fin", sa.Time(), nullable=True))


def downgrade() -> None:
    op.drop_column("vuelos", "hora_fin")
    op.drop_column("vuelos", "hora_inicio")
    op.add_column("vuelos", sa.Column("nombre", sa.String(200), nullable=True))
