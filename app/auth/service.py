from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import Usuario
from app.auth.schemas import RegisterRequest
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _crear_token(data: dict, expires_delta: timedelta) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + expires_delta
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def crear_access_token(usuario_id: str) -> str:
    return _crear_token(
        {"sub": usuario_id, "type": "access"},
        timedelta(minutes=settings.access_token_expire_minutes),
    )


def crear_refresh_token(usuario_id: str) -> str:
    return _crear_token(
        {"sub": usuario_id, "type": "refresh"},
        timedelta(days=settings.refresh_token_expire_days),
    )


async def crear_usuario(db: AsyncSession, data: RegisterRequest) -> Usuario:
    usuario = Usuario(
        email=data.email,
        nombre=data.nombre,
        hashed_password=hash_password(data.password),
    )
    db.add(usuario)
    await db.commit()
    await db.refresh(usuario)
    return usuario


async def obtener_usuario_por_email(db: AsyncSession, email: str) -> Usuario | None:
    result = await db.execute(select(Usuario).where(Usuario.email == email))
    return result.scalar_one_or_none()


async def autenticar_usuario(db: AsyncSession, email: str, password: str) -> Usuario | None:
    usuario = await obtener_usuario_por_email(db, email)
    if not usuario:
        return None
    if not verify_password(password, usuario.hashed_password):
        return None
    if not usuario.is_active:
        return None
    return usuario
