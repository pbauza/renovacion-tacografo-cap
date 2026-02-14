from datetime import date, timedelta

import pytest


@pytest.mark.anyio
async def test_client_document_alert_flow(client):
    client_payload = {
        "full_name": "Juan Perez",
        "company": "Transporte Norte",
        "nif": "12345678A",
        "phone": "600000000",
        "email": "juan@example.com",
    }
    response = await client.post("/api/v1/clients", json=client_payload)
    assert response.status_code == 201
    client_id = response.json()["id"]

    response = await client.patch(f"/api/v1/clients/{client_id}", json={"phone": "611111111"})
    assert response.status_code == 200
    assert response.json()["phone"] == "611111111"

    document_payload = {
        "client_id": client_id,
        "doc_type": "cap",
        "expiry_date": (date.today() + timedelta(days=70)).isoformat(),
        "course_number": "CURSO-44",
    }
    response = await client.post("/api/v1/documents", json=document_payload)
    assert response.status_code == 201
    document_id = response.json()["id"]

    response = await client.get("/api/v1/alerts")
    assert response.status_code == 200
    alerts = response.json()
    assert len(alerts) == 1
    assert alerts[0]["document_id"] == document_id

    response = await client.delete(f"/api/v1/documents/{document_id}")
    assert response.status_code == 204

    response = await client.delete(f"/api/v1/clients/{client_id}")
    assert response.status_code == 204
