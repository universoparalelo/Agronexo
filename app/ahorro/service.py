"""
Orquestación de HU-R4-11 (I/O: DB + reuso del motor de diagnóstico).

Reusa el mismo pipeline que ya arma la orden de trabajo en PDF
(app/ordenes_trabajo/router.py): generar_diagnostico() -> unidades_manejo
-> generar_orden_trabajo(). La única pieza nueva de datos es el precio
por producto (app/diagnostico/precios.py); el cálculo de ahorro en sí es
puro y vive en app/ahorro/calculo.py.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ahorro.calculo import acumular_ahorro, calcular_ahorro_vuelo
from app.diagnostico import precios
from app.diagnostico.orden_trabajo import generar_orden_trabajo
from app.diagnostico.service import generar_diagnostico
from app.ingesta.service import listar_vuelos
from app.lotes.models import Cultivo, EstadoVueloEnum, Lote, Vuelo
from app.ordenes_trabajo.service import cargar_catalogo_dosis


async def _resolver_precios(db: AsyncSession, nombres_producto: set[str]) -> dict[str, dict]:
    """Resuelve el mejor precio (usuario vigente o referencia) para cada
    nombre de producto presente en la orden — una sola consulta por
    producto, no por unidad de manejo. producto_id viaja siempre que el
    producto exista en el catálogo (tenga o no precio cargado) — el
    frontend lo necesita para ofrecer "cargar precio" en los que faltan."""
    if not nombres_producto:
        return {}

    from sqlalchemy import select

    from app.diagnostico.models import ProductoFitosanitario

    result = await db.execute(
        select(ProductoFitosanitario).where(ProductoFitosanitario.nombre.in_(nombres_producto))
    )
    productos = {p.nombre: p for p in result.scalars().all()}

    resueltos: dict[str, dict] = {}
    for nombre, producto in productos.items():
        precio = await precios.resolver_precio(db, producto.id)
        resueltos[nombre] = {
            "producto_id": producto.id,
            "precio_usd": precio.precio_usd if precio else None,
            "tipo": precio.tipo if precio else None,
        }
    return resueltos


async def calcular_ahorro_del_vuelo(db: AsyncSession, lote: Lote, vuelo: Vuelo) -> dict | None:
    """Devuelve None si el vuelo no tiene diagnóstico disponible (no
    completado, sin NDVI, sin cultivo asociado). Un vuelo sin unidades de
    manejo (todo el lote en rango normal) es un resultado válido — ahorro
    cero, no None, porque no hubo nada que tratar en ninguno de los dos
    escenarios."""
    diagnostico = await generar_diagnostico(db, lote, vuelo.id)
    if diagnostico is None:
        return None

    unidades_manejo = diagnostico.get("unidades_manejo", [])
    if not unidades_manejo:
        return {
            "vuelo_id": vuelo.id,
            "fecha_vuelo": vuelo.fecha_vuelo,
            "area_total_lote_ha": lote.area_ha or 0.0,
            "area_tratada_ha": 0.0,
            "productos": [],
            "ahorro_total_pesos": 0.0,
            "todos_los_precios_cargados": True,
        }

    catalogo_dosis = await cargar_catalogo_dosis(db)
    orden = generar_orden_trabajo(unidades_manejo, catalogo_dosis)

    nombres = {t["producto"] for t in orden.get("totales_por_producto", [])}
    precios_por_producto = await _resolver_precios(db, nombres)

    resultado = calcular_ahorro_vuelo(orden, catalogo_dosis, lote.area_ha or 0.0, precios_por_producto)
    return {
        "vuelo_id": vuelo.id,
        "fecha_vuelo": vuelo.fecha_vuelo,
        "area_total_lote_ha": lote.area_ha or 0.0,
        "area_tratada_ha": resultado["area_total_tratada_ha"],
        "productos": resultado["productos"],
        "ahorro_total_pesos": resultado["ahorro_total_pesos"],
        "todos_los_precios_cargados": resultado["todos_los_precios_cargados"],
    }


async def calcular_ahorro_de_campana(db: AsyncSession, lote: Lote, cultivo: Cultivo) -> dict:
    """Suma el ahorro de todos los vuelos completados del cultivo
    (= campaña). Vuelos sin diagnóstico disponible (pendientes, en error,
    o sin unidades de manejo propias) se cuentan en n_vuelos_sin_diagnostico
    pero no rompen el acumulado — una campaña con un vuelo fallido igual
    puede mostrar el ahorro de los que sí procesaron."""
    todos_los_vuelos = await listar_vuelos(db, lote.id)
    vuelos_cultivo = [
        v for v in todos_los_vuelos
        if v.cultivo_id == cultivo.id and v.estado == EstadoVueloEnum.completado
    ]

    ahorros_por_vuelo = []
    n_sin_diagnostico = 0
    for vuelo in vuelos_cultivo:
        ahorro_vuelo = await calcular_ahorro_del_vuelo(db, lote, vuelo)
        if ahorro_vuelo is None:
            n_sin_diagnostico += 1
            continue
        ahorros_por_vuelo.append(ahorro_vuelo)

    acumulado = acumular_ahorro(ahorros_por_vuelo)

    return {
        "cultivo_id": cultivo.id,
        "tipo_cultivo": cultivo.tipo_cultivo,
        "variedad": cultivo.variedad,
        "fecha_siembra": cultivo.fecha_siembra,
        "fecha_cosecha": cultivo.fecha_cosecha,
        "n_vuelos_considerados": len(ahorros_por_vuelo),
        "n_vuelos_sin_diagnostico": n_sin_diagnostico,
        "productos": acumulado["productos"],
        "ahorro_total_pesos": acumulado["ahorro_total_pesos"],
        "todos_los_precios_cargados": acumulado["todos_los_precios_cargados"],
    }
