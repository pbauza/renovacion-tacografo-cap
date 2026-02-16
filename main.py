from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.core.app_config import get_app_json_config
from app.core.config import get_settings
from app.db.init_db import init_db
from app.scheduler import DailyScheduler
from app.ui import ui_router

settings = get_settings()
app_json = get_app_json_config()
scheduler = DailyScheduler(run_hour=3, run_minute=0)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()

    if settings.scheduler_enabled:
        scheduler.start()

    yield

    if settings.scheduler_enabled:
        await scheduler.stop()


app = FastAPI(title=app_json.app_name, lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/storage", StaticFiles(directory="storage"), name="storage")

app.include_router(ui_router)
app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.uvicorn_host,
        port=settings.uvicorn_port,
        reload=settings.uvicorn_reload,
    )
