"""agregar variedad, tipo_suelo y fecha_siembra a lotes

Revision ID: 0014
Revises: 0013
Create Date: 2026-08-30
"""

from alembic import op
import sqlalchemy as sa

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

tipo_suelo_enum = sa.Enum(
    "arcilloso", "franco", "franco_arcilloso", "franco_arenoso",
    "arenoso", "vertisol", "otro",
    name="tiposueloenum",
)


def upgrade() -> None:
    tipo_suelo_enum.create(op.get_bind(), checkfirst=True)
    op.add_column("lotes", sa.Column("variedad", sa.String(100), nullable=True))
    op.add_column("lotes", sa.Column("tipo_suelo", tipo_suelo_enum, nullable=True))
    op.add_column("lotes", sa.Column("fecha_siembra", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("lotes", "fecha_siembra")
    op.drop_column("lotes", "tipo_suelo")
    op.drop_column("lotes", "variedad")
    tipo_suelo_enum.drop(op.get_bind(), checkfirst=True)
