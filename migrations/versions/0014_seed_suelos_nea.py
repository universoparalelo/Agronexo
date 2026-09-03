"""seed de tipos de suelo típicos del NEA (Chaco, Formosa, Corrientes)

Revision ID: 0014
Revises: 0013
Create Date: 2026-08-10

La creación de lotes ahora exige elegir un suelo_id de este catálogo — sin
seed, el formulario no tendría opciones para mostrar. Órdenes de suelo
(taxonomía USDA) predominantes en la región según docs/CLAUDE.md.
"""

from alembic import op
import sqlalchemy as sa

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

TIPOS = ["Vertisol", "Molisol", "Alfisol", "Entisol", "Inceptisol", "Suelo sódico-salino"]


def upgrade() -> None:
    conn = op.get_bind()
    for tipo in TIPOS:
        conn.execute(
            sa.text("INSERT INTO suelos (id, tipo, serie) VALUES (uuid_generate_v4(), :tipo, NULL)"),
            {"tipo": tipo},
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM suelos WHERE tipo = ANY(:tipos)"), {"tipos": TIPOS})
