"""
Tests de app/ingesta/absorcion.py — absorción de huecos chicos entre zonas
para el mapa de vistazo. Puro (Shapely), sin base de datos.

Correr en el contenedor api:
    docker compose exec api python3 -m pytest tests/test_absorcion.py -v
"""
from shapely.geometry import box, mapping, shape
from shapely.ops import unary_union

from app.ingesta.absorcion import absorber_huecos

# Lote de ~0.02° x 0.02° (≈ 2 km x 2 km) cerca de Resistencia; 0.001° ≈ 100 m
X0, Y0 = -59.05, -27.46
LOTE = box(X0, Y0, X0 + 0.02, Y0 + 0.02)


def _feature(geom, clase, ndvi=0.5):
    return {
        "type": "Feature",
        "geometry": mapping(geom),
        "properties": {"clase": clase, "ndvi_promedio": ndvi, "area_ha": 0.0},
    }


def _coleccion(*features, **extra):
    return {"type": "FeatureCollection", "features": list(features), **extra}


def _area(geojson) -> float:
    return unary_union([shape(f["geometry"]) for f in geojson["features"]]).area


def test_un_hueco_chico_se_absorbe_en_la_zona_que_lo_rodea():
    izquierda = box(X0, Y0, X0 + 0.01, Y0 + 0.02)
    derecha = box(X0 + 0.01, Y0, X0 + 0.02, Y0 + 0.02)
    hueco = box(X0 + 0.003, Y0 + 0.008, X0 + 0.0037, Y0 + 0.0087)   # ≈ 70 m x 70 m ≈ 0.5 ha
    entrada = _coleccion(
        _feature(izquierda.difference(hueco), "deficiente", 0.3),
        _feature(derecha, "normal", 0.6),
    )
    salida = absorber_huecos(entrada, LOTE)

    zona_izq = shape(salida["features"][0]["geometry"])
    assert len(zona_izq.interiors) == 0 if zona_izq.geom_type == "Polygon" else all(len(p.interiors) == 0 for p in zona_izq.geoms)
    assert abs(_area(salida) - LOTE.area) / LOTE.area < 1e-6
    # la clase y el valor de la zona no cambian; el área sí se recalcula
    assert salida["features"][0]["properties"]["clase"] == "deficiente"
    assert salida["features"][0]["properties"]["area_ha"] > 50


def test_el_hueco_va_a_la_zona_con_la_que_comparte_mas_borde():
    izquierda = box(X0, Y0, X0 + 0.01, Y0 + 0.02)
    derecha = box(X0 + 0.01, Y0, X0 + 0.02, Y0 + 0.02)
    # hueco a caballo del borde entre ambas, pero con casi todo su contorno del lado derecho
    hueco = box(X0 + 0.0098, Y0 + 0.008, X0 + 0.0108, Y0 + 0.0088)
    izq_original, der_original = izquierda.difference(hueco), derecha.difference(hueco)
    entrada = _coleccion(_feature(izq_original, "deficiente"), _feature(der_original, "normal"))
    salida = absorber_huecos(entrada, LOTE)
    assert shape(salida["features"][1]["geometry"]).area > der_original.area   # la derecha lo absorbe
    assert abs(shape(salida["features"][0]["geometry"]).area - izq_original.area) < 1e-12   # la izquierda no cambia
    assert abs(_area(salida) - LOTE.area) / LOTE.area < 1e-6


def test_un_hueco_grande_no_se_rellena():
    izquierda = box(X0, Y0, X0 + 0.01, Y0 + 0.02)
    derecha = box(X0 + 0.01, Y0, X0 + 0.02, Y0 + 0.02)
    nube = box(X0 + 0.003, Y0 + 0.005, X0 + 0.009, Y0 + 0.012)   # ≈ 600 m x 700 m ≈ 42 ha
    entrada = _coleccion(_feature(izquierda.difference(nube), "deficiente"), _feature(derecha, "normal"))
    salida = absorber_huecos(entrada, LOTE)
    assert abs(_area(salida) - (LOTE.area - nube.area)) / LOTE.area < 1e-6


def test_la_parte_del_lote_que_el_raster_no_cubre_queda_en_blanco():
    solo_mitad = box(X0, Y0, X0 + 0.02, Y0 + 0.008)   # el GeoTIFF cubre apenas la parte de abajo
    salida = absorber_huecos(_coleccion(_feature(solo_mitad, "normal")), LOTE)
    assert abs(_area(salida) - solo_mitad.area) / LOTE.area < 1e-6


def test_sin_huecos_devuelve_lo_mismo_y_conserva_los_miembros_extra():
    entrada = _coleccion(
        _feature(box(X0, Y0, X0 + 0.02, Y0 + 0.02), "normal"),
        umbrales=[0.2, 0.4, 0.7], metodo_umbral="fijo",
    )
    salida = absorber_huecos(entrada, LOTE)
    assert salida["umbrales"] == [0.2, 0.4, 0.7] and salida["metodo_umbral"] == "fijo"
    assert len(salida["features"]) == 1
    assert abs(_area(salida) - LOTE.area) / LOTE.area < 1e-6


def test_sin_limite_del_lote_usa_la_envolvente_de_las_zonas():
    a = box(X0, Y0, X0 + 0.01, Y0 + 0.01)
    hueco = box(X0 + 0.003, Y0 + 0.003, X0 + 0.0037, Y0 + 0.0037)
    salida = absorber_huecos(_coleccion(_feature(a.difference(hueco), "normal")), None)
    assert abs(_area(salida) - a.area) / a.area < 1e-6


