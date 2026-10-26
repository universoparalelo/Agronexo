"""crear tabla presentaciones_productos (marcas y concentraciones)

Revision ID: 0027
Revises: 0026
Create Date: 2026-10-26

Una presentación es una marca/concentración comercial de un principio activo
(productos_fitosanitarios). Tiene su propia dosis y precio porque la
concentración cambia la dosis. La carga la hace app/catalogo/importador.py
desde el Excel del catálogo; la migración no inserta datos.

concentracion y variante son NOT NULL con default '' para que la restricción
única detecte duplicados (en Postgres los NULL no chocan entre sí).
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "presentaciones_productos",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("producto_id", UUID(as_uuid=True),
                  sa.ForeignKey("productos_fitosanitarios.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("marca", sa.String(200), nullable=False),
        sa.Column("concentracion", sa.Text(), nullable=False, server_default=""),
        sa.Column("variante", sa.Text(), nullable=False, server_default=""),
        sa.Column("dosis_referencia", sa.Float(), nullable=False),
        sa.Column("unidad", sa.String(50), nullable=False),
        sa.Column("confiabilidad_dosis", sa.String(20), nullable=True),
        sa.Column("precio_usd", sa.Float(), nullable=False),
        sa.Column("unidad_precio", sa.String(10), nullable=False),
        sa.Column("fuente_precio", sa.String(200), nullable=True),
        sa.Column("fecha_precio", sa.Date(), nullable=False),
        sa.Column("cultivos", sa.String(200), nullable=True),
        sa.Column("observaciones_marbete", sa.Text(), nullable=True),
        sa.UniqueConstraint("producto_id", "marca", "concentracion", "variante",
                            name="uq_presentacion_producto"),
    )
    op.create_index("ix_presentaciones_productos_producto_id", "presentaciones_productos", ["producto_id"])


def downgrade() -> None:
    op.drop_table("presentaciones_productos")
