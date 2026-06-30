"""add task_id y error_detalle a vuelos

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-30
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vuelos", sa.Column("task_id", sa.String(255), nullable=True))
    op.add_column("vuelos", sa.Column("error_detalle", sa.String(1000), nullable=True))


def downgrade() -> None:
    op.drop_column("vuelos", "error_detalle")
    op.drop_column("vuelos", "task_id")
