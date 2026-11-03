"""
Tests de la migración 0029: el catálogo de fitosanitarios tiene que venir cargado
en cualquier base recién migrada (la app de escritorio no corre el importador).

Solo leen la base: no crean ni borran nada.

Correr en el contenedor api:
    docker compose exec api python3 -m pytest tests/test_catalogo_migracion.py -v
"""
from sqlalchemy import create_engine, text

from app.core.config import settings


def _escalar(sql: str):
    engine = create_engine(settings.database_url_sync)
    try:
        with engine.connect() as conn:
            return conn.execute(text(sql)).scalar()
    finally:
        engine.dispose()


def test_todos_los_productos_tienen_dosis():
    sin_dosis = _escalar("SELECT count(*) FROM productos_fitosanitarios WHERE dosis_referencia IS NULL")
    assert sin_dosis == 0


def test_catalogo_cargado():
    assert _escalar("SELECT count(*) FROM productos_fitosanitarios") >= 30
    assert _escalar("SELECT count(*) FROM presentaciones_productos") >= 59


def test_productos_originales_tienen_precio_de_referencia():
    sin_precio = _escalar("""
        SELECT count(*) FROM productos_fitosanitarios p
        WHERE p.nombre IN ('Glifosato', 'Clorpirifos', 'Thiamethoxam')
          AND NOT EXISTS (SELECT 1 FROM precios_productos x
                          WHERE x.producto_id = p.id AND x.tipo = 'referencia')
    """)
    assert sin_precio == 0


def test_toda_presentacion_tiene_dosis_y_precio():
    incompletas = _escalar("""
        SELECT count(*) FROM presentaciones_productos
        WHERE dosis_referencia IS NULL OR precio_usd IS NULL
    """)
    assert incompletas == 0
