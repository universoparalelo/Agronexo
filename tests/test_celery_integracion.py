"""
Test de integración end-to-end del pipeline Celery.

Verifica el ciclo completo: subir GeoTIFF a MinIO → encolar tarea →
worker procesa → polling devuelve completado → zonas.geojson en MinIO.

Requiere el stack completo levantado (MinIO, Redis, worker).
Correr en el contenedor worker:
    docker compose exec worker sh -c "PYTHONPATH=//app python3 tests/test_celery_integracion.py"
"""

import io
import time
import uuid

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_bounds


# ── Fixture ──────────────────────────────────────────────────────────

def _geotiff_dji_sintetico() -> bytes:
    """GeoTIFF de 5 bandas simulando DJI Mavic 3 Multispectral."""
    buf = io.BytesIO()
    transform = from_bounds(-60.68, -27.48, -60.67, -27.47, 30, 30)
    with rasterio.open(
        buf, "w", driver="GTiff",
        height=30, width=30, count=5, dtype="float32",
        crs=CRS.from_epsg(4326), transform=transform,
    ) as dst:
        # Valores NDVI controlados: NIR (banda 5) > RED (banda 3) → vigor positivo
        for i in range(1, 6):
            valor = 0.6 if i == 5 else 0.15  # NIR alto, resto bajo
            dst.write(np.full((30, 30), valor, dtype="float32"), i)
    return buf.getvalue()


# ── Tests ─────────────────────────────────────────────────────────────

def test_ciclo_completo_encolar_y_esperar():
    from app.core.config import settings
    from app.core.storage import upload_bytes, upload_geotiff
    from workers.celery_app import celery_app

    usuario_id = "test-user"
    lote_id    = str(uuid.uuid4())
    vuelo_id   = str(uuid.uuid4())

    # 1. Subir GeoTIFF sintético a MinIO
    data = _geotiff_dji_sintetico()
    minio_key = upload_geotiff(usuario_id, lote_id, vuelo_id, data)
    print(f"✓ GeoTIFF subido → {minio_key}")

    # 2. Encolar tarea
    task = celery_app.send_task(
        "workers.gis.tasks.procesar_vuelo",
        kwargs={
            "vuelo_id": vuelo_id,
            "minio_key": minio_key,
            "sensor": "dji_mavic3",
            "indice": "ndvi",
        },
        queue="gis",
    )
    print(f"✓ Tarea encolada → task_id={task.id}")

    # 3. Polling hasta completado o timeout (60 s)
    timeout = 60
    intervalo = 2
    transcurrido = 0
    while transcurrido < timeout:
        estado = task.state
        info   = task.info if isinstance(task.info, dict) else {}
        progreso = info.get("progreso", "—")
        mensaje  = info.get("mensaje", "")
        print(f"  [{transcurrido:>3}s] estado={estado} progreso={progreso} {mensaje}")

        if estado == "SUCCESS":
            break
        if estado == "FAILURE":
            raise AssertionError(f"La tarea falló: {task.info}")

        time.sleep(intervalo)
        transcurrido += intervalo
    else:
        raise AssertionError(f"Timeout: la tarea no completó en {timeout}s (último estado: {task.state})")

    # 4. Verificar resultado de la tarea
    resultado = task.result
    assert "estadisticas" in resultado, f"Resultado inesperado: {resultado}"
    stats = resultado["estadisticas"]
    assert stats["indice"] == "ndvi"
    assert stats["sensor"] == "dji_mavic3"
    assert "ndvi_promedio_lote" in stats
    print(f"✓ Resultado OK → {stats['total_poligonos']} polígonos, NDVI prom={stats['ndvi_promedio_lote']}")

    # 5. Verificar que zonas.geojson fue subido a MinIO
    from app.core.storage import download_geotiff
    prefijo = "/".join(minio_key.split("/")[:3])
    geojson_bytes = download_geotiff(f"{prefijo}/zonas.geojson")
    assert len(geojson_bytes) > 0
    import json
    geojson = json.loads(geojson_bytes)
    assert geojson.get("type") == "FeatureCollection"
    print(f"✓ zonas.geojson en MinIO → {len(geojson['features'])} features")


def test_resultado_expira_en_redis():
    """Verifica que result_expires está configurado (no hace wait, solo chequea config)."""
    from workers.celery_app import celery_app
    expires = celery_app.conf.result_expires
    assert expires is not None and expires > 0, "result_expires debe estar configurado"
    print(f"✓ result_expires configurado → {expires}s")


def test_cola_gis_declarada():
    from workers.celery_app import celery_app
    queues = celery_app.conf.task_queues
    assert "gis" in queues, f"Cola 'gis' no declarada. Queues: {queues}"
    print(f"✓ Cola 'gis' declarada explícitamente en Celery")


if __name__ == "__main__":
    print("\n── Configuración Celery ─────────────────────────────")
    test_resultado_expira_en_redis()
    test_cola_gis_declarada()

    print("\n── Ciclo completo end-to-end ────────────────────────")
    test_ciclo_completo_encolar_y_esperar()

    print("\nTodos los tests pasaron.\n")
