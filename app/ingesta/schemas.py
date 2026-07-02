import uuid
from datetime import datetime

from pydantic import BaseModel

from app.lotes.models import EstadoVueloEnum, SensorEnum


class VueloListItem(BaseModel):
    vuelo_id: uuid.UUID
    lote_id: uuid.UUID
    sensor: SensorEnum
    estado: EstadoVueloEnum
    fecha_vuelo: datetime
    task_id: str | None
    created_at: datetime


class VueloUploadResponse(BaseModel):
    vuelo_id: uuid.UUID
    lote_id: uuid.UUID
    sensor: SensorEnum
    estado: EstadoVueloEnum
    task_id: str
    created_at: datetime
    mensaje: str = "GeoTIFF recibido. Validación y procesamiento iniciados."


class LoteDesdeGeotiffResponse(BaseModel):
    lote_id: uuid.UUID
    vuelo_id: uuid.UUID
    sensor: SensorEnum
    estado: EstadoVueloEnum
    task_id: str
    created_at: datetime
    mensaje: str = "GeoTIFF recibido. El lote y el análisis serán procesados en breve."


class EstadoVueloResponse(BaseModel):
    vuelo_id: uuid.UUID
    estado: EstadoVueloEnum
    task_id: str | None
    progreso: int | None
    mensaje: str | None
    error: str | None
