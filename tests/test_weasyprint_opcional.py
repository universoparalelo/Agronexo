"""
WeasyPrint necesita GTK/Pango del sistema, que no viene con pip. La API tiene
que poder arrancar sin él (app de escritorio): solo la generación de PDF
depende de esas librerías, y WeasyPrint se importa al pedir un PDF, no al
cargar la aplicación.

Cada test corre en un proceso aparte para que el estado de sys.modules no
contamine a los demás tests.

Correr en el contenedor api:
    docker compose exec api python3 -m pytest tests/test_weasyprint_opcional.py -v

Correr en CI o local:
    PYTHONPATH=$(pwd) python3 -m pytest tests/test_weasyprint_opcional.py -v
"""
import subprocess
import sys
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent.parent


def _correr(codigo: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", codigo], cwd=_RAIZ, capture_output=True, text=True, timeout=120,
    )


def test_la_api_carga_aunque_weasyprint_no_este_disponible():
    # None en sys.modules hace que "import weasyprint" lance ImportError,
    # igual que cuando faltan las DLL de GTK.
    r = _correr("import sys; sys.modules['weasyprint'] = None; import app.main; print('ok')")

    assert r.returncode == 0, r.stderr
    assert "ok" in r.stdout
    print("✓ app.main se importa aunque WeasyPrint no se pueda cargar")


def test_cargar_la_api_no_importa_weasyprint():
    r = _correr("import sys; import app.main; print('weasyprint' in sys.modules)")

    assert r.returncode == 0, r.stderr
    assert r.stdout.strip().splitlines()[-1] == "False"
    print("✓ cargar la API no importa WeasyPrint (se importa recién al generar un PDF)")


def test_generar_un_pdf_sin_weasyprint_falla_con_importerror():
    # El endpoint ya captura cualquier excepción y responde 500 "No se pudo
    # generar el PDF"; acá se verifica que el fallo sea un ImportError claro.
    codigo = (
        "import sys; sys.modules['weasyprint'] = None\n"
        "from app.reportes.service import generar_pdf_reporte\n"
        "try:\n"
        "    generar_pdf_reporte({'type': 'FeatureCollection', 'features': [], 'unidades_manejo': [], 'metadata': {}}, {})\n"
        "except ImportError:\n"
        "    print('importerror')\n"
        "except Exception as e:\n"
        "    print('otro:', type(e).__name__, e)\n"
    )
    r = _correr(codigo)

    assert r.returncode == 0, r.stderr
    assert r.stdout.strip().splitlines()[-1] == "importerror", r.stdout
    print("✓ pedir un PDF sin WeasyPrint lanza ImportError")
