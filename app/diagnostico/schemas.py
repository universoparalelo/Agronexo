"""
Schemas del motor de diagnóstico y catálogo de productos fitosanitarios.
"""

import uuid
from datetime import date

from pydantic import BaseModel, Field, field_validator

from app.diagnostico.models import CausaIndiceEnum, ConfianzaEnum, TipoProductoEnum


class ProductoSugerido(BaseModel):
    nombre: str
    tipo: str


class ProductoFitosanitarioResponse(BaseModel):
    id: uuid.UUID
    nombre: str
    tipo: TipoProductoEnum
    causa_indice: CausaIndiceEnum
    dosis_referencia: float | None
    unidad: str | None
    restricciones_ambientales: str | None
    instrucciones_seguridad: str | None

    model_config = {"from_attributes": True}


class ProductoFitosanitarioListResponse(BaseModel):
    total: int
    items: list[ProductoFitosanitarioResponse]


# ── Precios (HU-R4-11) ──────────────────────────────────────────────

class PrecioProductoResponse(BaseModel):
    id: uuid.UUID
    producto_id: uuid.UUID
    precio_usd: float
    unidad: str
    fuente: str | None
    fecha: date
    tipo: str

    model_config = {"from_attributes": True}


class PrecioProductoCreateRequest(BaseModel):
    """Siempre crea un precio tipo 'usuario' — los de tipo 'referencia' solo
    se cargan por migración/seed, no desde la API."""

    precio_usd: float = Field(..., gt=0)
    unidad: str = Field(..., min_length=1, max_length=10)
    fecha: date

    @field_validator("fecha")
    @classmethod
    def fecha_no_futura(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("La fecha del precio no puede ser futura")
        return v


class OrdenTrabajoItem(BaseModel):
    """Una línea de la orden de trabajo — una unidad de manejo a tratar."""

    unidad_id: int
    causa_indice: str
    severidad: str
    area_ha: float
    zona_ids: list[int]
    producto: str | None
    dosis_por_ha: float | None
    unidad_dosis: str | None
    volumen_total: float | None
    restricciones_ambientales: str | None
    instrucciones_seguridad: str | None
    sin_dosis_referencia: bool


class TotalProducto(BaseModel):
    producto: str
    area_ha: float
    volumen_total: float
    unidad_dosis: str | None


class OrdenTrabajoResponse(BaseModel):
    items: list[OrdenTrabajoItem]
    totales_por_producto: list[TotalProducto]
    area_total_tratada_ha: float


class ZonaDiagnosticoProperties(BaseModel):
    clase: str
    codigo: int
    ndvi_promedio: float
    area_ha: float
    zscore: float
    es_atipica: bool
    patron_espacial: str
    zona_id: int
    regla_id: str
    regla_nombre: str
    confianza: ConfianzaEnum
    causa_indice: str
    accion_recomendada: str
    como_confirmar_campo: str
    excluida: bool
    productos_sugeridos: list[ProductoSugerido]


class EstadiosFenologicosResponse(BaseModel):
    """Estadios elegibles por tipo de cultivo (clave = valor de CultivoEnum)."""
    estadios: dict[str, list[str]]


class DiagnosticoMetadata(BaseModel):
    cultivo: str
    cultivo_id: str | None = None
    variedad: str | None = None
    fecha_siembra: str | None = None
    fecha_cosecha: str | None = None
    estadio_fenologico: str | None
    ndvi_promedio_lote: float
    indices_disponibles: list[str]
    calculado_en: str | None = None


class DiagnosticoLoteResponse(BaseModel):
    type: str = "FeatureCollection"
    features: list[dict]
    metadata: DiagnosticoMetadata
