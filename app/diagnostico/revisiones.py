"""
Criterio técnico del agrónomo sobre el diagnóstico por zona (RFDR-04) y su
uso como casos etiquetados del motor probabilístico (bayes.py).
"""

from __future__ import annotations

import copy
import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.diagnostico.bayes import CAUSAS, EvidenciaZona, causa_efectiva
from app.diagnostico.models import DecisionRevisionEnum, RevisionDiagnostico
from app.lotes.models import CultivoEnum


class RevisionInvalida(ValueError):
    pass


def evidencia_de_zona(props: dict, metadata: dict) -> dict:
    """
    Diagnósticos guardados antes del motor v1.1.0 no traen `evidencia` en
    cada zona: se reconstruye con lo que sí está (sin NDRE/ExG por zona).
    """
    if props.get("evidencia"):
        return props["evidencia"]
    return EvidenciaZona(
        cultivo=CultivoEnum(metadata["cultivo"]),
        estadio=metadata.get("estadio_fenologico"),
        patron=props.get("patron_espacial", "manchas_irregulares"),
        ndvi=float(props.get("ndvi_promedio", 0.0)),
        ndvi_promedio_lote=float(metadata.get("ndvi_promedio_lote", 0.0)),
        ndvi_esperado=metadata.get("ndvi_esperado_estadio"),
        ndvi_esperado_min=metadata.get("ndvi_esperado_estadio_min"),
    ).a_dict()


def causa_etiquetada(rev: RevisionDiagnostico) -> str | None:
    """Causa real según el agrónomo, en las clases del motor bayesiano. Un
    rechazo sin causa confirmada solo dice "no es esto" — no etiqueta."""
    if rev.decision == DecisionRevisionEnum.aceptado:
        return causa_efectiva(rev.regla_id, rev.causa_sugerida)
    return rev.causa_confirmada


async def guardar_revision(
    db: AsyncSession, *, vuelo_id: uuid.UUID, zona_id: int, diagnostico: dict,
    decision: DecisionRevisionEnum, causa_confirmada: str | None, comentario: str | None,
    usuario_id: uuid.UUID,
) -> RevisionDiagnostico:
    zona = next(
        (f.get("properties", {}) for f in diagnostico.get("features", [])
         if f.get("properties", {}).get("zona_id") == zona_id),
        None,
    )
    if zona is None:
        raise LookupError(f"La zona {zona_id} no existe en el diagnóstico de este vuelo.")

    regla_id = zona.get("regla_id", "")
    sugerida = causa_efectiva(regla_id, zona.get("causa_indice")) or zona.get("causa_indice", "")

    if causa_confirmada is not None and causa_confirmada not in CAUSAS:
        raise RevisionInvalida(f"Causa '{causa_confirmada}' desconocida.")
    if decision == DecisionRevisionEnum.modificado:
        if causa_confirmada is None:
            raise RevisionInvalida("Para modificar el diagnóstico hay que indicar la causa confirmada.")
        if causa_confirmada == sugerida:
            raise RevisionInvalida("La causa confirmada es la misma que la sugerida: usar 'aceptado'.")
    if decision == DecisionRevisionEnum.aceptado:
        causa_confirmada = None

    valores = dict(
        regla_id=regla_id,
        causa_sugerida=sugerida,
        decision=decision,
        causa_confirmada=causa_confirmada,
        comentario=(comentario or "").strip() or None,
        evidencia=evidencia_de_zona(zona, diagnostico.get("metadata", {})),
        motor_version=diagnostico.get("metadata", {}).get("motor_version"),
        usuario_id=usuario_id,
    )
    stmt = pg_insert(RevisionDiagnostico).values(vuelo_id=vuelo_id, zona_id=zona_id, **valores)
    stmt = stmt.on_conflict_do_update(
        index_elements=[RevisionDiagnostico.vuelo_id, RevisionDiagnostico.zona_id],
        set_={**valores, "updated_at": func.now()},
    ).returning(RevisionDiagnostico)
    result = await db.execute(stmt)
    revision = result.scalar_one()
    await db.flush()
    return revision


async def eliminar_revision(db: AsyncSession, vuelo_id: uuid.UUID, zona_id: int) -> bool:
    result = await db.execute(
        delete(RevisionDiagnostico).where(
            RevisionDiagnostico.vuelo_id == vuelo_id, RevisionDiagnostico.zona_id == zona_id,
        )
    )
    return result.rowcount > 0


async def listar_revisiones(db: AsyncSession, vuelo_id: uuid.UUID) -> list[RevisionDiagnostico]:
    result = await db.execute(
        select(RevisionDiagnostico).where(RevisionDiagnostico.vuelo_id == vuelo_id)
    )
    return list(result.scalars().all())


async def cargar_casos_entrenamiento(db: AsyncSession) -> list[tuple[EvidenciaZona, str]]:
    """Todas las revisiones con causa etiquetada, de todos los usuarios: la
    evidencia son solo valores numéricos y patrón, no datos del lote."""
    result = await db.execute(select(RevisionDiagnostico))
    casos = []
    for rev in result.scalars().all():
        causa = causa_etiquetada(rev)
        if causa is None:
            continue
        try:
            casos.append((EvidenciaZona.desde_dict(rev.evidencia), causa))
        except (KeyError, ValueError):
            continue
    return casos


def revision_a_dict(rev: RevisionDiagnostico) -> dict:
    return {
        "zona_id": rev.zona_id,
        "decision": rev.decision.value,
        "causa_sugerida": rev.causa_sugerida,
        "causa_confirmada": rev.causa_confirmada,
        "comentario": rev.comentario,
        "usuario_id": str(rev.usuario_id),
        "actualizado_en": rev.updated_at.isoformat() if rev.updated_at else None,
    }


def adjuntar_revisiones(diagnostico: dict, revisiones: list[RevisionDiagnostico]) -> dict:
    """Copia del diagnóstico con `revision` en cada zona revisada. No se guarda
    dentro del diagnóstico persistido: un recálculo no debe borrar el criterio
    del agrónomo."""
    por_zona = {r.zona_id: revision_a_dict(r) for r in revisiones}
    salida = copy.deepcopy(diagnostico)
    for f in salida.get("features", []):
        props = f.setdefault("properties", {})
        props["revision"] = por_zona.get(props.get("zona_id"))
    salida.setdefault("metadata", {})["n_zonas_revisadas"] = len(por_zona)
    return salida
