"""crear tabla productos_fitosanitarios con catálogo inicial

Revision ID: 0015
Revises: 0014
Create Date: 2026-08-30

Migra el catálogo de 21 productos que estaba hardcodeado en
app/diagnostico/productos.py a una tabla en BD para permitir
extensión futura (CRUD, filtros por cultivo, dosis).
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None

SEED_PRODUCTOS = [
    ("Glifosato", "herbicida", "interferencia_vegetacion"),
    ("2,4-D", "herbicida", "interferencia_vegetacion"),
    ("Atrazina", "herbicida", "interferencia_vegetacion"),
    ("Cletodim", "herbicida", "interferencia_vegetacion"),
    ("Imazetapir", "herbicida", "interferencia_vegetacion"),
    ("Azoxistrobina", "fungicida", "estres_biotico_fungico"),
    ("Trifloxistrobina", "fungicida", "estres_biotico_fungico"),
    ("Mancozeb", "fungicida", "estres_biotico_fungico"),
    ("Tebuconazol", "fungicida", "estres_biotico_fungico"),
    ("Carbendazim", "fungicida", "estres_biotico_fungico"),
    ("Clorpirifos", "insecticida", "estres_biotico_insecto"),
    ("Lambda-cihalotrina", "insecticida", "estres_biotico_insecto"),
    ("Imidacloprid", "insecticida", "estres_biotico_insecto"),
    ("Spinosad", "insecticida", "estres_biotico_insecto"),
    ("Thiamethoxam", "insecticida", "estres_biotico_insecto"),
    ("Urea 46% N", "fertilizante", "estres_nutricional_nitrogeno"),
    ("Sulfato de Magnesio", "fertilizante_foliar", "estres_nutricional_micro"),
    ("Boro foliar 17%", "fertilizante_foliar", "estres_nutricional_micro"),
    ("Superfosfato Triple 46%", "fertilizante", "estres_nutricional_fosforo"),
    ("Ethephon 48%", "acelerador_madurez", "madurez_temprana_diferencial"),
    ("Tiidiazurón + Diurón", "defoliante", "madurez_temprana_diferencial"),
]


def upgrade() -> None:
    bind = op.get_bind()

    bind.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE tipoproductoenum AS ENUM (
                'herbicida', 'fungicida', 'insecticida', 'fertilizante',
                'fertilizante_foliar', 'acelerador_madurez', 'defoliante'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """))

    bind.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE causaindiceenum AS ENUM (
                'sin_problema_detectado', 'interferencia_vegetacion',
                'estres_biotico_fungico', 'estres_biotico_insecto',
                'estres_nutricional_nitrogeno', 'estres_nutricional_micro',
                'estres_nutricional_fosforo', 'estres_hidrico',
                'madurez_temprana_diferencial', 'vigor_excesivo'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """))

    op.execute("""
        CREATE TABLE productos_fitosanitarios (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            nombre VARCHAR(200) NOT NULL,
            tipo tipoproductoenum NOT NULL,
            causa_indice causaindiceenum NOT NULL,
            dosis_referencia FLOAT,
            unidad VARCHAR(50)
        )
    """)

    op.create_index("ix_productos_causa_indice", "productos_fitosanitarios", ["causa_indice"])

    values = ", ".join(
        f"('{nombre}', '{tipo}'::tipoproductoenum, '{causa}'::causaindiceenum)"
        for nombre, tipo, causa in SEED_PRODUCTOS
    )
    op.execute(
        f"INSERT INTO productos_fitosanitarios (nombre, tipo, causa_indice) VALUES {values}"
    )


def downgrade() -> None:
    op.drop_table("productos_fitosanitarios")
    op.execute("DROP TYPE IF EXISTS tipoproductoenum")
    op.execute("DROP TYPE IF EXISTS causaindiceenum")
