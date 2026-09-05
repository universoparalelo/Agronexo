"""
Schemas del motor de diagnóstico y catálogo de productos fitosanitarios.
"""

import uuid

from pydantic import BaseModel, Field

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

    model_config = {"from_attributes": True}


class ProductoFitosanitarioListResponse(BaseModel):
    total: int
    items: list[ProductoFitosanitarioResponse]


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


class DiagnosticoMetadata(BaseModel):
    cultivo: str
    estadio_fenologico: str | None
    ndvi_promedio_lote: float
    indices_disponibles: list[str]
    calculado_en: str | None = None


class DiagnosticoLoteResponse(BaseModel):
    type: str = "FeatureCollection"
    features: list[dict]
    metadata: DiagnosticoMetadata
