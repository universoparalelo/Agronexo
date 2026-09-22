"""crear tabla cultivos y mover cultivo/variedad/fecha_siembra/estadio fuera de lotes

Revision ID: 0020
Revises: 0019
Create Date: 2026-09-20

Un lote pasa a ser solo la parcela (nombre, suelo, límite). Lo que se siembra
en él vive en `cultivos` (tipo_cultivo, variedad, fecha_siembra,
fecha_cosecha) y cada vuelo apunta al cultivo que estaba en pie
(vuelos.cultivo_id).

Backfill: cada lote existente genera un cultivo con sus datos actuales y todos
sus vuelos quedan asociados a él. lotes.estadio_fenologico era el fallback del
diagnóstico cuando el vuelo no tenía el suyo — se copia a los vuelos que no lo
tenían para que los diagnósticos ya calculados no cambien de criterio.

El tipo enum `cultivoenum` se reutiliza para cultivos.tipo_cultivo (no se
elimina al soltar la columna vieja de lotes).
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    cultivo_enum = postgresql.ENUM(name="cultivoenum", create_type=False)

    op.create_table(
        "cultivos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("lote_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lotes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("tipo_cultivo", cultivo_enum, nullable=False),
        sa.Column("variedad", sa.String(100), nullable=True),
        sa.Column("fecha_siembra", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fecha_cosecha", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_cultivos_lote_id", "cultivos", ["lote_id"])

    op.add_column(
        "vuelos",
        sa.Column("cultivo_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cultivos.id", ondelete="RESTRICT"), nullable=True),
    )
    op.create_index("ix_vuelos_cultivo_id", "vuelos", ["cultivo_id"])

    op.execute("""
        INSERT INTO cultivos (lote_id, tipo_cultivo, variedad, fecha_siembra, created_at)
        SELECT id, cultivo, variedad, fecha_siembra, created_at FROM lotes
    """)
    op.execute("""
        UPDATE vuelos v SET cultivo_id = c.id
        FROM cultivos c WHERE c.lote_id = v.lote_id
    """)
    op.execute("""
        UPDATE vuelos v SET estadio_fenologico = l.estadio_fenologico
        FROM lotes l
        WHERE l.id = v.lote_id AND v.estadio_fenologico IS NULL AND l.estadio_fenologico IS NOT NULL
    """)

    op.drop_column("lotes", "cultivo")
    op.drop_column("lotes", "variedad")
    op.drop_column("lotes", "fecha_siembra")
    op.drop_column("lotes", "estadio_fenologico")


def downgrade() -> None:
    cultivo_enum = postgresql.ENUM(name="cultivoenum", create_type=False)

    op.add_column("lotes", sa.Column("estadio_fenologico", sa.String(30), nullable=True))
    op.add_column("lotes", sa.Column("fecha_siembra", sa.DateTime(timezone=True), nullable=True))
    op.add_column("lotes", sa.Column("variedad", sa.String(100), nullable=True))
    op.add_column("lotes", sa.Column("cultivo", cultivo_enum, nullable=True))

    # Se restaura el cultivo más reciente de cada lote; lotes sin cultivos quedan en soja
    # (la columna original era NOT NULL).
    op.execute("""
        UPDATE lotes l SET cultivo = c.tipo_cultivo, variedad = c.variedad, fecha_siembra = c.fecha_siembra
        FROM (
            SELECT DISTINCT ON (lote_id) lote_id, tipo_cultivo, variedad, fecha_siembra
            FROM cultivos WHERE deleted_at IS NULL ORDER BY lote_id, created_at DESC
        ) c WHERE c.lote_id = l.id
    """)
    op.execute("UPDATE lotes SET cultivo = 'soja' WHERE cultivo IS NULL")
    op.alter_column("lotes", "cultivo", nullable=False)

    op.drop_index("ix_vuelos_cultivo_id", table_name="vuelos")
    op.drop_column("vuelos", "cultivo_id")
    op.drop_index("ix_cultivos_lote_id", table_name="cultivos")
    op.drop_table("cultivos")
