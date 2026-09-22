import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator
from shapely.geometry import mapping, shape
from shapely.geometry.polygon import Polygon

from app.lotes.models import CultivoEnum, TipoSueloEnum

# Rango de área razonable para un lote agrícola — mismo rango que valida el
# frontend en frontend/src/components/MapaDibujoLote.jsx (AREA_MIN_HA/AREA_MAX_HA).
AREA_MIN_HA = 0.5
AREA_MAX_HA = 5000.0


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


# ── Cultivo schemas ─────────────────────────────────────────────────

def _validar_fechas_cultivo(fecha_siembra: datetime | None, fecha_cosecha: datetime | None) -> None:
    if fecha_siembra and fecha_cosecha and fecha_cosecha < fecha_siembra:
        raise ValueError("fecha_cosecha no puede ser anterior a fecha_siembra")


class CultivoCreate(BaseModel):
    tipo_cultivo: CultivoEnum = Field(..., examples=["soja"])
    variedad: str | None = Field(None, max_length=100, examples=["DM 46i17"])
    fecha_siembra: datetime | None = Field(None, examples=["2026-11-15T00:00:00Z"])
    fecha_cosecha: datetime | None = Field(None, examples=["2027-04-20T00:00:00Z"])

    @model_validator(mode="after")
    def fechas_coherentes(self):
        _validar_fechas_cultivo(self.fecha_siembra, self.fecha_cosecha)
        return self


class CultivoUpdate(BaseModel):
    tipo_cultivo: CultivoEnum | None = None
    variedad: str | None = Field(None, max_length=100)
    fecha_siembra: datetime | None = None
    fecha_cosecha: datetime | None = None

    @model_validator(mode="after")
    def fechas_coherentes(self):
        _validar_fechas_cultivo(self.fecha_siembra, self.fecha_cosecha)
        return self


class CultivoResponse(BaseModel):
    id: uuid.UUID
    lote_id: uuid.UUID
    tipo_cultivo: CultivoEnum
    variedad: str | None
    fecha_siembra: datetime | None
    fecha_cosecha: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Lote schemas ────────────────────────────────────────────────────

class LoteCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=200, examples=["Lote Norte"])
    tipo_suelo: TipoSueloEnum | None = Field(None, examples=["franco_arcilloso"])
    geometry: dict | None = Field(
        None,
        description="Opcional. Si no se provee, el lote queda sin límites — se puede cargar después.",
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
    def geometry_valida(cls, v: Any) -> dict | None:
        if v is None:
            return v
        return _validar_polygon_geojson(v)


class LoteUpdate(BaseModel):
    nombre: str | None = Field(None, min_length=1, max_length=200)
    tipo_suelo: TipoSueloEnum | None = None
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
    tipo_suelo: TipoSueloEnum | None
    geometry: dict | None
    area_ha: float | None
    usuario_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    cultivos: list["CultivoResponse"] = []

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
