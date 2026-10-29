"""
Arma el contexto del documento de orden de trabajo y genera el PDF final.

Input: el dict de app.diagnostico.orden_trabajo.generar_orden_trabajo()
(dosis por unidad de manejo, ya resueltas) + la metadata del diagnóstico
(app.diagnostico.service.generar_diagnostico). Mismo pipeline técnico que
app/reportes/service.py (Jinja2 + WeasyPrint), duplicado a propósito en
vez de reusado: RFSA-04 (orden de trabajo / prescripción) es un dominio
propio, separado del reporte ejecutivo de diagnóstico.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.diagnostico.models import ProductoFitosanitario

CULTIVO_LABEL = {"soja": "Soja", "maiz": "Maíz", "algodon": "Algodón", "sorgo": "Sorgo"}

SEVERIDAD_LABELS = {
    "critica": "Crítica",
    "moderada": "Moderada",
    "leve": "Leve",
    "normal": "Normal",
    "vigorosa": "Vigorosa",
}

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
    "compactacion_falla_siembra": "Compactación / falla de siembra",
    "bajo_vigor_estadio": "Vigor bajo para el estadio",
}

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_env = Environment(
    loader=FileSystemLoader(_TEMPLATES_DIR),
    autoescape=select_autoescape(["html"]),
)


async def cargar_catalogo_dosis(db: AsyncSession) -> dict[str, dict]:
    """
    Catálogo indexado por NOMBRE de producto — a diferencia de
    app.diagnostico.service._cargar_catalogo_productos (indexado por
    causa_indice, para sugerir productos). generar_orden_trabajo() ya
    recibe el producto puntual sugerido por unidad de manejo y necesita
    resolver su dosis_referencia/restricciones por nombre.
    """
    result = await db.execute(select(ProductoFitosanitario))
    return {
        prod.nombre: {
            "dosis_referencia": prod.dosis_referencia,
            "unidad": prod.unidad,
            "restricciones_ambientales": prod.restricciones_ambientales,
            "instrucciones_seguridad": prod.instrucciones_seguridad,
        }
        for prod in result.scalars().all()
    }


def generar_pdf_orden_trabajo(orden: dict, metadata: dict, datos_aplicador: dict | None = None) -> bytes:
    """
    Recibe el dict de generar_orden_trabajo() (items + totales_por_producto
    + area_total_tratada_ha) y la metadata del diagnóstico del vuelo, y
    devuelve los bytes del PDF de orden de trabajo.

    datos_aplicador (HU-R4-10): igual a app.reportes.service — dict ya
    resuelto por el router con los datos de perfil del usuario (incluye
    logo_empresa_base64 ya descargado, este módulo no toca MinIO).
    """
    items_raw = orden.get("items", [])
    items = [_item_a_contexto(item) for item in items_raw]
    datos_aplicador = datos_aplicador or {}

    contexto = {
        "lote_nombre": metadata.get("lote_nombre") or "Lote sin nombre",
        "cultivo_label": CULTIVO_LABEL.get(metadata.get("cultivo"), metadata.get("cultivo")),
        "fecha_vuelo": _formatear_fecha(metadata.get("fecha_vuelo")) or "—",
        "estadio_fenologico": metadata.get("estadio_fenologico"),
        "generado_en": _formatear_fecha(metadata.get("calculado_en"))
            or datetime.now(timezone.utc).strftime("%d/%m/%Y"),
        "n_unidades": len(items),
        "area_total_tratada_ha": orden.get("area_total_tratada_ha", 0.0),
        "items": items,
        "totales": [_total_a_contexto(t) for t in orden.get("totales_por_producto", [])],
        "productos_con_seguridad": _productos_con_seguridad(items_raw),
        "productos_sin_seguridad_cargada": _productos_sin_seguridad(items_raw),
        "hay_items_sin_dosis": any(i["sin_dosis_referencia"] for i in items),
        # Perfil del aplicador (HU-R4-10)
        "nombre_empresa": datos_aplicador.get("nombre_empresa"),
        "aplicador_nombre": datos_aplicador.get("aplicador_nombre"),
        "matricula_aplicador": datos_aplicador.get("matricula_aplicador"),
        "aplicador_cuit": datos_aplicador.get("aplicador_cuit"),
        "aplicador_contacto": datos_aplicador.get("aplicador_contacto"),
        "logo_empresa_base64": datos_aplicador.get("logo_empresa_base64"),
    }

    template = _env.get_template("orden_trabajo.html")
    html_str = template.render(**contexto)

    # Ver el comentario equivalente en app/reportes/service.py.
    from weasyprint import HTML

    return HTML(string=html_str, base_url=str(_TEMPLATES_DIR)).write_pdf()


def _item_a_contexto(item: dict) -> dict:
    severidad = item.get("severidad", "normal")
    causa = item.get("causa_indice", "sin_problema_detectado")

    return {
        "unidad_id": item.get("unidad_id"),
        "causa_label": CAUSA_CORTO.get(causa, causa),
        "severidad": severidad,
        "severidad_label": SEVERIDAD_LABELS.get(severidad, severidad),
        "area_ha": item.get("area_ha", 0.0),
        "zona_ids_texto": ", ".join(f"#{z}" for z in item.get("zona_ids", [])),
        "producto": item.get("producto") or "— (sin producto sugerido)",
        "dosis_por_ha": item.get("dosis_por_ha"),
        "unidad_dosis": item.get("unidad_dosis") or "",
        "unidad_volumen": _unidad_volumen(item.get("unidad_dosis")),
        "como_confirmar_campo": item.get("como_confirmar_campo", ""),
        "volumen_total": item.get("volumen_total"),
        "sin_dosis_referencia": bool(item.get("sin_dosis_referencia", False)),
    }


def _unidad_volumen(unidad_dosis: str | None) -> str:
    # La dosis viene por hectárea ("L/ha"); el volumen total es la cantidad, sin "/ha".
    return (unidad_dosis or "").split("/")[0]


def _total_a_contexto(total: dict) -> dict:
    return {
        "producto": total.get("producto"),
        "area_ha": total.get("area_ha", 0.0),
        "volumen_total": total.get("volumen_total", 0.0),
        "unidad_dosis": total.get("unidad_dosis") or "",
        "unidad_volumen": _unidad_volumen(total.get("unidad_dosis")),
    }


def _productos_con_seguridad(items: list[dict]) -> list[dict]:
    """Un bloque por producto usado (deduplicado) que tenga al menos un
    campo de seguridad cargado — para la sección de seguridad del PDF."""
    vistos: dict[str, dict] = {}
    for item in items:
        producto = item.get("producto")
        if not producto or producto in vistos:
            continue
        restricciones = item.get("restricciones_ambientales")
        instrucciones = item.get("instrucciones_seguridad")
        if not restricciones and not instrucciones:
            continue
        vistos[producto] = {
            "producto": producto,
            "restricciones_ambientales": restricciones,
            "instrucciones_seguridad": instrucciones,
        }
    return list(vistos.values())


def _productos_sin_seguridad(items: list[dict]) -> list[str]:
    """Productos usados en esta orden sin ficha de seguridad cargada — para
    advertir explícitamente en vez de omitir la sección en silencio."""
    vistos: list[str] = []
    for item in items:
        producto = item.get("producto")
        if not producto or producto in vistos:
            continue
        if not item.get("restricciones_ambientales") and not item.get("instrucciones_seguridad"):
            vistos.append(producto)
    return vistos


def _formatear_fecha(valor: str | None) -> str | None:
    if not valor:
        return None
    try:
        dt = datetime.fromisoformat(valor.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y")
    except ValueError:
        return valor
