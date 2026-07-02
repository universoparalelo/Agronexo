import io
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


def download_geotiff(key: str) -> bytes:
    """Descarga un GeoTIFF desde MinIO y retorna sus bytes."""
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


def download_object(key: str) -> bytes:
    """Descarga un objeto arbitrario desde MinIO y retorna sus bytes."""
    client = _client()
    response = client.get_object(settings.minio_bucket, key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def presigned_url(key: str) -> str:
    client = _client()
    return client.presigned_get_object(
        settings.minio_bucket,
        key,
        expires=timedelta(seconds=settings.minio_presigned_url_expiry),
    )
