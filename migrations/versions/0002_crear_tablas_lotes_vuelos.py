"""crear tablas lotes y vuelos

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-24
"""

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lotes",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("cultivo", sa.Enum("soja", "maiz", "algodon", "sorgo", name="cultivoenum"), nullable=False),
        sa.Column("estadio_fenologico", sa.String(10), nullable=True),
        sa.Column("geometry", Geometry(geometry_type="POLYGON", srid=4326, spatial_index=False), nullable=False),
        sa.Column("area_ha", sa.Float(), nullable=True),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    # Índice GiST para consultas espaciales eficientes
    op.create_index("idx_lotes_geometry", "lotes", ["geometry"], postgresql_using="gist")
    op.create_index("idx_lotes_usuario_id", "lotes", ["usuario_id"])
    op.create_index("idx_lotes_deleted_at", "lotes", ["deleted_at"])

    op.create_table(
        "vuelos",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("lote_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fecha_vuelo", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sensor", sa.Enum("sentinel2", "dji_mavic3", name="sensorenum"), nullable=False),
        sa.Column("archivo_original", sa.String(500), nullable=True),
        sa.Column("estado", sa.Enum("pendiente", "procesando", "completado", "error", name="estadovueloenum"), nullable=False, server_default="pendiente"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["lote_id"], ["lotes.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_vuelos_lote_id", "vuelos", ["lote_id"])


def downgrade() -> None:
    op.drop_index("idx_vuelos_lote_id", table_name="vuelos")
    op.drop_table("vuelos")
    op.drop_index("idx_lotes_deleted_at", table_name="lotes")
    op.drop_index("idx_lotes_usuario_id", table_name="lotes")
    op.drop_index("idx_lotes_geometry", table_name="lotes")
    op.drop_table("lotes")
    op.execute("DROP TYPE IF EXISTS estadovueloenum")
    op.execute("DROP TYPE IF EXISTS sensorenum")
    op.execute("DROP TYPE IF EXISTS cultivoenum")
