"""
Evaluador en cascada del motor de reglas. Puro — sin I/O, sin FastAPI, sin
SQLAlchemy. app/diagnostico/service.py construye un ContextoZona por cada
zona del GeoJSON y llama a evaluar_zona().
"""

from dataclasses import dataclass

from app.diagnostico.models import ConfianzaEnum
from app.lotes.models import CultivoEnum


@dataclass
class ContextoZona:
    zona_id: int
    valores: dict[str, float]      # solo índices con dato resuelto para ESTA zona
    patron_espacial: str
    area_ha: float
    ndvi_promedio_lote: float      # promedio ponderado por área de toda la partición NDVI
    cultivo: CultivoEnum
    estadio_normalizado: str | None


@dataclass
class ResultadoDiagnostico:
    regla_id: str
    regla_nombre: str
    confianza: ConfianzaEnum
    causa_indice: str
    accion_recomendada: str
    como_confirmar_campo: str
    excluida: bool


def evaluar_zona(contexto: ContextoZona) -> ResultadoDiagnostico:
    """
    Recorre REGLAS en orden fijo — la primera que cumple todas sus
    condiciones (cultivo, estadio, índices disponibles, condición numérica/
    de patrón) gana y las demás no se evalúan. R99 no tiene condiciones y
    siempre coincide, así que la cascada termina siempre.
    """
    # Import diferido: reglas.py importa ContextoZona de este módulo para
    # tipar Regla.condicion — importar arriba crearía un ciclo.
    from app.diagnostico.estadios import estadio_coincide
    from app.diagnostico.reglas import REGLAS

    for regla in REGLAS:
        if regla.cultivos is not None and contexto.cultivo not in regla.cultivos:
            continue
        if not estadio_coincide(contexto.estadio_normalizado, regla.estadios):
            continue
        if not set(regla.requiere_indices) <= contexto.valores.keys():
            continue
        if regla.condicion(contexto):
            return ResultadoDiagnostico(
                regla_id=regla.id,
                regla_nombre=regla.nombre,
                confianza=regla.confianza,
                causa_indice=regla.causa_indice,
                accion_recomendada=regla.accion_recomendada,
                como_confirmar_campo=regla.como_confirmar_campo,
                excluida=regla.excluye_zona,
            )

    raise AssertionError("Ninguna regla coincidió — R99 debe matchear siempre. Revisar REGLAS.")
