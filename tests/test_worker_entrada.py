"""
Tests de escritorio/worker.py, el punto de entrada del worker GIS en la app de
escritorio.

Necesitan las librerías GIS del worker (rasterio y compañía): se saltean donde
no están, por ejemplo en el contenedor de la API.

Correr en el contenedor worker:
    docker compose exec worker python3 -m pytest tests/test_worker_entrada.py -v

Correr local (con las dependencias del worker):
    PYTHONPATH=$(pwd) python3 -m pytest tests/test_worker_entrada.py -v
"""
import pytest

pytest.importorskip("rasterio", reason="el worker necesita las librerías GIS")

from workers.celery_app import celery_app  # noqa: E402


@pytest.fixture
def llamadas(monkeypatch):
    registradas = []
    monkeypatch.setattr(celery_app, "worker_main", lambda argv: registradas.append(argv))
    monkeypatch.delenv("AGRONEXO_LOG_LEVEL", raising=False)
    return registradas


def test_arranca_celery_con_pool_solo_y_la_cola_gis(llamadas):
    from escritorio import worker

    worker.main()

    assert llamadas == [["worker", "-Q", "gis", "--pool=solo", "-l", "info"]]
    print("✓ escritorio.worker arranca Celery con --pool=solo y la cola gis")


def test_registra_las_tareas_del_pipeline_gis(llamadas):
    from escritorio import worker

    worker.main()

    assert "workers.gis.tasks.procesar_vuelo" in celery_app.tasks


def test_el_nivel_de_log_sale_de_la_variable_de_entorno(llamadas, monkeypatch):
    from escritorio import worker

    monkeypatch.setenv("AGRONEXO_LOG_LEVEL", "warning")
    worker.main()

    assert llamadas[0][-2:] == ["-l", "warning"]
