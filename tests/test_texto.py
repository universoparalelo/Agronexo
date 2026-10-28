"""
Tests de app/diagnostico/texto.py — generación de texto legible y
cálculo de severidad. Puro: sin I/O, sin DB, sin geometrías.

Correr:
    docker compose exec api python3 -m pytest tests/test_texto.py -v
"""
import pytest

from app.diagnostico.texto import (
    calcular_severidad,
    generar_resumen_general,
    generar_texto_unidad,
    generar_texto_zona,
)


# ── calcular_severidad ──────────────────────────────────────────────────

class TestCalcularSeveridad:
    def test_sin_problema_siempre_normal(self):
        assert calcular_severidad(0.10, 0.70, "sin_problema_detectado") == "normal"

    def test_vigor_excesivo_siempre_vigorosa(self):
        assert calcular_severidad(0.90, 0.70, "vigor_excesivo") == "vigorosa"

    def test_ndvi_none_retorna_normal(self):
        assert calcular_severidad(None, 0.70, "estres_hidrico") == "normal"

    def test_ndvi_promedio_cero_retorna_normal(self):
        assert calcular_severidad(0.30, 0.0, "estres_hidrico") == "normal"

    def test_critica_ratio_mayor_050(self):
        # ratio = (0.70 - 0.30) / 0.70 = 0.571 > 0.50
        assert calcular_severidad(0.30, 0.70, "estres_hidrico") == "critica"

    def test_moderada_ratio_entre_025_y_050(self):
        # ratio = (0.70 - 0.45) / 0.70 = 0.357
        assert calcular_severidad(0.45, 0.70, "estres_hidrico") == "moderada"

    def test_leve_ratio_entre_010_y_025(self):
        # ratio = (0.70 - 0.58) / 0.70 = 0.171
        assert calcular_severidad(0.58, 0.70, "estres_hidrico") == "leve"

    def test_normal_ratio_menor_010(self):
        # ratio = (0.70 - 0.65) / 0.70 = 0.071
        assert calcular_severidad(0.65, 0.70, "estres_hidrico") == "normal"

    def test_zona_por_encima_del_promedio_es_normal(self):
        # ratio negativo → normal
        assert calcular_severidad(0.80, 0.70, "estres_hidrico") == "normal"

    def test_umbral_exacto_050_es_moderada(self):
        # ratio = (0.70 - 0.35) / 0.70 = 0.50 → no es > 0.50, es moderada
        assert calcular_severidad(0.35, 0.70, "estres_hidrico") == "moderada"

    def test_umbral_justo_debajo_025_es_leve(self):
        # ratio = (0.70 - 0.53) / 0.70 = 0.2428… < 0.25 → leve
        assert calcular_severidad(0.53, 0.70, "estres_hidrico") == "leve"


# ── generar_texto_zona ──────────────────────────────────────────────────

