"""crear tabla revisiones_diagnostico (RFDR-04 — criterio técnico del agrónomo)

Revision ID: 0026
Revises: 0025
Create Date: 2026-10-23

Una revisión vigente por zona de un vuelo (UNIQUE vuelo_id + zona_id): el
agrónomo acepta, modifica o rechaza la causa sugerida por el motor de
reglas. `evidencia` (JSONB) es el caso etiquetado con el que se ajusta el
motor probabilístico (app/diagnostico/bayes.py).
"""

from alembic import op
import sqlalchemy as sa

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE decisionrevisionenum AS ENUM ('aceptado', 'modificado', 'rechazado');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """))
    op.execute("""
        CREATE TABLE revisiones_diagnostico (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            vuelo_id UUID NOT NULL REFERENCES vuelos(id) ON DELETE CASCADE,
            zona_id INTEGER NOT NULL,
            regla_id VARCHAR(5) NOT NULL,
            causa_sugerida VARCHAR(40) NOT NULL,
            decision decisionrevisionenum NOT NULL,
            causa_confirmada VARCHAR(40),
            comentario TEXT,
            evidencia JSONB NOT NULL,
            motor_version VARCHAR(20),
            usuario_id UUID NOT NULL REFERENCES usuarios(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (vuelo_id, zona_id)
        )
    """)


def downgrade() -> None:
    op.drop_table("revisiones_diagnostico")
    op.execute("DROP TYPE IF EXISTS decisionrevisionenum")
