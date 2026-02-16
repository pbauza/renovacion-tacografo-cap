from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()
engine_kwargs: dict = {
    "echo": False,
    "future": True,
}

if settings.database_url.startswith("sqlite+aiosqlite"):
    engine_kwargs["connect_args"] = {"timeout": 30}

engine = create_async_engine(
    settings.database_url,
    **engine_kwargs,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
