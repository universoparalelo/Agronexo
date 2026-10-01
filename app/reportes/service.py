"""
Arma el contexto del reporte ejecutivo y genera el PDF final.

Input: el mismo dict que devuelve app.diagnostico.service.generar_diagnostico
(FeatureCollection enriquecida + unidades_manejo + metadata) — este módulo
no vuelve a tocar DB ni MinIO, es una transformación pura de datos ya
resueltos (armar el contexto Jinja2 + generar el mapa) más el renderizado.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

from app.reportes.mapa import generar_imagen_mapa_zonas

CULTIVO_LABEL = {"soja": "Soja", "maiz": "Maíz", "algodon": "Algodón", "sorgo": "Sorgo"}

CONFIANZA_CORTO = {"alta": "Alta", "media": "Media", "baja": "Baja"}

SEVERIDAD_LABELS = {
    "critica": "Crítica",
    "moderada": "Moderada",
    "leve": "Leve",
    "normal": "Normal",
    "vigorosa": "Vigorosa",
}

# Versión corta para la columna de tabla — mismo mapeo que la constante
# CAUSA_LABELS de frontend/src/components/TablaDiagnostico.jsx.
# app.diagnostico.texto.CAUSA_LABELS ya existe pero es la forma narrativa
# larga usada dentro de texto_explicativo, no entra en una celda angosta.
CAUSA_CORTO = {
    "sin_problema_detectado": "Sin problema",
    "interferencia_vegetacion": "Malezas",
    "estres_biotico_fungico": "Hongo",
    "estres_biotico_insecto": "Insecto",
    "estres_nutricional_nitrogeno": "Déficit N",
    "estres_nutricional_micro": "Déficit micro",
    "estres_nutricional_fosforo": "Déficit P",
    "estres_hidrico": "Estrés hídrico",
    "madurez_temprana_diferencial": "Madurez dif.",
    "vigor_excesivo": "Vigor excesivo",
}

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_env = Environment(
    loader=FileSystemLoader(_TEMPLATES_DIR),
    autoescape=select_autoescape(["html"]),
)


def generar_pdf_reporte(diagnostico: dict) -> bytes:
    """
    Recibe el dict completo de generar_diagnostico() y devuelve los bytes
    del PDF ejecutivo (mapa + estadísticas por zona + diagnóstico narrado).
    """
    metadata = diagnostico.get("metadata", {})
    features = diagnostico.get("features", [])

    mapa_png = generar_imagen_mapa_zonas(diagnostico, modo="clase")
    mapa_base64 = "data:image/png;base64," + base64.b64encode(mapa_png).decode("ascii")

    zonas = [_zona_a_contexto(f.get("properties", {})) for f in features]
    con_problema = [
        f for f in features
        if f.get("properties", {}).get("regla_id") not in ("R99", "R00")
    ]

    contexto = {
        "lote_nombre": metadata.get("lote_nombre") or "Lote sin nombre",
        "cultivo_label": CULTIVO_LABEL.get(metadata.get("cultivo"), metadata.get("cultivo")),
        "fecha_vuelo": _formatear_fecha(metadata.get("fecha_vuelo")) or "—",
        "estadio_fenologico": metadata.get("estadio_fenologico"),
        "generado_en": _formatear_fecha(metadata.get("calculado_en"))
            or datetime.now(timezone.utc).strftime("%d/%m/%Y"),
        "mapa_base64": mapa_base64,
        "resumen_texto": metadata.get("resumen_general", ""),
        "n_zonas": len(features),
        "n_zonas_con_problema": len(con_problema),
        "area_afectada_ha": sum(f.get("properties", {}).get("area_ha", 0.0) for f in con_problema),
        "ndvi_promedio_lote": metadata.get("ndvi_promedio_lote", 0.0),
        "n_unidades_manejo": metadata.get("n_unidades_manejo", len(diagnostico.get("unidades_manejo", []))),
        "zonas": zonas,
    }

    template = _env.get_template("reporte_ejecutivo.html")
    html_str = template.render(**contexto)

    return HTML(string=html_str, base_url=str(_TEMPLATES_DIR)).write_pdf()


def _zona_a_contexto(props: dict) -> dict:
    severidad = props.get("severidad", "normal")
    confianza = props.get("confianza", "media")
    causa = props.get("causa_indice", "sin_problema_detectado")
    productos = props.get("productos_sugeridos", [])

    return {
        "zona_id": props.get("zona_id"),
        "area_ha": props.get("area_ha", 0.0),
        "ndvi_promedio": props.get("ndvi_promedio", 0.0),
        "severidad": severidad,
        "severidad_label": SEVERIDAD_LABELS.get(severidad, severidad),
        "causa_label": CAUSA_CORTO.get(causa, causa),
        "confianza_corto": CONFIANZA_CORTO.get(confianza, confianza),
        "excluida": bool(props.get("excluida", False)),
        "sin_problema": props.get("regla_id") == "R99",
        "texto_explicativo": props.get("texto_explicativo", ""),
        "accion_recomendada": props.get("accion_recomendada", ""),
        "productos_texto": ", ".join(p["nombre"] for p in productos[:3]) if productos else "",
    }


def _formatear_fecha(valor: str | None) -> str | None:
    if not valor:
        return None
    try:
        dt = datetime.fromisoformat(valor.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y")
    except ValueError:
        return valor
