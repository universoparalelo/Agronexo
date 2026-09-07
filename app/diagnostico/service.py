"""
Orquestación del diagnóstico: único módulo del motor con I/O (DB + MinIO).
Carga el vuelo y sus GeoJSON ya generados, calcula patrón espacial,
resuelve valores multi-índice por intersección geométrica, corre el motor
de reglas por zona y arma la respuesta GeoJSON enriquecida.

Deliberadamente sin GeoPandas/pandas/numpy — este módulo corre dentro del
proceso FastAPI, que no tiene esas dependencias GIS instaladas (ver
app/diagnostico/forma.py para el detalle de por qué). Solo Shapely, ya
presente en docker/requirements.api.txt.

Persistido desde 0016_crear_tabla_diagnosticos — un vuelo tiene a lo sumo un
diagnóstico guardado (tabla `diagnosticos`, UNIQUE en vuelo_id). La primera
vez que se pide se calcula y se guarda; las siguientes veces se devuelve lo
guardado sin recalcular, salvo que se pida explícitamente recalcular (ver
generar_diagnostico(forzar_recalculo=True)), que sobrescribe la fila. No es
historial multi-versión — eso sigue siendo alcance de release 4 (RFGL-03,
ver docs/release-v1.0.0.md "Problemas abiertos").
"""

from __future__ import annotations

import logging
import math
import uuid
from datetime import datetime, timezone

from shapely.geometry import mapping, shape
from shapely.geometry.base import BaseGeometry
from geoalchemy2.shape import to_shape
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from sqlalchemy import select

from app.diagnostico.engine import ContextoZona, evaluar_zona
from app.diagnostico.estadios import normalizar_estadio
from app.diagnostico.forma import ZonaInput, clasificar_patrones, proyectar_a_metros_locales
from app.diagnostico.models import CausaIndiceEnum, Diagnostico, ProductoFitosanitario, TipoProductoEnum
from app.diagnostico.texto import calcular_severidad, generar_resumen_general, generar_texto_zona
from app.diagnostico.zonificacion import generar_unidades_manejo
from app.ingesta.service import obtener_analisis_indice, obtener_resultado_geojson, obtener_resultado_geojson_indice, obtener_vuelo
from app.lotes.models import EstadoVueloEnum, IndiceEnum, Lote, Vuelo

logger = logging.getLogger(__name__)

# Índices adicionales que pueden estar disponibles además de NDVI (siempre presente).
_INDICES_ADICIONALES = (IndiceEnum.ndre, IndiceEnum.savi, IndiceEnum.exg, IndiceEnum.gndvi)


async def listar_productos(
    db: AsyncSession,
    causa: CausaIndiceEnum | None = None,
    tipo: TipoProductoEnum | None = None,
) -> list[ProductoFitosanitario]:
    stmt = select(ProductoFitosanitario)
    if causa is not None:
        stmt = stmt.where(ProductoFitosanitario.causa_indice == causa)
    if tipo is not None:
        stmt = stmt.where(ProductoFitosanitario.tipo == tipo)
    stmt = stmt.order_by(ProductoFitosanitario.causa_indice, ProductoFitosanitario.nombre)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _cargar_catalogo_productos(db: AsyncSession) -> dict[str, list[dict[str, str]]]:
    result = await db.execute(
        select(ProductoFitosanitario).order_by(ProductoFitosanitario.causa_indice)
    )
    catalogo: dict[str, list[dict[str, str]]] = {}
    for prod in result.scalars().all():
        catalogo.setdefault(prod.causa_indice.value, []).append({
            "nombre": prod.nombre,
            "tipo": prod.tipo.value,
        })
    return catalogo


def _resolver_estadio(lote: Lote, vuelo: Vuelo) -> str | None:
    """
    El estadio fenológico del vuelo puntual tiene prioridad — el del lote
    es solo el valor cargado al crear el lote (ver migración 0017) y puede
    haber quedado desactualizado para vuelos posteriores.
    """
    return vuelo.estadio_fenologico or lote.estadio_fenologico


def _features_a_zonas(geojson: dict) -> list[ZonaInput]:
    zonas = []
    for i, feat in enumerate(geojson.get("features", [])):
        props = feat.get("properties", {})
        zonas.append(ZonaInput(
            id=i,
            geometry=shape(feat["geometry"]),
            clase=props.get("clase", "sin_dato"),
            area_ha=float(props.get("area_ha", 0.0)),
        ))
    return zonas