class TestGenerarTextoZona:
    def test_zona_r99_texto_sin_problemas(self):
        props = {"area_ha": 5.0, "regla_id": "R99"}
        texto = generar_texto_zona(props, 0.70)
        assert "sin problemas" in texto.lower()
        assert "5.0 ha" in texto

    def test_zona_excluida_r00(self):
        props = {
            "area_ha": 0.03, "regla_id": "R00", "excluida": True,
            "ndvi_promedio": 0.08,
        }
        texto = generar_texto_zona(props, 0.70)
        assert "excluida" in texto.lower()
        assert "0.08" in texto

    def test_zona_con_problema_incluye_causa_y_patron(self):
        props = {
            "area_ha": 2.5,
            "ndvi_promedio": 0.35,
            "patron_espacial": "circular",
            "causa_indice": "estres_biotico_fungico",
            "confianza": "alta",
            "regla_id": "R20",
            "accion_recomendada": "Aplicar fungicida foliar.",
            "productos_sugeridos": [{"nombre": "Amistar Xtra"}],
        }
        texto = generar_texto_zona(props, 0.70)
        assert "circular" in texto
        assert "fúngica" in texto
        assert "confianza alta" in texto
        assert "Amistar Xtra" in texto

    def test_accion_recomendada_no_se_repite_en_el_parrafo(self):
        # accion_recomendada tiene su propia sección en el frontend
        # ("Acción recomendada:") y en el PDF — no debe duplicarse acá.
        props = {
            "area_ha": 2.5, "ndvi_promedio": 0.35,
            "patron_espacial": "circular", "causa_indice": "estres_biotico_fungico",
            "confianza": "alta", "regla_id": "R20",
            "accion_recomendada": "Aplicar fungicida foliar de contacto ahora mismo.",
        }
        texto = generar_texto_zona(props, 0.70)
        assert "fungicida" not in texto.lower()

    def test_desviacion_porcentual_correcta(self):
        props = {
            "area_ha": 1.0, "ndvi_promedio": 0.35,
            "patron_espacial": "circular", "causa_indice": "estres_hidrico",
            "confianza": "media", "regla_id": "R40",
        }
        texto = generar_texto_zona(props, 0.70)
        assert "50%" in texto
        assert "por debajo" in texto

    def test_ndvi_por_encima_dice_por_encima(self):
        props = {
            "area_ha": 1.0, "ndvi_promedio": 0.85,
            "patron_espacial": "difuso_homogeneo", "causa_indice": "vigor_excesivo",
            "confianza": "media", "regla_id": "R70",
        }
        texto = generar_texto_zona(props, 0.70)
        assert "por encima" in texto

    def test_sin_ndvi_no_incluye_desviacion(self):
        props = {
            "area_ha": 1.0, "patron_espacial": "circular",
            "causa_indice": "estres_hidrico", "confianza": "media",
            "regla_id": "R40",
        }
        texto = generar_texto_zona(props, 0.70)
        assert "%" not in texto

    def test_multiples_productos_con_truncado(self):
        productos = [
            {"nombre": "P1"}, {"nombre": "P2"},
            {"nombre": "P3"}, {"nombre": "P4"},
        ]
        props = {
            "area_ha": 1.0, "patron_espacial": "circular",
            "causa_indice": "estres_hidrico", "confianza": "media",
            "regla_id": "R40", "productos_sugeridos": productos,
        }
        texto = generar_texto_zona(props, 0.70)
        assert "P1" in texto
        assert "1 más" in texto


# ── generar_texto_unidad ────────────────────────────────────────────────

class TestGenerarTextoUnidad:
    def test_unidad_basica(self):
        props = {
            "area_total_ha": 10.5,
            "n_zonas": 3,
            "causa_indice": "estres_hidrico",
            "severidad": "moderada",
            "ndvi_promedio": 0.450,
            "accion_recomendada": "Regar.",
            "productos_sugeridos": [],
        }
        texto = generar_texto_unidad(props)
        assert "10.5 ha" in texto
        assert "3 zonas agrupadas" in texto
        assert "estrés hídrico" in texto
        assert "moderada" in texto
        assert "0.450" in texto

    def test_unidad_singular(self):
        props = {
            "area_total_ha": 2.0, "n_zonas": 1,
            "causa_indice": "estres_biotico_fungico", "severidad": "critica",
            "productos_sugeridos": [],
        }
        texto = generar_texto_unidad(props)
        assert "1 zona agrupada" in texto
        assert "zonas" not in texto.replace("1 zona agrupada", "")

    def test_unidad_sin_ndvi(self):
        props = {
            "area_total_ha": 5.0, "n_zonas": 2,
            "causa_indice": "estres_hidrico", "severidad": "leve",
            "ndvi_promedio": None, "productos_sugeridos": [],
        }
        texto = generar_texto_unidad(props)
        assert "NDVI" not in texto

    def test_unidad_con_productos(self):
        props = {
            "area_total_ha": 5.0, "n_zonas": 2,
            "causa_indice": "estres_hidrico", "severidad": "leve",
            "productos_sugeridos": [{"nombre": "AquaFert"}],
        }
        texto = generar_texto_unidad(props)
        assert "AquaFert" in texto


