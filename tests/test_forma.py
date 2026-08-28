"""
Tests de app/diagnostico/forma.py — métricas de forma y clasificación de
patrón espacial. Geometrías Shapely sintéticas de forma conocida.

clasificar_patron_zona() opera sobre geometrías ya en un plano cartesiano
en metros (no le importa si es UTM real o la proyección local
equirectangular del módulo) — los tests de más bajo nivel usan
coordenadas "metro" directamente. clasificar_patrones() sí opera sobre
geometrías EPSG:4326 reales (grados), como las que vendrían de un GeoJSON.
"""
from shapely.geometry import Point, Polygon, box

from app.diagnostico.forma import ZonaInput, clasificar_patron_zona, clasificar_patrones

# "Lote" cuadrado de 1000m x 1000m (100 ha) en un plano local en metros.
_LOTE_M = box(500_000, 7_000_000, 501_000, 7_001_000)

# El mismo lote, pero expresado en coordenadas EPSG:4326 aproximadas
# (grados) para los tests de clasificar_patrones(), que sí reproyecta.
_LOTE_4326 = box(-60.700, -27.100, -60.690, -27.091)


def _forma_plus(cx: float, cy: float, lado: float) -> Polygon:
    """
    Cruz/plus grande e irregular (no rectangular): ocupa 5/9 de su propio
    bounding box cuadrado → rectangularidad ≈ 0.56 (por debajo del umbral
    de 'por_sectores') y circularidad baja, a diferencia de un box() que
    siempre tiene rectangularidad 1.0.
    """
    mitad = lado / 2
    tercio = lado / 3
    x0, x3 = cx - mitad, cx + mitad
    y0, y3 = cy - mitad, cy + mitad
    x1, x2 = x0 + tercio, x0 + 2 * tercio
    y1, y2 = y0 + tercio, y0 + 2 * tercio
    return Polygon([
        (x1, y0), (x2, y0), (x2, y1), (x3, y1), (x3, y2), (x2, y2),
        (x2, y3), (x1, y3), (x1, y2), (x0, y2), (x0, y1), (x1, y1),
    ])


def _blob_irregular(cx: float, cy: float) -> Polygon:
    """
    Pequeño polígono en forma de L (cóncavo, no circular ni alargado) —
    circularidad baja (~0.59) y elongación baja (~1.0), a diferencia de un
    círculo (que siempre cae en 'circular', ver nota en el test de abajo).
    Área ≈ 300 m², bounding box 20x20 m centrado en (cx, cy).
    """
    return Polygon([
        (cx - 10, cy - 10), (cx - 10, cy + 10), (cx, cy + 10),
        (cx, cy), (cx + 10, cy), (cx + 10, cy - 10),
    ])


# ── clasificar_patron_zona — geometrías individuales (plano en metros) ───

def test_circulo_lejos_del_borde_es_circular():
    centro = Point(500_500, 7_000_500)  # centro del lote, lejos de cualquier borde
    circulo = centro.buffer(50)  # radio 50m → circularidad ≈ 1.0
    patron = clasificar_patron_zona(
        circulo, circulo.area, _LOTE_M.boundary, _LOTE_M.area,
        n_zonas_misma_clase=1, area_total_clase_relativa=circulo.area / _LOTE_M.area,
    )
    assert patron == "circular"


def test_rectangulo_alargado_es_lineal():
    franja = box(500_100, 7_000_400, 500_600, 7_000_420)  # 500m x 20m → elongación 25
    patron = clasificar_patron_zona(
        franja, franja.area, _LOTE_M.boundary, _LOTE_M.area,
        n_zonas_misma_clase=1, area_total_clase_relativa=franja.area / _LOTE_M.area,
    )
    assert patron == "lineal"


def test_zona_pegada_al_borde_es_bordes_lote():
    franja_borde = box(500_000, 7_000_000, 501_000, 7_000_015)  # pegada al borde sur, 15m de ancho
    patron = clasificar_patron_zona(
        franja_borde, franja_borde.area, _LOTE_M.boundary, _LOTE_M.area,
        n_zonas_misma_clase=1, area_total_clase_relativa=franja_borde.area / _LOTE_M.area,
    )
    assert patron == "bordes_lote"


def test_zona_grande_rectangular_es_por_sectores():
    # Con margen de 100m respecto de cualquier borde del lote — evita que
    # también matchee "bordes_lote" (que se evalúa primero en la cascada).
    sector = box(500_100, 7_000_100, 500_800, 7_000_800)  # 49 ha, ~49% del lote, rectangular
    patron = clasificar_patron_zona(
        sector, sector.area, _LOTE_M.boundary, _LOTE_M.area,
        n_zonas_misma_clase=1, area_total_clase_relativa=sector.area / _LOTE_M.area,
    )
    assert patron == "por_sectores"


