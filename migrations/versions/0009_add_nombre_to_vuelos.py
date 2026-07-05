"""agregar nombre a vuelos

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-04

Un lote puede tener muchos vuelos; cada vuelo necesita un nombre propio
para poder distinguirlos en la tabla de "Análisis Recientes" del dashboard
(antes solo se mostraba un vuelo por lote). Nullable para no romper filas
existentes — el formulario de carga lo exige a partir de ahora.
"""

from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "vuelos",
        sa.Column("nombre", sa.String(200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("vuelos", "nombre")