# ── generar_resumen_general ─────────────────────────────────────────────

class TestGenerarResumenGeneral:
    def test_sin_zonas(self):
        texto = generar_resumen_general([])
        assert "no se encontraron" in texto.lower()

    def test_todas_sanas(self):
        features = [
            {"properties": {"regla_id": "R99", "area_ha": 5.0}},
            {"properties": {"regla_id": "R99", "area_ha": 3.0}},
        ]
        texto = generar_resumen_general(features)
        assert "2 zonas" in texto
        assert "sin problemas" in texto
        assert "requiere" not in texto.lower()

    def test_mezcla_problemas_y_sanas(self):
        features = [
            {"properties": {"regla_id": "R20", "area_ha": 2.0, "causa_indice": "estres_biotico_fungico"}},
            {"properties": {"regla_id": "R99", "area_ha": 5.0}},
            {"properties": {"regla_id": "R00", "area_ha": 0.03}},
        ]
        texto = generar_resumen_general(features)
        assert "3 zonas" in texto
        assert "1 zona" in texto and "requiere" in texto.lower()
        assert "fúngica" in texto
        assert "sin problemas" in texto
        assert "excluida" in texto

    def test_multiples_causas_en_resumen(self):
        features = [
            {"properties": {"regla_id": "R20", "area_ha": 1.0, "causa_indice": "estres_biotico_fungico"}},
            {"properties": {"regla_id": "R40", "area_ha": 2.0, "causa_indice": "estres_hidrico"}},
            {"properties": {"regla_id": "R40", "area_ha": 1.5, "causa_indice": "estres_hidrico"}},
        ]
        texto = generar_resumen_general(features)
        assert "fúngica" in texto
        assert "hídrico" in texto
        assert "3 zonas" in texto


if __name__ == "__main__":
    import sys
    raise SystemExit(pytest.main([__file__, "-v"]))


def test_severidad_toma_la_peor_entre_lote_y_esperado():
    from app.diagnostico.texto import calcular_severidad
    # Contra el lote (0.32) la zona apenas cae; contra lo esperado (0.587) cae ~49%.
    assert calcular_severidad(0.30, 0.32, "bajo_vigor_estadio") == "normal"
    assert calcular_severidad(0.30, 0.32, "bajo_vigor_estadio", ndvi_esperado=0.587) == "moderada"
    assert calcular_severidad(0.25, 0.32, "bajo_vigor_estadio", ndvi_esperado=0.587) == "critica"


def test_texto_menciona_lo_esperado_para_el_estadio():
    from app.diagnostico.texto import generar_texto_zona
    props = {"area_ha": 2.0, "ndvi_promedio": 0.30, "patron_espacial": "por_sectores",
             "causa_indice": "bajo_vigor_estadio", "confianza": "baja", "regla_id": "R80"}
    texto = generar_texto_zona(props, 0.32, ndvi_esperado=0.587, estadio="R5")
    assert "Para el estadio R5 se espera un NDVI cercano a 0.59" in texto
    assert "49% por debajo" in texto


def test_texto_r80_nombra_las_causas_candidatas():
    from app.diagnostico.texto import generar_texto_zona
    props = {"area_ha": 1.4, "ndvi_promedio": 0.30, "patron_espacial": "bordes_lote", "causa_indice": "bajo_vigor_estadio",
             "confianza": "baja", "regla_id": "R80",
             "regla_nombre": "Vigor bajo para el estadio — estrés hídrico o déficit de nitrógeno"}
    texto = generar_texto_zona(props, 0.45)
    assert "Diagnóstico: vigor bajo para el estadio, estrés hídrico o déficit de nitrógeno" in texto
    assert "sin una causa puntual" not in texto
