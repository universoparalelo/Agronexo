"""
Tests puros del reporte ejecutivo PDF (app/reportes/service.py): resumen no
técnico y presencia en el PDF de lo que muestra la pantalla de Diagnóstico.
Sin DB ni MinIO.

    docker compose exec api python3 -m pytest tests/test_reporte_ejecutivo.py -v
"""
from unittest.mock import patch

from app.reportes import service
from app.reportes.service import generar_resumen_ejecutivo


def _zona(zona_id, regla_id, causa, severidad, area, confianza="alta", **extra):
    props = {
        "zona_id": zona_id, "regla_id": regla_id, "causa_indice": causa,
        "severidad": severidad, "area_ha": area, "confianza": confianza,
        "ndvi_promedio": 0.5,
    }
    props.update(extra)
    return {"type": "Feature", "geometry": None, "properties": props}


def test_lote_sano_no_tiene_problemas_ni_proximo_paso():
    r = generar_resumen_ejecutivo([
        _zona(1, "R99", "sin_problema_detectado", "normal", 10.0),
        _zona(2, "R99", "sin_problema_detectado", "normal", 5.0),
    ])
    assert "sano" in r["estado"]
    assert r["problemas"] == []
    assert r["proximo_paso"] is None


def test_porcentajes_y_orden_por_urgencia():
    r = generar_resumen_ejecutivo([
        _zona(1, "R99", "sin_problema_detectado", "normal", 6.0),
        _zona(2, "R05", "estres_hidrico", "leve", 3.0),
        _zona(3, "R03", "estres_biotico_fungico", "critica", 1.0),
        _zona(4, "R00", "sin_problema_detectado", "normal", 50.0),
    ])
    # La zona excluida (R00) no cuenta en la superficie analizada.
    assert "El 60% del lote se ve sano" in r["estado"]
    assert "4.0 ha de 10.0 ha" in r["estado"]
    assert [p["severidad"] for p in r["problemas"]] == ["critica", "leve"]
    assert r["problemas"][0]["urgencia"] == "atender cuanto antes"
    assert "NDVI" not in r["estado"]


def test_suelo_desnudo_no_se_muestra_como_sin_problema():
    r = generar_resumen_ejecutivo([
        _zona(1, "R01", "sin_problema_detectado", "normal", 1.9),
        _zona(2, "R99", "sin_problema_detectado", "normal", 16.4),
    ])
    assert r["problemas"][0]["que_es"] == "Zonas sin plantas (suelo desnudo)"
    assert "no se corrige con productos" in r["problemas"][0]["que_hacer"]


def test_zonas_con_poca_confianza_se_mencionan_en_el_proximo_paso():
    r = generar_resumen_ejecutivo([
        _zona(1, "R03", "estres_biotico_fungico", "moderada", 2.0, confianza="media"),
        _zona(2, "R03", "estres_biotico_fungico", "leve", 1.0),
    ])
    assert len(r["problemas"]) == 1
    assert r["problemas"][0]["n_zonas"] == 2
    assert r["problemas"][0]["severidad"] == "moderada"
    assert "En 1 zona el sistema no tiene certeza" in r["proximo_paso"]


def test_pdf_incluye_como_confirmar_en_campo_y_unidades():
    diagnostico = {
        "features": [
            _zona(
                1, "R03", "estres_biotico_fungico", "critica", 2.0,
                regla_nombre="Enfermedad fúngica focal", patron_espacial="circular",
                texto_explicativo="Texto técnico.", accion_recomendada="Aplicar fungicida.",
                como_confirmar_campo="Buscar lesiones en hojas inferiores.",
                productos_sugeridos=[{"nombre": "Prod A"}, {"nombre": "Prod B"}, {"nombre": "Prod C"}, {"nombre": "Prod D"}],
            ),
        ],
        "unidades_manejo": [{"properties": {
            "unidad_id": 1, "severidad": "critica", "regla_nombre": "Enfermedad fúngica focal",
            "area_total_ha": 2.0, "n_zonas": 1, "zona_ids": [1], "ndvi_promedio": 0.4,
            "texto_unidad": "Unidad de manejo de 2.0 ha.", "productos_sugeridos": [],
        }}],
        "metadata": {"lote_nombre": "Lote X", "cultivo": "soja", "variedad": "DM 46i20",
                     "indices_disponibles": ["ndvi", "ndre"]},
    }
    capturado = {}

    class _HTMLFalso:
        def __init__(self, string, base_url):
            capturado["html"] = string

        def write_pdf(self):
            return b"%PDF"

    with patch.object(service, "generar_imagen_mapa_zonas", return_value=b"png"), \
         patch("weasyprint.HTML", _HTMLFalso):
        assert service.generar_pdf_reporte(diagnostico) == b"%PDF"

    html = capturado["html"]
    assert "En pocas palabras" in html
    assert "Cómo confirmar en campo" in html
    assert "Buscar lesiones en hojas inferiores." in html
    assert "Prod D" in html
    assert "Unidad #1" in html
    assert "DM 46i20" in html
    assert "NDVI, NDRE" in html


def test_pdf_marca_como_provisoria_la_zona_con_causa_sin_confirmar():
    diagnostico = {
        "features": [
            _zona(
                1, "R80", "estres_hidrico", "critica", 15.0, confianza="baja", provisorio=True,
                regla_nombre="Vigor bajo para el estadio — estrés hídrico o déficit de nitrógeno",
                patron_espacial="por_sectores", texto_explicativo="Texto técnico.",
                accion_recomendada="Recomendación provisoria según la causa más probable (estrés hídrico, 51%).",
                productos_sugeridos=[{"nombre": "Prod A"}],
            ),
            _zona(2, "R40", "estres_biotico_insecto", "moderada", 2.0, productos_sugeridos=[{"nombre": "Prod B"}]),
        ],
        "unidades_manejo": [{"properties": {
            "unidad_id": 1, "severidad": "critica", "regla_nombre": "Vigor bajo para el estadio",
            "area_total_ha": 15.0, "n_zonas": 1, "zona_ids": [1], "ndvi_promedio": 0.26,
            "texto_unidad": "Unidad.", "productos_sugeridos": [{"nombre": "Prod A"}], "provisorio": True,
        }}],
        "metadata": {"lote_nombre": "Lote X", "cultivo": "soja", "indices_disponibles": ["ndvi"]},
    }
    capturado = {}

    class _HTMLFalso:
        def __init__(self, string, base_url):
            capturado["html"] = string

        def write_pdf(self):
            return b"%PDF"

    with patch.object(service, "generar_imagen_mapa_zonas", return_value=b"png"),          patch("weasyprint.HTML", _HTMLFalso):
        service.generar_pdf_reporte(diagnostico)

    html = capturado["html"]
    # Solo la zona 1: resumen ejecutivo, tabla, detalle técnico y unidad de manejo; la zona firme no suma cartel.
    assert html.count("Provisorio, verificar en campo") == 4
    assert "la causa no está confirmada" in html


def test_resumen_ejecutivo_marca_el_grupo_con_zonas_provisorias():
    r = generar_resumen_ejecutivo([
        _zona(1, "R80", "estres_hidrico", "critica", 15.0, confianza="baja", provisorio=True),
        _zona(2, "R05", "estres_biotico_insecto", "leve", 2.0),
    ])
    por_severidad = {p["severidad"]: p for p in r["problemas"]}
    assert por_severidad["critica"]["provisorio"] is True
    assert por_severidad["leve"]["provisorio"] is False
