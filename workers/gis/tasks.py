from workers.celery_app import celery_app


@celery_app.task(bind=True, name="workers.gis.tasks.procesar_analisis")
def procesar_analisis(self, analisis_id: str) -> dict:
    """
    Tarea principal de procesamiento GIS.
    Recibe el ID de análisis, lee el GeoTIFF desde MinIO,
    calcula índices y persiste zonas en PostGIS.
    Se implementa en el sprint de Worker GIS.
    """
    self.update_state(state="STARTED", meta={"progreso": 0, "mensaje": "Iniciando procesamiento"})
    # TODO: implementar pipeline GIS
    return {"analisis_id": analisis_id, "status": "pendiente_implementacion"}
