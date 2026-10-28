from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.auth import schemas, service
from app.auth.dependencies import get_current_user
from app.auth.models import Usuario
from app.auth.validator import validar_archivo_imagen
from app.core.database import get_db
from app.core.storage import presigned_url, upload_bytes

router = APIRouter()

_CONTENT_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}


async def _construir_respuesta_perfil(usuario: Usuario) -> schemas.UsuarioResponse:
    """Resuelve avatar_key/logo_empresa_key a URLs firmadas para la response.

    Son calculadas, no columnas — se resuelven acá en vez de en el schema
    porque presigned_url() pega contra MinIO y Pydantic no puede ser async.
    """
    avatar_url = await run_in_threadpool(presigned_url, usuario.avatar_key) if usuario.avatar_key else None
    logo_url = await run_in_threadpool(presigned_url, usuario.logo_empresa_key) if usuario.logo_empresa_key else None
    data = schemas.UsuarioResponse.model_validate(usuario).model_dump()
    data["avatar_url"] = avatar_url
    data["logo_empresa_url"] = logo_url
    return schemas.UsuarioResponse(**data)


@router.post("/register", response_model=schemas.UsuarioResponse, status_code=status.HTTP_201_CREATED)
async def register(data: schemas.RegisterRequest, db: AsyncSession = Depends(get_db)):
    existente = await service.obtener_usuario_por_email(db, data.email)
    if existente:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El email ya está registrado")
    return await service.crear_usuario(db, data)


@router.post("/login", response_model=schemas.TokenResponse)
async def login(data: schemas.LoginRequest, db: AsyncSession = Depends(get_db)):
    usuario = await service.autenticar_usuario(db, data.email, data.password)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return schemas.TokenResponse(
        access_token=service.crear_access_token(usuario.id),
        refresh_token=service.crear_refresh_token(usuario.id),
    )


@router.post("/refresh", response_model=schemas.TokenResponse)
async def refresh(data: dict, db: AsyncSession = Depends(get_db)):
    import jwt
    from app.core.config import settings
    from sqlalchemy import select

    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token inválido o expirado",
    )
    try:
        payload = jwt.decode(data.get("refresh_token", ""), settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        usuario_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        if usuario_id is None or token_type != "refresh":
            raise credentials_exc
    except jwt.InvalidTokenError:
        raise credentials_exc

    result = await db.execute(select(Usuario).where(Usuario.id == usuario_id))
    usuario = result.scalar_one_or_none()
    if usuario is None or not usuario.is_active:
        raise credentials_exc

    return schemas.TokenResponse(
        access_token=service.crear_access_token(usuario.id),
        refresh_token=service.crear_refresh_token(usuario.id),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout():
    # JWT es stateless — el cliente descarta los tokens.
    # Implementar blacklist en Redis si se requiere invalidación inmediata (Sprint futuro).
    return


@router.get("/me", response_model=schemas.UsuarioResponse)
async def me(current_user: Usuario = Depends(get_current_user)):
    return await _construir_respuesta_perfil(current_user)


@router.put("/me", response_model=schemas.UsuarioResponse)
async def actualizar_perfil(
    data: schemas.PerfilUpdateRequest,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    usuario = await service.actualizar_perfil(db, current_user, data)
    return await _construir_respuesta_perfil(usuario)


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def cambiar_password(
    data: schemas.CambioPasswordRequest,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await service.cambiar_password(db, current_user, data.password_actual, data.password_nueva)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/me/avatar", response_model=schemas.UsuarioResponse)
async def subir_avatar(
    archivo: UploadFile = File(...),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    contenido = await archivo.read()
    validar_archivo_imagen(archivo, contenido)
    ext = Path(archivo.filename or "").suffix.lower()
    key = f"{current_user.id}/perfil/avatar{ext}"
    await run_in_threadpool(upload_bytes, key, contenido, _CONTENT_TYPES[ext])
    usuario = await service.actualizar_avatar_key(db, current_user, key)
    return await _construir_respuesta_perfil(usuario)


@router.post("/me/logo-empresa", response_model=schemas.UsuarioResponse)
async def subir_logo_empresa(
    archivo: UploadFile = File(...),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    contenido = await archivo.read()
    validar_archivo_imagen(archivo, contenido)
    ext = Path(archivo.filename or "").suffix.lower()
    key = f"{current_user.id}/perfil/logo_empresa{ext}"
    await run_in_threadpool(upload_bytes, key, contenido, _CONTENT_TYPES[ext])
    usuario = await service.actualizar_logo_empresa_key(db, current_user, key)
    return await _construir_respuesta_perfil(usuario)
