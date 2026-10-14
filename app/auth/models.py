import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.lotes.models import IndiceEnum


class UnidadAreaEnum(str, enum.Enum):
    ha = "ha"
    acre = "acre"


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )

    # Perfil (HU-R4-10) — usado para identificar al aplicador en el PDF
    # ejecutivo y la orden de trabajo. avatar_key/logo_empresa_key guardan
    # la clave del objeto en MinIO, no una URL (mismo patrón que
    # lotes.geojson_key) — la URL firmada se resuelve al servir /auth/me.
    avatar_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    cuit: Mapped[str | None] = mapped_column(String(13), nullable=True)
    telefono_contacto: Mapped[str | None] = mapped_column(String(30), nullable=True)
    matricula_aplicador: Mapped[str | None] = mapped_column(String(50), nullable=True)
    nombre_empresa: Mapped[str | None] = mapped_column(String(200), nullable=True)
    logo_empresa_key: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Preferencias de uso (HU-R4-12) — valores por defecto para no elegirlos
    # en cada análisis. producto_habitual_id no tiene relationship porque el
    # frontend ya resuelve el nombre contra el catálogo que trae de
    # GET /productos-fitosanitarios.
    indice_preferido: Mapped[IndiceEnum | None] = mapped_column(Enum(IndiceEnum), nullable=True)
    unidad_area_preferida: Mapped[UnidadAreaEnum | None] = mapped_column(Enum(UnidadAreaEnum), nullable=True)
    producto_habitual_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("productos_fitosanitarios.id", ondelete="SET NULL"), nullable=True
    )

    lotes: Mapped[list] = relationship("Lote", back_populates="usuario", lazy="select", foreign_keys="[Lote.usuario_id]")
