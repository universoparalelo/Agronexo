import enum
import uuid
from datetime import datetime, time

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Time, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CultivoEnum(str, enum.Enum):
    soja = "soja"
    maiz = "maiz"
    algodon = "algodon"
    sorgo = "sorgo"


class TipoSueloEnum(str, enum.Enum):
    arcilloso = "arcilloso"
    franco = "franco"
    franco_arcilloso = "franco_arcilloso"
    franco_arenoso = "franco_arenoso"
    arenoso = "arenoso"
    vertisol = "vertisol"
    otro = "otro"


class SensorEnum(str, enum.Enum):
    sentinel2 = "sentinel2"
    dji_mavic3 = "dji_mavic3"


class EstadoVueloEnum(str, enum.Enum):
    pendiente = "pendiente"
    procesando = "procesando"
    completado = "completado"
    error = "error"


class IndiceEnum(str, enum.Enum):
    ndvi = "ndvi"
    ndre = "ndre"
    savi = "savi"
    exg = "exg"
    gndvi = "gndvi"


class Lote(Base):
    __tablename__ = "lotes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4()
    )
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    cultivo: Mapped[CultivoEnum] = mapped_column(Enum(CultivoEnum), nullable=False)
    estadio_fenologico: Mapped[str | None] = mapped_column(String(30), nullable=True)
    variedad: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tipo_suelo: Mapped[TipoSueloEnum | None] = mapped_column(Enum(TipoSueloEnum), nullable=True)
    fecha_siembra: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
    hora_inicio: Mapped[time | None] = mapped_column(Time(), nullable=True)
    hora_fin: Mapped[time | None] = mapped_column(Time(), nullable=True)
    sensor: Mapped[SensorEnum] = mapped_column(Enum(SensorEnum), nullable=False)
    archivo_original: Mapped[str | None] = mapped_column(String(500), nullable=True)
    estado: Mapped[EstadoVueloEnum] = mapped_column(
        Enum(EstadoVueloEnum), nullable=False, default=EstadoVueloEnum.pendiente
    )
    task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_detalle: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    geojson_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    lote: Mapped["Lote"] = relationship("Lote", back_populates="vuelos")
    analisis_indices: Mapped[list["AnalisisIndice"]] = relationship(
        "AnalisisIndice", back_populates="vuelo"
    )


class AnalisisIndice(Base):
    """
    Análisis de UN índice adicional sobre un vuelo ya existente. El primer
    índice (NDVI) se calcula siempre al subir el vuelo y su resultado vive en
    vuelos.geojson_key/estado — este modelo es para índices que el usuario
    pide analizar DESPUÉS o EN PARALELO (NDRE, SAVI, ExG), cada uno con su
    propio ciclo de vida async (pendiente → procesando → completado/error),
    igual que un vuelo pero acotado a un índice puntual.
    """
    __tablename__ = "analisis_indices"
    __table_args__ = (
        UniqueConstraint("vuelo_id", "indice", name="uq_analisis_indices_vuelo_indice"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4()
    )
    vuelo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vuelos.id", ondelete="CASCADE"), nullable=False
    )
    indice: Mapped[IndiceEnum] = mapped_column(Enum(IndiceEnum), nullable=False)
    estado: Mapped[EstadoVueloEnum] = mapped_column(
        Enum(EstadoVueloEnum), nullable=False, default=EstadoVueloEnum.pendiente
    )
    task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_detalle: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    geojson_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    metodo_umbral: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    vuelo: Mapped["Vuelo"] = relationship("Vuelo", back_populates="analisis_indices")
