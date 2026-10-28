"""
Motor probabilístico (Naive Bayes) que corre en paralelo al motor de reglas.
Puro — sin I/O. Para cada zona calcula P(causa | evidencia) y devuelve un
ranking de causas con un nivel de certeza (los tres mensajes de CLAUDE.md).

    P(causa | e) ∝ P(causa | fase) · Π P(e_i | causa)

No hay datos con la causa confirmada a campo para entrenarlo, así que las
tablas iniciales son conocimiento experto (BORRADOR — a validar por un
agrónomo, ver docs/release-v4.0.0.md). Cada revisión del agrónomo (RFDR-04,
tabla revisiones_diagnostico) suma un caso etiquetado: las tablas se
actualizan como una Dirichlet con la tabla experta como prior de peso
PESO_PRIOR_EXPERTO casos. Con pocas revisiones manda la tabla experta; con
muchas, mandan los datos.

"Naive" = trata las evidencias como independientes dada la causa. No lo son
del todo (patrón y desvío están relacionados), pero con pocas evidencias
discretas el ranking resultante es razonable; las probabilidades absolutas
tienden a quedar sobreconfiadas.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.diagnostico.estadios import normalizar_estadio
from app.lotes.models import CultivoEnum

MODELO_VERSION = "0.1.0"
PESO_PRIOR_EXPERTO = 20.0

CAUSAS = [
    "sin_problema_detectado",
    "suelo_desnudo",
    "interferencia_vegetacion",
    "estres_biotico_fungico",
    "estres_biotico_insecto",
    "estres_nutricional_nitrogeno",
    "estres_nutricional_micro",
    "estres_nutricional_fosforo",
    "estres_hidrico",
    "compactacion_falla_siembra",
    "madurez_temprana_diferencial",
    "vigor_excesivo",
]

FASES = ["temprana", "vegetativa", "reproductiva", "madurez", "desconocida"]

VALORES_EVIDENCIA = {
    "desvio": ["muy_bajo", "bajo", "normal", "alto"],
    "patron": [
        "circular", "focos_aislados", "manchas_irregulares", "difuso_homogeneo",
        "por_sectores", "bordes_lote", "lineal",
    ],
    "ndvi_abs": ["bajo", "medio", "alto"],
    "ndre": ["bajo", "normal"],
    "exg": ["alto", "normal"],
}

# ── Tablas expertas (borrador) ────────────────────────────────────────
# Cada fila: P(valor | causa), en el orden de VALORES_EVIDENCIA.

_PRIOR_POR_FASE = {
    #                         sinp  suelo malez fung  insec N     micro P     hidr  comp  madur vigor
    "temprana":     [0.45, 0.10, 0.15, 0.02, 0.05, 0.04, 0.03, 0.06, 0.05, 0.05, 0.001, 0.001],
    "vegetativa":   [0.45, 0.03, 0.10, 0.06, 0.08, 0.08, 0.04, 0.04, 0.07, 0.04, 0.001, 0.02],
    "reproductiva": [0.42, 0.02, 0.05, 0.14, 0.12, 0.05, 0.04, 0.02, 0.09, 0.02, 0.01, 0.02],
    "madurez":      [0.45, 0.02, 0.04, 0.08, 0.06, 0.02, 0.02, 0.01, 0.08, 0.02, 0.18, 0.01],
    "desconocida":  [0.44, 0.04, 0.08, 0.08, 0.08, 0.05, 0.03, 0.03, 0.07, 0.03, 0.05, 0.02],
}

_VEROSIMILITUD = {
    "desvio": {  # muy_bajo, bajo, normal, alto
        "sin_problema_detectado":       [0.02, 0.13, 0.75, 0.10],
        "suelo_desnudo":                [0.85, 0.12, 0.025, 0.005],
        "interferencia_vegetacion":     [0.15, 0.40, 0.35, 0.10],
        "estres_biotico_fungico":       [0.35, 0.50, 0.13, 0.02],
        "estres_biotico_insecto":       [0.30, 0.50, 0.17, 0.03],
        "estres_nutricional_nitrogeno": [0.20, 0.55, 0.23, 0.02],
        "estres_nutricional_micro":     [0.10, 0.50, 0.37, 0.03],
        "estres_nutricional_fosforo":   [0.20, 0.55, 0.23, 0.02],
        "estres_hidrico":               [0.35, 0.50, 0.13, 0.02],
        "compactacion_falla_siembra":   [0.35, 0.50, 0.13, 0.02],
        "madurez_temprana_diferencial": [0.60, 0.35, 0.04, 0.01],
        "vigor_excesivo":               [0.01, 0.04, 0.25, 0.70],
    },
    "patron": {  # circular, focos, manchas, difuso, sectores, bordes, lineal
        "sin_problema_detectado":       [0.10, 0.08, 0.22, 0.25, 0.20, 0.10, 0.05],
        "suelo_desnudo":                [0.10, 0.15, 0.30, 0.10, 0.15, 0.10, 0.10],
        "interferencia_vegetacion":     [0.05, 0.15, 0.35, 0.10, 0.15, 0.15, 0.05],
        "estres_biotico_fungico":       [0.40, 0.25, 0.15, 0.05, 0.05, 0.05, 0.05],
        "estres_biotico_insecto":       [0.10, 0.25, 0.35, 0.05, 0.05, 0.15, 0.05],
        "estres_nutricional_nitrogeno": [0.03, 0.04, 0.10, 0.40, 0.35, 0.05, 0.03],
        "estres_nutricional_micro":     [0.03, 0.07, 0.30, 0.15, 0.15, 0.27, 0.03],
        "estres_nutricional_fosforo":   [0.03, 0.04, 0.10, 0.35, 0.40, 0.05, 0.03],
        "estres_hidrico":               [0.03, 0.04, 0.13, 0.45, 0.25, 0.07, 0.03],
        "compactacion_falla_siembra":   [0.02, 0.03, 0.08, 0.04, 0.10, 0.13, 0.60],
        "madurez_temprana_diferencial": [0.10, 0.30, 0.35, 0.10, 0.10, 0.03, 0.02],
        "vigor_excesivo":               [0.05, 0.05, 0.15, 0.45, 0.25, 0.03, 0.02],
    },
    "ndvi_abs": {  # bajo (<0.20), medio, alto (>0.75)
        "sin_problema_detectado":       [0.05, 0.65, 0.30],
        "suelo_desnudo":                [0.90, 0.098, 0.002],
        "interferencia_vegetacion":     [0.10, 0.80, 0.10],
        "estres_biotico_fungico":       [0.10, 0.80, 0.10],
        "estres_biotico_insecto":       [0.10, 0.80, 0.10],
        "estres_nutricional_nitrogeno": [0.08, 0.85, 0.07],
        "estres_nutricional_micro":     [0.05, 0.80, 0.15],
        "estres_nutricional_fosforo":   [0.10, 0.85, 0.05],
        "estres_hidrico":               [0.15, 0.80, 0.05],
        "compactacion_falla_siembra":   [0.20, 0.75, 0.05],
        "madurez_temprana_diferencial": [0.45, 0.53, 0.02],
        "vigor_excesivo":               [0.005, 0.20, 0.795],
    },
    "ndre": {  # bajo (<0.20), normal
        "sin_problema_detectado":       [0.10, 0.90],
        "suelo_desnudo":                [0.90, 0.10],
        "interferencia_vegetacion":     [0.30, 0.70],
        "estres_biotico_fungico":       [0.55, 0.45],
        "estres_biotico_insecto":       [0.35, 0.65],
        "estres_nutricional_nitrogeno": [0.85, 0.15],
        "estres_nutricional_micro":     [0.75, 0.25],
        "estres_nutricional_fosforo":   [0.70, 0.30],
        "estres_hidrico":               [0.50, 0.50],
        "compactacion_falla_siembra":   [0.40, 0.60],
        "madurez_temprana_diferencial": [0.70, 0.30],
        "vigor_excesivo":               [0.03, 0.97],
    },
    "exg": {  # alto (>0.20), normal
        **{c: [0.15, 0.85] for c in CAUSAS},
        "suelo_desnudo": [0.02, 0.98],
        "interferencia_vegetacion": [0.80, 0.20],
        "vigor_excesivo": [0.40, 0.60],
    },
}

# Causas que solo tienen sentido en un cultivo puntual (mismo criterio que
# las reglas R60/R70): fuera de él su prior se multiplica por este factor.
_RESTRICCION_CULTIVO = {
    "madurez_temprana_diferencial": ({CultivoEnum.algodon}, 0.05),
    "vigor_excesivo": ({CultivoEnum.maiz}, 0.3),
}

_FASE_MADUREZ = {
    CultivoEnum.soja: {"r6", "r7", "r8"},
    CultivoEnum.maiz: {"r4", "r5", "r6"},
    CultivoEnum.algodon: {"r4", "r5", "apertura_de_capsulas"},
    CultivoEnum.sorgo: {"llenado_de_grano"},
}
_FASE_REPRODUCTIVA_EXTRA = {"boton_floral", "floracion", "espigado"}
_FASE_TEMPRANA = {"ve", "vc", "v1", "v2", "v3"}

MENSAJES_CERTEZA = {
    "alta": "Diagnóstico probable con alta confianza",
    "media": "Diagnóstico probable — conviene verificar en campo",
    "ambigua": "Diagnóstico ambiguo — se requiere verificación en campo",
}


@dataclass
class EvidenciaZona:
    cultivo: CultivoEnum
    estadio: str | None
    patron: str
    ndvi: float
    ndvi_promedio_lote: float
    ndvi_esperado: float | None = None
    ndvi_esperado_min: float | None = None
    ndre: float | None = None
    exg: float | None = None

    def a_dict(self) -> dict:
        return {
            "cultivo": self.cultivo.value, "estadio": self.estadio, "patron": self.patron,
            "ndvi": self.ndvi, "ndvi_promedio_lote": self.ndvi_promedio_lote,
            "ndvi_esperado": self.ndvi_esperado, "ndvi_esperado_min": self.ndvi_esperado_min,
            "ndre": self.ndre, "exg": self.exg,
        }

    @classmethod
    def desde_dict(cls, d: dict) -> "EvidenciaZona":
        return cls(
            cultivo=CultivoEnum(d["cultivo"]), estadio=d.get("estadio"), patron=d["patron"],
            ndvi=d["ndvi"], ndvi_promedio_lote=d["ndvi_promedio_lote"],
            ndvi_esperado=d.get("ndvi_esperado"), ndvi_esperado_min=d.get("ndvi_esperado_min"),
            ndre=d.get("ndre"), exg=d.get("exg"),
        )


def fase_fenologica(cultivo: CultivoEnum, estadio: str | None) -> str:
    est = normalizar_estadio(estadio)
    if est is None:
        return "desconocida"
    if est in _FASE_TEMPRANA:
        return "temprana"
    if est in _FASE_MADUREZ.get(cultivo, set()):
        return "madurez"
    if est.startswith("r") or est in _FASE_REPRODUCTIVA_EXTRA:
        return "reproductiva"
    return "vegetativa"


def discretizar(ev: EvidenciaZona) -> dict[str, str]:
    """Evidencia continua → categorías de VALORES_EVIDENCIA. Las evidencias
    sin dato (índice no calculado) se omiten — no penalizan a ninguna causa."""
    if ev.ndvi_esperado is not None and ev.ndvi_esperado_min is not None:
        banda = ev.ndvi_esperado - ev.ndvi_esperado_min
        if ev.ndvi < ev.ndvi_esperado_min - 0.15:
            desvio = "muy_bajo"
        elif ev.ndvi < ev.ndvi_esperado_min:
            desvio = "bajo"
        elif ev.ndvi > ev.ndvi_esperado + banda:
            desvio = "alto"
        else:
            desvio = "normal"
    else:
        ratio = (ev.ndvi - ev.ndvi_promedio_lote) / ev.ndvi_promedio_lote if ev.ndvi_promedio_lote > 0 else 0.0
        desvio = "muy_bajo" if ratio < -0.35 else "bajo" if ratio < -0.10 else "alto" if ratio > 0.15 else "normal"

    out = {
        "desvio": desvio,
        "ndvi_abs": "bajo" if ev.ndvi < 0.20 else "alto" if ev.ndvi > 0.75 else "medio",
    }
    if ev.patron in VALORES_EVIDENCIA["patron"]:
        out["patron"] = ev.patron
    if ev.ndre is not None:
        out["ndre"] = "bajo" if ev.ndre < 0.20 else "normal"
    if ev.exg is not None:
        out["exg"] = "alto" if ev.exg > 0.20 else "normal"
    return out


@dataclass
class ModeloBayes:
    prior: dict[str, dict[str, float]]                    # fase → causa → p
    verosimilitud: dict[str, dict[str, dict[str, float]]]  # evidencia → causa → valor → p
    n_casos: int = 0
    casos_por_causa: dict[str, int] = field(default_factory=dict)


def _normalizar(d: dict[str, float]) -> dict[str, float]:
    total = sum(d.values()) or 1.0
    return {k: v / total for k, v in d.items()}


def construir_modelo(casos: list[tuple[EvidenciaZona, str]] | None = None) -> ModeloBayes:
    """
    casos: (evidencia, causa confirmada por el agrónomo). Actualización
    Dirichlet de cada tabla: (PESO·p_experto + n_observado) / (PESO + n_total).
    """
    casos = [(ev, c) for ev, c in (casos or []) if c in CAUSAS]

    conteo_prior: dict[str, dict[str, float]] = {f: {c: 0.0 for c in CAUSAS} for f in FASES}
    conteo_ev: dict[str, dict[str, dict[str, float]]] = {
        e: {c: {v: 0.0 for v in vals} for c in CAUSAS} for e, vals in VALORES_EVIDENCIA.items()
    }
    por_causa: dict[str, int] = {}
    for ev, causa in casos:
        por_causa[causa] = por_causa.get(causa, 0) + 1
        conteo_prior[fase_fenologica(ev.cultivo, ev.estadio)][causa] += 1
        for nombre, valor in discretizar(ev).items():
            conteo_ev[nombre][causa][valor] += 1

    prior = {}
    for fase in FASES:
        experto = dict(zip(CAUSAS, _PRIOR_POR_FASE[fase]))
        experto = _normalizar(experto)
        n_fase = sum(conteo_prior[fase].values())
        prior[fase] = {
            c: (PESO_PRIOR_EXPERTO * experto[c] + conteo_prior[fase][c]) / (PESO_PRIOR_EXPERTO + n_fase)
            for c in CAUSAS
        }

    verosimilitud = {}
    for nombre, valores in VALORES_EVIDENCIA.items():
        verosimilitud[nombre] = {}
        for causa in CAUSAS:
            experto = _normalizar(dict(zip(valores, _VEROSIMILITUD[nombre][causa])))
            n_causa = sum(conteo_ev[nombre][causa].values())
            verosimilitud[nombre][causa] = {
                v: (PESO_PRIOR_EXPERTO * experto[v] + conteo_ev[nombre][causa][v]) / (PESO_PRIOR_EXPERTO + n_causa)
                for v in valores
            }

    return ModeloBayes(prior=prior, verosimilitud=verosimilitud, n_casos=len(casos), casos_por_causa=por_causa)


def nivel_certeza(ranking: list[tuple[str, float]]) -> str:
    p1 = ranking[0][1]
    p2 = ranking[1][1] if len(ranking) > 1 else 0.0
    if p1 - p2 < 0.15:
        return "ambigua"
    if p1 >= 0.60 and p1 - p2 >= 0.25:
        return "alta"
    return "media"


def evaluar_bayes(ev: EvidenciaZona, modelo: ModeloBayes) -> dict:
    fase = fase_fenologica(ev.cultivo, ev.estadio)
    evidencias = discretizar(ev)

    puntaje = {}
    for causa in CAUSAS:
        p = modelo.prior[fase][causa]
        cultivos_ok, factor = _RESTRICCION_CULTIVO.get(causa, (None, 1.0))
        if cultivos_ok is not None and ev.cultivo not in cultivos_ok:
            p *= factor
        for nombre, valor in evidencias.items():
            p *= modelo.verosimilitud[nombre][causa][valor]
        puntaje[causa] = p

    posterior = _normalizar(puntaje)
    ranking = sorted(posterior.items(), key=lambda kv: kv[1], reverse=True)
    certeza = nivel_certeza(ranking)
    return {
        "ranking": [{"causa": c, "probabilidad": round(p, 3)} for c, p in ranking[:3]],
        "posterior": {c: round(p, 4) for c, p in ranking},
        "certeza": certeza,
        "mensaje": MENSAJES_CERTEZA[certeza],
        "evidencias": evidencias,
        "fase": fase,
    }


def causa_efectiva(regla_id: str | None, causa_indice: str | None) -> str | None:
    """
    Causa de la regla expresada en las clases del motor bayesiano: R01
    comparte causa_indice con R99 pero es suelo desnudo, y R80
    (bajo_vigor_estadio) no es una causa sino "no se sabe" — sin clase.
    """
    if regla_id == "R01":
        return "suelo_desnudo"
    if causa_indice in CAUSAS:
        return causa_indice
    return None
