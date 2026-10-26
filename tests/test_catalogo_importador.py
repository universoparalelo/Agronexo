"""
Tests del importador del catálogo de fitosanitarios (app/catalogo/importador.py).

Lectura y validación del Excel corren sin base. Los tests de aplicar() usan
la BD real dentro de una transacción que se revierte siempre — nunca tocan
los productos reales.

Correr en el contenedor api:
    docker compose exec api python3 -m pytest tests/test_catalogo_importador.py -v
"""
import uuid
from datetime import date

import openpyxl
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.catalogo.importador import (
    FilaCatalogo,
    aplicar,
    leer_catalogo,
    normalizar_confiabilidad,
    parsear_fuente_y_fecha,
)
from app.core.config import settings
from app.diagnostico.models import (
    CausaIndiceEnum,
    PrecioProducto,
    ProductoFitosanitario,
    TipoProductoEnum,
)

_CABECERA = [
    "Nombre", "Tipo", "Causa asociada", "Dosis de referencia (por ha)", "Unidad de dosis",
    "Precio aproximado (USD por L o kg)", "Estado", "Fecha / fuente del precio", "Confiabilidad ",
]


def _xlsx(tmp_path, filas, cabecera=None):
    libro = openpyxl.Workbook()
    hoja = libro.active
    hoja.append(cabecera or _CABECERA)
    for fila in filas:
        hoja.append(fila)
    ruta = tmp_path / "catalogo.xlsx"
    libro.save(ruta)
    return ruta


def _fila(nombre="Glifosato", dosis=2.22, unidad="L/ha", precio=5.5,
          estado="Recomendado por el motor", fuente="camposimple.com.ar, 10/2026",
          confiabilidad="Dosis habitual según WEB"):
    return [nombre, "herbicida", "interferencia_vegetacion", dosis, unidad, precio, estado, fuente, confiabilidad]


def test_lee_solo_las_filas_del_motor_e_ignora_notas(tmp_path):
    ruta = _xlsx(tmp_path, [
        _fila("Glifosato"),
        _fila("Glifosato 54% Power Plus II", estado="Pendiente"),
        ["Notas:", None, None, None, None, None, None, None, None],
    ])
    filas, errores = leer_catalogo(ruta)
    assert errores == []
    assert [f.nombre for f in filas] == ["Glifosato"]
    assert filas[0].dosis == 2.22
    assert filas[0].confiabilidad == "web"


def test_acepta_precio_como_texto_con_signo_pesos(tmp_path):
    filas, errores = leer_catalogo(_xlsx(tmp_path, [_fila(precio="$5,50")]))
    assert errores == []
    assert filas[0].precio_usd == 5.5


@pytest.mark.parametrize("fila, texto_error", [
    (_fila(dosis=None), "dosis vacía"),
    (_fila(dosis=0), "dosis vacía"),
    (_fila(precio=None), "precio vacío"),
    (_fila(unidad="gal/ha"), "no es L/ha ni kg/ha"),
])
def test_rechaza_filas_invalidas(tmp_path, fila, texto_error):
    filas, errores = leer_catalogo(_xlsx(tmp_path, [fila]))
    assert filas == []
    assert any(texto_error in e for e in errores)


def test_rechaza_nombres_repetidos_entre_los_del_motor(tmp_path):
    _, errores = leer_catalogo(_xlsx(tmp_path, [_fila("Glifosato"), _fila("Glifosato")]))
    assert any("repetido" in e for e in errores)


def test_avisa_si_falta_una_columna_obligatoria(tmp_path):
    cabecera = [c for c in _CABECERA if not c.startswith("Dosis de referencia")]
    _, errores = leer_catalogo(_xlsx(tmp_path, [], cabecera))
    assert any("dosis" in e for e in errores)


def test_encuentra_las_columnas_aunque_cambie_el_orden(tmp_path):
    cabecera = list(reversed(_CABECERA))
    fila = list(reversed(_fila()))
    filas, errores = leer_catalogo(_xlsx(tmp_path, [fila], cabecera))
    assert errores == []
    assert filas[0].nombre == "Glifosato"


@pytest.mark.parametrize("texto, esperado", [
    ("Dosis según marbete", "marbete"),
    ("Dosis habitual según WEB", "web"),
    ("Dosis según marbete Glifosato", "marbete"),
    (None, None),
    ("", None),
    ("otra cosa", None),
])
def test_normalizar_confiabilidad(texto, esperado):
    assert normalizar_confiabilidad(texto) == esperado


