"""Schemas de HU-R4-11 — ahorro de aplicación variable vs. uniforme."""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.lotes.models import CultivoEnum


class AhorroProducto(BaseModel):
    """Ahorro de un producto puntual, dentro de un vuelo."""

    producto: str
    producto_id: uuid.UUID | None
    unidad_dosis: str | None
    cantidad_variable: float
    cantidad_uniforme: float | None
    ahorro_cantidad: float | None
    ahorro_pct: float | None
    precio_usd: float | None
    precio_tipo: str | None
    ahorro_pesos: float | None


class AhorroVueloResponse(BaseModel):
    vuelo_id: uuid.UUID
    fecha_vuelo: datetime | None
    area_total_lote_ha: float
    area_tratada_ha: float
    productos: list[AhorroProducto]
    ahorro_total_pesos: float
    todos_los_precios_cargados: bool


class AhorroProductoAcumulado(BaseModel):
    """Ahorro de un producto acumulado entre todos los vuelos de una campaña."""

    producto: str
    producto_id: uuid.UUID | None
    unidad_dosis: str | None
    cantidad_variable: float
    cantidad_uniforme: float
    ahorro_cantidad: float
    ahorro_pct: float | None
    ahorro_pesos: float
    sin_dosis_referencia: bool
    sin_precio: bool


class AhorroCampanaResponse(BaseModel):
    cultivo_id: uuid.UUID
    tipo_cultivo: CultivoEnum
    variedad: str | None
    fecha_siembra: datetime | None
    fecha_cosecha: datetime | None
    n_vuelos_considerados: int
    n_vuelos_sin_diagnostico: int
    productos: list[AhorroProductoAcumulado]
    ahorro_total_pesos: float
    todos_los_precios_cargados: bool


class AhorroComparativoResponse(BaseModel):
    lote_id: uuid.UUID
    area_total_lote_ha: float
    campana_a: AhorroCampanaResponse
    campana_b: AhorroCampanaResponse | None = None
