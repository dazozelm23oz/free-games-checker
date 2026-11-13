"""Base checker abstract class, circuit breaker, and caching layer."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import ClassVar

from free_games_checker.models.game import Game
from free_games_checker.utils.logging import get_logger

logger = get_logger("checkers.base")


class CircuitBreaker:
    """Circuit breaker pattern preventing repeated requests to failing stores."""

    def __init__(self, failure_threshold: int = 3, cooldown_seconds: float = 900.0) -> None:
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.failure_count = 0
        self.last_failure_time: float = 0.0
        self.state: str = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def can_execute(self) -> bool:
        """Check if the circuit allows execution."""
        if self.state == "CLOSED":
            return True
        now = time.monotonic()
        if self.state == "OPEN":
            if now - self.last_failure_time >= self.cooldown_seconds:
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker entering HALF_OPEN state.")
                return True
            return False
        return True  # HALF_OPEN allows one trial request

    def record_success(self) -> None:
        """Reset failures on successful request."""
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self) -> None:
        """Record a failure and potentially trip the breaker to OPEN."""
        self.failure_count += 1
        self.last_failure_time = time.monotonic()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(
                "Circuit breaker tripped OPEN. Backing off for %.0f seconds.",
                self.cooldown_seconds,
            )


class BaseChecker(ABC):
    """Abstract base class for all store free-game checkers."""

    name: ClassVar[str] = "Base"

    def __init__(
        self,
        cache_ttl_seconds: float = 900.0,
        failure_threshold: int = 3,
        cooldown_seconds: float = 900.0,
    ) -> None:
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cached_games: list[Game] = []
        self._cache_timestamp: float = 0.0
        self.circuit_breaker = CircuitBreaker(failure_threshold, cooldown_seconds)
        self.last_error: str | None = None

    @abstractmethod
    async def _fetch_impl(self) -> list[Game]:
        """Subclass implementation of store scraper/API parser."""
        raise NotImplementedError

    async def fetch(self, force_refresh: bool = False) -> list[Game]:
        """Fetch games using circuit breaker protection and TTL cache."""
        now = time.monotonic()

        # Check in-memory cache if not forced
        if not force_refresh and self._cached_games:
            if now - self._cache_timestamp < self.cache_ttl_seconds:
                logger.debug("[%s] Returning %d cached games.", self.name, len(self._cached_games))
                self.last_error = None
                return self._cached_games

        # Check circuit breaker
        if not self.circuit_breaker.can_execute():
            self.last_error = "Circuit breaker open (temporary cooldown)"
            logger.warning("[%s] Skipping check: %s", self.name, self.last_error)
            return self._cached_games

        try:
            games = await self._fetch_impl()
            self.circuit_breaker.record_success()
            self._cached_games = games
            self._cache_timestamp = now
            self.last_error = None
            logger.info("[%s] Successfully retrieved %d free games.", self.name, len(games))
            return games
        except Exception as err:
            self.circuit_breaker.record_failure()
            self.last_error = str(err)
            logger.error("[%s] Fetch failed: %s", self.name, err)
            # Return last good cache if available
            return self._cached_games
