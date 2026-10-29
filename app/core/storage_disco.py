import os
import shutil
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt

from app.core.config import settings

TOKEN_TYPE = "archivo"
RUTA_PUBLICA = "/api/v1/archivos"


def _raiz() -> Path:
    return Path(settings.storage_path).resolve()


def ruta_de(key: str) -> Path:
    """Resuelve una clave a su ruta dentro de la carpeta de datos.

    Una clave mal formada o un token manipulado no tiene que poder salir de
    la carpeta: se rechazan rutas absolutas, con letra de unidad y con "..".
    """
    if not key or "\\" in key or ":" in key or any(p in ("", ".", "..") for p in key.split("/")):
        raise ValueError(f"Clave de almacenamiento inválida: {key!r}")
    raiz = _raiz()
    ruta = (raiz / key).resolve()
    if not ruta.is_relative_to(raiz):
        raise ValueError(f"Clave de almacenamiento fuera de la carpeta de datos: {key!r}")
    return ruta


def _escribir_atomico(ruta: Path, escribir) -> None:
    # La API y el worker comparten la carpeta, y object_exists() se usa como
    # caché (GeoTIFF preparado, exportaciones): nadie debe ver un archivo a medias.
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=ruta.parent, prefix=".tmp-")
    try:
        with os.fdopen(fd, "wb") as f:
            escribir(f)
        os.replace(tmp, ruta)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def upload_geotiff(usuario_id: str, lote_id: str, vuelo_id: str, data: bytes) -> str:
    key = f"{usuario_id}/{lote_id}/{vuelo_id}/original.tif"
    return upload_bytes(key, data)


def upload_geotiff_stream(
    usuario_id: str,
    lote_id: str,
    vuelo_id: str,
    stream,
    length: int = -1,
) -> str:
    key = f"{usuario_id}/{lote_id}/{vuelo_id}/original.tif"
    _escribir_atomico(ruta_de(key), lambda f: shutil.copyfileobj(stream, f, length=8 * 1024 * 1024))
    return key


def download_geotiff_to_file(key: str, destino: str) -> str:
    shutil.copyfile(ruta_de(key), destino)
    return destino


def download_bytes(key: str) -> bytes:
    return ruta_de(key).read_bytes()


download_geotiff = download_bytes


def upload_bytes(key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    # content_type se acepta solo para conservar la firma de storage.py: el tipo
    # se deduce de la extensión al servir el archivo.
    _escribir_atomico(ruta_de(key), lambda f: f.write(data))
    return key


def object_exists(key: str) -> bool:
    try:
        return ruta_de(key).is_file()
    except ValueError:
        return False


def upload_file(key: str, local_path: str, content_type: str = "application/octet-stream") -> str:
    def copiar(destino):
        with open(local_path, "rb") as origen:
            shutil.copyfileobj(origen, destino, length=8 * 1024 * 1024)

    _escribir_atomico(ruta_de(key), copiar)
    return key


def presigned_url(key: str) -> str:
    ruta_de(key)
    expira = datetime.now(timezone.utc) + timedelta(seconds=settings.minio_presigned_url_expiry)
    token = jwt.encode(
        {"k": key, "type": TOKEN_TYPE, "exp": expira},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return f"{RUTA_PUBLICA}/{token}"


def clave_desde_token(token: str) -> str:
    """Devuelve la clave del archivo si el token es válido; lanza jwt.InvalidTokenError si no."""
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    key = payload.get("k")
    if payload.get("type") != TOKEN_TYPE or not isinstance(key, str):
        raise jwt.InvalidTokenError("Token de archivo inválido")
    return key
