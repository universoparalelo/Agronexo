import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.lotes.models import CultivoEnum


class PatronEspacialEnum(str, enum.Enum):
    circular = "circular"
    lineal = "lineal"
    difuso_homogeneo = "difuso_homogeneo"
    manchas_irregulares = "manchas_irregulares"
    bordes_lote = "bordes_lote"
    focos_aislados = "focos_aislados"
    por_sectores = "por_sectores"


class ConfianzaEnum(str, enum.Enum):
    alta = "alta"
    media = "media"
    baja = "baja"


class CausaIndiceEnum(str, enum.Enum):
    sin_problema_detectado = "sin_problema_detectado"
    interferencia_vegetacion = "interferencia_vegetacion"
    estres_biotico_fungico = "estres_biotico_fungico"
    estres_biotico_insecto = "estres_biotico_insecto"
    estres_nutricional_nitrogeno = "estres_nutricional_nitrogeno"
    estres_nutricional_micro = "estres_nutricional_micro"
    estres_nutricional_fosforo = "estres_nutricional_fosforo"
    estres_hidrico = "estres_hidrico"
    madurez_temprana_diferencial = "madurez_temprana_diferencial"
    vigor_excesivo = "vigor_excesivo"


class TipoProductoEnum(str, enum.Enum):
    herbicida = "herbicida"
    fungicida = "fungicida"
    insecticida = "insecticida"
    fertilizante = "fertilizante"
    fertilizante_foliar = "fertilizante_foliar"
    acelerador_madurez = "acelerador_madurez"
    defoliante = "defoliante"


class ProductoFitosanitario(Base):
    __tablename__ = "productos_fitosanitarios"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4()
    )
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    tipo: Mapped[TipoProductoEnum] = mapped_column(Enum(TipoProductoEnum), nullable=False)
    causa_indice: Mapped[CausaIndiceEnum] = mapped_column(Enum(CausaIndiceEnum), nullable=False)
    dosis_referencia: Mapped[float | None] = mapped_column(Float, nullable=True)
    unidad: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confiabilidad_dosis: Mapped[str | None] = mapped_column(String(20), nullable=True)
    restricciones_ambientales: Mapped[str | None] = mapped_column(Text, nullable=True)
    instrucciones_seguridad: Mapped[str | None] = mapped_column(Text, nullable=True)


class PrecioProducto(Base):
    """
    Tabla creada en la migración 0023 (HU-R4-05), sin modelo ORM hasta
    ahora — HU-R4-11 es quien la consume. `tipo` distingue "referencia"
    (relevamiento inicial) de "usuario" (precio real cargado, con fecha);
    el service de ahorro (app/diagnostico/precios.py) prioriza "usuario"
    con fecha < 90 días y cae a "referencia" si no hay uno vigente.
    """

    __tablename__ = "precios_productos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4()
    )
    producto_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("productos_fitosanitarios.id", ondelete="CASCADE"), nullable=False
    )
    precio_usd: Mapped[float] = mapped_column(Float, nullable=False)
    unidad: Mapped[str] = mapped_column(String(10), nullable=False)
    fuente: Mapped[str | None] = mapped_column(String(200), nullable=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)


class PresentacionProducto(Base):
    """
    Marca/concentración comercial de un principio activo (migración 0027).
    `concentracion` y `variante` son '' (no NULL) cuando faltan, para que la
    restricción única (producto, marca, concentración, variante) también
    detecte duplicados — en Postgres los NULL nunca chocan entre sí.
    La dosis es de la presentación porque la concentración la cambia.
    """

    __tablename__ = "presentaciones_productos"
    __table_args__ = (
        UniqueConstraint("producto_id", "marca", "concentracion", "variante", name="uq_presentacion_producto"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4()
    )
    producto_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("productos_fitosanitarios.id", ondelete="CASCADE"), nullable=False
    )
    marca: Mapped[str] = mapped_column(String(200), nullable=False)
    concentracion: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    variante: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    dosis_referencia: Mapped[float] = mapped_column(Float, nullable=False)
    unidad: Mapped[str] = mapped_column(String(50), nullable=False)
    confiabilidad_dosis: Mapped[str | None] = mapped_column(String(20), nullable=True)
    precio_usd: Mapped[float] = mapped_column(Float, nullable=False)
    unidad_precio: Mapped[str] = mapped_column(String(10), nullable=False)
    fuente_precio: Mapped[str | None] = mapped_column(String(200), nullable=True)
    fecha_precio: Mapped[date] = mapped_column(Date, nullable=False)
    cultivos: Mapped[str | None] = mapped_column(String(200), nullable=True)
    observaciones_marbete: Mapped[str | None] = mapped_column(Text, nullable=True)


class NdviEsperadoEstadio(Base):
    """
    Migración 0025 — curva placeholder de NDVI esperado por
    cultivo/estadio para el gráfico "Tendencia del índice". Valores
    genéricos, no agronómicamente validados — ver docstring de la
    migración. `estadio_normalizado` se compara contra
    normalizar_estadio(vuelo.estadio_fenologico), no contra `etiqueta`.
    """

    __tablename__ = "ndvi_esperado_estadio"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4()
    )
    tipo_cultivo: Mapped[CultivoEnum] = mapped_column(Enum(CultivoEnum), nullable=False)
    estadio_normalizado: Mapped[str] = mapped_column(String(30), nullable=False)
    etiqueta: Mapped[str] = mapped_column(String(30), nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False)
    ndvi_esperado: Mapped[float] = mapped_column(Float, nullable=False)
    ndvi_min: Mapped[float] = mapped_column(Float, nullable=False)
    ndvi_max: Mapped[float] = mapped_column(Float, nullable=False)


class Diagnostico(Base):
    """
    Diagnóstico guardado de un vuelo — a lo sumo uno por vuelo (vuelo_id
    UNIQUE). "Recalcular" sobrescribe esta fila en vez de crear otra; no es
    historial multi-versión (eso es alcance de release 4, ver
    docs/release-v1.0.0.md "Problemas abiertos" #2).
    """

    __tablename__ = "diagnosticos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4()
    )
    vuelo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vuelos.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    resultado: Mapped[dict] = mapped_column(JSONB, nullable=False)
    calculado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    motor_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
