from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from app.db.session import SessionLocal
from app.scheduler.jobs import create_deadline_alerts

logger = logging.getLogger(__name__)


class DailyScheduler:
    def __init__(self, run_hour: int = 3, run_minute: int = 0) -> None:
        self.run_hour = run_hour
        self.run_minute = run_minute
        self._task: asyncio.Task[None] | None = None
        self._stopped = asyncio.Event()

    def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stopped.clear()
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        self._stopped.set()
        if self._task:
            await self._task

    async def run_once(self) -> int:
        async with SessionLocal() as session:
            return await create_deadline_alerts(session)

    async def _run_loop(self) -> None:
        while not self._stopped.is_set():
            delay_seconds = self._seconds_until_next_run()
            try:
                await asyncio.wait_for(self._stopped.wait(), timeout=delay_seconds)
                break
            except asyncio.TimeoutError:
                pass

            try:
                created = await self.run_once()
                logger.info("Daily alert job completed. Created alerts: %s", created)
            except Exception:
                logger.exception("Daily alert job failed")

    def _seconds_until_next_run(self) -> float:
        now = datetime.now()
        next_run = now.replace(hour=self.run_hour, minute=self.run_minute, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        return (next_run - now).total_seconds()
