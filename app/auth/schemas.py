from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    nombre: str
    password: str

    @field_validator("password")
    @classmethod
    def password_minlen(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        return v

    @field_validator("nombre")
    @classmethod
    def nombre_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("El nombre no puede estar vacío")
        return v.strip()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UsuarioResponse(BaseModel):
    id: str
    email: str
    nombre: str
    is_active: bool
    created_at: datetime
    descripcion: str | None = None
    cuit: str | None = None
    telefono_contacto: str | None = None
    matricula_aplicador: str | None = None
    nombre_empresa: str | None = None
    # URLs firmadas resueltas en el router a partir de avatar_key/logo_empresa_key
    # — no son columnas del modelo, por eso no viajan con from_attributes.
    avatar_url: str | None = None
    logo_empresa_url: str | None = None

    model_config = {"from_attributes": True}


_CUIT_RE = r"^\d{2}-\d{8}-\d{1}$"


class PerfilUpdateRequest(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    cuit: str | None = None
    telefono_contacto: str | None = None
    matricula_aplicador: str | None = None
    nombre_empresa: str | None = None

    @field_validator("nombre")
    @classmethod
    def nombre_nonempty(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("El nombre no puede estar vacío")
        return v.strip() if v is not None else v

    @field_validator("cuit")
    @classmethod
    def cuit_formato(cls, v: str | None) -> str | None:
        import re

        if v is not None and v != "" and not re.match(_CUIT_RE, v):
            raise ValueError("El CUIT debe tener el formato XX-XXXXXXXX-X")
        return v or None


class CambioPasswordRequest(BaseModel):
    password_actual: str
    password_nueva: str

    @field_validator("password_nueva")
    @classmethod
    def password_minlen(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        return v
