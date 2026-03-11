"""Tests for BroadcastScheduler."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from aiogram_broadcast.exceptions import SchedulerNotConfiguredError
from aiogram_broadcast.scheduler import BroadcastScheduler
from aiogram_broadcast.service import BroadcastService


@pytest.fixture
def mock_apscheduler() -> MagicMock:
    s = MagicMock()
    s.add_job = MagicMock()
    s.remove_job = MagicMock()
    return s


@pytest.fixture
def scheduler(service: BroadcastService, mock_apscheduler: MagicMock) -> BroadcastScheduler:
    return BroadcastScheduler(service, mock_apscheduler)


class TestBroadcastScheduler:
    async def test_ensure_scheduler_raises_when_none(self, service: BroadcastService) -> None:
        sched = BroadcastScheduler(service, scheduler=None)
        with pytest.raises(SchedulerNotConfiguredError):
            await sched.schedule_text("hi", run_date=datetime.now(timezone.utc))

    async def test_schedule_text(
        self, scheduler: BroadcastScheduler, mock_apscheduler: MagicMock
    ) -> None:
        dt = datetime(2025, 1, 1, tzinfo=timezone.utc)
        task_id = await scheduler.schedule_text("hello", run_date=dt)
        assert task_id.startswith("broadcast_")
        mock_apscheduler.add_job.assert_called_once()
        assert task_id in {t.id for t in scheduler.get_pending_tasks()}

    async def test_cancel_existing(
        self, scheduler: BroadcastScheduler, mock_apscheduler: MagicMock
    ) -> None:
        dt = datetime(2025, 1, 1, tzinfo=timezone.utc)
        task_id = await scheduler.schedule_text("msg", run_date=dt)
        assert await scheduler.cancel(task_id) is True
        mock_apscheduler.remove_job.assert_called_once_with(task_id)
        assert scheduler.get_task(task_id) is None

    async def test_cancel_nonexistent(
        self, scheduler: BroadcastScheduler, mock_apscheduler: MagicMock
    ) -> None:
        mock_apscheduler.remove_job.side_effect = Exception("not found")
        assert await scheduler.cancel("fake_id") is False

    async def test_execute_success_calls_on_complete(
        self, service: BroadcastService, mock_apscheduler: MagicMock
    ) -> None:
        on_complete = AsyncMock()
        sched = BroadcastScheduler(service, mock_apscheduler, on_complete=on_complete)
        dt = datetime(2025, 1, 1, tzinfo=timezone.utc)
        task_id = await sched.schedule_text("hi", run_date=dt)
        task = sched.get_task(task_id)
        assert task is not None

        await sched._execute_text_broadcast(task)
        on_complete.assert_called_once()
        assert sched.get_task(task_id) is None  # cleaned up

    async def test_execute_error_calls_on_error(
        self, service: BroadcastService, mock_apscheduler: MagicMock, storage: AsyncMock
    ) -> None:
        on_error = AsyncMock()
        storage.get_all_subscriber_ids.side_effect = RuntimeError("db down")
        sched = BroadcastScheduler(service, mock_apscheduler, on_error=on_error)
        dt = datetime(2025, 1, 1, tzinfo=timezone.utc)
        task_id = await sched.schedule_text("hi", run_date=dt)
        task = sched.get_task(task_id)
        assert task is not None

        await sched._execute_text_broadcast(task)
        on_error.assert_called_once()
        assert sched.get_task(task_id) is None
