import enum
import uuid

from pydantic import BaseModel

from app.lotes.models import IndiceEnum


class FormatoExportEnum(str, enum.Enum):
    geojson = "geojson"
    shapefile = "shapefile"


class ExportZonasResponse(BaseModel):
    vuelo_id: uuid.UUID
    formato: FormatoExportEnum
    indice: IndiceEnum
    url: str
    expira_en_segundos: int
