from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


def montar_frontend(app: FastAPI, directorio: Path) -> None:
    """Hace que la API entregue el frontend compilado (la carpeta `dist` de Vite).

    Se llama después de registrar los routers: las rutas de la API y de /api/docs
    ya existen y tienen prioridad sobre la ruta general que se agrega acá.
    """
    raiz = directorio.resolve()
    indice = raiz / "index.html"
    if not indice.is_file():
        raise RuntimeError(f"FRONTEND_DIR no tiene un index.html: {raiz}")

    assets = raiz / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="frontend-assets")

    @app.get("/{ruta:path}", include_in_schema=False)
    async def frontend(ruta: str):
        if ruta == "api" or ruta.startswith("api/"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")
        candidato = (raiz / ruta).resolve()
        if ruta and candidato.is_file() and candidato.is_relative_to(raiz):
            return FileResponse(candidato)
        # Las rutas de la app (/login, /lotes/...) las resuelve React Router en el navegador.
        return FileResponse(indice)