def enriquecer_con_indice(
    zonas_base: list[ZonaInput], geojson_indice: dict, lon0: float, lat0: float,
) -> dict[int, float]:
    """
    Para cada zona base (partición NDVI) calcula el promedio del otro
    índice ponderado por área de intersección geométrica real contra las
    zonas de geojson_indice (vectorizado independientemente, con bordes
    propios). Zonas sin superposición no aparecen en el resultado — las
    reglas que requieren ese índice se saltan para ellas.

    'ndvi_promedio' es el nombre de propiedad heredado de
    workers/gis/zonas.py — contiene el promedio del índice que se haya
    procesado (NDRE/SAVI/ExG/GNDVI también), no necesariamente NDVI. No se
    renombra para no romper el contrato de GET .../resultado, ya
    consumido por el frontend (MapaIndice.jsx, TablaZonas.jsx, MapaZonas.jsx).
    """
    geoms_otro: list[tuple[BaseGeometry, float]] = []
    for feat in geojson_indice.get("features", []):
        valor = feat.get("properties", {}).get("ndvi_promedio")
        if valor is None:
            continue
        geom_local = proyectar_a_metros_locales(shape(feat["geometry"]), lon0, lat0)
        geoms_otro.append((geom_local, float(valor)))

    resultado: dict[int, float] = {}
    for zona in zonas_base:
        geom_local = proyectar_a_metros_locales(zona.geometry, lon0, lat0)
        peso_total = 0.0
        acumulado = 0.0
        for geom_otro_local, valor in geoms_otro:
            if not geom_local.intersects(geom_otro_local):
                continue
            area_interseccion = geom_local.intersection(geom_otro_local).area
            if area_interseccion > 0:
                peso_total += area_interseccion
                acumulado += area_interseccion * valor
        if peso_total > 0:
            resultado[zona.id] = acumulado / peso_total
    return resultado


async def obtener_diagnostico_guardado(db: AsyncSession, vuelo_id: uuid.UUID) -> Diagnostico | None:
    stmt = select(Diagnostico).where(Diagnostico.vuelo_id == vuelo_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def guardar_diagnostico(db: AsyncSession, vuelo_id: uuid.UUID, resultado: dict, calculado_en: datetime) -> None:
    """
    Upsert — un vuelo tiene a lo sumo un diagnóstico guardado (vuelo_id
    UNIQUE en la tabla). Recalcular sobrescribe la fila existente, no
    acumula historial (ver docstring del módulo).
    """
    stmt = pg_insert(Diagnostico).values(vuelo_id=vuelo_id, resultado=resultado, calculado_en=calculado_en)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Diagnostico.vuelo_id],
        set_={"resultado": resultado, "calculado_en": calculado_en},
    )
    await db.execute(stmt)
    await db.flush()


async def generar_diagnostico(
    db: AsyncSession, lote: Lote, vuelo_id: uuid.UUID, *, forzar_recalculo: bool = False,
) -> dict | None:
    """
    Devuelve el GeoJSON de zonas NDVI del vuelo, enriquecido por zona con:
    patrón espacial, regla que matcheó, causa, confianza, acción
    recomendada, cómo confirmar en campo y productos sugeridos.

    Devuelve None si el vuelo no existe, no está 'completado' o no tiene
    NDVI calculado — el router lo traduce a 404.

    Primera llamada para un vuelo: calcula y guarda en `diagnosticos`. Las
    siguientes devuelven lo guardado sin recalcular, salvo
    forzar_recalculo=True (botón "Recalcular" del frontend), que vuelve a
    calcular todo y sobrescribe la fila guardada.

    Solo la parte async (DB + descarga de GeoJSON de MinIO, esta última ya
    corre en threadpool dentro de obtener_resultado_geojson*) toca el event
    loop acá. El cómputo geométrico (Shapely puro, sin I/O) se delega por
    completo a _calcular_diagnostico() vía run_in_threadpool — para un
    polígono con cientos de miles de vértices (raster real de varios GB mal
    simplificado, ver docs/release-v1.0.0.md) ese cómputo tarda minutos, y
    sin el threadpool bloqueaba el proceso de FastAPI entero mientras corría
    (nadie más podía usar la API, ver bug documentado 2026-08-28).
    """
    vuelo = await obtener_vuelo(db, lote.id, vuelo_id)
    if vuelo is None or vuelo.estado != EstadoVueloEnum.completado:
        return None

    if not forzar_recalculo:
        guardado = await obtener_diagnostico_guardado(db, vuelo_id)
        if guardado is not None:
            return guardado.resultado

    ndvi_geojson = await obtener_resultado_geojson(db, lote.id, vuelo_id)
    if ndvi_geojson is None:
        return None

    features_ndvi = ndvi_geojson.get("features", [])
    if not features_ndvi:
        return {"type": "FeatureCollection", "features": []}

    geojson_por_indice: dict[str, dict] = {}
    for indice in _INDICES_ADICIONALES:
        try:
            analisis = await obtener_analisis_indice(db, vuelo_id, indice)
            if analisis is None or analisis.estado != EstadoVueloEnum.completado or analisis.geojson_key is None:
                continue
            geojson_otro = await obtener_resultado_geojson_indice(db, vuelo_id, indice)
            if not geojson_otro or not geojson_otro.get("features"):
                continue
            geojson_por_indice[indice.value] = geojson_otro
        except Exception:
            logger.exception("No se pudo resolver el índice %s para el vuelo %s", indice.value, vuelo_id)
            continue

    lote_geom_4326: BaseGeometry | None = to_shape(lote.geometry) if lote.geometry is not None else None

    catalogo = await _cargar_catalogo_productos(db)

    resultado = await run_in_threadpool(
        _calcular_diagnostico,
        ndvi_geojson, geojson_por_indice, lote_geom_4326,
        lote.cultivo, _resolver_estadio(lote, vuelo), catalogo,
        lote_id=str(lote.id),
        lote_nombre=lote.nombre,
        vuelo_id=str(vuelo_id),
        fecha_vuelo=str(vuelo.fecha_vuelo) if vuelo.fecha_vuelo else None,
    )

    calculado_en = datetime.now(timezone.utc)
    resultado["metadata"]["calculado_en"] = calculado_en.isoformat()
    await guardar_diagnostico(db, vuelo_id, resultado, calculado_en)

    return resultado


