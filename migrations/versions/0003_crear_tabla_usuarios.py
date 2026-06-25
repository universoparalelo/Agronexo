"""crear tabla usuarios

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-25
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", postgresql.UUID(as_uuid=False), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_usuarios_email", "usuarios", ["email"], unique=True)

    # Agregar FK desde lotes.usuario_id hacia usuarios.id
    op.create_foreign_key(
        "fk_lotes_usuario_id",
        "lotes", "usuarios",
        ["usuario_id"], ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_lotes_usuario_id", "lotes", type_="foreignkey")
    op.drop_index("idx_usuarios_email", table_name="usuarios")
    op.drop_table("usuarios")
