"""agregar deleted_at a vuelos para soporte de soft delete

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-03

Permite eliminar (lógicamente) un vuelo/análisis desde el dashboard sin
perder el archivo original en MinIO ni romper la FK RESTRICT hacia lotes.
"""

from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "vuelos",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("vuelos", "deleted_at")
