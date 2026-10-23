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

from app.diagnostico.texto import CONFIANZA_LABELS, PATRON_LABELS
from app.reportes.mapa import generar_imagen_mapa_zonas

CULTIVO_LABEL = {"soja": "Soja", "maiz": "Maíz", "algodon": "Algodón", "sorgo": "Sorgo"}

CONFIANZA_CORTO = {"alta": "Alta", "media": "Media", "baja": "Baja"}

# Resumen ejecutivo: el lector es el productor, no el agrónomo — se evita
# hablar de NDVI, reglas o patrones y se dice qué pasa y qué hacer.
CAUSA_SIMPLE = {
    # R01 comparte causa_indice "sin_problema_detectado" con R99 (no hay nada
    # que tratar con productos), pero para el productor sí es algo a revisar.
    "suelo_desnudo": (
        "zonas sin plantas (suelo desnudo)",
        "verificar si hubo falla de siembra o pisoteo; no se corrige con productos",
    ),
    "interferencia_vegetacion": (
        "presencia de malezas",
        "recorrer la zona, identificar la maleza y evaluar un control dirigido",
    ),
    "estres_biotico_fungico": (
        "posible enfermedad por hongos",
        "confirmar síntomas en hojas y tallos antes de decidir un fungicida",
    ),
    "estres_biotico_insecto": (
        "posible ataque de insectos",
        "monitorear la plaga y aplicar solo si supera el umbral de daño",
    ),
    "estres_nutricional_nitrogeno": (
        "falta de nitrógeno",
        "evaluar una fertilización nitrogenada en esa zona",
    ),
    "estres_nutricional_micro": (
        "falta de micronutrientes",
        "confirmar con análisis foliar y evaluar una aplicación foliar",
    ),
    "estres_nutricional_fosforo": (
        "falta de fósforo",
        "revisar el análisis de suelo y planificar la fertilización",
    ),
    "estres_hidrico": (
        "falta de agua (estrés hídrico)",
        "revisar humedad del suelo; si hay riego, priorizar esta zona",
    ),
    "madurez_temprana_diferencial": (
        "plantas que maduran antes que el resto",
        "verificar el avance de madurez para planificar la cosecha",
    ),
    "compactacion_falla_siembra": (
        "franjas con menos plantas o plantas más chicas (compactación o falla de siembra)",
        "revisar a campo si faltan plantas o hay piso de arado; no se corrige con productos",
    ),
    "bajo_vigor_estadio": (
        "cultivo más atrasado de lo normal para su etapa",
        "recorrer el lote para identificar la causa antes de aplicar nada",
    ),
    "vigor_excesivo": (
        "crecimiento por encima de lo normal",
        "vigilar vuelco o exceso de follaje; en algodón evaluar regulador de crecimiento",
    ),
}

URGENCIA = {
    "critica": "atender cuanto antes",
    "moderada": "atender en los próximos días",
    "leve": "vigilar",
    "vigorosa": "vigilar",
    "normal": "vigilar",
}

_ORDEN_SEVERIDAD = {"critica": 0, "moderada": 1, "leve": 2, "vigorosa": 3, "normal": 4}

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
    "compactacion_falla_siembra": "Compactación/siembra",
    "bajo_vigor_estadio": "Vigor bajo p/ estadio",
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
        "variedad": metadata.get("variedad"),
        "indices_usados": ", ".join(i.upper() for i in metadata.get("indices_disponibles") or ["ndvi"]),
        "resumen_ejecutivo": generar_resumen_ejecutivo(features),
        "unidades": [_unidad_a_contexto(u.get("properties", {})) for u in diagnostico.get("unidades_manejo", [])],
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
        "regla_nombre": props.get("regla_nombre", ""),
        "patron_label": PATRON_LABELS.get(props.get("patron_espacial", ""), props.get("patron_espacial", "")),
        "confianza_label": CONFIANZA_LABELS.get(confianza, confianza),
        "productos_texto": ", ".join(p["nombre"] for p in productos[:3]) if productos else "",
        "productos_completo": ", ".join(p["nombre"] for p in productos),
    }


