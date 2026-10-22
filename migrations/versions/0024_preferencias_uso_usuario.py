"""preferencias de uso del usuario (HU-R4-12)

Revision ID: 0024
Revises: 0023
Create Date: 2026-10-14

Valores por defecto que el usuario configura una vez desde su perfil para
no elegirlos en cada análisis: índice preferido, unidad de área preferida
y producto fitosanitario habitual. Las tres columnas son nullable — ningún
usuario existente tiene preferencias cargadas todavía.

indice_preferido reutiliza el enum Postgres `indiceenum` ya creado en la
migración 0011 (create_type=False) en vez de crear uno nuevo.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import UUID

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None

indiceenum_columna = postgresql.ENUM(
    "ndvi", "ndre", "savi", "exg", "gndvi", name="indiceenum", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()

    bind.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE unidadareaenum AS ENUM ('ha', 'acre');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """))

    op.add_column("usuarios", sa.Column("indice_preferido", indiceenum_columna, nullable=True))
    op.add_column(
        "usuarios",
        sa.Column("unidad_area_preferida", postgresql.ENUM(
            "ha", "acre", name="unidadareaenum", create_type=False
        ), nullable=True),
    )
    op.add_column(
        "usuarios",
        sa.Column(
            "producto_habitual_id",
            UUID(as_uuid=True),
            sa.ForeignKey("productos_fitosanitarios.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("usuarios", "producto_habitual_id")
    op.drop_column("usuarios", "unidad_area_preferida")
    op.drop_column("usuarios", "indice_preferido")
    op.execute("DROP TYPE IF EXISTS unidadareaenum")
