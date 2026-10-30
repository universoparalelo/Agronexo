from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_env: str = "development"
    app_debug: bool = False
    allowed_origins: str = "http://localhost:5173"
    # Carpeta con el frontend compilado (app de escritorio). Vacío = la API no lo sirve.
    frontend_dir: str = ""

    # PostgreSQL
    postgres_host: str
    postgres_port: int = 5432
    postgres_db: str
    postgres_user: str
    postgres_password: str

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # Redis / Celery
    celery_broker_url: str
    celery_result_backend: str

    # Almacenamiento de archivos: "minio" (Docker y CI) o "disk" (app de
    # escritorio, carpeta storage_path). MinIO sale del proyecto cuando CI
    # pase con "disk".
    storage_backend: str = "minio"
    storage_path: str = ""

    # MinIO (solo con storage_backend="minio")
    minio_endpoint: str = ""
    minio_root_user: str = ""
    minio_root_password: str = ""
    minio_bucket: str = "agronexo"
    minio_use_ssl: bool = False
    minio_presigned_url_expiry: int = 3600
    # Host:puerto alcanzable por el navegador/cliente externo para las URLs
    # firmadas (presigned_url) — minio_endpoint es el nombre del servicio
    # Docker ("minio:9000"), válido solo dentro de la red de contenedores.
    # Sin este valor, una presigned URL generada con minio_endpoint queda
    # inservible para cualquier cliente fuera del stack. Si no se define,
    # se usa minio_endpoint (comportamiento previo, roto para uso externo).
    minio_public_endpoint: str | None = None
    # minio-py necesita el region del bucket antes de firmar una URL; si no
    # se le pasa explícito, lo resuelve pegándole al propio MinIO (HTTP GET
    # ?location=). Ese round-trip revienta cuando el cliente apunta a
    # minio_public_endpoint (p. ej. "localhost:9000" desde DENTRO del
    # contenedor de la API, donde "localhost" no es MinIO). MinIO sin
    # MINIO_REGION configurado en el server usa "us-east-1" por defecto.
    minio_region: str = "us-east-1"

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    @model_validator(mode="after")
    def _validar_almacenamiento(self):
        if self.storage_backend == "disk":
            if not self.storage_path:
                raise ValueError("STORAGE_PATH es obligatorio con STORAGE_BACKEND=disk")
        elif self.storage_backend == "minio":
            faltan = [
                nombre
                for nombre, valor in (
                    ("MINIO_ENDPOINT", self.minio_endpoint),
                    ("MINIO_ROOT_USER", self.minio_root_user),
                    ("MINIO_ROOT_PASSWORD", self.minio_root_password),
                )
                if not valor
            ]
            if faltan:
                raise ValueError(f"Faltan {', '.join(faltan)} con STORAGE_BACKEND=minio")
        else:
            raise ValueError("STORAGE_BACKEND debe ser 'minio' o 'disk'")
        return self

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]


settings = Settings()
