from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import Usuario
from app.auth.schemas import PerfilUpdateRequest, RegisterRequest
from app.core.config import settings


# Se llama a bcrypt directo (no vía passlib) porque passlib==1.7.4 (sin
# mantenimiento) hace un self-test interno al primer hash/verify que
# bcrypt>=5 rechaza (ValueError: password cannot be longer than 72 bytes
# — el self-test, no la contraseña real). El formato del hash ($2b$...)
# es el mismo que ya genera passlib, así que las contraseñas existentes
# en la base siguen verificando sin migración.
def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


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


async def actualizar_perfil(db: AsyncSession, usuario: Usuario, data: PerfilUpdateRequest) -> Usuario:
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(usuario, campo, valor)
    await db.commit()
    await db.refresh(usuario)
    return usuario


async def cambiar_password(
    db: AsyncSession, usuario: Usuario, password_actual: str, password_nueva: str,
) -> None:
    if not verify_password(password_actual, usuario.hashed_password):
        raise ValueError("La contraseña actual es incorrecta")
    usuario.hashed_password = hash_password(password_nueva)
    await db.commit()


async def actualizar_avatar_key(db: AsyncSession, usuario: Usuario, key: str) -> Usuario:
    usuario.avatar_key = key
    await db.commit()
    await db.refresh(usuario)
    return usuario


async def actualizar_logo_empresa_key(db: AsyncSession, usuario: Usuario, key: str) -> Usuario:
    usuario.logo_empresa_key = key
    await db.commit()
    await db.refresh(usuario)
    return usuario


def resolver_datos_aplicador(usuario: Usuario) -> dict:
    """
    Arma el dict de perfil que consumen app.reportes.service y
    app.ordenes_trabajo.service para identificar al aplicador en el PDF
    (HU-R4-10). Sync y bloqueante porque descarga el logo de MinIO
    (storage.download_bytes) — se llama desde el router via
    run_in_threadpool, igual que generar_pdf_reporte/generar_pdf_orden_trabajo.
    """
    import base64

    from app.core.storage import download_bytes

    logo_base64 = None
    if usuario.logo_empresa_key:
        ext = usuario.logo_empresa_key.rsplit(".", 1)[-1].lower()
        content_type = "image/png" if ext == "png" else "image/jpeg"
        logo_bytes = download_bytes(usuario.logo_empresa_key)
        logo_base64 = f"data:{content_type};base64," + base64.b64encode(logo_bytes).decode("ascii")

    return {
        "nombre_empresa": usuario.nombre_empresa,
        "aplicador_nombre": usuario.nombre,
        "matricula_aplicador": usuario.matricula_aplicador,
        "aplicador_cuit": usuario.cuit,
        "aplicador_contacto": usuario.telefono_contacto,
        "logo_empresa_base64": logo_base64,
    }
