"""
Punto de entrada de la API en la app de escritorio.

Prepara la base de datos y recién después arranca la API. Es el mismo orden que
usa Docker en producción (`alembic upgrade head` antes de uvicorn).

Variables propias: AGRONEXO_HOST (127.0.0.1 por defecto) y AGRONEXO_PORT (8000).
El resto de la configuración sale de app/core/config.py.
"""
import os

import uvicorn

from app.core.migraciones import aplicar_migraciones


def main() -> None:
    aplicar_migraciones()

    from app.main import app

    uvicorn.run(
        app,
        host=os.environ.get("AGRONEXO_HOST", "127.0.0.1"),
        port=int(os.environ.get("AGRONEXO_PORT", "8000")),
        log_level="info",
    )


if __name__ == "__main__":
    main()
