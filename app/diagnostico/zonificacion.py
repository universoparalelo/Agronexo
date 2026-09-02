"""
Zonificación de manejo (RFDR-02): agrupa zonas contiguas con misma causa
y severidad en unidades de manejo únicas para prescripción diferenciada.
Puro: sin I/O, sin DB. Usa Shapely para operaciones geométricas.
"""

from __future__ import annotations

from shapely.geometry import mapping, shape
from shapely.ops import unary_union

from app.diagnostico.forma import proyectar_a_metros_locales
from app.diagnostico.texto import generar_texto_unidad

BUFFER_CONTIGUIDAD_M = 20.0


def _componentes_conexos(
    indices: list[int], adyacencias: dict[int, set[int]],
) -> list[list[int]]:
    visitados: set[int] = set()
    componentes: list[list[int]] = []
    for idx in indices:
        if idx in visitados:
            continue
        componente: list[int] = []
        cola = [idx]
        while cola:
            actual = cola.pop()
            if actual in visitados:
                continue
            visitados.add(actual)
            componente.append(actual)
            for vecino in adyacencias.get(actual, set()):
                if vecino not in visitados:
                    cola.append(vecino)
        componentes.append(componente)
    return componentes


def generar_unidades_manejo(
    features: list[dict], lon0: float, lat0: float,
) -> list[dict]:
    candidatas: list[tuple[int, dict]] = []
    for i, f in enumerate(features):
        p = f.get("properties", {})
        if p.get("regla_id") in ("R99", "R00"):
            continue
        if p.get("severidad") == "normal":
            continue
        candidatas.append((i, f))

    if not candidatas:
        return []

    grupos: dict[tuple[str, str], list[tuple[int, dict]]] = {}
    for idx, feat in candidatas:
        p = feat.get("properties", {})
        clave = (p.get("causa_indice", ""), p.get("severidad", ""))
        grupos.setdefault(clave, []).append((idx, feat))

    unidades: list[dict] = []
    unidad_id = 0

    for (causa, severidad), miembros in grupos.items():
        if len(miembros) == 1:
            unidad_id += 1
            _, feat = miembros[0]
            unidades.append(_crear_unidad(unidad_id, [feat], causa, severidad))
            continue

        geoms_local = {}
        for idx, feat in miembros:
            geom_4326 = shape(feat["geometry"])
            geoms_local[idx] = proyectar_a_metros_locales(geom_4326, lon0, lat0)

        indices = [idx for idx, _ in miembros]
        adyacencias: dict[int, set[int]] = {idx: set() for idx in indices}

        for i, idx_a in enumerate(indices):
            buf_a = geoms_local[idx_a].buffer(BUFFER_CONTIGUIDAD_M)
            for idx_b in indices[i + 1:]:
                if buf_a.intersects(geoms_local[idx_b].buffer(BUFFER_CONTIGUIDAD_M)):
                    adyacencias[idx_a].add(idx_b)
                    adyacencias[idx_b].add(idx_a)

        componentes = _componentes_conexos(indices, adyacencias)
        feat_por_idx = {idx: feat for idx, feat in miembros}

        for componente in componentes:
            unidad_id += 1
            feats = [feat_por_idx[idx] for idx in componente]
            unidades.append(_crear_unidad(unidad_id, feats, causa, severidad))

    orden = {"critica": 0, "moderada": 1, "leve": 2, "vigorosa": 3}
    unidades.sort(key=lambda u: (
        orden.get(u["properties"]["severidad"], 9),
        -u["properties"]["area_total_ha"],
    ))

    return unidades


def _crear_unidad(
    unidad_id: int, features: list[dict], causa: str, severidad: str,
) -> dict:
    geoms = [shape(f["geometry"]) for f in features]
    union_geom = unary_union(geoms)

    area_total = sum(float(f.get("properties", {}).get("area_ha", 0)) for f in features)

    ndvi_acum = 0.0
    area_acum = 0.0
    for f in features:
        p = f.get("properties", {})
        area = float(p.get("area_ha", 0))
        ndvi = p.get("ndvi_promedio")
        if ndvi is not None and area > 0:
            ndvi_acum += float(ndvi) * area
            area_acum += area
    ndvi_promedio = round(ndvi_acum / area_acum, 3) if area_acum > 0 else None

    zona_ids = [f.get("properties", {}).get("zona_id") for f in features]
    p0 = features[0].get("properties", {})

    props = {
        "unidad_id": unidad_id,
        "causa_indice": causa,
        "severidad": severidad,
        "regla_nombre": p0.get("regla_nombre", ""),
        "accion_recomendada": p0.get("accion_recomendada", ""),
        "productos_sugeridos": p0.get("productos_sugeridos", []),
        "area_total_ha": round(area_total, 2),
        "ndvi_promedio": ndvi_promedio,
        "n_zonas": len(features),
        "zona_ids": zona_ids,
    }
    props["texto_unidad"] = generar_texto_unidad(props)

    return {
        "type": "Feature",
        "geometry": mapping(union_geom),
        "properties": props,
    }