def _unidad_a_contexto(props: dict) -> dict:
    severidad = props.get("severidad", "normal")
    productos = props.get("productos_sugeridos", [])
    return {
        "unidad_id": props.get("unidad_id"),
        "severidad": severidad,
        "severidad_label": SEVERIDAD_LABELS.get(severidad, severidad),
        "regla_nombre": props.get("regla_nombre", ""),
        "area_total_ha": props.get("area_total_ha", 0.0),
        "n_zonas": props.get("n_zonas", 1),
        "zona_ids": ", ".join(f"#{z}" for z in props.get("zona_ids", [])),
        "ndvi_promedio": props.get("ndvi_promedio"),
        "texto_unidad": props.get("texto_unidad", ""),
        "productos_completo": ", ".join(p["nombre"] for p in productos),
    }


def generar_resumen_ejecutivo(features: list[dict]) -> dict:
    """
    Versión no técnica del diagnóstico para la primera página del PDF:
    estado general en porcentaje de superficie, problemas agrupados por causa
    (de más a menos urgente) y el paso siguiente concreto.
    """
    props = [f.get("properties", {}) for f in features]
    analizadas = [p for p in props if p.get("regla_id") != "R00"]
    area_total = sum(p.get("area_ha", 0.0) for p in analizadas)
    con_problema = [p for p in analizadas if p.get("regla_id") != "R99"]
    area_problema = sum(p.get("area_ha", 0.0) for p in con_problema)
    pct_problema = (area_problema / area_total * 100) if area_total > 0 else 0.0

    if not con_problema:
        estado = (
            f"El lote se ve sano: en las {area_total:.1f} ha analizadas no se detectaron "
            f"problemas. No hace falta intervenir por ahora; conviene repetir el vuelo "
            f"en 2 o 3 semanas para seguir la evolución."
        )
    else:
        pct_sano = 100 - pct_problema
        estado = (
            f"El {pct_sano:.0f}% del lote se ve sano. El {pct_problema:.0f}% restante "
            f"({area_problema:.1f} ha de {area_total:.1f} ha) muestra señales de algún problema "
            f"que conviene revisar."
        )

    grupos: dict[str, dict] = {}
    for p in con_problema:
        causa = "suelo_desnudo" if p.get("regla_id") == "R01" else p.get("causa_indice", "")
        g = grupos.setdefault(causa, {
            "area": 0.0, "n": 0, "peor": "normal", "dudosas": 0, "regla_nombre": p.get("regla_nombre", ""),
        })
        g["area"] += p.get("area_ha", 0.0)
        g["n"] += 1
        sev = p.get("severidad", "normal")
        if _ORDEN_SEVERIDAD.get(sev, 9) < _ORDEN_SEVERIDAD.get(g["peor"], 9):
            g["peor"] = sev
        if p.get("confianza") in ("media", "baja"):
            g["dudosas"] += 1

    problemas = []
    for causa, g in sorted(grupos.items(), key=lambda kv: (_ORDEN_SEVERIDAD.get(kv[1]["peor"], 9), -kv[1]["area"])):
        que_es, que_hacer = CAUSA_SIMPLE.get(
            causa, (g["regla_nombre"] or causa.replace("_", " "), "recorrer la zona y ver qué está pasando"),
        )
        problemas.append({
            "que_es": que_es[0].upper() + que_es[1:],
            "area_ha": g["area"],
            "n_zonas": g["n"],
            "urgencia": URGENCIA.get(g["peor"], "vigilar"),
            "severidad": g["peor"],
            "que_hacer": que_hacer[0].upper() + que_hacer[1:],
        })

    n_dudosas = sum(g["dudosas"] for g in grupos.values())
    if not con_problema:
        proximo_paso = None
    else:
        proximo_paso = (
            "Antes de comprar o aplicar productos, recorrer las zonas marcadas en el mapa y "
            "confirmar el problema a campo. Cada zona del detalle técnico explica cómo hacerlo "
            "(sección \"Cómo confirmar en campo\")."
        )
        if n_dudosas:
            s = "s" if n_dudosas != 1 else ""
            proximo_paso += (
                f" En {n_dudosas} zona{s} el sistema no tiene certeza sobre la causa: ahí la "
                f"visita a campo es imprescindible."
            )

    return {"estado": estado, "problemas": problemas, "proximo_paso": proximo_paso}


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
