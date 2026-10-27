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


def generar_pdf_reporte(diagnostico: dict, datos_aplicador: dict | None = None) -> bytes:
    """
    Recibe el dict completo de generar_diagnostico() y devuelve los bytes
    del PDF ejecutivo (mapa + estadísticas por zona + diagnóstico narrado).

    datos_aplicador (HU-R4-10): dict ya resuelto por el router con
    nombre/nombre_empresa/matricula_aplicador/logo_empresa_base64 del
    usuario — este módulo no toca MinIO (ver docstring de arriba), por eso
    el logo llega ya descargado y en base64, igual que mapa_base64.
    """
    metadata = diagnostico.get("metadata", {})
    features = diagnostico.get("features", [])
    datos_aplicador = datos_aplicador or {}

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
        # Trazabilidad (HU-R4-02) — para justificar la prescripción ante el
        # productor o un control según la Ley 6.312.
        "archivo_original": metadata.get("archivo_original"),
        "subido_por": metadata.get("subido_por"),
        "metodo_umbral": metadata.get("metodo_umbral"),
        "mapeo_bandas": _formatear_mapeo_bandas(metadata.get("mapeo_bandas")),
        "motor_version": metadata.get("motor_version"),
        # Perfil del aplicador (HU-R4-10)
        "nombre_empresa": datos_aplicador.get("nombre_empresa"),
        "aplicador_nombre": datos_aplicador.get("aplicador_nombre"),
        "matricula_aplicador": datos_aplicador.get("matricula_aplicador"),
        "logo_empresa_base64": datos_aplicador.get("logo_empresa_base64"),
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
        "como_confirmar_campo": props.get("como_confirmar_campo", ""),
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


_BANDA_LABELS = {"BLUE": "Azul", "GREEN": "Verde", "RED": "Rojo", "RE": "Red Edge", "NIR": "NIR"}


def _formatear_mapeo_bandas(mapeo: dict | None) -> str | None:
    """Ver frontend/src/pages/ResultadosVuelo.jsx (BANDA_LABELS) — mismo criterio."""
    if not mapeo:
        return None
    partes = [f"{_BANDA_LABELS.get(nombre, nombre)}: banda {num}" for nombre, num in mapeo.items() if num is not None]
    return " · ".join(partes) or None
