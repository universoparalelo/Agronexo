import enum
import uuid
from datetime import datetime, time

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Time, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
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
    tipo_suelo: Mapped[TipoSueloEnum | None] = mapped_column(Enum(TipoSueloEnum), nullable=True)
    geometry: Mapped[object] = mapped_column(
        Geometry(geometry_type="POLYGON", srid=4326, spatial_index=True), nullable=True
    )
    area_ha: Mapped[float | None] = mapped_column(Float, nullable=True)

    # as_uuid=False a propósito, igual que Vuelo.subido_por_id — tiene que
    # matchear el tipo Python de Usuario.id para que un eager load futuro de
    # la relación `usuario` no quede en None en silencio (mismo bug real que
    # ese, encontrado y documentado en HU-R4-02).
    usuario_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    usuario: Mapped["Usuario"] = relationship("Usuario", back_populates="lotes")
    vuelos: Mapped[list["Vuelo"]] = relationship("Vuelo", back_populates="lote")
    # Solo los cultivos no eliminados, el más reciente primero — un cultivo
    # dado de baja no debe reaparecer en el selector de cultivo del análisis.
    cultivos: Mapped[list["Cultivo"]] = relationship(
        "Cultivo",
        primaryjoin="and_(Cultivo.lote_id == Lote.id, Cultivo.deleted_at.is_(None))",
        order_by="Cultivo.created_at.desc()",
        lazy="selectin",
        viewonly=True,
    )


class Cultivo(Base):
    """
    Cultivo sembrado en un lote (una campaña). Un lote puede tener varios a lo
    largo del tiempo; cada vuelo/análisis se asocia al cultivo que estaba en
    pie cuando se capturó — de ahí salen el tipo de cultivo y la variedad que
    usa el motor de diagnóstico.
    """
    __tablename__ = "cultivos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4()
    )
    lote_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lotes.id", ondelete="RESTRICT"), nullable=False
    )
    tipo_cultivo: Mapped[CultivoEnum] = mapped_column(Enum(CultivoEnum), nullable=False)
    variedad: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fecha_siembra: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fecha_cosecha: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


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
    cultivo_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cultivos.id", ondelete="RESTRICT"), nullable=True
    )
    sensor: Mapped[SensorEnum] = mapped_column(Enum(SensorEnum), nullable=False)
    estadio_fenologico: Mapped[str | None] = mapped_column(String(30), nullable=True)
    archivo_original: Mapped[str | None] = mapped_column(String(500), nullable=True)
    estado: Mapped[EstadoVueloEnum] = mapped_column(
        Enum(EstadoVueloEnum), nullable=False, default=EstadoVueloEnum.pendiente
    )
    task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_detalle: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    geojson_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Trazabilidad (HU-R4-02): quién lo subió, y qué mapeo de bandas/umbral se
    # usó en el NDVI primario — metodo_umbral y mapeo_bandas los completa el
    # worker al terminar (workers/gis/tasks.py::_actualizar_vuelo), no la API.
    # as_uuid=False a propósito: tiene que matchear el tipo Python de
    # Usuario.id (también as_uuid=False) para que el selectin loader de
    # `subido_por` pueda emparejar las filas — con as_uuid=True acá,
    # uuid.UUID(...) != str(...) y la relación queda en None (bug real,
    # detectado con un test de trazabilidad).
    subido_por_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    metodo_umbral: Mapped[str | None] = mapped_column(String(20), nullable=True)
    mapeo_bandas: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    lote: Mapped["Lote"] = relationship("Lote", back_populates="vuelos")
    cultivo: Mapped["Cultivo | None"] = relationship("Cultivo", lazy="selectin")
    subido_por: Mapped["Usuario | None"] = relationship(
        "Usuario", lazy="selectin", foreign_keys=[subido_por_id]
    )
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
