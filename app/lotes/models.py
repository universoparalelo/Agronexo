import enum
import uuid
from datetime import date, datetime, time

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, Date, DateTime, Enum, Float, ForeignKey, String, Time, UniqueConstraint, func
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


class IndiceEnum(str, enum.Enum):
    ndvi = "ndvi"
    ndre = "ndre"
    savi = "savi"
    exg = "exg"
    gndvi = "gndvi"
    msavi = "msavi"
    ndwi = "ndwi"


class ProvinciaEnum(str, enum.Enum):
    buenos_aires = "buenos_aires"
    catamarca = "catamarca"
    chaco = "chaco"
    chubut = "chubut"
    cordoba = "cordoba"
    corrientes = "corrientes"
    entre_rios = "entre_rios"
    formosa = "formosa"
    jujuy = "jujuy"
    la_pampa = "la_pampa"
    la_rioja = "la_rioja"
    mendoza = "mendoza"
    misiones = "misiones"
    neuquen = "neuquen"
    rio_negro = "rio_negro"
    salta = "salta"
    san_juan = "san_juan"
    san_luis = "san_luis"
    santa_cruz = "santa_cruz"
    santa_fe = "santa_fe"
    santiago_del_estero = "santiago_del_estero"
    tierra_del_fuego = "tierra_del_fuego"
    tucuman = "tucuman"
    caba = "caba"


class Lote(Base):
    __tablename__ = "lotes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4()
    )
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    geometry: Mapped[object] = mapped_column(
        Geometry(geometry_type="POLYGON", srid=4326, spatial_index=True), nullable=True
    )
    area_ha: Mapped[float | None] = mapped_column(Float, nullable=True)

    usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    suelo_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suelos.id", ondelete="SET NULL"), nullable=True
    )
    ubicacion_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ubicaciones.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    usuario: Mapped["Usuario"] = relationship("Usuario", back_populates="lotes")
    vuelos: Mapped[list["Vuelo"]] = relationship("Vuelo", back_populates="lote")
    cultivos: Mapped[list["Cultivo"]] = relationship("Cultivo", back_populates="lote", lazy="selectin")
    suelo: Mapped["Suelo"] = relationship("Suelo", lazy="selectin")
    ubicacion: Mapped["Ubicacion"] = relationship("Ubicacion", lazy="selectin")

    @property
    def cultivo_activo(self) -> "Cultivo | None":
        """Ciclo de cultivo vigente del lote — requiere `cultivos` ya cargado (lazy='selectin')."""
        return next((c for c in self.cultivos if c.activo), None)


class Suelo(Base):
    """Catálogo de tipo/serie de suelo (ej. taxonomía INTA) referenciado por lotes."""
    __tablename__ = "suelos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4()
    )
    tipo: Mapped[str] = mapped_column(String(100), nullable=False)
    serie: Mapped[str | None] = mapped_column(String(100), nullable=True)


class Ubicacion(Base):
    """Catálogo de provincia/departamento/localidad referenciado por lotes."""
    __tablename__ = "ubicaciones"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4()
    )
    provincia: Mapped[ProvinciaEnum] = mapped_column(Enum(ProvinciaEnum), nullable=False)
    departamento: Mapped[str | None] = mapped_column(String(100), nullable=True)
    localidad: Mapped[str | None] = mapped_column(String(100), nullable=True)


class Cultivo(Base):
    """Ciclo de cultivo sobre un lote (campaña) — un lote acumula varios a lo largo del tiempo."""
    __tablename__ = "cultivos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4()
    )
    lote_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lotes.id", ondelete="RESTRICT"), nullable=False
    )
    cultivo: Mapped[CultivoEnum] = mapped_column(Enum(CultivoEnum), nullable=False)
    estadio_fenologico: Mapped[str | None] = mapped_column(String(10), nullable=True)
    fecha_siembra: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_cosecha_estimada: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_cosecha_real: Mapped[date | None] = mapped_column(Date, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lote: Mapped["Lote"] = relationship("Lote", back_populates="cultivos")


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
