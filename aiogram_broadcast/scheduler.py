"""APScheduler integration for scheduled broadcasts."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import TYPE_CHECKING, Any

from aiogram_broadcast.exceptions import SchedulerNotConfiguredError
from aiogram_broadcast.models import BroadcastResult, BroadcastTask
from aiogram_broadcast.service import BroadcastService

if TYPE_CHECKING:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)

BroadcastCallback = Callable[[str, BroadcastResult], Awaitable[None]]


class BroadcastScheduler:
    """
    Scheduler for delayed broadcasts using APScheduler.

    Features:
    - Schedule broadcasts for a specific time
    - Cancel scheduled broadcasts
    - List pending broadcasts
    - Callbacks on broadcast completion

    Usage:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler

        scheduler = AsyncIOScheduler()
        broadcast_scheduler = BroadcastScheduler(service, scheduler)

        # Schedule a text broadcast
        task_id = await broadcast_scheduler.schedule_text(
            text="Hello!",
            run_date=datetime(2024, 1, 1, 12, 0),
        )

        # Cancel scheduled broadcast
        await broadcast_scheduler.cancel(task_id)
    """

    def __init__(
        self,
        service: BroadcastService,
        scheduler: AsyncIOScheduler | None = None,
        on_complete: BroadcastCallback | None = None,
        on_error: Callable[[str, Exception], Awaitable[None]] | None = None,
    ) -> None:
        """
        Initialize broadcast scheduler.

        Args:
            service: BroadcastService instance.
            scheduler: APScheduler instance. If None, scheduling is disabled.
            on_complete: Callback when broadcast completes.
            on_error: Callback when broadcast fails.
        """
        self._service = service
        self._scheduler = scheduler
        self._on_complete = on_complete
        self._on_error = on_error
        self._pending_tasks: dict[str, BroadcastTask] = {}

    @property
    def service(self) -> BroadcastService:
        """Get broadcast service."""
        return self._service

    @property
    def scheduler(self) -> AsyncIOScheduler | None:
        """Get APScheduler instance."""
        return self._scheduler

    @property
    def is_configured(self) -> bool:
        """Check if scheduler is configured."""
        return self._scheduler is not None

    def _ensure_scheduler(self) -> None:
        """Ensure scheduler is configured."""
        if not self.is_configured:
            raise SchedulerNotConfiguredError(
                "APScheduler is not configured. Pass scheduler to constructor."
            )

    def _generate_task_id(self) -> str:
        """Generate unique task ID."""
        return f"broadcast_{uuid.uuid4().hex[:8]}"

    async def schedule_text(
        self,
        text: str,
        run_date: datetime,
        parse_mode: str | None = None,
        reply_markup: Any = None,
        disable_notification: bool = False,
        **kwargs: Any,
    ) -> str:
        """
        Schedule a text broadcast.

        Args:
            text: Message text.
            run_date: When to execute the broadcast.
            parse_mode: Parse mode.
            reply_markup: Reply markup.
            disable_notification: Disable notification.
            **kwargs: Additional arguments for broadcast_text.

        Returns:
            Task ID for tracking/cancellation.
        """
        self._ensure_scheduler()

        task_id = self._generate_task_id()
        task = BroadcastTask(
            id=task_id,
            content=text,
            content_type="text",
            scheduled_at=run_date,
            kwargs={
                "parse_mode": parse_mode,
                "reply_markup": reply_markup,
                "disable_notification": disable_notification,
                **kwargs,
            },
        )

        assert self._scheduler is not None
        self._scheduler.add_job(
            self._execute_text_broadcast,
            trigger="date",
            run_date=run_date,
            id=task_id,
            args=[task],
            replace_existing=True,
        )

        self._pending_tasks[task_id] = task
        logger.info(f"Scheduled text broadcast {task_id} for {run_date}")
        return task_id

    async def schedule_photo(
        self,
        photo: str,
        run_date: datetime,
        caption: str | None = None,
        parse_mode: str | None = None,
        reply_markup: Any = None,
        disable_notification: bool = False,
        **kwargs: Any,
    ) -> str:
        """
        Schedule a photo broadcast.

        Args:
            photo: Photo file_id or URL.
            run_date: When to execute the broadcast.
            caption: Photo caption.
            parse_mode: Parse mode for caption.
            reply_markup: Reply markup.
            disable_notification: Disable notification.
            **kwargs: Additional arguments for broadcast_photo.

        Returns:
            Task ID for tracking/cancellation.
        """
        self._ensure_scheduler()

        task_id = self._generate_task_id()
        task = BroadcastTask(
            id=task_id,
            content=photo,
            content_type="photo",
            scheduled_at=run_date,
            kwargs={
                "caption": caption,
                "parse_mode": parse_mode,
                "reply_markup": reply_markup,
                "disable_notification": disable_notification,
                **kwargs,
            },
        )

        assert self._scheduler is not None
        self._scheduler.add_job(
            self._execute_photo_broadcast,
            trigger="date",
            run_date=run_date,
            id=task_id,
            args=[task],
            replace_existing=True,
        )

        self._pending_tasks[task_id] = task
        logger.info(f"Scheduled photo broadcast {task_id} for {run_date}")
        return task_id

    async def schedule_copy(
        self,
        from_chat_id: int,
        message_id: int,
        run_date: datetime,
        caption: str | None = None,
        parse_mode: str | None = None,
        reply_markup: Any = None,
        disable_notification: bool = False,
        **kwargs: Any,
    ) -> str:
        """
        Schedule a copy broadcast.

        Args:
            from_chat_id: Source chat ID.
            message_id: Source message ID.
            run_date: When to execute the broadcast.
            caption: New caption.
            parse_mode: Parse mode for caption.
            reply_markup: Reply markup.
            disable_notification: Disable notification.
            **kwargs: Additional arguments for broadcast_copy.

        Returns:
            Task ID for tracking/cancellation.
        """
        self._ensure_scheduler()

        task_id = self._generate_task_id()
        task = BroadcastTask(
            id=task_id,
            content={"from_chat_id": from_chat_id, "message_id": message_id},
            content_type="copy",
            scheduled_at=run_date,
            kwargs={
                "caption": caption,
                "parse_mode": parse_mode,
                "reply_markup": reply_markup,
                "disable_notification": disable_notification,
                **kwargs,
            },
        )

        assert self._scheduler is not None
        self._scheduler.add_job(
            self._execute_copy_broadcast,
            trigger="date",
            run_date=run_date,
            id=task_id,
            args=[task],
            replace_existing=True,
        )

        self._pending_tasks[task_id] = task
        logger.info(f"Scheduled copy broadcast {task_id} for {run_date}")
        return task_id

    async def cancel(self, task_id: str) -> bool:
        """
        Cancel a scheduled broadcast.

        Args:
            task_id: Task ID returned from schedule_* methods.

        Returns:
            True if task was cancelled, False if not found.
        """
        self._ensure_scheduler()

        assert self._scheduler is not None
        try:
            self._scheduler.remove_job(task_id)
            self._pending_tasks.pop(task_id, None)
            logger.info(f"Cancelled broadcast {task_id}")
            return True
        except Exception:
            return False

    def get_pending_tasks(self) -> list[BroadcastTask]:
        """
        Get list of pending broadcast tasks.

        Returns:
            List of pending BroadcastTask objects.
        """
        return list(self._pending_tasks.values())

    def get_task(self, task_id: str) -> BroadcastTask | None:
        """
        Get task by ID.

        Args:
            task_id: Task ID.

        Returns:
            BroadcastTask or None if not found.
        """
        return self._pending_tasks.get(task_id)

    async def _execute_text_broadcast(self, task: BroadcastTask) -> None:
        """Execute scheduled text broadcast."""
        try:
            result = await self._service.broadcast_text(
                text=task.content,
                **task.kwargs,
            )
            await self._handle_completion(task.id, result)
        except Exception as e:
            await self._handle_error(task.id, e)
        finally:
            self._pending_tasks.pop(task.id, None)

    async def _execute_photo_broadcast(self, task: BroadcastTask) -> None:
        """Execute scheduled photo broadcast."""
        try:
            result = await self._service.broadcast_photo(
                photo=task.content,
                **task.kwargs,
            )
            await self._handle_completion(task.id, result)
        except Exception as e:
            await self._handle_error(task.id, e)
        finally:
            self._pending_tasks.pop(task.id, None)

    async def _execute_copy_broadcast(self, task: BroadcastTask) -> None:
        """Execute scheduled copy broadcast."""
        try:
            result = await self._service.broadcast_copy(
                from_chat_id=task.content["from_chat_id"],
                message_id=task.content["message_id"],
                **task.kwargs,
            )
            await self._handle_completion(task.id, result)
        except Exception as e:
            await self._handle_error(task.id, e)
        finally:
            self._pending_tasks.pop(task.id, None)

    async def _handle_completion(self, task_id: str, result: BroadcastResult) -> None:
        """Handle broadcast completion."""
        logger.info(
            f"Broadcast {task_id} completed: {result.successful}/{result.total} successful"
        )
        if self._on_complete:
            try:
                await self._on_complete(task_id, result)
            except Exception as e:
                logger.error(f"Error in completion callback: {e}")

    async def _handle_error(self, task_id: str, error: Exception) -> None:
        """Handle broadcast error."""
        logger.error(f"Broadcast {task_id} failed: {error}")
        if self._on_error:
            try:
                await self._on_error(task_id, error)
            except Exception as e:
                logger.error(f"Error in error callback: {e}")
