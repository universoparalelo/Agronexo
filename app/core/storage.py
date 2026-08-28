import io
import shutil
from datetime import timedelta

from minio import Minio

from app.core.config import settings


def _client() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=settings.minio_use_ssl,
    )


def _ensure_bucket(client: Minio) -> None:
    if not client.bucket_exists(settings.minio_bucket):
        client.make_bucket(settings.minio_bucket)


def upload_geotiff(usuario_id: str, lote_id: str, vuelo_id: str, data: bytes) -> str:
    """Sube el GeoTIFF a MinIO y retorna la clave del objeto."""
    client = _client()
    _ensure_bucket(client)
    key = f"{usuario_id}/{lote_id}/{vuelo_id}/original.tif"
    client.put_object(
        settings.minio_bucket,
        key,
        io.BytesIO(data),
        length=len(data),
        content_type="image/tiff",
    )
    return key


def upload_geotiff_stream(
    usuario_id: str,
    lote_id: str,
    vuelo_id: str,
    stream,
    length: int = -1,
) -> str:
    """Sube el GeoTIFF a MinIO leyendo desde un stream sin cargarlo en RAM.

    length=-1 activa multipart upload automático con partes de 64 MB, lo que
    permite subir archivos de cualquier tamaño sin conocer el tamaño de antemano.
    """
    client = _client()
    _ensure_bucket(client)
    key = f"{usuario_id}/{lote_id}/{vuelo_id}/original.tif"
    client.put_object(
        settings.minio_bucket,
        key,
        stream,
        length=length,
        part_size=64 * 1024 * 1024,  # 64 MB por parte (mínimo MinIO: 5 MB)
        content_type="image/tiff",
    )
    return key


def download_geotiff_to_file(key: str, destino: str) -> str:
    """Descarga un objeto de MinIO a un archivo en disco usando streaming.

    No carga el archivo completo en RAM — escribe en chunks de 8 MB.
    Retorna la ruta del archivo descargado.
    """
    client = _client()
    response = client.get_object(settings.minio_bucket, key)
    try:
        with open(destino, "wb") as f:
            shutil.copyfileobj(response, f, length=8 * 1024 * 1024)
    finally:
        response.close()
        response.release_conn()
    return destino


def download_geotiff(key: str) -> bytes:
    """Descarga un GeoTIFF desde MinIO y retorna sus bytes."""
    client = _client()
    response = client.get_object(settings.minio_bucket, key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def download_bytes(key: str) -> bytes:
    """Descarga cualquier objeto desde MinIO y retorna sus bytes."""
    client = _client()
    response = client.get_object(settings.minio_bucket, key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def upload_bytes(key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    """Sube bytes arbitrarios a MinIO bajo la clave dada. Retorna la clave."""
    client = _client()
    _ensure_bucket(client)
    client.put_object(
        settings.minio_bucket,
        key,
        io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    return key


def object_exists(key: str) -> bool:
    """Verifica si un objeto existe en MinIO sin descargarlo (HEAD request)."""
    from minio.error import S3Error

    client = _client()
    try:
        client.stat_object(settings.minio_bucket, key)
        return True
    except S3Error:
        return False


def upload_file(key: str, local_path: str, content_type: str = "application/octet-stream") -> str:
    """Sube un archivo local a MinIO por streaming (fput_object) — no lo carga en RAM."""
    client = _client()
    _ensure_bucket(client)
    client.fput_object(settings.minio_bucket, key, local_path, content_type=content_type)
    return key


def presigned_url(key: str) -> str:
    client = _client()
    return client.presigned_get_object(
        settings.minio_bucket,
        key,
        expires=timedelta(seconds=settings.minio_presigned_url_expiry),
    )
