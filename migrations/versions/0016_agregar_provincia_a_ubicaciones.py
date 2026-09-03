"""agregar provincia a ubicaciones

Revision ID: 0016
Revises: 0015
Create Date: 2026-08-11

La ubicación de un lote ahora es provincia + departamento + localidad
(antes solo departamento/localidad, ambiguo sin la provincia). Las filas
existentes se backfillean a 'chaco' — los datos de prueba cargados hasta
ahora (Resistencia, Sáenz Peña, etc.) son todos del Chaco.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None

PROVINCIAS = [
    "buenos_aires", "catamarca", "chaco", "chubut", "cordoba", "corrientes",
    "entre_rios", "formosa", "jujuy", "la_pampa", "la_rioja", "mendoza",
    "misiones", "neuquen", "rio_negro", "salta", "san_juan", "san_luis",
    "santa_cruz", "santa_fe", "santiago_del_estero", "tierra_del_fuego",
    "tucuman", "caba",
]

provinciaenum_creador = postgresql.ENUM(*PROVINCIAS, name="provinciaenum")
provinciaenum_columna = postgresql.ENUM(*PROVINCIAS, name="provinciaenum", create_type=False)


def upgrade() -> None:
    provinciaenum_creador.create(op.get_bind(), checkfirst=True)
    op.add_column("ubicaciones", sa.Column("provincia", provinciaenum_columna, nullable=True))
    op.execute("UPDATE ubicaciones SET provincia = 'chaco' WHERE provincia IS NULL")
    op.alter_column("ubicaciones", "provincia", nullable=False)


def downgrade() -> None:
    op.drop_column("ubicaciones", "provincia")
    provinciaenum_creador.drop(op.get_bind(), checkfirst=True)
