import uuid
from datetime import datetime, time

from pydantic import BaseModel, Field, field_validator

from app.lotes.models import EstadoVueloEnum, IndiceEnum, SensorEnum
from app.lotes.schemas import CultivoCreate, CultivoResponse


class UsuarioResumen(BaseModel):
    """Identifica a quién subió un vuelo (HU-R4-02, trazabilidad) — solo lo
    necesario para mostrarlo, no el perfil completo de UsuarioResponse."""
    nombre: str
    email: str

    model_config = {"from_attributes": True}


class IndiceAnalisisItem(BaseModel):
    """Un índice ya calculado (o en curso) para un vuelo — incluye el NDVI
    "primario" sintetizado desde el propio vuelo, y cualquier adicional
    (NDRE/SAVI/ExG) que viva en la tabla analisis_indices."""
    indice: IndiceEnum
    estado: EstadoVueloEnum
    task_id: str | None
    error: str | None
    es_primario: bool  # True solo para el NDVI calculado al subir el vuelo


class VueloListItem(BaseModel):
    vuelo_id: uuid.UUID
    lote_id: uuid.UUID
    sensor: SensorEnum
    estado: EstadoVueloEnum
    fecha_vuelo: datetime
    hora_inicio: time | None
    hora_fin: time | None
    task_id: str | None
    created_at: datetime
    estadio_fenologico: str | None = None
    cultivo_id: uuid.UUID | None = None
    cultivo: CultivoResponse | None = None
    indices: list[IndiceAnalisisItem] = []
    # Trazabilidad (HU-R4-02): metodo_umbral y mapeo_bandas quedan en None
    # hasta que el worker termina de procesar (ver Vuelo.mapeo_bandas).
    archivo_original: str | None = None
    subido_por: UsuarioResumen | None = None
    metodo_umbral: str | None = None
    mapeo_bandas: dict | None = None


class VueloUpdate(BaseModel):
    """Solo los datos que el usuario carga a mano; sensor y archivo no se editan
    porque cambiarlos obligaría a reprocesar el GeoTIFF."""
    fecha_vuelo: datetime | None = None
    estadio_fenologico: str | None = Field(None, min_length=1, max_length=30)
    cultivo_id: uuid.UUID | None = None

    @field_validator("estadio_fenologico")
    @classmethod
    def estadio_sin_espacios(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("El estadio fenológico no puede estar vacío.")
        return v


class VueloActualizadoResponse(BaseModel):
    vuelo_id: uuid.UUID
    lote_id: uuid.UUID
    fecha_vuelo: datetime
    estadio_fenologico: str | None = None
    cultivo_id: uuid.UUID | None = None
    cultivo: CultivoResponse | None = None
    # Cambiar cultivo o estadio no recalcula solo el diagnóstico ya guardado.
    diagnostico_desactualizado: bool = False


class VueloUploadResponse(BaseModel):
    vuelo_id: uuid.UUID
    lote_id: uuid.UUID
    sensor: SensorEnum
    estado: EstadoVueloEnum
    task_id: str
    created_at: datetime
    estadio_fenologico: str | None = None
    cultivo_id: uuid.UUID | None = None
    cultivo: CultivoResponse | None = None
    mensaje: str = "GeoTIFF recibido. Validación y procesamiento iniciados."


class LoteDesdeGeotiffResponse(BaseModel):
    lote_id: uuid.UUID
    vuelo_id: uuid.UUID
    sensor: SensorEnum
    estado: EstadoVueloEnum
    task_id: str
    created_at: datetime
    mensaje: str = "GeoTIFF recibido. El lote y el análisis serán procesados en breve."


class VueloReintentoResponse(BaseModel):
    vuelo_id: uuid.UUID
    lote_id: uuid.UUID
    sensor: SensorEnum
    estado: EstadoVueloEnum
    task_id: str
    created_at: datetime
    mensaje: str = "Reprocesamiento encolado."


class EstadoVueloResponse(BaseModel):
    vuelo_id: uuid.UUID
    estado: EstadoVueloEnum
    task_id: str | None
    progreso: int | None
    mensaje: str | None
    error: str | None


class InspeccionGeotiffResponse(BaseModel):
    n_bandas: int | None
    bandas_requeridas: int
    compatible: bool
    mensaje: str | None


class IndiceAnalisisRequest(BaseModel):
    indice: IndiceEnum
    metodo_umbral: str = "fijo"


class IndiceAnalisisIniciarResponse(BaseModel):
    indice: IndiceEnum
    estado: EstadoVueloEnum
    task_id: str | None
    mensaje: str = "Análisis encolado."


class IndiceEstadoResponse(BaseModel):
    indice: IndiceEnum
    estado: EstadoVueloEnum
    task_id: str | None
    progreso: int | None
    mensaje: str | None
    error: str | None


class IndicesBatchRequest(BaseModel):
    """Pide varios índices adicionales de una — se calculan en una sola
    corrida de Celery (descarga y lectura de bandas compartida) en lugar de
    una task por índice. Ver workers.gis.tasks.analizar_indices_batch."""
    indices: list[IndiceEnum]
    metodo_umbral: str = "fijo"


class IndicesBatchIniciarResponse(BaseModel):
    items: list[IndiceAnalisisIniciarResponse]
    mensaje: str = "Análisis encolados."


class EscenaSatelitalItem(BaseModel):
    """Una escena Sentinel-2 candidata, del catálogo Earth Search — el
    usuario ve la nubosidad y elige, el sistema no filtra por él."""
    escena_id: str
    fecha: str
    nubes_pct: float | None
    dias_diferencia: int
    thumbnail_url: str | None = None


class EscenasSatelitalesResponse(BaseModel):
    items: list[EscenaSatelitalItem]
    fecha_elegida: str
    ventana_dias: int


class VueloDesdeSateliteRequest(BaseModel):
    escena_id: str
    fecha_vuelo: datetime
    # Obligatorio: el motor de diagnóstico lo usa para decidir qué reglas aplican.
    estadio_fenologico: str = Field(..., min_length=1, max_length=30)
    indices: list[IndiceEnum] = []
    # Exactamente uno de los dos: un cultivo ya cargado en el lote, o los datos de uno nuevo.
    cultivo_id: uuid.UUID | None = None
    cultivo: CultivoCreate | None = None

    @field_validator("estadio_fenologico")
    @classmethod
    def estadio_no_vacio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El estadio fenológico es obligatorio.")
        return v
