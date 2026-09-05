"""crear tabla diagnosticos para persistir el resultado por vuelo

Revision ID: 0016
Revises: 0015
Create Date: 2026-09-05

Hasta ahora GET .../diagnostico recalculaba todo en cada request (decisión
de alcance documentada en docs/release-v1.0.0.md "Problemas abiertos" #2).
Un vuelo tiene ahora a lo sumo un diagnóstico guardado (UNIQUE en vuelo_id):
la primera vez que se pide se calcula y se guarda acá; las siguientes veces
se devuelve lo guardado sin recalcular. "Recalcular" sobrescribe la fila
existente en vez de acumular historial — el historial multi-vuelo persistido
sigue siendo alcance de release 4 (RFGL-03), esto solo evita recalcular en
cada GET.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "diagnosticos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("vuelo_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vuelos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resultado", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("calculado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_diagnosticos_vuelo_id", "diagnosticos", ["vuelo_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_diagnosticos_vuelo_id", table_name="diagnosticos")
    op.drop_table("diagnosticos")
