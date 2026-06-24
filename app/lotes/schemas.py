import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator
from shapely.geometry import mapping, shape
from shapely.geometry.polygon import Polygon

from app.lotes.models import CultivoEnum, EstadoVueloEnum, SensorEnum


# ── Geometry helpers ────────────────────────────────────────────────

def _validar_polygon_geojson(v: Any) -> dict:
    """Valida que el dict sea un GeoJSON Polygon con Shapely."""
    if not isinstance(v, dict):
        raise ValueError("geometry debe ser un objeto GeoJSON")
    if v.get("type") != "Polygon":
        raise ValueError("geometry.type debe ser 'Polygon'")
    try:
        geom = shape(v)
    except Exception:
        raise ValueError("geometry no es un GeoJSON válido")
    if not isinstance(geom, Polygon):
        raise ValueError("geometry debe ser un Polígono")
    if not geom.is_valid:
        raise ValueError(f"geometry no es válida: {geom.is_valid_reason if hasattr(geom, 'is_valid_reason') else ''}")
    if geom.is_empty:
        raise ValueError("geometry no puede estar vacía")
    return v


# ── Lote schemas ────────────────────────────────────────────────────

class LoteCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=200, examples=["Lote Norte"])
    cultivo: CultivoEnum = Field(..., examples=["soja"])
    estadio_fenologico: str | None = Field(None, max_length=10, examples=["R3"])
    geometry: dict = Field(
        ...,
        examples=[{
            "type": "Polygon",
            "coordinates": [[
                [-60.6753, -27.4693],
                [-60.6701, -27.4693],
                [-60.6701, -27.4741],
                [-60.6753, -27.4741],
                [-60.6753, -27.4693],
            ]]
        }]
    )

    @field_validator("geometry")
    @classmethod
    def geometry_valida(cls, v: Any) -> dict:
        return _validar_polygon_geojson(v)


class LoteUpdate(BaseModel):
    nombre: str | None = Field(None, min_length=1, max_length=200)
    cultivo: CultivoEnum | None = None
    estadio_fenologico: str | None = Field(None, max_length=10)
    geometry: dict | None = None

    @field_validator("geometry")
    @classmethod
    def geometry_valida(cls, v: Any) -> dict | None:
        if v is None:
            return v
        return _validar_polygon_geojson(v)


class LoteResponse(BaseModel):
    id: uuid.UUID
    nombre: str
    cultivo: CultivoEnum
    estadio_fenologico: str | None
    geometry: dict
    area_ha: float | None
    usuario_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("geometry", mode="before")
    @classmethod
    def geometry_desde_wkb(cls, v: Any) -> dict:
        """Convierte WKBElement de GeoAlchemy2 a dict GeoJSON."""
        if isinstance(v, dict):
            return v
        try:
            from geoalchemy2.shape import to_shape
            return mapping(to_shape(v))
        except Exception:
            return v


class LoteListResponse(BaseModel):
    total: int
    items: list[LoteResponse]


# ── Vuelo schemas ────────────────────────────────────────────────────

class VueloResponse(BaseModel):
    id: uuid.UUID
    lote_id: uuid.UUID
    fecha_vuelo: datetime
    sensor: SensorEnum
    archivo_original: str | None
    estado: EstadoVueloEnum
    created_at: datetime

    model_config = {"from_attributes": True}
