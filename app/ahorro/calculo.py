"""
Cálculo del ahorro de aplicación variable vs. uniforme (HU-R4-11): puro,
sin I/O ni DB — mismo criterio que app/diagnostico/orden_trabajo.py.

"Variable" es lo que ya calcula generar_orden_trabajo(): tratar SOLO las
unidades de manejo con problema detectado, a la dosis de referencia del
producto. "Uniforme" es el escenario convencional con el que se compara:
tratar TODA la superficie del lote (Lote.area_ha) a la misma dosis de
referencia, en vez de limitarse a las zonas que de verdad lo necesitan.
La diferencia entre ambas cantidades es el ahorro — no hay variación de
dosis por zona en ninguno de los dos escenarios, la variable es el ÁREA
tratada, tal como surge de la nota de la propia tarjeta de Trello
("las dosis por zona ya se calculan para la orden de trabajo, así que
variable vs. uniforme es aritmética").
"""

from __future__ import annotations


def calcular_ahorro_vuelo(
    orden: dict,
    catalogo_dosis: dict[str, dict],
    area_total_lote_ha: float,
    precios_por_producto: dict[str, dict],
) -> dict:
    """
    orden: salida de generar_orden_trabajo() — totales_por_producto trae
    la cantidad variable ya calculada (volumen_total).
    catalogo_dosis: mismo catálogo que usa generar_orden_trabajo (nombre
    de producto -> dosis_referencia/unidad).
    precios_por_producto: nombre -> {"producto_id", "precio_usd", "tipo"}
    ya resuelto (precios.resolver_precio). Un producto sin precio cargado
    queda con ahorro_pesos=None en vez de excluirse silenciosamente del
    listado — producto_id viaja igual para que el frontend pueda ofrecer
    cargarlo.
    """
    productos: list[dict] = []
    ahorro_total_pesos = 0.0
    todos_los_precios_cargados = True

    for total in orden.get("totales_por_producto", []):
        nombre = total["producto"]
        cantidad_variable = total["volumen_total"]
        dosis_referencia = catalogo_dosis.get(nombre, {}).get("dosis_referencia")

        cantidad_uniforme = (
            round(area_total_lote_ha * dosis_referencia, 3) if dosis_referencia is not None else None
        )
        ahorro_cantidad = (
            round(cantidad_uniforme - cantidad_variable, 3) if cantidad_uniforme is not None else None
        )
        ahorro_pct = (
            round((ahorro_cantidad / cantidad_uniforme) * 100, 1)
            if ahorro_cantidad is not None and cantidad_uniforme
            else None
        )

        precio_info = precios_por_producto.get(nombre)
        precio_usd = precio_info["precio_usd"] if precio_info else None
        ahorro_pesos = (
            round(ahorro_cantidad * precio_usd, 2)
            if ahorro_cantidad is not None and precio_usd is not None
            else None
        )
        if ahorro_pesos is not None:
            ahorro_total_pesos += ahorro_pesos
        else:
            todos_los_precios_cargados = False

        productos.append({
            "producto": nombre,
            "producto_id": precio_info.get("producto_id") if precio_info else None,
            "unidad_dosis": total.get("unidad_dosis"),
            "cantidad_variable": cantidad_variable,
            "cantidad_uniforme": cantidad_uniforme,
            "ahorro_cantidad": ahorro_cantidad,
            "ahorro_pct": ahorro_pct,
            "precio_usd": precio_usd,
            "precio_tipo": precio_info["tipo"] if precio_info else None,
            "ahorro_pesos": ahorro_pesos,
        })

    return {
        "area_total_tratada_ha": orden.get("area_total_tratada_ha", 0.0),
        "productos": productos,
        "ahorro_total_pesos": round(ahorro_total_pesos, 2),
        "todos_los_precios_cargados": todos_los_precios_cargados,
    }


def acumular_ahorro(vuelos_ahorro: list[dict]) -> dict:
    """Suma el ahorro de varios vuelos de la misma campaña, agrupado por
    producto. Un producto sin dosis de referencia o sin precio en alguno
    de los vuelos queda marcado (sin_dosis_referencia/sin_precio) en vez
    de descartar silenciosamente esa parte del acumulado."""
    acumulado: dict[str, dict] = {}

    for vuelo_ahorro in vuelos_ahorro:
        for p in vuelo_ahorro.get("productos", []):
            nombre = p["producto"]
            entry = acumulado.setdefault(nombre, {
                "producto": nombre,
                "producto_id": p.get("producto_id"),
                "unidad_dosis": p["unidad_dosis"],
                "cantidad_variable": 0.0,
                "cantidad_uniforme": 0.0,
                "ahorro_cantidad": 0.0,
                "ahorro_pesos": 0.0,
                "sin_dosis_referencia": False,
                "sin_precio": False,
            })
            entry["cantidad_variable"] += p["cantidad_variable"] or 0.0
            if p["cantidad_uniforme"] is None:
                entry["sin_dosis_referencia"] = True
            else:
                entry["cantidad_uniforme"] += p["cantidad_uniforme"]
                entry["ahorro_cantidad"] += p["ahorro_cantidad"] or 0.0
            if p["ahorro_pesos"] is None:
                entry["sin_precio"] = True
            else:
                entry["ahorro_pesos"] += p["ahorro_pesos"]

    productos: list[dict] = []
    ahorro_total_pesos = 0.0
    todos_los_precios_cargados = True

    for entry in acumulado.values():
        entry["cantidad_variable"] = round(entry["cantidad_variable"], 3)
        entry["cantidad_uniforme"] = round(entry["cantidad_uniforme"], 3)
        entry["ahorro_cantidad"] = round(entry["ahorro_cantidad"], 3)
        entry["ahorro_pct"] = (
            round((entry["ahorro_cantidad"] / entry["cantidad_uniforme"]) * 100, 1)
            if entry["cantidad_uniforme"]
            else None
        )
        entry["ahorro_pesos"] = round(entry["ahorro_pesos"], 2)
        if entry["sin_precio"]:
            todos_los_precios_cargados = False
        # Suma igual aunque sea parcial (algún vuelo sin precio para este
        # producto) — es plata real ahorrada en los vuelos que sí tenían
        # precio cargado, no un total "sucio" que conviene ocultar.
        ahorro_total_pesos += entry["ahorro_pesos"]
        productos.append(entry)

    return {
        "productos": sorted(productos, key=lambda p: p["producto"]),
        "ahorro_total_pesos": round(ahorro_total_pesos, 2),
        "todos_los_precios_cargados": todos_los_precios_cargados,
    }
