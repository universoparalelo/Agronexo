"""geometry nullable en lotes

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-01
"""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("lotes", "geometry", nullable=True)


def downgrade() -> None:
    op.alter_column("lotes", "geometry", nullable=False)
