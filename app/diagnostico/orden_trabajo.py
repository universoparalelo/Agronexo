"""
Cálculo de la orden de trabajo (RFSA-04): a partir de las unidades de
manejo del diagnóstico (app/diagnostico/zonificacion.py), resuelve por
unidad el producto a aplicar, la dosis por hectárea, el volumen total y
las restricciones ambientales / instrucciones de seguridad, usando el
catálogo de productos fitosanitarios.

Puro: sin I/O, sin DB — recibe unidades_manejo (lista de Features GeoJSON
ya calculada por _calcular_diagnostico) y un catálogo de dosis ya
resuelto desde la BD. No expone endpoint ni persiste nada todavía — eso
es alcance de las tarjetas de Trello "Documento y endpoint de orden de
trabajo PDF" e "Integración en el dashboard" (backlog).
"""

from __future__ import annotations


def generar_orden_trabajo(
    unidades_manejo: list[dict],
    catalogo_dosis: dict[str, dict],
) -> dict:
    """
    unidades_manejo: salida de generar_unidades_manejo() — Features con
    properties.productos_sugeridos = [{"nombre": ..., "tipo": ...}, ...].

    catalogo_dosis: nombre de producto -> {"dosis_referencia", "unidad",
    "restricciones_ambientales", "instrucciones_seguridad"}. Una unidad
    cuyo producto sugerido no está en el catálogo, o cuyo producto no
    tiene dosis_referencia cargada, se incluye igual en la orden con
    sin_dosis_referencia=True — la cantidad queda pendiente de completar
    a mano en vez de descartarse silenciosamente.
    """
    items: list[dict] = []

    for unidad in unidades_manejo:
        props = unidad.get("properties", {})
        area_ha = float(props.get("area_total_ha", 0.0))
        productos_sugeridos = props.get("productos_sugeridos") or []
        nombre_producto = productos_sugeridos[0]["nombre"] if productos_sugeridos else None

        info_producto = catalogo_dosis.get(nombre_producto, {}) if nombre_producto else {}
        dosis_referencia = info_producto.get("dosis_referencia")
        unidad_dosis = info_producto.get("unidad")

        sin_dosis = dosis_referencia is None
        volumen_total = None if sin_dosis else round(area_ha * dosis_referencia, 3)

        items.append({
            "unidad_id": props.get("unidad_id"),
            "causa_indice": props.get("causa_indice"),
            "severidad": props.get("severidad"),
            "area_ha": area_ha,
            "zona_ids": props.get("zona_ids", []),
            "producto": nombre_producto,
            "dosis_por_ha": dosis_referencia,
            "unidad_dosis": unidad_dosis,
            "volumen_total": volumen_total,
            "restricciones_ambientales": info_producto.get("restricciones_ambientales"),
            "instrucciones_seguridad": info_producto.get("instrucciones_seguridad"),
            "sin_dosis_referencia": sin_dosis,
        })

    return {
        "items": items,
        "totales_por_producto": _totales_por_producto(items),
        "area_total_tratada_ha": round(sum(item["area_ha"] for item in items), 2),
    }


def _totales_por_producto(items: list[dict]) -> list[dict]:
    totales: dict[str, dict] = {}

    for item in items:
        producto = item["producto"]
        if producto is None:
            continue

        acumulado = totales.setdefault(producto, {
            "producto": producto,
            "area_ha": 0.0,
            "volumen_total": 0.0,
            "unidad_dosis": item["unidad_dosis"],
        })
        acumulado["area_ha"] += item["area_ha"]
        if item["volumen_total"] is not None:
            acumulado["volumen_total"] += item["volumen_total"]

    resultado = list(totales.values())
    for acumulado in resultado:
        acumulado["area_ha"] = round(acumulado["area_ha"], 2)
        acumulado["volumen_total"] = round(acumulado["volumen_total"], 3)

    return sorted(resultado, key=lambda t: t["producto"])
