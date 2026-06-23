"""inicial: habilitar extensiones PostGIS y uuid-ossp

Revision ID: 0001
Revises:
Create Date: 2026-06-23
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis_topology")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')


def downgrade() -> None:
    # No se eliminan las extensiones en downgrade — pueden estar usadas por otras BDs
    pass
