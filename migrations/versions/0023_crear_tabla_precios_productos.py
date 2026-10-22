"""crear tabla precios_productos (HU-R4-05)

Revision ID: 0023
Revises: 0022
Create Date: 2026-10-13

Modelo de datos para costos de fitosanitarios. Soporta dos tipos de precio
que coexisten por producto:
  - "referencia": valores del relevamiento inicial (docs/precios_fitosanitarios_referencia.md)
  - "usuario": precio real pagado por el productor/asesor, con fecha de compra

HU-R4-11 (ahorro comparativo) usará precio_usuario si existe con fecha
reciente (< 90 días), y precio_referencia como fallback.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None

SEED_PRECIOS = [
    # (nombre_producto, precio_usd, unidad, fuente, tipo)
    ("Glifosato",              3.50,  "L",   "CASAFE Lista 2026-S1; AgroNEA Resistencia",                "referencia"),
    ("2,4-D",                  3.80,  "L",   "CASAFE Lista 2026-S1",                                     "referencia"),
    ("Atrazina",               5.20,  "L",   "CASAFE Lista 2026-S1; Agrogen NEA",                        "referencia"),
    ("Cletodim",              15.00,  "L",   "CASAFE Lista 2026-S1",                                     "referencia"),
    ("Imazetapir",            22.00,  "L",   "INTA EEA Sáenz Peña 2026",                                 "referencia"),
    ("Azoxistrobina",         28.00,  "L",   "CASAFE Lista 2026-S1; Syngenta AMISTAR",                   "referencia"),
    ("Trifloxistrobina",      48.00,  "kg",  "CASAFE Lista 2026-S1; Bayer NATIVO equivalente",           "referencia"),
    ("Mancozeb",               5.50,  "kg",  "CASAFE Lista 2026-S1",                                     "referencia"),
    ("Tebuconazol",           18.00,  "L",   "CASAFE Lista 2026-S1; Bayer FOLICUR",                      "referencia"),
    ("Carbendazim",           10.00,  "L",   "INTA EEA Reconquista 2026; distribuidoras regionales",     "referencia"),
    ("Clorpirifos",            6.50,  "L",   "CASAFE Lista 2026-S1",                                     "referencia"),
    ("Lambda-cihalotrina",    25.00,  "L",   "CASAFE Lista 2026-S1; Syngenta KARATE",                    "referencia"),
    ("Imidacloprid",          30.00,  "L",   "CASAFE Lista 2026-S1; Bayer CONFIDOR",                     "referencia"),
    ("Spinosad",              95.00,  "L",   "Dow/Corteva TRACER; INTA precio referencia",               "referencia"),
    ("Thiamethoxam",          45.00,  "kg",  "CASAFE Lista 2026-S1; Syngenta ACTARA",                    "referencia"),
    ("Urea 46% N",             0.45,  "kg",  "CIAFA 2026-T3; Profertil lista de precios",                "referencia"),
    ("Sulfato de Magnesio",    0.80,  "kg",  "K+S Kali EPSO Top; INTA NEA 2026",                         "referencia"),
    ("Boro foliar 17%",        4.20,  "L",   "Distribuidoras NEA (estimado por principio activo)",        "referencia"),
    ("Superfosfato Triple 46%",0.50,  "kg",  "CIAFA 2026-T3; Profertil lista de precios",                "referencia"),
    ("Ethephon 48%",          28.00,  "L",   "INTA EEA Sáenz Peña 2026; BASF ETHREL",                    "referencia"),
    ("Tiidiazurón + Diurón",  38.00,  "kg",  "INTA EEA Sáenz Peña 2026; Bayer DROPP equivalente",        "referencia"),
]


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        "precios_productos",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("producto_id", UUID(as_uuid=True),
                  sa.ForeignKey("productos_fitosanitarios.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("precio_usd", sa.Float(), nullable=False),
        sa.Column("unidad", sa.String(10), nullable=False),
        sa.Column("fuente", sa.String(200), nullable=True),
        sa.Column("fecha", sa.Date(), nullable=False),
        # "referencia" = valor del relevamiento inicial
        # "usuario"    = precio real cargado por el productor/asesor
        sa.Column("tipo", sa.String(20), nullable=False),
    )

    op.create_index("ix_precios_productos_producto_id", "precios_productos", ["producto_id"])
    op.create_index("ix_precios_productos_tipo_fecha",  "precios_productos", ["tipo", "fecha"])

    for nombre, precio, unidad, fuente, tipo in SEED_PRECIOS:
        bind.execute(sa.text("""
            INSERT INTO precios_productos (id, producto_id, precio_usd, unidad, fuente, fecha, tipo)
            SELECT uuid_generate_v4(), p.id, :precio, :unidad, :fuente, '2026-10-13', :tipo
            FROM productos_fitosanitarios p
            WHERE p.nombre = :nombre
        """), {"nombre": nombre, "precio": precio, "unidad": unidad,
               "fuente": fuente, "tipo": tipo})


def downgrade() -> None:
    op.drop_table("precios_productos")
