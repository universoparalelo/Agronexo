"""
Punto de entrada del worker GIS en la app de escritorio.

Corre Celery con el pool `solo`, que procesa un análisis a la vez: el pool
`prefork` no funciona en Windows. La cola y los resultados salen de
CELERY_BROKER_URL y CELERY_RESULT_BACKEND (en escritorio, la propia base de
datos Postgres). Nivel de log con AGRONEXO_LOG_LEVEL (info por defecto).
"""
import multiprocessing
import os


def main() -> None:
    multiprocessing.freeze_support()

    from workers.celery_app import celery_app
    import workers.gis.tasks  # noqa: F401  registra las tareas en la app de Celery

    celery_app.worker_main([
        "worker",
        "-Q", "gis",
        "--pool=solo",
        "-l", os.environ.get("AGRONEXO_LOG_LEVEL", "info"),
    ])


if __name__ == "__main__":
    main()
