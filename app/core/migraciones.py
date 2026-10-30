import sys
from pathlib import Path

from alembic import command
from alembic.config import Config


def _raiz() -> Path:
    # Empaquetado con PyInstaller, migrations/ viaja como dato dentro de _MEIPASS.
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))


def aplicar_migraciones() -> None:
    """Lleva la base de datos al último esquema (`alembic upgrade head`).

    Con una base vacía crea todo; con una base al día no hace nada. Se llama antes
    de arrancar la API, no desde adentro: migrations/env.py abre su propio loop
    asíncrono con asyncio.run(), que no puede correr dentro de uno ya en marcha.
    """
    config = Config()
    config.set_main_option("script_location", str(_raiz() / "migrations"))
    command.upgrade(config, "head")
