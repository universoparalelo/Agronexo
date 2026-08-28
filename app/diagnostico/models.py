"""
Enums del motor de diagnóstico. No hay tabla de base de datos para esto
(decisión de alcance: el diagnóstico se calcula on-demand, ver
app/diagnostico/service.py) — son tipos puros usados por engine.py/reglas.py.
"""

import enum


class PatronEspacialEnum(str, enum.Enum):
    circular = "circular"
    lineal = "lineal"
    difuso_homogeneo = "difuso_homogeneo"
    manchas_irregulares = "manchas_irregulares"
    bordes_lote = "bordes_lote"
    focos_aislados = "focos_aislados"
    por_sectores = "por_sectores"


class ConfianzaEnum(str, enum.Enum):
    alta = "alta"
    media = "media"
    baja = "baja"


class CausaIndiceEnum(str, enum.Enum):
    sin_problema_detectado = "sin_problema_detectado"
    interferencia_vegetacion = "interferencia_vegetacion"
    estres_biotico_fungico = "estres_biotico_fungico"
    estres_biotico_insecto = "estres_biotico_insecto"
    estres_nutricional_nitrogeno = "estres_nutricional_nitrogeno"
    estres_nutricional_micro = "estres_nutricional_micro"
    estres_nutricional_fosforo = "estres_nutricional_fosforo"
    estres_hidrico = "estres_hidrico"
    madurez_temprana_diferencial = "madurez_temprana_diferencial"
    vigor_excesivo = "vigor_excesivo"
