from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.core.database import AsyncSessionLocal

app = FastAPI(
    title="AgroNexo API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "env": settings.app_env}


@app.get("/api/v1/health/db")
async def health_db():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT PostGIS_Version()"))
        postgis_version = result.scalar()
    return {"status": "ok", "postgis": postgis_version}


from app.auth.router import router as auth_router
from app.diagnostico.router import productos_router, router as diagnostico_router
from app.ingesta.router import router as ingesta_router
from app.lotes.router import router as lotes_router
from app.ordenes_trabajo.router import router as ordenes_trabajo_router
from app.reportes.router import router as reportes_router

app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(lotes_router, prefix="/api/v1/lotes", tags=["lotes"])
app.include_router(ingesta_router, prefix="/api/v1/lotes", tags=["ingesta"])
app.include_router(diagnostico_router, prefix="/api/v1/lotes", tags=["diagnostico"])
app.include_router(productos_router, prefix="/api/v1/productos-fitosanitarios", tags=["productos"])
app.include_router(reportes_router, prefix="/api/v1/lotes", tags=["reportes"])
app.include_router(ordenes_trabajo_router, prefix="/api/v1/lotes", tags=["ordenes-trabajo"])
