from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.models.alert import Alert
from app.models.client import Client
from app.models.document import Document, DocumentType
from app.scheduler.jobs import create_deadline_alerts


@pytest.mark.anyio
async def test_scheduler_creates_alerts_for_30_60_90_windows(session_factory):
    async with session_factory() as session:
        client = Client(full_name="Pedro Martin", nif="11112222X", phone="633333333")
        session.add(client)
        await session.flush()

        for days in (30, 60, 90):
            session.add(
                Document(
                    client_id=client.id,
                    doc_type=DocumentType.OTHER,
                    expiry_date=date.today() + timedelta(days=days),
                )
            )

        await session.commit()

    async with session_factory() as session:
        created = await create_deadline_alerts(session)
        assert created == 3

        alerts = list(await session.scalars(select(Alert).order_by(Alert.id.asc())))
        assert len(alerts) == 3


@pytest.mark.anyio
async def test_scheduler_creates_alerts_for_power_of_attorney_windows(session_factory):
    async with session_factory() as session:
        client = Client(full_name="Nuria Soler", nif="22223333Y", phone="644444444")
        session.add(client)
        await session.flush()

        session.add(
            Document(
                client_id=client.id,
                doc_type=DocumentType.POWER_OF_ATTORNEY,
                flag_fran=True,
                expiry_fran=date.today() + timedelta(days=30),
                flag_ciusaba=True,
                expiry_ciusaba=date.today() + timedelta(days=60),
            )
        )
        await session.commit()

    async with session_factory() as session:
        created = await create_deadline_alerts(session)
        assert created == 2

        alerts = list(await session.scalars(select(Alert).order_by(Alert.id.asc())))
        assert len(alerts) == 2