def test_coleccion_vacia():
    vacia = _coleccion()
    assert absorber_huecos(vacia, LOTE) == vacia   # absorber no inventa nada; "sin datos" se marca aparte


# ── Análisis que SÍ registraron `sin_datos` (lo mide el worker) ───────
# Lo registrado manda: el tamaño del hueco deja de importar. Lo que tiene datos se
# combina con la vecina aunque sea grande; el sin_datos real nunca se rellena.

def test_analisis_viejo_sin_sin_datos_registrado_rellena_solo_huecos_chicos():
    izquierda = box(X0, Y0, X0 + 0.01, Y0 + 0.02)
    derecha = box(X0 + 0.01, Y0, X0 + 0.02, Y0 + 0.02)
    grande = box(X0 + 0.003, Y0 + 0.005, X0 + 0.009, Y0 + 0.012)   # ≈ 42 ha
    entrada = _coleccion(_feature(izquierda.difference(grande), "deficiente"), _feature(derecha, "normal"))
    assert "sin_datos" not in entrada
    salida = absorber_huecos(entrada, LOTE)
    assert abs(_area(salida) - (LOTE.area - grande.area)) / LOTE.area < 1e-6


def test_un_hueco_grande_con_datos_se_combina_con_la_vecina_si_sin_datos_esta_registrado():
    izquierda = box(X0, Y0, X0 + 0.01, Y0 + 0.02)
    derecha = box(X0 + 0.01, Y0, X0 + 0.02, Y0 + 0.02)
    grande = box(X0 + 0.003, Y0 + 0.005, X0 + 0.009, Y0 + 0.012)   # ≈ 42 ha, pero con datos
    entrada = _coleccion(
        _feature(izquierda.difference(grande), "deficiente"), _feature(derecha, "normal"), sin_datos=None,
    )
    salida = absorber_huecos(entrada, LOTE)
    assert abs(_area(salida) - LOTE.area) / LOTE.area < 1e-6
    assert salida["features"][0]["properties"]["area_ha"] > 200   # la zona izquierda quedó completa (≈ 218 ha)


def test_el_sin_datos_real_no_se_rellena_aunque_sea_chico():
    izquierda = box(X0, Y0, X0 + 0.01, Y0 + 0.02)
    derecha = box(X0 + 0.01, Y0, X0 + 0.02, Y0 + 0.02)
    nube = box(X0 + 0.003, Y0 + 0.008, X0 + 0.0037, Y0 + 0.0087)   # ≈ 0,5 ha, pero es sin datos real
    entrada = _coleccion(
        _feature(izquierda.difference(nube), "deficiente"), _feature(derecha, "normal"), sin_datos=mapping(nube),
    )
    salida = absorber_huecos(entrada, LOTE)
    assert abs(_area(salida) - (LOTE.area - nube.area)) / LOTE.area < 1e-6
    assert salida["sin_datos"] == mapping(nube)   # se conserva tal cual para que el mapa lo dibuje


def test_solo_se_rellena_la_parte_del_hueco_que_no_es_sin_datos():
    izquierda = box(X0, Y0, X0 + 0.01, Y0 + 0.02)
    derecha = box(X0 + 0.01, Y0, X0 + 0.02, Y0 + 0.02)
    hueco = box(X0 + 0.003, Y0 + 0.005, X0 + 0.009, Y0 + 0.012)
    nube = box(X0 + 0.003, Y0 + 0.005, X0 + 0.006, Y0 + 0.012)   # la mitad del hueco es nube
    entrada = _coleccion(_feature(izquierda.difference(hueco), "deficiente"), _feature(derecha, "normal"), sin_datos=mapping(nube))
    salida = absorber_huecos(entrada, LOTE)
    assert abs(_area(salida) - (LOTE.area - nube.area)) / LOTE.area < 1e-3


def test_la_parte_del_lote_que_el_raster_no_cubre_queda_en_blanco_si_esta_en_sin_datos():
    solo_abajo = box(X0, Y0, X0 + 0.02, Y0 + 0.008)
    no_cubierto = box(X0, Y0 + 0.008, X0 + 0.02, Y0 + 0.02)
    salida = absorber_huecos(_coleccion(_feature(solo_abajo, "normal"), sin_datos=mapping(no_cubierto)), LOTE)
    assert abs(_area(salida) - solo_abajo.area) / LOTE.area < 1e-3


def test_muchos_huecos_con_bordes_densos_termina_rapido():
    """Regresión: en un ortomosaico de dron (píxeles de cm) había miles de huecos contra
    zonas de decenas de miles de vértices y el endpoint tardaba minutos."""
    import time

    # borde dentado: 4.000 dientes de 0.5 m sobre la zona izquierda
    n = 4_000
    xs = [X0 + 0.01 * i / n for i in range(n + 1)]
    diente = [(x, Y0 + 0.02 - (0.00001 if i % 2 else 0)) for i, x in enumerate(xs)]
    zona = shape({"type": "Polygon", "coordinates": [[(X0, Y0), (X0 + 0.01, Y0), *reversed(diente)]]}).buffer(0)
    huecos = [box(X0 + 0.0102 + i * 0.00002, Y0 + 0.005, X0 + 0.0102 + i * 0.00002 + 0.00001, Y0 + 0.005 + 0.00001) for i in range(500)]
    otra = box(X0 + 0.0101, Y0, X0 + 0.02, Y0 + 0.02).difference(unary_union(huecos))

    t = time.perf_counter()
    salida = absorber_huecos(_coleccion(_feature(zona, "normal"), _feature(otra, "critica")), LOTE)
    assert time.perf_counter() - t < 20
    assert len(salida["features"]) == 2
