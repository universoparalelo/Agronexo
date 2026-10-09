"""trazabilidad completa del analisis (HU-R4-02)

Revision ID: 0021
Revises: 0020
Create Date: 2026-09-30

Agrega lo que faltaba para justificar una prescripcion ante el productor o
un control segun la Ley 6.312: quien subio cada vuelo, que metodo de
umbral y que mapeo de bandas se usaron en el NDVI primario (ya existian
para los indices adicionales en analisis_indices), y que version del
motor de reglas genero cada diagnostico guardado.

Backfill: subido_por_id no se puede reconstruir con certeza para vuelos
viejos (no habia trazabilidad) — se aproxima con el dueño del lote, que
es quien podia subir vuelos en la practica. motor_version se completa con
"1.0.0" para los diagnosticos ya calculados, unica version que existio
hasta esta migracion.

metodo_umbral y mapeo_bandas SI se pueden reconstruir con certeza para
vuelos completados: ningun endpoint permitia elegir otro metodo para el
NDVI primario (siempre "fijo", ver workers/gis/tasks.py::procesar_vuelo),
y el mapeo de bandas es una funcion pura de vuelos.sensor (ver
workers/gis/band_mapping.py::MAPEO_SENSORES) — se congela ese valor acá,
no es una aproximación.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "vuelos",
        sa.Column("subido_por_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column("vuelos", sa.Column("metodo_umbral", sa.String(20), nullable=True))
    op.add_column("vuelos", sa.Column("mapeo_bandas", postgresql.JSONB(), nullable=True))
    op.create_index("ix_vuelos_subido_por_id", "vuelos", ["subido_por_id"])

    op.add_column("diagnosticos", sa.Column("motor_version", sa.String(20), nullable=True))

    op.execute("""
        UPDATE vuelos v SET subido_por_id = l.usuario_id
        FROM lotes l WHERE l.id = v.lote_id AND v.subido_por_id IS NULL
    """)
    op.execute("UPDATE diagnosticos SET motor_version = '1.0.0' WHERE motor_version IS NULL")

    op.execute("""
        UPDATE vuelos SET metodo_umbral = 'fijo'
        WHERE estado = 'completado' AND metodo_umbral IS NULL
    """)
    # Mismos números que workers/gis/band_mapping.py::MAPEO_SENSORES — si ese
    # dict cambia en el futuro, esto queda como estaba, que es la idea.
    op.execute("""
        UPDATE vuelos SET mapeo_bandas = '{"BLUE": 2, "GREEN": 3, "RED": 4, "RE": 5, "NIR": 8}'::jsonb
        WHERE estado = 'completado' AND sensor = 'sentinel2' AND mapeo_bandas IS NULL
    """)
    op.execute("""
        UPDATE vuelos SET mapeo_bandas = '{"BLUE": null, "GREEN": 1, "RED": 2, "RE": 3, "NIR": 4}'::jsonb
        WHERE estado = 'completado' AND sensor = 'dji_mavic3' AND mapeo_bandas IS NULL
    """)


def downgrade() -> None:
    op.drop_column("diagnosticos", "motor_version")

    op.drop_index("ix_vuelos_subido_por_id", table_name="vuelos")
    op.drop_column("vuelos", "mapeo_bandas")
    op.drop_column("vuelos", "metodo_umbral")
    op.drop_column("vuelos", "subido_por_id")
