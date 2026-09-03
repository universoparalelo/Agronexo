"""agregar created_at a cultivos (faltaba desde la migración 0012)

Revision ID: 0015
Revises: 0014
Create Date: 2026-08-10

El modelo Cultivo se creó sin created_at por un descuido — CultivoResponse
ya lo exponía como campo, lo que rompía la serialización de cultivo_activo
en LoteResponse en cuanto existía al menos un ciclo de cultivo.
"""

from alembic import op
import sqlalchemy as sa

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cultivos", sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))


def downgrade() -> None:
    op.drop_column("cultivos", "created_at")
