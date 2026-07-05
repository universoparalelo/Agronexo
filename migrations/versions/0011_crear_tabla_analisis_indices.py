"""crear tabla analisis_indices para soportar múltiples índices por vuelo

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-06

El primer índice (NDVI) se sigue calculando siempre al subir el vuelo y su
resultado vive en vuelos.geojson_key/estado (sin cambios, retrocompatible).
Esta tabla es para índices adicionales (NDRE, SAVI, ExG) que el usuario pide
analizar sobre un vuelo ya existente — cada uno con su propio ciclo de vida
async, igual que un vuelo pero acotado a un índice puntual.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

indiceenum_creador = postgresql.ENUM("ndvi", "ndre", "savi", "exg", name="indiceenum")
indiceenum_columna = postgresql.ENUM("ndvi", "ndre", "savi", "exg", name="indiceenum", create_type=False)


def upgrade() -> None:
    indiceenum_creador.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "analisis_indices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("vuelo_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vuelos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("indice", indiceenum_columna, nullable=False),
        sa.Column("estado", postgresql.ENUM("pendiente", "procesando", "completado", "error", name="estadovueloenum", create_type=False), nullable=False, server_default="pendiente"),
        sa.Column("task_id", sa.String(255), nullable=True),
        sa.Column("error_detalle", sa.String(1000), nullable=True),
        sa.Column("geojson_key", sa.String(500), nullable=True),
        sa.Column("metodo_umbral", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("vuelo_id", "indice", name="uq_analisis_indices_vuelo_indice"),
    )
    op.create_index("idx_analisis_indices_vuelo_id", "analisis_indices", ["vuelo_id"])


def downgrade() -> None:
    op.drop_index("idx_analisis_indices_vuelo_id", table_name="analisis_indices")
    op.drop_table("analisis_indices")
    indiceenum_creador.drop(op.get_bind(), checkfirst=True)
