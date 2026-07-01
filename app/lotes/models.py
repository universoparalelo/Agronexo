import enum
import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CultivoEnum(str, enum.Enum):
    soja = "soja"
    maiz = "maiz"
    algodon = "algodon"
    sorgo = "sorgo"


class SensorEnum(str, enum.Enum):
    sentinel2 = "sentinel2"
    dji_mavic3 = "dji_mavic3"


class EstadoVueloEnum(str, enum.Enum):
    pendiente = "pendiente"
    procesando = "procesando"
    completado = "completado"
    error = "error"


class Lote(Base):
    __tablename__ = "lotes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4()
    )
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    cultivo: Mapped[CultivoEnum] = mapped_column(Enum(CultivoEnum), nullable=False)
    estadio_fenologico: Mapped[str | None] = mapped_column(String(10), nullable=True)
    geometry: Mapped[object] = mapped_column(
        Geometry(geometry_type="POLYGON", srid=4326, spatial_index=True), nullable=True
    )
    area_ha: Mapped[float | None] = mapped_column(Float, nullable=True)

    usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    usuario: Mapped["Usuario"] = relationship("Usuario", back_populates="lotes")
    vuelos: Mapped[list["Vuelo"]] = relationship("Vuelo", back_populates="lote")


class Vuelo(Base):
    __tablename__ = "vuelos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4()
    )
    lote_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lotes.id", ondelete="RESTRICT"), nullable=False
    )
    fecha_vuelo: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sensor: Mapped[SensorEnum] = mapped_column(Enum(SensorEnum), nullable=False)
    archivo_original: Mapped[str | None] = mapped_column(String(500), nullable=True)
    estado: Mapped[EstadoVueloEnum] = mapped_column(
        Enum(EstadoVueloEnum), nullable=False, default=EstadoVueloEnum.pendiente
    )
    task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_detalle: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lote: Mapped["Lote"] = relationship("Lote", back_populates="vuelos")
