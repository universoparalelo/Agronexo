"""
Schemas documentales de la respuesta del motor de diagnóstico. No se usan
como `response_model` estricto del endpoint (la forma de un Feature GeoJSON
es dinámica, mismo criterio que los endpoints `.../resultado` existentes) —
sirven de referencia para el frontend y para los tests.
"""

from pydantic import BaseModel

from app.diagnostico.models import ConfianzaEnum


class ProductoSugerido(BaseModel):
    nombre: str
    tipo: str


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


class DiagnosticoLoteResponse(BaseModel):
    type: str = "FeatureCollection"
    features: list[dict]
    metadata: DiagnosticoMetadata
