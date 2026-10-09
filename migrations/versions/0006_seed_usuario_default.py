"""seed usuario default para desarrollo

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-01

Usuario por defecto (desarrollo, sin ADMIN_EMAIL/ADMIN_PASSWORD en el entorno):
  email:    admin@agronexo.com
  password: password123

En producción, setear ADMIN_EMAIL/ADMIN_PASSWORD en .env.prod (ver
.env.prod.example) antes del primer deploy — de lo contrario esta migración
sigue sembrando las credenciales de desarrollo (HU-R4-06).
"""

import os

import bcrypt
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

_DEFAULT_EMAIL = "admin@agronexo.com"
_DEFAULT_PASSWORD = "password123"


def upgrade() -> None:
    # bcrypt directo, no passlib — ver app/auth/service.py::hash_password
    # (passlib==1.7.4 no es compatible con bcrypt>=5, y esta migración
    # correría igual en cualquier `alembic upgrade head` desde cero).
    # Mismo formato de hash que generaba passlib, no afecta bases ya seedeadas.
    email = os.environ.get("ADMIN_EMAIL", _DEFAULT_EMAIL)
    password = os.environ.get("ADMIN_PASSWORD", _DEFAULT_PASSWORD)
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    op.execute(
        f"""
        INSERT INTO usuarios (email, nombre, hashed_password, is_active)
        VALUES ('{email}', 'Admin', '{hashed}', TRUE)
        ON CONFLICT (email) DO NOTHING
        """
    )


def downgrade() -> None:
    email = os.environ.get("ADMIN_EMAIL", _DEFAULT_EMAIL)
    op.execute(f"DELETE FROM usuarios WHERE email = '{email}'")
