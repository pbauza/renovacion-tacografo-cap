from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field


class UIConfig(BaseModel):
    logo_path: str = "/static/img/logo.png"
    favicon_path: str = "/static/img/logo.png"
    dashboard_logo_path: str = "/static/img/logo.png"


class PDFConfig(BaseModel):
    report_title: str = "Informe de renovaciones de cliente"
    organization_name: str = "Renovaciones Tacografo CAP"
    contact_email: str = "contact@renovaciones.local"
    contact_phone: str = "+34 000 000 000"


class AppJSONConfig(BaseModel):
    app_name: str = "Renovaciones Tacografo CAP"
    workspace_subtitle: str = "Espacio de gestion de Tacografo y CAP"
    ui: UIConfig = Field(default_factory=UIConfig)
    pdf: PDFConfig = Field(default_factory=PDFConfig)


@lru_cache
def get_app_json_config() -> AppJSONConfig:
    path = Path("config/app_config.json")
    if not path.exists():
        return AppJSONConfig()

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return AppJSONConfig()
    return AppJSONConfig.model_validate(raw)
