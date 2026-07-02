"""seed usuario default para desarrollo

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-01

Usuario por defecto:
  email:    admin@agronexo.com
  password: password123
"""

from alembic import op
from passlib.context import CryptContext

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def upgrade() -> None:
    hashed = _pwd_context.hash("password123")
    op.execute(
        f"""
        INSERT INTO usuarios (email, nombre, hashed_password, is_active)
        VALUES ('admin@agronexo.com', 'Admin', '{hashed}', TRUE)
        ON CONFLICT (email) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM usuarios WHERE email = 'admin@agronexo.com'")