def test_foco_pequeno_irregular_disperso_es_foco_aislado():
    # OJO: un círculo pequeño NO sirve para este test — su circularidad alta
    # lo clasifica como "circular" antes de llegar al chequeo de focos
    # aislados (a propósito: R00 depende de que copas de árbol pequeñas y
    # circulares sigan siendo "circular"). "focos_aislados" necesita una
    # forma pequeña pero NO circular.
    foco = _blob_irregular(500_500, 7_000_500)  # área ≈ 300 m² << AREA_MAX_FOCO_M2
    patron = clasificar_patron_zona(
        foco, foco.area, None, _LOTE_M.area,
        n_zonas_misma_clase=5, area_total_clase_relativa=0.01,
    )
    assert patron == "focos_aislados"


def test_mancha_grande_difusa_pocas_zonas_es_difuso_homogeneo():
    # Una cruz grande, no un box(): un rectángulo perfecto siempre tiene
    # rectangularidad=1.0 y cae en "por_sectores" antes de llegar acá.
    mancha = _forma_plus(500_500, 7_000_500, 780)  # ~34 ha, rectangularidad ≈ 0.56
    patron = clasificar_patron_zona(
        mancha, mancha.area, None, _LOTE_M.area,
        n_zonas_misma_clase=1, area_total_clase_relativa=0.40,
    )
    assert patron == "difuso_homogeneo"


def test_forma_irregular_es_manchas_irregulares_catch_all():
    # Estrella cóncava: circularidad baja, elongación baja, no toca borde,
    # área chica y sin suficientes zonas de la misma clase para "focos_aislados".
    estrella = Polygon([
        (500_300, 7_000_300), (500_340, 7_000_500), (500_500, 7_000_320),
        (500_360, 7_000_300), (500_500, 7_000_100), (500_320, 7_000_260),
        (500_300, 7_000_300),
    ])
    patron = clasificar_patron_zona(
        estrella, estrella.area, None, _LOTE_M.area,
        n_zonas_misma_clase=1, area_total_clase_relativa=estrella.area / _LOTE_M.area,
    )
    assert patron == "manchas_irregulares"


def test_lote_boundary_none_no_lanza_excepcion():
    circulo = Point(500_500, 7_000_500).buffer(30)
    patron = clasificar_patron_zona(
        circulo, circulo.area, None, _LOTE_M.area,
        n_zonas_misma_clase=1, area_total_clase_relativa=circulo.area / _LOTE_M.area,
    )
    assert patron == "circular"  # sin lote, pero la forma sigue siendo circular


# ── clasificar_patrones — integración sobre zonas EPSG:4326 ─────────────

def test_clasificar_patrones_devuelve_patron_por_id():
    circulo_4326 = Point(-60.695, -27.095).buffer(0.0005)  # pequeño círculo en grados
    zonas = [ZonaInput(id=0, geometry=circulo_4326, clase="critica", area_ha=0.5)]
    resultado = clasificar_patrones(zonas, _LOTE_4326)
    assert resultado == {0: "circular"}


def test_clasificar_patrones_lista_vacia_no_lanza_excepcion():
    assert clasificar_patrones([], _LOTE_4326) == {}


def test_clasificar_patrones_sin_lote_usa_fallback():
    circulo_4326 = Point(-60.695, -27.095).buffer(0.0005)
    zonas = [ZonaInput(id=0, geometry=circulo_4326, clase="critica", area_ha=0.5)]
    resultado = clasificar_patrones(zonas, None)
    assert resultado[0] is not None


def test_multiples_focos_irregulares_misma_clase_dispersos():
    # Tres blobs en forma de L muy separados dentro del lote 4326 (usando
    # el mismo desplazamiento angular pequeño para no salir del lote).
    centros = [(-60.698, -27.095), (-60.695, -27.095), (-60.692, -27.095)]
    zonas = []
    for i, (lon, lat) in enumerate(centros):
        # Blob pequeño (L-shape) expresado directamente en grados, escala
        # arbitraria pequeña — solo importa que sea "chico y no circular".
        d = 0.00005
        blob = Polygon([
            (lon - d, lat - d), (lon - d, lat + d), (lon, lat + d),
            (lon, lat), (lon + d, lat), (lon + d, lat - d),
        ])
        zonas.append(ZonaInput(id=i, geometry=blob, clase="critica", area_ha=0.03))
    resultado = clasificar_patrones(zonas, _LOTE_4326)
    assert all(p == "focos_aislados" for p in resultado.values())


if __name__ == "__main__":
    test_circulo_lejos_del_borde_es_circular()
    test_rectangulo_alargado_es_lineal()
    test_zona_pegada_al_borde_es_bordes_lote()
    test_zona_grande_rectangular_es_por_sectores()
    test_foco_pequeno_irregular_disperso_es_foco_aislado()
    test_mancha_grande_difusa_pocas_zonas_es_difuso_homogeneo()
    test_forma_irregular_es_manchas_irregulares_catch_all()
    test_lote_boundary_none_no_lanza_excepcion()
    test_clasificar_patrones_devuelve_patron_por_id()
    test_clasificar_patrones_lista_vacia_no_lanza_excepcion()
    test_clasificar_patrones_sin_lote_usa_fallback()
    test_multiples_focos_irregulares_misma_clase_dispersos()
    print("Todos los tests de forma.py pasaron.")
