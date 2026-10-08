"""personalizacion de perfil del usuario (HU-R4-10)

Revision ID: 0022
Revises: 0021
Create Date: 2026-10-08

Agrega los campos de perfil/empresa que RFSA-01..04 necesitan para
identificar al aplicador en el PDF ejecutivo y la orden de trabajo:
avatar, descripcion, CUIT, telefono de contacto, matricula del aplicador,
nombre de empresa y logo de empresa. Todos nullable — el usuario sembrado
en 0006 y cualquier cuenta existente no tienen estos datos cargados.

avatar_key / logo_empresa_key guardan la CLAVE del objeto en MinIO (mismo
patron que lotes.geojson_key / vuelos.geojson_key), no una URL — la URL
firmada se resuelve en el momento de la request via presigned_url().
"""

from alembic import op
import sqlalchemy as sa

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("usuarios", sa.Column("avatar_key", sa.String(500), nullable=True))
    op.add_column("usuarios", sa.Column("descripcion", sa.Text(), nullable=True))
    op.add_column("usuarios", sa.Column("cuit", sa.String(13), nullable=True))
    op.add_column("usuarios", sa.Column("telefono_contacto", sa.String(30), nullable=True))
    op.add_column("usuarios", sa.Column("matricula_aplicador", sa.String(50), nullable=True))
    op.add_column("usuarios", sa.Column("nombre_empresa", sa.String(200), nullable=True))
    op.add_column("usuarios", sa.Column("logo_empresa_key", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("usuarios", "logo_empresa_key")
    op.drop_column("usuarios", "nombre_empresa")
    op.drop_column("usuarios", "matricula_aplicador")
    op.drop_column("usuarios", "telefono_contacto")
    op.drop_column("usuarios", "cuit")
    op.drop_column("usuarios", "descripcion")
    op.drop_column("usuarios", "avatar_key")
