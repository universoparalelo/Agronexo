"""
Tests de workers/gis/tasks.py::_actualizar_lote_geometry contra la base real:
un lote sin límite lo recibe (con su área en hectáreas) y uno que ya lo tiene
no se pisa. Requiere la base de datos y el contenedor worker (rasterio).

Correr en el contenedor worker:
    docker compose exec worker python3 -m pytest tests/test_lote_limites_worker.py -v
"""
import uuid

import pytest
from sqlalchemy import create_engine, text

from app.core.config import settings
from workers.gis.tasks import _actualizar_lote_geometry

# ~1.9 km x 2.2 km cerca de Resistencia
_WKT = "POLYGON((-60.68 -27.48,-60.66 -27.48,-60.66 -27.46,-60.68 -27.46,-60.68 -27.48))"
_WKT_OTRO = "POLYGON((-59.10 -27.40,-59.09 -27.40,-59.09 -27.39,-59.10 -27.39,-59.10 -27.40))"


@pytest.fixture
def lote_id():
    try:
        engine = create_engine(settings.database_url_sync)
        conn = engine.connect()
    except Exception:
        pytest.skip("base de datos no disponible")
    lote_id = str(uuid.uuid4())
    conn.execute(text("INSERT INTO lotes (id, nombre) VALUES (CAST(:id AS uuid), 'Test límites desde GeoTIFF')"), {"id": lote_id})
    conn.commit()
    yield lote_id
    conn.execute(text("DELETE FROM lotes WHERE id = CAST(:id AS uuid)"), {"id": lote_id})
    conn.commit()
    conn.close()
    engine.dispose()


def _leer(lote_id: str):
    engine = create_engine(settings.database_url_sync)
    with engine.connect() as conn:
        fila = conn.execute(
            text("SELECT ST_AsText(geometry), area_ha FROM lotes WHERE id = CAST(:id AS uuid)"), {"id": lote_id}
        ).one()
    engine.dispose()
    return fila


def test_lote_sin_limite_recibe_geometry_y_area(lote_id):
    _actualizar_lote_geometry(lote_id, _WKT)
    geometry, area_ha = _leer(lote_id)
    assert geometry is not None
    assert area_ha is not None and 300 < area_ha < 600  # ≈ 1.9 km × 2.2 km ≈ 440 ha


def test_lote_con_limite_no_se_pisa(lote_id):
    _actualizar_lote_geometry(lote_id, _WKT)
    geometry, area_ha = _leer(lote_id)
    _actualizar_lote_geometry(lote_id, _WKT_OTRO)
    assert _leer(lote_id) == (geometry, area_ha)
