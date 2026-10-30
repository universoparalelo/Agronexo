"""
Tests del backend de almacenamiento en disco (STORAGE_BACKEND=disk), de la
validación de la configuración y del endpoint GET /api/v1/archivos/{token}.

No necesitan base de datos ni MinIO: la carpeta de datos es un directorio
temporal. Las funciones se llaman a través de app/core/storage.py para probar
también que delega en el backend de disco.

Correr en el contenedor api:
    docker compose exec api python3 -m pytest tests/test_almacenamiento_disco.py -v

Correr en CI o local:
    PYTHONPATH=$(pwd) python3 -m pytest tests/test_almacenamiento_disco.py -v
"""
import io
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from pydantic import ValidationError
from starlette.testclient import TestClient

from app.auth.service import crear_access_token
from app.core import storage, storage_disco
from app.core.config import Settings, settings
from app.main import app

_CONFIG_BASE = dict(
    postgres_host="h",
    postgres_db="d",
    postgres_user="u",
    postgres_password="p",
    celery_broker_url="redis://x",
    celery_result_backend="redis://x",
    jwt_secret_key="k",
)


@pytest.fixture
def carpeta(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_backend", "disk")
    monkeypatch.setattr(settings, "storage_path", str(tmp_path))
    return tmp_path


def _temporales(carpeta):
    return [p for p in carpeta.rglob(".tmp-*")]


# ── Ida y vuelta ──────────────────────────────────────────────────────────────

def test_upload_y_download_bytes(carpeta):
    storage.upload_bytes("u1/l1/v1/zonas.geojson", b'{"a": 1}', "application/geo+json")

    assert storage.download_bytes("u1/l1/v1/zonas.geojson") == b'{"a": 1}'
    assert (carpeta / "u1" / "l1" / "v1" / "zonas.geojson").is_file()
    print("✓ upload_bytes/download_bytes con disco: ida y vuelta, crea las subcarpetas")


def test_upload_reemplaza_el_archivo_existente(carpeta):
    storage.upload_bytes("u/a.bin", b"viejo")
    storage.upload_bytes("u/a.bin", b"nuevo")

    assert storage.download_bytes("u/a.bin") == b"nuevo"
    assert _temporales(carpeta) == []


def test_object_exists(carpeta):
    assert storage.object_exists("u/a.bin") is False
    storage.upload_bytes("u/a.bin", b"x")
    assert storage.object_exists("u/a.bin") is True
    print("✓ object_exists con disco")


def test_upload_geotiff_stream_escribe_el_stream_completo(carpeta):
    datos = b"II*\x00" + bytes(range(256)) * 20000

    key = storage.upload_geotiff_stream(usuario_id="u1", lote_id="l1", vuelo_id="v1", stream=io.BytesIO(datos))

    assert key == "u1/l1/v1/original.tif"
    assert storage.download_geotiff(key) == datos
    assert _temporales(carpeta) == []
    print("✓ upload_geotiff_stream con disco: clave esperada y contenido completo")


def test_upload_geotiff_con_bytes(carpeta):
    key = storage.upload_geotiff("u1", "l1", "v1", b"datos")
    assert key == "u1/l1/v1/original.tif"
    assert storage.download_geotiff(key) == b"datos"


def test_upload_file_y_download_a_archivo(carpeta, tmp_path_factory):
    origen = tmp_path_factory.mktemp("origen") / "reporte.pdf"
    origen.write_bytes(b"%PDF-1.4 contenido")
    destino = tmp_path_factory.mktemp("destino") / "copia.pdf"

    storage.upload_file("u1/l1/v1/reporte.pdf", str(origen), "application/pdf")
    devuelto = storage.download_geotiff_to_file("u1/l1/v1/reporte.pdf", str(destino))

    assert devuelto == str(destino)
    assert destino.read_bytes() == b"%PDF-1.4 contenido"
    assert origen.read_bytes() == b"%PDF-1.4 contenido"


def test_descargar_una_clave_inexistente_falla(carpeta):
    with pytest.raises(FileNotFoundError):
        storage.download_bytes("u/no_existe.bin")


# ── Escritura atómica ─────────────────────────────────────────────────────────

class _StreamQueFalla:
    def read(self, n=-1):
        raise RuntimeError("se cortó la subida")


def test_una_escritura_fallida_no_deja_archivo_ni_temporales(carpeta):
    with pytest.raises(RuntimeError):
        storage.upload_geotiff_stream("u1", "l1", "v1", _StreamQueFalla())

    assert storage.object_exists("u1/l1/v1/original.tif") is False
    assert _temporales(carpeta) == []
    print("✓ subida cortada: no queda archivo a medias ni temporales")


def test_una_escritura_fallida_no_pisa_el_archivo_anterior(carpeta):
    storage.upload_geotiff("u1", "l1", "v1", b"bueno")

    with pytest.raises(RuntimeError):
        storage.upload_geotiff_stream("u1", "l1", "v1", _StreamQueFalla())

    assert storage.download_geotiff("u1/l1/v1/original.tif") == b"bueno"


# ── Claves peligrosas ─────────────────────────────────────────────────────────

_CLAVES_INVALIDAS = [
    "../fuera.txt",
    "a/../../fuera.txt",
    "/absoluta.txt",
    "\\absoluta.txt",
    "C:/Windows/x.txt",
    "a\\b.txt",
    "a//b.txt",
    "./a.txt",
    "",
]


@pytest.mark.parametrize("clave", _CLAVES_INVALIDAS)
def test_las_claves_que_salen_de_la_carpeta_se_rechazan(carpeta, clave):
    with pytest.raises(ValueError):
        storage.upload_bytes(clave, b"x")
    assert storage.object_exists(clave) is False
    assert list(carpeta.parent.glob("fuera.txt")) == []


# ── Configuración ─────────────────────────────────────────────────────────────

def test_config_disk_exige_storage_path():
    with pytest.raises(ValidationError, match="STORAGE_PATH"):
        Settings(_env_file=None, storage_backend="disk", storage_path="", **_CONFIG_BASE)


def test_config_disk_no_exige_variables_de_minio():
    s = Settings(
        _env_file=None, storage_backend="disk", storage_path="/datos",
        minio_endpoint="", minio_root_user="", minio_root_password="", **_CONFIG_BASE,
    )
    assert s.storage_backend == "disk"


def test_config_minio_exige_sus_variables():
    with pytest.raises(ValidationError, match="MINIO_ENDPOINT"):
        Settings(
            _env_file=None, storage_backend="minio",
            minio_endpoint="", minio_root_user="u", minio_root_password="p", **_CONFIG_BASE,
        )


def test_config_rechaza_un_backend_desconocido():
    with pytest.raises(ValidationError, match="STORAGE_BACKEND"):
        Settings(_env_file=None, storage_backend="s3", **_CONFIG_BASE)


def test_config_por_defecto_es_minio(monkeypatch):
    monkeypatch.delenv("STORAGE_BACKEND", raising=False)
    monkeypatch.delenv("STORAGE_PATH", raising=False)
    s = Settings(
        _env_file=None, minio_endpoint="m:9000", minio_root_user="u", minio_root_password="p", **_CONFIG_BASE,
    )
    assert s.storage_backend == "minio"


# ── Tokens de archivo ─────────────────────────────────────────────────────────

def test_presigned_url_devuelve_una_ruta_de_la_api(carpeta):
    url = storage.presigned_url("u1/perfil/avatar.png")

    assert url.startswith("/api/v1/archivos/")
    token = url.removeprefix("/api/v1/archivos/")
    assert storage_disco.clave_desde_token(token) == "u1/perfil/avatar.png"


def test_presigned_url_rechaza_una_clave_invalida(carpeta):
    with pytest.raises(ValueError):
        storage.presigned_url("../secreto.txt")


def test_un_token_vencido_no_sirve(carpeta, monkeypatch):
    monkeypatch.setattr(settings, "minio_presigned_url_expiry", -10)
    token = storage.presigned_url("u/a.bin").removeprefix("/api/v1/archivos/")

    with pytest.raises(jwt.InvalidTokenError):
        storage_disco.clave_desde_token(token)


def test_un_token_de_acceso_no_sirve_como_token_de_archivo(carpeta):
    with pytest.raises(jwt.InvalidTokenError):
        storage_disco.clave_desde_token(crear_access_token("un-usuario"))


def test_un_token_de_archivo_no_sirve_como_token_de_acceso(carpeta):
    token = storage.presigned_url("u/a.bin").removeprefix("/api/v1/archivos/")
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    assert payload["type"] != "access"


# ── Endpoint ──────────────────────────────────────────────────────────────────

_tc = TestClient(app)


def test_endpoint_sirve_el_archivo_con_su_tipo(carpeta):
    storage.upload_bytes("u1/perfil/avatar.png", b"\x89PNG-falso", "image/png")
    url = storage.presigned_url("u1/perfil/avatar.png")

    r = _tc.get(url)

    assert r.status_code == 200
    assert r.content == b"\x89PNG-falso"
    assert r.headers["content-type"] == "image/png"
    print("✓ GET /archivos/{token} sirve el archivo con content-type por extensión")


def test_endpoint_tipo_generico_si_la_extension_es_desconocida(carpeta):
    storage.upload_bytes("u1/dato.zzzdesconocida", b"x")

    r = _tc.get(storage.presigned_url("u1/dato.zzzdesconocida"))

    assert r.status_code == 200
    assert r.headers["content-type"] == "application/octet-stream"


def test_endpoint_rechaza_un_token_vencido(carpeta, monkeypatch):
    storage.upload_bytes("u/a.bin", b"x")
    monkeypatch.setattr(settings, "minio_presigned_url_expiry", -10)

    r = _tc.get(storage.presigned_url("u/a.bin"))

    assert r.status_code == 401
    print("✓ GET /archivos/{token} con token vencido → 401")


def test_endpoint_rechaza_un_token_manipulado(carpeta):
    storage.upload_bytes("u/a.bin", b"x")
    url = storage.presigned_url("u/a.bin")

    r = _tc.get(url[:-4] + "XXXX")

    assert r.status_code == 401


def test_endpoint_rechaza_un_token_de_acceso(carpeta):
    r = _tc.get(f"/api/v1/archivos/{crear_access_token('un-usuario')}")
    assert r.status_code == 401


def test_endpoint_rechaza_un_token_firmado_con_otra_clave(carpeta):
    token = jwt.encode(
        {"k": "u/a.bin", "type": "archivo", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        "otra-clave-secreta-distinta-0123456789",
        algorithm=settings.jwt_algorithm,
    )
    assert _tc.get(f"/api/v1/archivos/{token}").status_code == 401


def test_endpoint_rechaza_un_token_con_ruta_fuera_de_la_carpeta(carpeta):
    token = jwt.encode(
        {"k": "../fuera.txt", "type": "archivo", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    assert _tc.get(f"/api/v1/archivos/{token}").status_code == 401


def test_endpoint_devuelve_404_si_el_archivo_ya_no_existe(carpeta):
    storage.upload_bytes("u/a.bin", b"x")
    url = storage.presigned_url("u/a.bin")
    (carpeta / "u" / "a.bin").unlink()

    assert _tc.get(url).status_code == 404


def test_endpoint_no_existe_si_el_backend_no_es_disco(carpeta, monkeypatch):
    storage.upload_bytes("u/a.bin", b"x")
    url = storage.presigned_url("u/a.bin")
    monkeypatch.setattr(settings, "storage_backend", "minio")

    assert _tc.get(url).status_code == 404
    print("✓ con STORAGE_BACKEND=minio el endpoint responde 404")
