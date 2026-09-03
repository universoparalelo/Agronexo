"""crear tabla cultivos para trackear ciclos de cultivo por lote

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-10

Un lote es la parcela física; un cultivo es una campaña sobre esa parcela
(siembra → cosecha). Un lote acumula varios cultivos a lo largo del tiempo,
por eso viven en tabla aparte con su propio ciclo de fechas. El flag `activo`
identifica el ciclo vigente sin tener que comparar fechas en cada consulta.

Reutiliza el tipo `cultivoenum` creado en 0002 para lotes.cultivo — no se
crea de nuevo (create_type=False).
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

cultivoenum_columna = postgresql.ENUM("soja", "maiz", "algodon", "sorgo", name="cultivoenum", create_type=False)


def upgrade() -> None:
    op.create_table(
        "cultivos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("lote_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lotes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("cultivo", cultivoenum_columna, nullable=False),
        sa.Column("estadio_fenologico", sa.String(10), nullable=True),
        sa.Column("fecha_siembra", sa.Date(), nullable=False),
        sa.Column("fecha_cosecha_estimada", sa.Date(), nullable=True),
        sa.Column("fecha_cosecha_real", sa.Date(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("idx_cultivos_lote_id", "cultivos", ["lote_id"])


def downgrade() -> None:
    op.drop_index("idx_cultivos_lote_id", table_name="cultivos")
    op.drop_table("cultivos")
