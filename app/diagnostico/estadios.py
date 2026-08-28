"""
Normalización y catálogo de estadios fenológicos usados por el motor de
reglas. Los tokens están extraídos literalmente de la sección 5 del
documento de referencia (las condiciones de cada regla), no de la sección 3
(descriptiva, con etiquetas más largas e inconsistentes entre cultivos).

lotes.estadio_fenologico es texto libre cargado por el usuario (ej. "R3",
"Botón floral") — normalizar_estadio() lo lleva a una forma comparable
(minúsculas, sin acentos, espacios → guión bajo) antes de matchear contra
los estadios de cada Regla.
"""

import re
import unicodedata

from app.lotes.models import CultivoEnum


def normalizar_estadio(texto: str | None) -> str | None:
    if not texto:
        return None
    sin_acentos = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    normalizado = re.sub(r"\s+", "_", sin_acentos.strip().lower())
    return normalizado or None


# Catálogo canónico por cultivo — unión de todos los tokens que aparecen en
# las condiciones de "Estadios" de las 20 reglas (app/diagnostico/reglas.py)
# para ese cultivo. Sirve de referencia/picklist; el matcheo real de cada
# regla usa su propio conjunto de estadios (Regla.estadios), no este catálogo.
ESTADIOS_VALIDOS_POR_CULTIVO: dict[CultivoEnum, set[str]] = {
    CultivoEnum.soja: {
        "v1", "v2", "v3", "v4", "v5", "v6",
        "r1", "r2", "r3", "r4", "r5",
    },
    CultivoEnum.maiz: {
        "v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8", "v9", "v10", "v11", "v12",
        "vt", "r1",
    },
    CultivoEnum.algodon: {
        "v4", "v5", "v6", "v7", "v8",
        "boton_floral", "floracion", "r1", "r2", "r3", "r4", "r5",
        "apertura_de_capsulas",
    },
    CultivoEnum.sorgo: {
        "v4", "v5", "v6", "v7", "v8", "v9", "v10", "v11", "v12", "vt",
        "espigado", "floracion",
    },
}


def estadio_coincide(estadio_normalizado: str | None, estadios_regla: frozenset[str] | None) -> bool:
    """
    estadios_regla=None significa "todos los estadios" (la regla no filtra
    por estadio) y siempre coincide. Un lote sin estadio cargado no puede
    coincidir con una regla que sí exige un estadio específico.
    """
    if estadios_regla is None:
        return True
    if estadio_normalizado is None:
        return False
    return estadio_normalizado in estadios_regla
