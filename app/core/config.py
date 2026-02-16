from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Renovaciones Tacografo CAP"
    api_prefix: str = "/api/v1"
    uvicorn_host: str = "0.0.0.0"
    uvicorn_port: int = 8000
    uvicorn_reload: bool = False
    database_url: str = Field(
        default="sqlite+aiosqlite:///./renovaciones.db",
        description="URL async de SQLAlchemy. Ejemplo: postgresql+asyncpg://usuario:clave@host/bd",
    )
    scheduler_enabled: bool = True
    reset_db_on_startup: bool = False
    auto_reset_sqlite_on_schema_mismatch: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
