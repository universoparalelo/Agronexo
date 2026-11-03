"""
El worker importa app.core.storage al subir resultados. Si falta una dependencia en
docker/requirements.worker.txt (como PyJWT, que usa storage_disco), la tarea falla
recién al llegar a ese import y el análisis queda "pendiente" sin avisar.
"""


def test_storage_se_importa_con_las_dependencias_del_worker():
    from app.core import storage, storage_disco

    assert callable(storage.upload_bytes)
    assert callable(storage_disco.presigned_url)