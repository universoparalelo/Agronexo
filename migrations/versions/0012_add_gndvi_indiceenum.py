"""agregar 'gndvi' al enum indiceenum

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-27

GNDVI se suma como quinto índice para habilitar la regla R21 del motor de
diagnóstico (enfermedad tardía en soja, estadios R3-R5) — es el único caso
donde el NDVI ya está saturado y se necesita GNDVI para distinguir pérdida
de clorofila. ALTER TYPE ... ADD VALUE debe correr fuera de una transacción
implícita (requisito de Postgres), de ahí el autocommit_block.
"""

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE indiceenum ADD VALUE IF NOT EXISTS 'gndvi'")


def downgrade() -> None:
    # Postgres no soporta quitar un valor de un enum directamente. Revertir
    # requeriría recrear el tipo (rename + create + migrar columnas + drop),
    # lo cual es riesgoso si ya hay filas con indice='gndvi'. Se deja como
    # no-op documentado, igual que la práctica estándar de Alembic para este caso.
    pass
