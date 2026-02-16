from fastapi import APIRouter

from app.api.routers.alerts import router as alerts_router
from app.api.routers.clients import router as clients_router
from app.api.routers.documents import router as documents_router
from app.api.routers.reporting import router as reporting_router
from app.api.routers.tools import router as tools_router

api_router = APIRouter()
api_router.include_router(clients_router)
api_router.include_router(documents_router)
api_router.include_router(alerts_router)
api_router.include_router(reporting_router)
api_router.include_router(tools_router)

__all__ = ["api_router"]
