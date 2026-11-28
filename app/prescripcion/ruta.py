"""
Recorrido sugerido de la máquina: pasadas paralelas en ida y vuelta,
orientadas sobre el lado más largo del lote (menos giros en cabecera).

La barra se abre en una pasada cuando cualquier parte de su ancho de labor
toca una zona a tratar, no solo la línea central: así una franja angosta que
cae entre dos pasadas no queda sin aplicar. El costo es algo de
sobreaplicación en los bordes, que simular_cobertura() mide.

Todo en metros locales (ver app/prescripcion/mapa.py).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from shapely.affinity import rotate
from shapely.geometry import LineString, box
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from app.prescripcion.mapa import M2_POR_HA, partes_poligonales

APLICACION = "aplicacion"
TRASLADO = "traslado"

_TOLERANCIA_M = 1e-6


@dataclass
class Tramo:
    pasada: int
    tipo: str
    linea_local: LineString
    dosis_por_ha: float


@dataclass
class Ruta:
    tramos: list[Tramo]
    angulo_grados: float
    ancho_labor_m: float
    n_pasadas: int

    def longitud_m(self, tipo: str) -> float:
        return sum(t.linea_local.length for t in self.tramos if t.tipo == tipo)


def generar_ruta(
    campo_local: BaseGeometry,
    zonas: list[tuple[BaseGeometry, float]],
    ancho_labor_m: float,
    solo_pasadas_con_aplicacion: bool,
) -> Ruta:
    """zonas: (geometría en metros locales, dosis por ha) de un mismo producto."""
    angulo = _angulo_lado_mayor(campo_local)
    campo_r = rotate(campo_local, -angulo, origin=(0, 0))
    zonas_r = [(rotate(g, -angulo, origin=(0, 0)), d) for g, d in zonas]

    minx, miny, maxx, maxy = campo_r.bounds
    medio = ancho_labor_m / 2
    tramos: list[Tramo] = []
    ultimo_punto: tuple[float, float] | None = None
    n_pasadas = 0

    y = miny + medio
    while y - medio < maxy:
        banda = box(minx - ancho_labor_m, y - medio, maxx + ancho_labor_m, y + medio)
        intervalos = _intervalos_aplicacion(banda, zonas_r)

        if solo_pasadas_con_aplicacion:
            extension = (intervalos[0][0], intervalos[-1][1]) if intervalos else None
        else:
            extension = _rango_x(campo_r.intersection(banda))
            if extension and intervalos:
                extension = (min(extension[0], intervalos[0][0]), max(extension[1], intervalos[-1][1]))

        if extension is not None and extension[1] - extension[0] > _TOLERANCIA_M:
            piezas = _piezas(extension[0], extension[1], intervalos)
            ida = n_pasadas % 2 == 0
            if not ida:
                piezas = [(b, a, d) for a, b, d in reversed(piezas)]

            inicio = (piezas[0][0], y)
            if ultimo_punto is not None:
                tramos.append(Tramo(n_pasadas, TRASLADO, LineString([ultimo_punto, inicio]), 0.0))
            for xa, xb, dosis in piezas:
                tipo = APLICACION if dosis is not None else TRASLADO
                tramos.append(Tramo(n_pasadas, tipo, LineString([(xa, y), (xb, y)]), dosis or 0.0))
            ultimo_punto = (piezas[-1][1], y)
            n_pasadas += 1

        y += ancho_labor_m

    for tramo in tramos:
        tramo.linea_local = rotate(tramo.linea_local, angulo, origin=(0, 0))

    return Ruta(tramos=tramos, angulo_grados=angulo, ancho_labor_m=ancho_labor_m, n_pasadas=n_pasadas)


def simular_cobertura(ruta: Ruta, zonas: list[tuple[BaseGeometry, float]]) -> dict:
    """
    Recorre la ruta como si fuera la máquina: cada tramo de aplicación pinta
    una franja del ancho de labor. Es la verificación de que el recorrido
    cubre lo que pide el mapa, sin máquina real.
    """
    objetivo = unary_union([g for g, _ in zonas])
    aplicados = [t for t in ruta.tramos if t.tipo == APLICACION]
    franjas = unary_union([
        t.linea_local.buffer(ruta.ancho_labor_m / 2, cap_style="flat") for t in aplicados
    ]) if aplicados else None

    area_objetivo = objetivo.area
    if franjas is None or franjas.is_empty:
        cubierta = 0.0
        area_aplicada = 0.0
        fuera = 0.0
    else:
        cubierta = franjas.intersection(objetivo).area
        area_aplicada = franjas.area
        fuera = franjas.difference(objetivo).area

    # Las pasadas están separadas exactamente un ancho de labor, así que las
    # franjas no se superponen y la cantidad se puede sumar tramo por tramo.
    cantidad = sum(t.linea_local.length * ruta.ancho_labor_m * t.dosis_por_ha for t in aplicados) / M2_POR_HA

    return {
        "cobertura_pct": round(100.0 * cubierta / area_objetivo, 2) if area_objetivo > 0 else 100.0,
        "superficie_aplicada_ha": round(area_aplicada / M2_POR_HA, 4),
        "superficie_fuera_de_zona_ha": round(fuera / M2_POR_HA, 4),
        "cantidad_aplicada": round(cantidad, 3),
    }


def _angulo_lado_mayor(geom: BaseGeometry) -> float:
    rectangulo = geom.minimum_rotated_rectangle
    if rectangulo.geom_type != "Polygon":
        return 0.0
    coords = list(rectangulo.exterior.coords)
    mejor, angulo = -1.0, 0.0
    for (x0, y0), (x1, y1) in zip(coords, coords[1:]):
        largo = math.hypot(x1 - x0, y1 - y0)
        if largo > mejor:
            mejor, angulo = largo, math.degrees(math.atan2(y1 - y0, x1 - x0))
    return angulo


def _rango_x(geom: BaseGeometry) -> tuple[float, float] | None:
    if geom.is_empty:
        return None
    minx, _, maxx, _ = geom.bounds
    return (minx, maxx)


def _intervalos_aplicacion(
    banda: BaseGeometry, zonas_r: list[tuple[BaseGeometry, float]],
) -> list[tuple[float, float, float]]:
    """Tramos en x donde la barra va abierta y con qué dosis; si dos zonas se
    tocan dentro de la banda, manda la dosis mayor."""
    crudos: list[tuple[float, float, float]] = []
    for geom, dosis in zonas_r:
        for parte in partes_poligonales(banda.intersection(geom)):
            if parte.area <= _TOLERANCIA_M:
                continue
            minx, _, maxx, _ = parte.bounds
            crudos.append((minx, maxx, dosis))
    if not crudos:
        return []

    cortes = sorted({x for a, b, _ in crudos for x in (a, b)})
    intervalos: list[tuple[float, float, float]] = []
    for a, b in zip(cortes, cortes[1:]):
        dosis = [d for x0, x1, d in crudos if x0 <= a and x1 >= b]
        if not dosis:
            continue
        d = max(dosis)
        if intervalos and abs(intervalos[-1][1] - a) <= _TOLERANCIA_M and intervalos[-1][2] == d:
            intervalos[-1] = (intervalos[-1][0], b, d)
        else:
            intervalos.append((a, b, d))
    return intervalos


def _piezas(
    x0: float, x1: float, intervalos: list[tuple[float, float, float]],
) -> list[tuple[float, float, float | None]]:
    piezas: list[tuple[float, float, float | None]] = []
    cursor = x0
    for a, b, dosis in intervalos:
        a, b = max(a, x0), min(b, x1)
        if b - a <= _TOLERANCIA_M:
            continue
        if a - cursor > _TOLERANCIA_M:
            piezas.append((cursor, a, None))
        piezas.append((a, b, dosis))
        cursor = b
    if x1 - cursor > _TOLERANCIA_M:
        piezas.append((cursor, x1, None))
    return piezas
