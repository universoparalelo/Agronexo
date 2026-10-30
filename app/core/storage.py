import io
import shutil
from datetime import timedelta

from minio import Minio

from app.core import storage_disco
from app.core.config import settings


def _disco() -> bool:
    return settings.storage_backend == "disk"


def _client() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=settings.minio_use_ssl,
        region=settings.minio_region,
    )


def _ensure_bucket(client: Minio) -> None:
    if not client.bucket_exists(settings.minio_bucket):
        client.make_bucket(settings.minio_bucket)


def upload_geotiff(usuario_id: str, lote_id: str, vuelo_id: str, data: bytes) -> str:
    """Sube el GeoTIFF a MinIO y retorna la clave del objeto."""
    if _disco():
        return storage_disco.upload_geotiff(usuario_id, lote_id, vuelo_id, data)
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
    if _disco():
        return storage_disco.upload_geotiff_stream(usuario_id, lote_id, vuelo_id, stream, length)
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
    if _disco():
        return storage_disco.download_geotiff_to_file(key, destino)
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
    if _disco():
        return storage_disco.download_geotiff(key)
    client = _client()
    response = client.get_object(settings.minio_bucket, key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def download_bytes(key: str) -> bytes:
    """Descarga cualquier objeto desde MinIO y retorna sus bytes."""
    if _disco():
        return storage_disco.download_bytes(key)
    client = _client()
    response = client.get_object(settings.minio_bucket, key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def upload_bytes(key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    """Sube bytes arbitrarios a MinIO bajo la clave dada. Retorna la clave."""
    if _disco():
        return storage_disco.upload_bytes(key, data, content_type)
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
    if _disco():
        return storage_disco.object_exists(key)
    from minio.error import S3Error

    client = _client()
    try:
        client.stat_object(settings.minio_bucket, key)
        return True
    except S3Error:
        return False


def upload_file(key: str, local_path: str, content_type: str = "application/octet-stream") -> str:
    """Sube un archivo local a MinIO por streaming (fput_object) — no lo carga en RAM."""
    if _disco():
        return storage_disco.upload_file(key, local_path, content_type)
    client = _client()
    _ensure_bucket(client)
    client.fput_object(settings.minio_bucket, key, local_path, content_type=content_type)
    return key


def presigned_url(key: str) -> str:
    """
    Genera la URL firmada con un cliente apuntado al endpoint PÚBLICO
    (settings.minio_public_endpoint), no al endpoint interno de Docker
    (minio_endpoint = "minio:9000") que usa el resto de este módulo.
    Si no hay endpoint público configurado, cae al interno (comportamiento
    previo — la URL solo sirve dentro de la red de Docker). region=
    explícito es obligatorio acá: sin él, minio-py intenta resolver el
    region pegándole por HTTP al propio endpoint del cliente — y ese
    endpoint público (p. ej. "localhost:9000") no es alcanzable DESDE el
    contenedor de la API, solo desde afuera.

    Con storage_backend="disk" devuelve una ruta de la propia API
    (/api/v1/archivos/{token}), con un token firmado que vence.
    """
    if _disco():
        return storage_disco.presigned_url(key)
    client = Minio(
        settings.minio_public_endpoint or settings.minio_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=settings.minio_use_ssl,
        region=settings.minio_region,
    )
    return client.presigned_get_object(
        settings.minio_bucket,
        key,
        expires=timedelta(seconds=settings.minio_presigned_url_expiry),
    )
