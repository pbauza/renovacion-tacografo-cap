from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.core.app_config import get_app_json_config
from app.core.config import get_settings

settings = get_settings()
app_json = get_app_json_config()
templates = Jinja2Templates(directory="templates")

router = APIRouter(tags=["ui"])


def _base_context(page_title: str, active_nav: str) -> dict:
    return {
        "app_name": app_json.app_name,
        "api_prefix": settings.api_prefix,
        "page_title": page_title,
        "active_nav": active_nav,
        "workspace_subtitle": app_json.workspace_subtitle,
        "logo_path": app_json.ui.logo_path,
        "favicon_path": app_json.ui.favicon_path,
        "dashboard_logo_path": app_json.ui.dashboard_logo_path,
        "quick_stats": {"d30": 24, "d60": 47, "d90": 91},
    }


@router.get("/", include_in_schema=False)
async def home() -> RedirectResponse:
    return RedirectResponse(url="/dashboard", status_code=307)


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="dashboard/index.html",
        context=_base_context(page_title="Resumen del panel", active_nav="dashboard"),
    )


@router.get("/clients", response_class=HTMLResponse)
async def clients(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="clients/index.html",
        context=_base_context(page_title="Clientes", active_nav="clients"),
    )


@router.get("/alerts", response_class=HTMLResponse)
async def alerts(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="alerts/index.html",
        context=_base_context(page_title="Alertas", active_nav="alerts"),
    )


@router.get("/documents", response_class=HTMLResponse)
async def documents(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="documents/index.html",
        context=_base_context(page_title="Documentos", active_nav="documents"),
    )


@router.get("/tools", response_class=HTMLResponse)
async def tools(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="tools/index.html",
        context=_base_context(page_title="Herramientas y acciones", active_nav="tools"),
    )


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="settings/index.html",
        context=_base_context(page_title="Configuracion", active_nav="settings"),
    )
