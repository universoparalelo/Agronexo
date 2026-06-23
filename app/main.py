from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

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


# Los routers se registran acá a medida que se implementan los módulos
# from app.auth.router import router as auth_router
# from app.lotes.router import router as lotes_router
# app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
# app.include_router(lotes_router, prefix="/api/v1/lotes", tags=["lotes"])
