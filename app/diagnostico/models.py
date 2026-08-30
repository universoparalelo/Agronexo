import enum
import uuid

from sqlalchemy import Enum, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


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
