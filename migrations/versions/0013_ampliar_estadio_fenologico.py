"""ampliar lotes.estadio_fenologico de VARCHAR(10) a VARCHAR(30)

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-27

Los estadios fenológicos de algodón usados por el motor de reglas (sección 5
del documento de referencia) incluyen tokens más largos que no entraban en
10 caracteres, ej. "apertura_de_capsulas", "boton_floral". Soja/maíz/sorgo
siguen usando códigos cortos (V4, R2, VT) que entran sin problema.
"""

from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "lotes", "estadio_fenologico",
        existing_type=sa.String(10),
        type_=sa.String(30),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "lotes", "estadio_fenologico",
        existing_type=sa.String(30),
        type_=sa.String(10),
        existing_nullable=True,
    )
