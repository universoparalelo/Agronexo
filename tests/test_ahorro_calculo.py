"""
Tests de app/ahorro/calculo.py — puro, sin DB ni HTTP.

Correr:
    docker compose exec api python3 -m pytest tests/test_ahorro_calculo.py -v
    PYTHONPATH=$(pwd) python3 -m pytest tests/test_ahorro_calculo.py -v
"""

from app.ahorro.calculo import acumular_ahorro, calcular_ahorro_vuelo

_CATALOGO = {
    "Glifosato": {"dosis_referencia": 3.0, "unidad": "L/ha"},
    "Azoxistrobina": {"dosis_referencia": 1.0, "unidad": "L/ha"},
    "Sin Dosis": {"dosis_referencia": None, "unidad": None},
}


def _orden(*totales):
    return {"totales_por_producto": list(totales), "area_total_tratada_ha": sum(t["area_ha"] for t in totales)}


def _total(producto, area_ha, volumen_total, unidad_dosis="L/ha"):
    return {"producto": producto, "area_ha": area_ha, "volumen_total": volumen_total, "unidad_dosis": unidad_dosis}


# ── calcular_ahorro_vuelo ────────────────────────────────────────────

def test_ahorro_variable_menor_a_uniforme():
    # Lote de 100 ha, solo se trataron 20 ha (zonas con problema) a 3 L/ha → 60 L
    # Uniforme: tratar las 100 ha a 3 L/ha → 300 L. Ahorro: 240 L (80%).
    orden = _orden(_total("Glifosato", 20.0, 60.0))
    precios = {"Glifosato": {"precio_usd": 3.5, "tipo": "referencia"}}

    resultado = calcular_ahorro_vuelo(orden, _CATALOGO, area_total_lote_ha=100.0, precios_por_producto=precios)

    producto = resultado["productos"][0]
    assert producto["cantidad_variable"] == 60.0
    assert producto["cantidad_uniforme"] == 300.0
    assert producto["ahorro_cantidad"] == 240.0
    assert producto["ahorro_pct"] == 80.0
    assert producto["ahorro_pesos"] == 240.0 * 3.5
    assert resultado["ahorro_total_pesos"] == round(240.0 * 3.5, 2)
    assert resultado["todos_los_precios_cargados"] is True
    print("✓ ahorro variable < uniforme calcula cantidad/%/pesos correctos")


def test_ahorro_sin_precio_cargado_no_rompe_pero_marca_parcial():
    orden = _orden(_total("Glifosato", 20.0, 60.0))

    resultado = calcular_ahorro_vuelo(orden, _CATALOGO, area_total_lote_ha=100.0, precios_por_producto={})

    producto = resultado["productos"][0]
    assert producto["ahorro_cantidad"] == 240.0  # la cantidad sí se puede calcular sin precio
    assert producto["ahorro_pesos"] is None
    assert producto["precio_usd"] is None
    assert resultado["ahorro_total_pesos"] == 0.0
    assert resultado["todos_los_precios_cargados"] is False
    print("✓ sin precio cargado: cantidad se calcula igual, pesos queda None y marca parcial")


def test_ahorro_sin_dosis_referencia_no_rompe():
    orden = _orden(_total("Sin Dosis", 20.0, 0.0))

    resultado = calcular_ahorro_vuelo(orden, _CATALOGO, area_total_lote_ha=100.0, precios_por_producto={})

    producto = resultado["productos"][0]
    assert producto["cantidad_uniforme"] is None
    assert producto["ahorro_cantidad"] is None
    assert producto["ahorro_pct"] is None
    assert producto["ahorro_pesos"] is None
    print("✓ producto sin dosis_referencia: cantidad_uniforme/ahorro quedan None, no rompe")


def test_ahorro_multiples_productos_en_un_vuelo():
    orden = _orden(
        _total("Glifosato", 20.0, 60.0),
        _total("Azoxistrobina", 5.0, 5.0),
    )
    precios = {
        "Glifosato": {"precio_usd": 3.5, "tipo": "referencia"},
        "Azoxistrobina": {"precio_usd": 28.0, "tipo": "referencia"},
    }

    resultado = calcular_ahorro_vuelo(orden, _CATALOGO, area_total_lote_ha=100.0, precios_por_producto=precios)

    assert len(resultado["productos"]) == 2
    ahorro_glifosato = next(p for p in resultado["productos"] if p["producto"] == "Glifosato")["ahorro_pesos"]
    ahorro_azoxi = next(p for p in resultado["productos"] if p["producto"] == "Azoxistrobina")["ahorro_pesos"]
    assert resultado["ahorro_total_pesos"] == round(ahorro_glifosato + ahorro_azoxi, 2)
    print("✓ varios productos en un vuelo: el total general suma el ahorro de cada uno")


# ── acumular_ahorro ───────────────────────────────────────────────────

def test_acumular_ahorro_entre_vuelos_de_la_misma_campana():
    vuelo_1 = calcular_ahorro_vuelo(
        _orden(_total("Glifosato", 20.0, 60.0)), _CATALOGO, 100.0, {"Glifosato": {"precio_usd": 3.5, "tipo": "referencia"}},
    )
    vuelo_2 = calcular_ahorro_vuelo(
        _orden(_total("Glifosato", 10.0, 30.0)), _CATALOGO, 100.0, {"Glifosato": {"precio_usd": 3.5, "tipo": "referencia"}},
    )

    acumulado = acumular_ahorro([vuelo_1, vuelo_2])

    assert len(acumulado["productos"]) == 1
    glifosato = acumulado["productos"][0]
    assert glifosato["cantidad_variable"] == 90.0  # 60 + 30
    assert glifosato["cantidad_uniforme"] == 600.0  # 300 + 300 (cada vuelo compara contra el lote completo)
    assert glifosato["ahorro_cantidad"] == 510.0
    assert acumulado["todos_los_precios_cargados"] is True
    assert acumulado["ahorro_total_pesos"] == round(510.0 * 3.5, 2)
    print("✓ acumular_ahorro suma cantidades de varios vuelos de la misma campaña por producto")


def test_acumular_ahorro_vuelo_sin_precio_marca_campana_parcial():
    vuelo_1 = calcular_ahorro_vuelo(
        _orden(_total("Glifosato", 20.0, 60.0)), _CATALOGO, 100.0, {"Glifosato": {"precio_usd": 3.5, "tipo": "referencia"}},
    )
    vuelo_2 = calcular_ahorro_vuelo(_orden(_total("Glifosato", 10.0, 30.0)), _CATALOGO, 100.0, {})

    acumulado = acumular_ahorro([vuelo_1, vuelo_2])

    assert acumulado["todos_los_precios_cargados"] is False
    # el ahorro en pesos del vuelo con precio sigue contando en el total
    assert acumulado["ahorro_total_pesos"] == round(240.0 * 3.5, 2)
    print("✓ un vuelo sin precio marca la campaña como parcial sin perder el ahorro de los que sí tienen precio")


def test_acumular_ahorro_lista_vacia():
    acumulado = acumular_ahorro([])
    assert acumulado["productos"] == []
    assert acumulado["ahorro_total_pesos"] == 0.0
    assert acumulado["todos_los_precios_cargados"] is True
    print("✓ acumular_ahorro con lista vacía no rompe (campaña sin vuelos completados)")
