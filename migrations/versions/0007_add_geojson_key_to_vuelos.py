"""agregar geojson_key a vuelos para vincular análisis explícitamente

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-02

El worker ahora escribe la ruta MinIO del GeoJSON de zonas directamente
en la tabla vuelos. Antes se derivaba parseando archivo_original, lo que
era frágil ante cambios de estructura de paths.
"""

from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "vuelos",
        sa.Column("geojson_key", sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("vuelos", "geojson_key")