@pytest.mark.parametrize("texto, fecha_esperada", [
    ("camposimple.com.ar, 10/2026", date(2026, 10, 1)),
    ("Catálogo herbicidas PDF 15/10/2026 (proveedor sin identificar)", date(2026, 10, 15)),
    ("Relevamiento PDF HU-R4-05 (2026-10), estimado", date(2026, 10, 1)),
    ("sin fecha reconocible", date(2026, 1, 2)),
    ("mes imposible 13/2026", date(2026, 1, 2)),
])
def test_parsear_fecha_de_la_fuente(texto, fecha_esperada):
    fuente, fecha = parsear_fuente_y_fecha(texto, hoy=date(2026, 1, 2))
    assert fuente == texto
    assert fecha == fecha_esperada


def test_sin_texto_de_fuente_usa_la_fecha_de_hoy():
    assert parsear_fuente_y_fecha(None, hoy=date(2026, 1, 2)) == (None, date(2026, 1, 2))


@pytest.fixture
def sesion():
    engine = create_engine(settings.database_url_sync)
    with Session(engine) as s:
        yield s
        s.rollback()


def _producto(sesion, unidad=None):
    nombre = f"Producto Test {uuid.uuid4().hex[:8]}"
    producto = ProductoFitosanitario(
        nombre=nombre, tipo=TipoProductoEnum.herbicida,
        causa_indice=CausaIndiceEnum.interferencia_vegetacion, unidad=unidad,
    )
    sesion.add(producto)
    sesion.flush()
    return producto


def _fila_catalogo(nombre, **cambios):
    datos = dict(fila=2, nombre=nombre, dosis=2.0, unidad="L/ha", precio_usd=5.0,
                 fuente_precio="camposimple.com.ar, 10/2026", confiabilidad="web")
    datos.update(cambios)
    return FilaCatalogo(**datos)


def test_aplicar_carga_dosis_confiabilidad_y_crea_el_precio(sesion):
    producto = _producto(sesion)
    resumen = aplicar(sesion, [_fila_catalogo(producto.nombre)])

    assert producto.dosis_referencia == 2.0
    assert producto.unidad == "L/ha"
    assert producto.confiabilidad_dosis == "web"
    precio = sesion.scalars(select(PrecioProducto).where(PrecioProducto.producto_id == producto.id)).one()
    assert (precio.precio_usd, precio.unidad, precio.tipo) == (5.0, "L", "referencia")
    assert precio.fecha == date(2026, 10, 1)
    assert resumen.sin_cambios == 0


def test_aplicar_dos_veces_no_cambia_nada_la_segunda(sesion):
    producto = _producto(sesion)
    fila = _fila_catalogo(producto.nombre)
    aplicar(sesion, [fila])
    resumen = aplicar(sesion, [fila])

    assert resumen.cambios == []
    assert resumen.sin_cambios == 1
    assert len(sesion.scalars(select(PrecioProducto).where(PrecioProducto.producto_id == producto.id)).all()) == 1


def test_aplicar_actualiza_un_precio_distinto_y_corrige_la_unidad(sesion):
    producto = _producto(sesion)
    sesion.add(PrecioProducto(
        producto_id=producto.id, precio_usd=3.0, unidad="L", fuente="CASAFE", fecha=date(2026, 10, 13), tipo="referencia",
    ))
    sesion.flush()

    aplicar(sesion, [_fila_catalogo(producto.nombre, unidad="kg/ha", precio_usd=6.5)])

    precio = sesion.scalars(select(PrecioProducto).where(PrecioProducto.producto_id == producto.id)).one()
    assert (precio.precio_usd, precio.unidad) == (6.5, "kg")
    assert precio.fuente == "camposimple.com.ar, 10/2026"


def test_aplicar_conserva_la_fuente_si_el_precio_no_cambia(sesion):
    producto = _producto(sesion)
    sesion.add(PrecioProducto(
        producto_id=producto.id, precio_usd=5.0, unidad="L", fuente="CASAFE Lista 2026-S1",
        fecha=date(2026, 10, 13), tipo="referencia",
    ))
    sesion.flush()

    aplicar(sesion, [_fila_catalogo(producto.nombre)])

    precio = sesion.scalars(select(PrecioProducto).where(PrecioProducto.producto_id == producto.id)).one()
    assert precio.fuente == "CASAFE Lista 2026-S1"
    assert precio.fecha == date(2026, 10, 13)


def test_aplicar_informa_los_productos_que_no_existen_sin_crearlos(sesion):
    nombre = f"No Existe {uuid.uuid4().hex[:8]}"
    resumen = aplicar(sesion, [_fila_catalogo(nombre)])

    assert resumen.no_encontrados == [nombre]
    assert sesion.scalars(select(ProductoFitosanitario).where(ProductoFitosanitario.nombre == nombre)).first() is None
