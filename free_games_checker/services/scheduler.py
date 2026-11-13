"""Background giveaway polling scheduler powered by APScheduler."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING, Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from free_games_checker.utils.logging import get_logger

if TYPE_CHECKING:
    from free_games_checker.models.config import SchedulerConfig

logger = get_logger("services.scheduler")


class AppScheduler:
    """Manages scheduled periodic checks in the background."""

    def __init__(self, config: SchedulerConfig, check_callback: Callable[[], Any]) -> None:
        self.config = config
        self.check_callback = check_callback
        self._scheduler = BackgroundScheduler(timezone=self.config.timezone)
        self.is_running = False

    def start(self) -> None:
        """Start scheduler with configured check interval."""
        if self.is_running:
            return

        trigger = IntervalTrigger(
            hours=self.config.check_interval_hours,
            timezone=self.config.timezone,
        )
        self._scheduler.add_job(
            self.check_callback,
            trigger=trigger,
            id="periodic_game_check",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )
        self._scheduler.start()
        self.is_running = True
        logger.info(
            "Scheduler started (Every %d hours, timezone: %s)",
            self.config.check_interval_hours,
            self.config.timezone,
        )

    def stop(self) -> None:
        """Stop scheduler safely."""
        if not self.is_running:
            return
        self._scheduler.shutdown(wait=False)
        self.is_running = False
        logger.info("Scheduler stopped.")

    def reschedule(self, interval_hours: int, timezone: str) -> None:
        """Update interval or timezone."""
        self.config.check_interval_hours = interval_hours
        self.config.timezone = timezone
        if self.is_running:
            trigger = IntervalTrigger(hours=interval_hours, timezone=timezone)
            self._scheduler.reschedule_job("periodic_game_check", trigger=trigger)
            logger.info("Scheduler rescheduled to every %d hours (%s)", interval_hours, timezone)

    def get_next_run_time(self) -> datetime | None:
        """Return next scheduled run timestamp."""
        job = self._scheduler.get_job("periodic_game_check")
        if job and getattr(job, "next_run_time", None):
            next_time = job.next_run_time
            if isinstance(next_time, datetime):
                return next_time
        return None
