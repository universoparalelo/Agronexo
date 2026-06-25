from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import schemas, service
from app.auth.dependencies import get_current_user
from app.auth.models import Usuario
from app.core.database import get_db

router = APIRouter()


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
    from jose import JWTError, jwt
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
    except JWTError:
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
    return current_user
