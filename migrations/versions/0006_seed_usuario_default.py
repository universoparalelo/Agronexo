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

from alembic import op
from passlib.context import CryptContext

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_DEFAULT_EMAIL = "admin@agronexo.com"
_DEFAULT_PASSWORD = "password123"


def upgrade() -> None:
    email = os.environ.get("ADMIN_EMAIL", _DEFAULT_EMAIL)
    password = os.environ.get("ADMIN_PASSWORD", _DEFAULT_PASSWORD)
    hashed = _pwd_context.hash(password)
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
