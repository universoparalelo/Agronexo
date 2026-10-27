"""
Detalle por zona del reporte ejecutivo — qué campos del diagnóstico llegan al PDF.
Puro: renderiza la plantilla Jinja2 con zonas sintéticas, sin WeasyPrint, DB ni MinIO.
"""

from app.reportes.service import _env, _zona_a_contexto

COMO_CONFIRMAR = "Verificar en campo si hay plantas en esa zona."


def _props(**extra):
    base = {
        "zona_id": 1,
        "area_ha": 3.72,
        "ndvi_promedio": 0.3,
        "severidad": "critica",
        "confianza": "alta",
        "causa_indice": "estres_biotico_fungico",
        "regla_id": "R05",
        "texto_explicativo": "Zona con enfermedad fúngica probable.",
        "accion_recomendada": "Aplicar fungicida.",
        "como_confirmar_campo": COMO_CONFIRMAR,
        "productos_sugeridos": [{"nombre": "Azoxistrobina"}],
    }
    base.update(extra)
    return base


def _renderizar(*props_zonas):
    zonas = [_zona_a_contexto(p) for p in props_zonas]
    return _env.get_template("reporte_ejecutivo.html").render(
        zonas=zonas, n_zonas=len(zonas), n_zonas_con_problema=len(zonas),
        area_afectada_ha=0.0, ndvi_promedio_lote=0.5, n_unidades_manejo=0,
    )


def test_zona_con_problema_muestra_como_confirmar_en_campo():
    html = _renderizar(_props())
    assert "Cómo confirmar en campo:" in html
    assert COMO_CONFIRMAR in html


def test_como_confirmar_va_entre_la_accion_y_los_productos():
    html = _renderizar(_props())
    assert html.index("Acción recomendada:") < html.index("Cómo confirmar en campo:") < html.index("Productos sugeridos:")


def test_zona_sin_problema_no_muestra_como_confirmar():
    html = _renderizar(_props(regla_id="R99", causa_indice="sin_problema_detectado"))
    assert "Cómo confirmar en campo:" not in html


def test_zona_sin_como_confirmar_no_deja_la_etiqueta_vacia():
    html = _renderizar(_props(como_confirmar_campo=""))
    assert "Cómo confirmar en campo:" not in html


# ── Orden de trabajo (el PDF que ve el usuario en la app) ──

from app.diagnostico.orden_trabajo import generar_orden_trabajo
from app.ordenes_trabajo.service import _env as _env_orden, _item_a_contexto, _total_a_contexto, _unidad_volumen


def _unidad(**extra):
    props = {
        "unidad_id": 1, "causa_indice": "estres_biotico_fungico", "severidad": "critica",
        "area_total_ha": 3.72, "zona_ids": [0], "como_confirmar_campo": COMO_CONFIRMAR,
        "productos_sugeridos": [{"nombre": "Azoxistrobina", "tipo": "fungicida"}],
    }
    props.update(extra)
    return {"properties": props}


def _orden_html(unidades):
    catalogo = {"Azoxistrobina": {"dosis_referencia": 0.4, "unidad": "L/ha"}}
    orden = generar_orden_trabajo(unidades, catalogo)
    return _env_orden.get_template("orden_trabajo.html").render(
        lote_nombre="L", cultivo_label="Soja", fecha_vuelo="—", generado_en="—",
        n_unidades=len(orden["items"]), area_total_tratada_ha=orden["area_total_tratada_ha"],
        items=[_item_a_contexto(i) for i in orden["items"]],
        totales=[_total_a_contexto(t) for t in orden["totales_por_producto"]],
        productos_con_seguridad=[], productos_sin_seguridad_cargada=[], hay_items_sin_dosis=False,
    )


def test_orden_muestra_como_confirmar_en_campo_por_unidad():
    html = _orden_html([_unidad()])
    assert "Cómo confirmar en campo" in html
    assert COMO_CONFIRMAR in html
    assert "Unidad #1" in html


def test_orden_sin_dato_de_confirmacion_no_muestra_la_seccion():
    html = _orden_html([_unidad(como_confirmar_campo="")])
    assert "Cómo confirmar en campo" not in html


def test_volumen_total_sin_por_hectarea():
    html = _orden_html([_unidad()])
    assert "1.49 L<" in html
    assert "1.49 L/ha" not in html
    assert _unidad_volumen("kg/ha") == "kg"
    assert _unidad_volumen(None) == ""


def test_orden_agrupa_unidades_con_el_mismo_texto_de_confirmacion():
    html = _orden_html([_unidad(), _unidad(unidad_id=2)])
    assert html.count(COMO_CONFIRMAR) == 1
    assert "Unidades #1, #2" in html


def test_orden_lleva_el_logo_de_agronexo():
    from pathlib import Path
    import app.ordenes_trabajo.service as servicio
    assert 'src="agronexo-logo.svg"' in _orden_html([_unidad()])
    assert (Path(servicio.__file__).parent / "templates" / "agronexo-logo.svg").is_file()
