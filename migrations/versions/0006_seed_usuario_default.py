"""seed usuario default para desarrollo

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-01

Usuario por defecto:
  email:    admin@agronexo.com
  password: password123
"""

import bcrypt
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # bcrypt directo, no passlib — ver app/auth/service.py::hash_password
    # (passlib==1.7.4 no es compatible con bcrypt>=5, y esta migración
    # correría igual en cualquier `alembic upgrade head` desde cero).
    # Mismo formato de hash que generaba passlib, no afecta bases ya seedeadas.
    hashed = bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode("utf-8")
    op.execute(
        f"""
        INSERT INTO usuarios (email, nombre, hashed_password, is_active)
        VALUES ('admin@agronexo.com', 'Admin', '{hashed}', TRUE)
        ON CONFLICT (email) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM usuarios WHERE email = 'admin@agronexo.com'")
