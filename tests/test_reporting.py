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


@pytest.mark.anyio
async def test_renewals_report_filters_by_year_and_payment_method(client):
    response = await client.post(
        "/api/v1/clients",
        json={
            "full_name": "Laura Gomez",
            "nif": "99998888E",
            "phone": "611000111",
        },
    )
    assert response.status_code == 201
    client_id = response.json()["id"]

    response = await client.post(
        "/api/v1/documents",
        json={
            "client_id": client_id,
            "doc_type": "cap",
            "expiry_date": (date.today() + timedelta(days=100)).isoformat(),
            "renewed_with_us": True,
            "payment_method": "visa",
        },
    )
    assert response.status_code == 201

    response = await client.post(
        "/api/v1/documents",
        json={
            "client_id": client_id,
            "doc_type": "tachograph_card",
            "expiry_date": (date.today() + timedelta(days=130)).isoformat(),
            "renewed_with_us": True,
            "payment_method": "empresa",
            "fundae": True,
            "fundae_payment_type": "recibo",
            "operation_number": "OP-123",
        },
    )
    assert response.status_code == 201

    this_year = date.today().year
    response = await client.get(f"/api/v1/reporting/renewals?year={this_year}")
    assert response.status_code == 200
    report = response.json()
    assert report["total"] == 2
    assert report["by_doc_type"]["cap"] == 1
    assert report["by_doc_type"]["tachograph_card"] == 1

    response = await client.get(f"/api/v1/reporting/renewals?year={this_year}&payment_method=visa")
    assert response.status_code == 200
    report = response.json()
    assert report["total"] == 1
    assert report["items"][0]["payment_method"] == "visa"
    assert report["items"][0]["fundae"] is False

    response = await client.get(f"/api/v1/reporting/renewals?year={this_year}&payment_method=empresa")
    assert response.status_code == 200
    report = response.json()
    assert report["total"] == 1
    assert report["items"][0]["payment_method"] == "empresa"
    assert report["items"][0]["fundae"] is True

    response = await client.get(f"/api/v1/reporting/renewals?year={this_year}&fundae=true")
    assert response.status_code == 200
    report = response.json()
    assert report["total"] == 1
    assert report["fundae"] is True
    assert report["items"][0]["fundae"] is True

    response = await client.get(f"/api/v1/reporting/renewals?year={this_year}&fundae=false")
    assert response.status_code == 200
    report = response.json()
    assert report["total"] == 1
    assert report["fundae"] is False
    assert report["items"][0]["fundae"] is False
