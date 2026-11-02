"""Archivos binarios del backup (GeoTIFF, resultados, avatar y logo).

Funciona con los dos almacenamientos: en disco copia directo, sin cargar el
archivo en memoria (un GeoTIFF original puede pesar varios GB); con MinIO pasa
por un archivo temporal.
"""
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

from app.core import storage, storage_disco
from app.core.config import settings

PREFIJO_ZIP = "archivos/"
_BLOQUE = 8 * 1024 * 1024


def _en_disco() -> bool:
    return settings.storage_backend == "disk"


def carpeta_copias() -> Path:
    """Donde se guardan los .zip generados. Con almacenamiento en disco queda al
    lado de la carpeta de archivos (así el desinstalador la borra con el resto de
    los datos); sin él, en la carpeta temporal."""
    if settings.storage_path:
        carpeta = Path(settings.storage_path).resolve().parent / "copias"
    else:
        carpeta = Path(tempfile.gettempdir()) / "agronexo_copias"
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def existe(clave: str) -> bool:
    return storage.object_exists(clave)


def agregar_al_zip(zf: zipfile.ZipFile, clave: str) -> bool:
    if not existe(clave):
        return False
    nombre = PREFIJO_ZIP + clave
    # Los GeoTIFF y las imágenes ya vienen comprimidos: recomprimirlos solo gasta tiempo.
    if _en_disco():
        zf.write(storage_disco.ruta_de(clave), nombre, compress_type=zipfile.ZIP_STORED)
        return True
    with tempfile.TemporaryDirectory() as carpeta:
        local = os.path.join(carpeta, "archivo")
        storage.download_geotiff_to_file(clave, local)
        zf.write(local, nombre, compress_type=zipfile.ZIP_STORED)
    return True


def extraer_del_zip(zf: zipfile.ZipFile, clave_origen: str, clave_destino: str) -> bool:
    try:
        info = zf.getinfo(PREFIJO_ZIP + clave_origen)
    except KeyError:
        return False
    if _en_disco():
        with zf.open(info) as origen:
            storage_disco.upload_stream(clave_destino, origen)
        return True
    with tempfile.TemporaryDirectory() as carpeta:
        local = os.path.join(carpeta, "archivo")
        with zf.open(info) as origen, open(local, "wb") as destino:
            shutil.copyfileobj(origen, destino, length=_BLOQUE)
        storage.upload_file(clave_destino, local)
    return True


def borrar(clave: str) -> None:
    # Solo con almacenamiento en disco: MinIO no tiene borrado en storage.py y
    # los archivos huérfanos quedan en el bucket (el copy previo los conserva).
    if not _en_disco():
        return
    try:
        storage_disco.ruta_de(clave).unlink(missing_ok=True)
    except ValueError:
        pass
