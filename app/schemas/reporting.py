from pydantic import BaseModel


class DashboardSummary(BaseModel):
    due_in_30_days: int
    due_in_60_days: int
    due_in_90_days: int
    documents_total: int
    alerts_total: int
    alerts_due_today_or_older: int
