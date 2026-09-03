"""crear tablas suelos/ubicaciones y quitar cultivo/estadio_fenologico de lotes

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-10

cultivo/estadio_fenologico ahora viven en la tabla cultivos (0012) — un lote
puede tener varios ciclos de cultivo a lo largo del tiempo, no uno solo. El
tipo `cultivoenum` NO se elimina: sigue en uso por cultivos.cultivo.

suelos y ubicaciones son catálogos referenciados por lotes vía FK nullable
(SET NULL si se borra el catálogo) — sin seed inicial, se cargan después.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

cultivoenum_columna = postgresql.ENUM("soja", "maiz", "algodon", "sorgo", name="cultivoenum", create_type=False)


def upgrade() -> None:
    op.create_table(
        "suelos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tipo", sa.String(100), nullable=False),
        sa.Column("serie", sa.String(100), nullable=True),
    )

    op.create_table(
        "ubicaciones",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("departamento", sa.String(100), nullable=False),
        sa.Column("localidad", sa.String(100), nullable=True),
    )

    op.add_column("lotes", sa.Column("suelo_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("suelos.id", ondelete="SET NULL"), nullable=True))
    op.add_column("lotes", sa.Column("ubicacion_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ubicaciones.id", ondelete="SET NULL"), nullable=True))
    op.create_index("idx_lotes_suelo_id", "lotes", ["suelo_id"])
    op.create_index("idx_lotes_ubicacion_id", "lotes", ["ubicacion_id"])

    op.drop_column("lotes", "cultivo")
    op.drop_column("lotes", "estadio_fenologico")


def downgrade() -> None:
    # Datos de cultivo/estadio_fenologico se pierden — se recrean nullable.
    op.add_column("lotes", sa.Column("estadio_fenologico", sa.String(10), nullable=True))
    op.add_column("lotes", sa.Column("cultivo", cultivoenum_columna, nullable=True))

    op.drop_index("idx_lotes_ubicacion_id", table_name="lotes")
    op.drop_index("idx_lotes_suelo_id", table_name="lotes")
    op.drop_column("lotes", "ubicacion_id")
    op.drop_column("lotes", "suelo_id")

    op.drop_table("ubicaciones")
    op.drop_table("suelos")
