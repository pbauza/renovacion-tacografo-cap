from datetime import date, timedelta


def calculate_alert_date(expiry_date: date) -> date:
    return expiry_date - timedelta(days=50)
