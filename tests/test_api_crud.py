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


@pytest.mark.anyio
async def test_client_finder_supports_name_nif_phone_company_and_cap_course(client):
    clients_payload = [
        {
            "full_name": "Maria Rios",
            "company": "Trans Iberia",
            "nif": "22334455A",
            "phone": "600100100",
            "email": "maria@example.com",
        },
        {
            "full_name": "Luis Perez",
            "company": "Trans Iberia",
            "nif": "33445566B",
            "phone": "600200200",
            "email": "luis@example.com",
        },
    ]

    client_ids: list[int] = []
    for payload in clients_payload:
        response = await client.post("/api/v1/clients", json=payload)
        assert response.status_code == 201
        client_ids.append(response.json()["id"])

    for client_id in client_ids:
        response = await client.post(
            "/api/v1/documents",
            json={
                "client_id": client_id,
                "doc_type": "cap",
                "expiry_date": (date.today() + timedelta(days=120)).isoformat(),
                "course_number": "CAP-2026",
            },
        )
        assert response.status_code == 201

    response = await client.get("/api/v1/clients?q=Maria")
    assert response.status_code == 200
    assert {c["nif"] for c in response.json()} == {"22334455A"}

    response = await client.get("/api/v1/clients?q=33445566B")
    assert response.status_code == 200
    assert {c["nif"] for c in response.json()} == {"33445566B"}

    response = await client.get("/api/v1/clients?q=600100100")
    assert response.status_code == 200
    assert {c["nif"] for c in response.json()} == {"22334455A"}

    response = await client.get("/api/v1/clients?q=Trans%20Iberia")
    assert response.status_code == 200
    assert len(response.json()) == 2

    response = await client.get("/api/v1/clients?q=CAP-2026")
    assert response.status_code == 200
    found_ids = [item["id"] for item in response.json()]
    assert len(found_ids) == 2
    assert len(set(found_ids)) == 2


@pytest.mark.anyio
async def test_power_of_attorney_creates_and_updates_alerts(client):
    response = await client.post(
        "/api/v1/clients",
        json={
            "full_name": "Ramon Vidal",
            "nif": "44556677C",
            "phone": "600300300",
        },
    )
    assert response.status_code == 201
    client_id = response.json()["id"]

    response = await client.post(
        "/api/v1/documents",
        json={
            "client_id": client_id,
            "doc_type": "power_of_attorney",
            "flag_fran": True,
            "expiry_fran": (date.today() + timedelta(days=40)).isoformat(),
            "flag_ciusaba": True,
            "expiry_ciusaba": (date.today() + timedelta(days=80)).isoformat(),
        },
    )
    assert response.status_code == 201
    document_id = response.json()["id"]

    response = await client.get(f"/api/v1/alerts?client_id={client_id}")
    assert response.status_code == 200
    alert_expiries = {item["expiry_date"] for item in response.json()}
    assert len(alert_expiries) == 2

    response = await client.patch(
        f"/api/v1/documents/{document_id}",
        json={
            "flag_ciusaba": False,
        },
    )
    assert response.status_code == 200

    response = await client.get(f"/api/v1/alerts?client_id={client_id}")
    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.anyio
async def test_cap_payment_rules(client):
    response = await client.post(
        "/api/v1/clients",
        json={
            "full_name": "Carlos Pena",
            "nif": "55667788D",
            "phone": "600400400",
        },
    )
    assert response.status_code == 201
    client_id = response.json()["id"]

    response = await client.post(
        "/api/v1/documents",
        json={
            "client_id": client_id,
            "doc_type": "cap",
            "expiry_date": (date.today() + timedelta(days=140)).isoformat(),
            "renewed_with_us": True,
        },
    )
    assert response.status_code == 422

    response = await client.post(
        "/api/v1/documents",
        json={
            "client_id": client_id,
            "doc_type": "cap",
            "expiry_date": (date.today() + timedelta(days=140)).isoformat(),
            "renewed_with_us": True,
            "payment_method": "visa",
        },
    )
    assert response.status_code == 201
    document_id = response.json()["id"]

    response = await client.patch(
        f"/api/v1/documents/{document_id}",
        json={
            "payment_method": "empresa",
            "fundae_payment_type": "recibo",
            "operation_number": "OP-EMP-1",
        },
    )
    assert response.status_code == 200
    assert response.json()["payment_method"] == "empresa"
    assert response.json()["fundae"] is False
    assert response.json()["fundae_payment_type"] == "recibo"
    assert response.json()["operation_number"] == "OP-EMP-1"

    response = await client.patch(
        f"/api/v1/documents/{document_id}",
        json={
            "payment_method": "empresa",
            "fundae": True,
            "fundae_payment_type": "transferencia",
            "operation_number": "OP-7788",
        },
    )
    assert response.status_code == 200
    assert response.json()["payment_method"] == "empresa"
    assert response.json()["fundae"] is True
    assert response.json()["fundae_payment_type"] == "transferencia"
