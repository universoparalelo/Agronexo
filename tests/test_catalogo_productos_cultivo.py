"""
Tests del filtro de productos sugeridos por cultivo
(app/diagnostico/service.py::armar_catalogo_productos). Función pura: no
necesita DB.

    docker compose exec api python3 -m pytest tests/test_catalogo_productos_cultivo.py -v
"""

import uuid
from types import SimpleNamespace

from app.diagnostico.models import CausaIndiceEnum, TipoProductoEnum
from app.diagnostico.service import armar_catalogo_productos
from app.lotes.models import CultivoEnum

HERBICIDA = CausaIndiceEnum.interferencia_vegetacion


def _producto(nombre, causa=HERBICIDA, tipo=TipoProductoEnum.herbicida):
    return SimpleNamespace(id=uuid.uuid4(), nombre=nombre, causa_indice=causa, tipo=tipo)


def _catalogo(cultivo, **marcas_por_nombre):
    productos = {nombre: _producto(nombre) for nombre in marcas_por_nombre}
    cultivos = {productos[n].id: marcas for n, marcas in marcas_por_nombre.items()}
    return armar_catalogo_productos(list(productos.values()), cultivos, cultivo)


def _nombres(catalogo, causa=HERBICIDA):
    return [p["nombre"] for p in catalogo.get(causa.value, [])]


def test_sin_cultivo_devuelve_todos_los_productos():
    catalogo = _catalogo(None, Atrazina=["maiz, sorgo"], Cletodim=["soja"])
    assert sorted(_nombres(catalogo)) == ["Atrazina", "Cletodim"]


def test_filtra_los_productos_que_no_son_del_cultivo():
    catalogo = _catalogo(CultivoEnum.soja, Atrazina=["maiz, sorgo"], Cletodim=["soja, algodon"])
    assert _nombres(catalogo) == ["Cletodim"]


def test_un_producto_es_apto_si_alguna_marca_lo_es():
    catalogo = _catalogo(CultivoEnum.soja, **{"2,4-D": ["maiz, sorgo", "soja, maiz"]})
    assert _nombres(catalogo) == ["2,4-D"]


def test_ignora_tildes_mayusculas_y_espacios():
    catalogo = _catalogo(CultivoEnum.maiz, Atrazina=["Maíz ,  SORGO"])
    assert _nombres(catalogo) == ["Atrazina"]


def test_barbecho_no_cuenta_como_ningun_cultivo():
    catalogo = _catalogo(CultivoEnum.soja, Glifosato=["barbecho"])
    assert catalogo == {}


def test_sin_producto_apto_la_causa_queda_vacia():
    catalogo = _catalogo(CultivoEnum.sorgo, Cletodim=["soja, algodon"])
    assert catalogo.get(HERBICIDA.value, []) == []


def test_producto_sin_marcas_cargadas_no_se_sugiere_con_cultivo():
    producto = _producto("Sin marcas")
    assert armar_catalogo_productos([producto], {}, CultivoEnum.soja) == {}


def test_marca_con_cultivos_vacios_no_cuenta():
    catalogo = _catalogo(CultivoEnum.soja, Glifosato=[None, ""])
    assert catalogo == {}


def test_orden_mas_marcas_aptas_primero():
    catalogo = _catalogo(
        CultivoEnum.soja,
        Cletodim=["soja"],
        Glifosato=["soja", "soja, maiz", "barbecho"],
    )
    assert _nombres(catalogo) == ["Glifosato", "Cletodim"]


def test_orden_empate_por_nombre_y_estable():
    entrada = dict(Zeta=["soja"], Alfa=["soja"], Medio=["soja"])
    assert _nombres(_catalogo(CultivoEnum.soja, **entrada)) == ["Alfa", "Medio", "Zeta"]
    assert _nombres(_catalogo(CultivoEnum.soja, **dict(reversed(list(entrada.items()))))) == ["Alfa", "Medio", "Zeta"]


def test_agrupa_por_causa():
    herbicida = _producto("Glifosato")
    fungicida = _producto("Mancozeb", CausaIndiceEnum.estres_biotico_fungico, TipoProductoEnum.fungicida)
    cultivos = {herbicida.id: ["soja"], fungicida.id: ["soja"]}
    catalogo = armar_catalogo_productos([herbicida, fungicida], cultivos, CultivoEnum.soja)
    assert _nombres(catalogo) == ["Glifosato"]
    assert _nombres(catalogo, CausaIndiceEnum.estres_biotico_fungico) == ["Mancozeb"]
