"""
Perfiles de máquina para el paquete de prescripción.

Valores por defecto típicos, no de un modelo puntual: el usuario puede pisar
ancho de labor y margen al pedir el paquete. El margen sale de
docs/Arquitectura.md ("Buffer de aplicación": 3 a 7 m para equipos
terrestres, por el tiempo de apertura de las boquillas); el dron abre y
cierra más rápido y va más lento, por eso lleva el mínimo.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MaquinaEnum(str, Enum):
    dron = "dron"
    mosquito = "mosquito"


@dataclass(frozen=True)
class PerfilMaquina:
    nombre: str
    ancho_labor_m: float
    margen_m: float
    caldo_l_ha: float
    tanque_l: float
    # Un dron vuela solo donde hay que aplicar; un mosquito recorre el lote
    # entero y abre o cierra la barra según el mapa.
    solo_pasadas_con_aplicacion: bool


PERFILES: dict[MaquinaEnum, PerfilMaquina] = {
    MaquinaEnum.dron: PerfilMaquina(
        nombre="Dron pulverizador",
        ancho_labor_m=7.0,
        margen_m=3.0,
        caldo_l_ha=15.0,
        tanque_l=40.0,
        solo_pasadas_con_aplicacion=True,
    ),
    MaquinaEnum.mosquito: PerfilMaquina(
        nombre="Pulverizadora autopropulsada (mosquito)",
        ancho_labor_m=28.0,
        margen_m=5.0,
        caldo_l_ha=80.0,
        tanque_l=3000.0,
        solo_pasadas_con_aplicacion=False,
    ),
}


def resolver_perfil(
    maquina: MaquinaEnum, ancho_labor_m: float | None = None, margen_m: float | None = None,
) -> PerfilMaquina:
    base = PERFILES[maquina]
    return PerfilMaquina(
        nombre=base.nombre,
        ancho_labor_m=ancho_labor_m if ancho_labor_m is not None else base.ancho_labor_m,
        margen_m=margen_m if margen_m is not None else base.margen_m,
        caldo_l_ha=base.caldo_l_ha,
        tanque_l=base.tanque_l,
        solo_pasadas_con_aplicacion=base.solo_pasadas_con_aplicacion,
    )
