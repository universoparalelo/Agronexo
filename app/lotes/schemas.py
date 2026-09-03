import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator
from shapely.geometry import mapping, shape
from shapely.geometry.polygon import Polygon

from app.lotes.models import CultivoEnum, ProvinciaEnum


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
    """El límite geográfico no se pide acá — se deriva automáticamente del
    bounding box del primer GeoTIFF que se suba como vuelo (ver workers/gis/tasks.py)."""
    nombre: str = Field(..., min_length=1, max_length=200, examples=["Lote Norte"])
    suelo_id: uuid.UUID = Field(..., description="FK a suelos — ver GET /lotes/suelos.")
    provincia: ProvinciaEnum | None = Field(None, examples=["chaco"])
    departamento: str | None = Field(None, min_length=1, max_length=100, examples=["Presidencia Roque Sáenz Peña"])
    localidad: str | None = Field(None, min_length=1, max_length=100)

    @model_validator(mode="after")
    def ubicacion_consistente(self) -> "LoteCreate":
        algo = self.provincia is not None or self.departamento is not None or self.localidad is not None
        if algo and self.provincia is None:
            raise ValueError("Para cargar ubicación hace falta al menos la provincia.")
        return self


class LoteUpdate(BaseModel):
    nombre: str | None = Field(None, min_length=1, max_length=200)
    suelo_id: uuid.UUID | None = None
    ubicacion_id: uuid.UUID | None = None
    geometry: dict | None = None

    @field_validator("geometry")
    @classmethod
    def geometry_valida(cls, v: Any) -> dict | None:
        if v is None:
            return v
        return _validar_polygon_geojson(v)


class SueloResponse(BaseModel):
    id: uuid.UUID
    tipo: str
    serie: str | None

    model_config = {"from_attributes": True}


class UbicacionResponse(BaseModel):
    id: uuid.UUID
    provincia: ProvinciaEnum
    departamento: str | None
    localidad: str | None

    model_config = {"from_attributes": True}


class CultivoResponse(BaseModel):
    id: uuid.UUID
    lote_id: uuid.UUID
    cultivo: CultivoEnum
    estadio_fenologico: str | None
    fecha_siembra: date
    fecha_cosecha_estimada: date | None
    fecha_cosecha_real: date | None
    activo: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class LoteResponse(BaseModel):
    id: uuid.UUID
    nombre: str
    suelo_id: uuid.UUID | None
    ubicacion_id: uuid.UUID | None
    geometry: dict | None
    area_ha: float | None
    usuario_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    suelo: SueloResponse | None = None
    ubicacion: UbicacionResponse | None = None
    cultivo_activo: CultivoResponse | None = None

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

    model_config = {"from_attributes": True}
