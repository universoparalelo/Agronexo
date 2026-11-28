"""
Mapa de prescripción por producto (RFSA-02): cruza la geometría de las
unidades de manejo del diagnóstico con el producto y la dosis que les asigna
la orden de trabajo (app/diagnostico/orden_trabajo.py).

Puro: sin I/O ni DB. La geometría se trabaja en metros locales (misma
proyección equirectangular que app/diagnostico/forma.py, suficiente a escala
de lote) y se vuelve a EPSG:4326 solo al escribir los archivos.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import shapely
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from app.diagnostico.forma import proyectar_a_metros_locales
from app.diagnostico.orden_trabajo import texto_marca

M2_POR_HA = 10_000.0


@dataclass
class ZonaPrescripcion:
    unidad_id: int
    severidad: str
    causa_indice: str
    provisorio: bool
    dosis_por_ha: float
    # Con margen, recortada al lote y sin superponerse con otra zona del mismo producto.
    geom_local: BaseGeometry
    area_ha_orden: float

    @property
    def area_ha(self) -> float:
        return self.geom_local.area / M2_POR_HA

    @property
    def cantidad(self) -> float:
        return self.area_ha * self.dosis_por_ha


@dataclass
class PrescripcionProducto:
    producto: str
    marca: str | None
    unidad_dosis: str
    zonas: list[ZonaPrescripcion]
    # Total de la orden de trabajo (superficie diagnosticada, sin margen).
    cantidad_orden: float
    area_ha_orden: float

    @property
    def provisorio(self) -> bool:
        return any(z.provisorio for z in self.zonas)

    @property
    def area_ha(self) -> float:
        return sum(z.area_ha for z in self.zonas)

    @property
    def cantidad(self) -> float:
        return sum(z.cantidad for z in self.zonas)

    @property
    def dosis_maxima(self) -> float:
        return max((z.dosis_por_ha for z in self.zonas), default=0.0)

    @property
    def unidad_cantidad(self) -> str:
        return self.unidad_dosis.split("/")[0]


@dataclass
class MapaPrescripcion:
    lon0: float
    lat0: float
    campo_local: BaseGeometry
    # True si el campo es el límite real del lote; False si se estimó por falta de límite.
    campo_es_limite_lote: bool
    margen_m: float
    productos: list[PrescripcionProducto]
    sin_prescripcion: list[dict] = field(default_factory=list)

    def a_wgs84(self, geom_local: BaseGeometry) -> BaseGeometry:
        """Inversa de app.diagnostico.forma.proyectar_a_metros_locales."""
        escala_x = 111_320.0 * math.cos(math.radians(self.lat0))
        return shapely.transform(
            geom_local,
            lambda c: np.column_stack((c[:, 0] / escala_x + self.lon0, c[:, 1] / 110_540.0 + self.lat0)),
        )


def armar_mapa_prescripcion(
    unidades_manejo: list[dict],
    orden: dict,
    limite_lote_4326: BaseGeometry | None,
    margen_m: float,
) -> MapaPrescripcion:
    """
    unidades_manejo: salida de generar_unidades_manejo() (con geometría).
    orden: salida de generar_orden_trabajo() sobre esas mismas unidades.

    Una unidad sin producto o sin dosis no entra en ningún mapa: queda en
    sin_prescripcion con el motivo, para avisarlo en el paquete en vez de
    descartarla en silencio (mismo criterio que la orden de trabajo).
    """
    geoms_4326 = {
        u["properties"]["unidad_id"]: shape(u["geometry"])
        for u in unidades_manejo
        if u.get("geometry")
    }

    hay_limite = limite_lote_4326 is not None and not limite_lote_4326.is_empty
    referencia = limite_lote_4326 if hay_limite else unary_union(list(geoms_4326.values()))
    centro = referencia.centroid
    lon0, lat0 = centro.x, centro.y

    geoms_local = {uid: proyectar_a_metros_locales(g, lon0, lat0) for uid, g in geoms_4326.items()}
    if hay_limite:
        campo_local = proyectar_a_metros_locales(limite_lote_4326, lon0, lat0)
    else:
        campo_local = unary_union(list(geoms_local.values())).buffer(margen_m).envelope

    sin_prescripcion: list[dict] = []
    items_por_producto: dict[str, list[dict]] = {}
    for item in orden.get("items", []):
        uid = item.get("unidad_id")
        if uid not in geoms_local:
            sin_prescripcion.append({"unidad_id": uid, "motivo": "La unidad no tiene geometría."})
        elif not item.get("producto"):
            sin_prescripcion.append({"unidad_id": uid, "motivo": "Sin producto sugerido para la causa."})
        elif item.get("dosis_por_ha") is None:
            sin_prescripcion.append({
                "unidad_id": uid,
                "motivo": f"{item['producto']}: sin dosis cargada en el catálogo.",
            })
        else:
            items_por_producto.setdefault(item["producto"], []).append(item)

    productos = [
        _armar_producto(nombre, items, geoms_local, campo_local, margen_m)
        for nombre, items in items_por_producto.items()
    ]

    return MapaPrescripcion(
        lon0=lon0,
        lat0=lat0,
        campo_local=campo_local,
        campo_es_limite_lote=hay_limite,
        margen_m=margen_m,
        productos=[p for p in productos if p.zonas],
        sin_prescripcion=sin_prescripcion,
    )


def _armar_producto(
    nombre: str,
    items: list[dict],
    geoms_local: dict[int, BaseGeometry],
    campo_local: BaseGeometry,
    margen_m: float,
) -> PrescripcionProducto:
    # Con margen, dos unidades vecinas del mismo producto se pisan: la zona de
    # mayor dosis se queda con la superposición, así ningún punto recibe menos
    # de lo que su unidad necesita y ninguno se cuenta dos veces.
    ocupado: BaseGeometry | None = None
    zonas: list[ZonaPrescripcion] = []
    for item in sorted(items, key=lambda i: -float(i["dosis_por_ha"])):
        geom = geoms_local[item["unidad_id"]]
        if margen_m > 0:
            # Esquinas en ángulo y no redondeadas: el redondeo agrega decenas
            # de vértices por esquina, que algunos monitores no aceptan.
            geom = geom.buffer(margen_m, join_style="mitre", mitre_limit=2.0)
        geom = geom.intersection(campo_local)
        if ocupado is not None:
            geom = geom.difference(ocupado)
        geom = _solo_poligonos(geom)
        if geom is None:
            continue
        ocupado = geom if ocupado is None else ocupado.union(geom)
        zonas.append(ZonaPrescripcion(
            unidad_id=item["unidad_id"],
            severidad=item.get("severidad") or "",
            causa_indice=item.get("causa_indice") or "",
            provisorio=bool(item.get("provisorio")),
            dosis_por_ha=float(item["dosis_por_ha"]),
            geom_local=geom,
            area_ha_orden=float(item.get("area_ha") or 0.0),
        ))

    zonas.sort(key=lambda z: z.unidad_id)
    primero = items[0]
    return PrescripcionProducto(
        producto=nombre,
        marca=texto_marca(primero.get("marca_recomendada")),
        unidad_dosis=primero.get("unidad_dosis") or "",
        zonas=zonas,
        cantidad_orden=sum(float(i.get("volumen_total") or 0.0) for i in items),
        area_ha_orden=sum(float(i.get("area_ha") or 0.0) for i in items),
    )


def _solo_poligonos(geom: BaseGeometry) -> BaseGeometry | None:
    """intersection/difference pueden dejar líneas o puntos sueltos en los bordes."""
    if geom.is_empty:
        return None
    if geom.geom_type in ("Polygon", "MultiPolygon"):
        return geom
    partes = [g for g in getattr(geom, "geoms", []) if g.geom_type in ("Polygon", "MultiPolygon")]
    if not partes:
        return None
    return unary_union(partes)


def partes_poligonales(geom: BaseGeometry) -> list:
    if geom.is_empty:
        return []
    if geom.geom_type == "Polygon":
        return [geom]
    return [g for g in getattr(geom, "geoms", []) if g.geom_type == "Polygon"]
