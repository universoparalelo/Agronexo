"""agregar estadio_fenologico a vuelos

Revision ID: 0017
Revises: 0016
Create Date: 2026-09-07

Hasta ahora estadio_fenologico vivía solo en lotes, cargado una única vez
al crear el lote y sin ninguna pantalla para actualizarlo — el motor de
diagnóstico (app/diagnostico/service.py) reutilizaba ese mismo valor
congelado para todos los vuelos futuros del lote, aunque el estadio real
del cultivo cambia semana a semana. Se agrega la misma columna a vuelos
(nullable) para poder cargarlo por análisis puntual; el valor del lote
queda como fallback cuando el vuelo no lo especifica.
"""

from alembic import op
import sqlalchemy as sa

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vuelos", sa.Column("estadio_fenologico", sa.String(30), nullable=True))


def downgrade() -> None:
    op.drop_column("vuelos", "estadio_fenologico")
