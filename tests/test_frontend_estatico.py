"""
Tests de app/frontend.py::montar_frontend(), que hace que la API entregue el
frontend compilado en la app de escritorio.

No necesitan base de datos: se arma una API mínima con una ruta /api/v1/health
y se le monta una carpeta temporal que imita el `dist` de Vite.

Correr en el contenedor api:
    docker compose exec api python3 -m pytest tests/test_frontend_estatico.py -v

Correr en CI o local:
    PYTHONPATH=$(pwd) python3 -m pytest tests/test_frontend_estatico.py -v
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from app.frontend import montar_frontend

_RAIZ = Path(__file__).resolve().parent.parent
_INDICE = "<html><body>pantalla de AgroNexo</body></html>"


@pytest.fixture
def dist(tmp_path):
    carpeta = tmp_path / "dist"
    (carpeta / "assets").mkdir(parents=True)
    (carpeta / "index.html").write_text(_INDICE, encoding="utf-8")
    (carpeta / "assets" / "app-123.js").write_text("console.log('hola')", encoding="utf-8")
    (carpeta / "logo.png").write_bytes(b"\x89PNG-falso")
    (tmp_path / "secreto.txt").write_text("no se debe poder leer", encoding="utf-8")
    return carpeta


@pytest.fixture
def cliente(dist):
    app = FastAPI()

    @app.get("/api/v1/health")
    async def health():
        return {"status": "ok"}

    montar_frontend(app, dist)
    return TestClient(app)


def test_la_raiz_entrega_la_pantalla(cliente):
    r = cliente.get("/")

    assert r.status_code == 200
    assert "pantalla de AgroNexo" in r.text


@pytest.mark.parametrize("ruta", ["/login", "/dashboard", "/lotes/abc", "/lotes/abc/vuelos/def"])
def test_las_rutas_de_la_app_entregan_la_misma_pantalla(cliente, ruta):
    r = cliente.get(ruta)

    assert r.status_code == 200
    assert "pantalla de AgroNexo" in r.text


def test_los_assets_se_entregan_como_archivos(cliente):
    r = cliente.get("/assets/app-123.js")

    assert r.status_code == 200
    assert r.text == "console.log('hola')"
    assert "javascript" in r.headers["content-type"]


def test_un_asset_que_no_existe_es_404(cliente):
    assert cliente.get("/assets/no-existe.js").status_code == 404


def test_los_archivos_de_la_raiz_se_entregan_como_archivos(cliente):
    r = cliente.get("/logo.png")

    assert r.status_code == 200
    assert r.content == b"\x89PNG-falso"


def test_la_api_no_queda_tapada_por_el_frontend(cliente):
    r = cliente.get("/api/v1/health")

    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


@pytest.mark.parametrize("ruta", ["/api/v1/no-existe", "/api"])
def test_una_ruta_de_la_api_que_no_existe_es_404_y_no_la_pantalla(cliente, ruta):
    r = cliente.get(ruta)

    assert r.status_code == 404
    assert "pantalla de AgroNexo" not in r.text


def test_no_se_pueden_leer_archivos_fuera_de_la_carpeta(cliente):
    for ruta in ("/../secreto.txt", "/%2e%2e/secreto.txt", "/..%2fsecreto.txt", "/assets/../../secreto.txt"):
        r = cliente.get(ruta)
        assert "no se debe poder leer" not in r.text, ruta


def test_una_carpeta_sin_index_html_falla_al_montarse(tmp_path):
    with pytest.raises(RuntimeError, match="index.html"):
        montar_frontend(FastAPI(), tmp_path)


def _correr_con_frontend(dist: Path, codigo: str) -> subprocess.CompletedProcess:
    entorno = {**os.environ, "FRONTEND_DIR": str(dist)}
    return subprocess.run(
        [sys.executable, "-c", codigo], cwd=_RAIZ, env=entorno, capture_output=True, text=True, timeout=120,
    )


def test_con_frontend_dir_la_api_real_entrega_la_pantalla_y_conserva_la_api(dist):
    r = _correr_con_frontend(dist, (
        "from starlette.testclient import TestClient\n"
        "from app.main import app\n"
        "c = TestClient(app)\n"
        "print(c.get('/').status_code, 'pantalla de AgroNexo' in c.get('/dashboard').text)\n"
        "print(c.get('/api/v1/health').json()['status'])\n"
    ))

    assert r.returncode == 0, r.stderr
    assert r.stdout.split() == ["200", "True", "ok"]
    print("✓ con FRONTEND_DIR, app.main entrega la pantalla y sigue respondiendo la API")


def test_sin_frontend_dir_la_api_real_no_sirve_pantallas():
    entorno = {k: v for k, v in os.environ.items() if k != "FRONTEND_DIR"}
    r = subprocess.run(
        [sys.executable, "-c",
         "from starlette.testclient import TestClient\nfrom app.main import app\nprint(TestClient(app).get('/dashboard').status_code)"],
        cwd=_RAIZ, env=entorno, capture_output=True, text=True, timeout=120,
    )

    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "404"
    print("✓ sin FRONTEND_DIR nada cambia: la API no sirve pantallas")