def _calcular_diagnostico(
    ndvi_geojson: dict,
    geojson_por_indice: dict[str, dict],
    lote_geom_4326: BaseGeometry | None,
    cultivo,
    estadio_fenologico: str | None,
    catalogo: dict[str, list[dict[str, str]]] | None = None,
    *,
    lote_id: str | None = None,
    lote_nombre: str | None = None,
    vuelo_id: str | None = None,
    fecha_vuelo: str | None = None,
) -> dict:
    """Cómputo geométrico puro (Shapely, sin I/O ni DB) — ver generar_diagnostico()."""
    estadio_normalizado = normalizar_estadio(estadio_fenologico)
    features_ndvi = ndvi_geojson.get("features", [])
    zonas = _features_a_zonas(ndvi_geojson)

    patrones = clasificar_patrones(zonas, lote_geom_4326)

    area_total_ha = sum(z.area_ha for z in zonas) or 1.0
    ndvi_promedio_lote = sum(
        float(f["properties"].get("ndvi_promedio", 0.0)) * z.area_ha
        for f, z in zip(features_ndvi, zonas)
    ) / area_total_ha

    if lote_geom_4326 is not None:
        lon0, lat0 = lote_geom_4326.centroid.x, lote_geom_4326.centroid.y
    else:
        lon0 = sum(z.geometry.centroid.x for z in zonas) / len(zonas)
        lat0 = sum(z.geometry.centroid.y for z in zonas) / len(zonas)

    valores_por_indice: dict[str, dict[int, float]] = {
        "ndvi": {z.id: float(f["properties"].get("ndvi_promedio", 0.0)) for z, f in zip(zonas, features_ndvi)}
    }
    for nombre_indice, geojson_otro in geojson_por_indice.items():
        valores_por_indice[nombre_indice] = enriquecer_con_indice(zonas, geojson_otro, lon0, lat0)

    features_salida = []
    for zona, feat_original in zip(zonas, features_ndvi):
        valores: dict[str, float] = {}
        for nombre, mapa in valores_por_indice.items():
            if zona.id in mapa and not math.isnan(mapa[zona.id]):
                valores[nombre] = mapa[zona.id]

        contexto = ContextoZona(
            zona_id=zona.id,
            valores=valores,
            patron_espacial=patrones.get(zona.id, "manchas_irregulares"),
            area_ha=zona.area_ha,
            ndvi_promedio_lote=ndvi_promedio_lote,
            cultivo=cultivo,
            estadio_normalizado=estadio_normalizado,
        )
        resultado = evaluar_zona(contexto)

        ndvi_zona = float(feat_original.get("properties", {}).get("ndvi_promedio", 0.0))
        severidad = calcular_severidad(ndvi_zona, ndvi_promedio_lote, resultado.causa_indice)

        props = dict(feat_original.get("properties", {}))
        props.update({
            "patron_espacial": contexto.patron_espacial,
            "zona_id": zona.id,
            "regla_id": resultado.regla_id,
            "regla_nombre": resultado.regla_nombre,
            "confianza": resultado.confianza.value,
            "causa_indice": resultado.causa_indice,
            "severidad": severidad,
            "accion_recomendada": resultado.accion_recomendada,
            "como_confirmar_campo": resultado.como_confirmar_campo,
            "excluida": resultado.excluida,
            "productos_sugeridos": (catalogo or {}).get(resultado.causa_indice, []),
        })
        props["texto_explicativo"] = generar_texto_zona(props, ndvi_promedio_lote)

        features_salida.append({
            "type": "Feature",
            "geometry": mapping(zona.geometry),
            "properties": props,
        })

    resumen = generar_resumen_general(features_salida)
    unidades = generar_unidades_manejo(features_salida, lon0, lat0)

    return {
        "type": "FeatureCollection",
        "features": features_salida,
        "unidades_manejo": unidades,
        "metadata": {
            "lote_id": lote_id,
            "lote_nombre": lote_nombre,
            "vuelo_id": vuelo_id,
            "fecha_vuelo": fecha_vuelo,
            "cultivo": cultivo.value,
            "estadio_fenologico": estadio_fenologico,
            "ndvi_promedio_lote": round(ndvi_promedio_lote, 4),
            "indices_disponibles": list(valores_por_indice.keys()),
            "n_unidades_manejo": len(unidades),
            "resumen_general": resumen,
        },
    }
