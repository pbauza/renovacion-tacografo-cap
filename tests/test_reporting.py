from datetime import date, timedelta

import pytest


@pytest.mark.anyio
async def test_dashboard_summary(client):
    response = await client.post(
        "/api/v1/clients",
        json={
            "full_name": "Ana Lopez",
            "nif": "87654321Z",
            "phone": "622222222",
            "email": "ana@example.com",
        },
    )
    assert response.status_code == 201
    client_id = response.json()["id"]

    for days in (20, 45, 80):
        response = await client.post(
            "/api/v1/documents",
            json={
                "client_id": client_id,
                "doc_type": "other",
                "expiry_date": (date.today() + timedelta(days=days)).isoformat(),
            },
        )
        assert response.status_code == 201

    response = await client.get("/api/v1/reporting/dashboard")
    assert response.status_code == 200
    summary = response.json()

    assert summary["due_in_30_days"] == 1
    assert summary["due_in_60_days"] == 2
    assert summary["due_in_90_days"] == 3
    assert summary["documents_total"] == 3
    assert summary["alerts_total"] == 3
