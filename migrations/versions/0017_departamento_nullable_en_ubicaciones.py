"""departamento pasa a opcional en ubicaciones

Revision ID: 0017
Revises: 0016
Create Date: 2026-08-11

Requerir departamento junto con provincia resultó poco realista — la
mayoría de los usuarios sabe su provincia y localidad, no necesariamente
el departamento administrativo oficial (ej. "Resistencia" es la localidad,
el departamento es "San Fernando"). Solo provincia queda obligatoria si se
carga algo de ubicación.
"""

from alembic import op
import sqlalchemy as sa

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("ubicaciones", "departamento", nullable=True)


def downgrade() -> None:
    op.execute("UPDATE ubicaciones SET departamento = '(sin especificar)' WHERE departamento IS NULL")
    op.alter_column("ubicaciones", "departamento", nullable=False)
