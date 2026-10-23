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
    # Curva ndvi_esperado_estadio (migración 0025) para cultivo+estadio del
    # vuelo; None si el estadio no está cargado o no está en la curva.
    ndvi_esperado: float | None = None
    ndvi_esperado_min: float | None = None


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


# Por encima de esta probabilidad (y sin empate) R80 adopta la causa del
# motor probabilístico; por debajo da un diagnóstico diferencial de dos.
PROB_MIN_CAUSA_UNICA = 0.40

# Qué índice ayudaría a separar cada par de causas cuando falta.
_INDICE_QUE_DESEMPATA = {
    frozenset({"estres_nutricional_nitrogeno", "estres_hidrico"}): "ndre",
    frozenset({"estres_nutricional_nitrogeno", "estres_nutricional_fosforo"}): "ndre",
    frozenset({"estres_nutricional_micro", "estres_hidrico"}): "ndre",
    frozenset({"interferencia_vegetacion", "estres_biotico_insecto"}): "exg",
}


def _regla_representativa(causa: str, cultivo: CultivoEnum):
    from app.diagnostico.reglas import R01, REGLAS
    if causa == "suelo_desnudo":
        return R01
    return next(
        (r for r in REGLAS
         if r.causa_indice == causa and (r.cultivos is None or cultivo in r.cultivos)),
        None,
    )


def precisar_con_bayes(
    resultado: ResultadoDiagnostico, bayes: dict, cultivo: CultivoEnum, indices_disponibles: set[str],
) -> ResultadoDiagnostico:
    """
    R80 solo sabe que la zona está por debajo de lo esperado para el estadio.
    En vez de devolver ese "no sé", usa el ranking del motor probabilístico:
    con una causa clara la adopta (confianza baja — no la confirmó ninguna
    regla); con empate devuelve las dos más probables y cómo distinguirlas a
    campo. "Sin problema" no es candidata: la zona ya está fuera de rango.
    """
    if resultado.regla_id != "R80":
        return resultado
    from app.diagnostico.models import ConfianzaEnum
    from app.diagnostico.texto import CAUSA_LABELS

    # Probabilidad condicionada a "hay un problema": la zona ya está fuera del
    # rango normal, así que se descarta "sin problema" y se renormaliza.
    posterior = bayes.get("posterior") or {r["causa"]: r["probabilidad"] for r in bayes.get("ranking", [])}
    # Suelo desnudo real ya lo toma R01 (NDVI < 0.20); acá sería ruido.
    problemas = {
        c: p for c, p in posterior.items()
        if c not in ("sin_problema_detectado", "suelo_desnudo") and _regla_representativa(c, cultivo) is not None
    }
    total = sum(problemas.values())
    candidatas = sorted(((c, p / total) for c, p in problemas.items()), key=lambda cp: cp[1], reverse=True) if total > 0 else []
    if not candidatas:
        return resultado

    def etiqueta(causa):
        # CAUSA_LABELS ya trae "probable" en algunas causas ("ataque de insectos
        # probable") y acá el nombre lo agrega aparte.
        return CAUSA_LABELS.get(causa, causa).removesuffix(" probable")

    (c1, p1) = candidatas[0]
    regla1 = _regla_representativa(c1, cultivo)
    segunda = candidatas[1] if len(candidatas) > 1 else None

    if p1 >= PROB_MIN_CAUSA_UNICA and (segunda is None or p1 - segunda[1] >= 0.15):
        return ResultadoDiagnostico(
            regla_id="R80",
            regla_nombre=f"Vigor bajo para el estadio — probable {etiqueta(c1)}",
            confianza=ConfianzaEnum.baja,
            causa_indice=c1,
            accion_recomendada=(
                f"El motor probabilístico atribuye la caída de vigor a {etiqueta(c1)} "
                f"({p1:.0%}). {regla1.accion_recomendada}"
            ),
            como_confirmar_campo=regla1.como_confirmar_campo,
            excluida=False,
        )

    c2, p2 = segunda
    regla2 = _regla_representativa(c2, cultivo)
    accion = (
        f"La caída de vigor es compatible sobre todo con {etiqueta(c1)} ({p1:.0%}) o "
        f"{etiqueta(c2)} ({p2:.0%}), sin que los datos permitan elegir una. No aplicar "
        f"productos hasta confirmar a campo cuál de las dos es."
    )
    indice = _INDICE_QUE_DESEMPATA.get(frozenset({c1, c2}))
    if indice and indice not in indices_disponibles:
        accion += f" Calcular {indice.upper()} para este vuelo ayudaría a distinguirlas."
    return ResultadoDiagnostico(
        regla_id="R80",
        regla_nombre=f"Vigor bajo para el estadio — {etiqueta(c1)} o {etiqueta(c2)}",
        confianza=ConfianzaEnum.baja,
        causa_indice="bajo_vigor_estadio",
        accion_recomendada=accion,
        como_confirmar_campo=(
            f"Para confirmar {etiqueta(c1)}: {regla1.como_confirmar_campo}\n\n"
            f"Para confirmar {etiqueta(c2)}: {regla2.como_confirmar_campo}"
        ),
        excluida=False,
    )
