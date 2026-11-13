"""Checkers package and concurrent fetch orchestrator."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from free_games_checker.checkers.base import BaseChecker
from free_games_checker.checkers.epic import EpicChecker
from free_games_checker.checkers.gamerpower import GamerPowerChecker
from free_games_checker.checkers.gog import GOGChecker
from free_games_checker.checkers.steam import SteamChecker
from free_games_checker.models.game import Game, titles_match
from free_games_checker.utils.logging import get_logger

if TYPE_CHECKING:
    from free_games_checker.models.config import AppConfig

logger = get_logger("checkers")

DEFAULT_CHECKERS: list[type[BaseChecker]] = [
    EpicChecker,
    SteamChecker,
    GOGChecker,
    GamerPowerChecker,
]


class CheckerRegistry:
    """Manages active store checker instances and orchestrates concurrent queries."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.checkers: list[BaseChecker] = []
        self._init_checkers()

    def _init_checkers(self) -> None:
        stores = self.config.stores
        ttl = float(stores.cache_ttl_minutes * 60)
        failures = stores.circuit_breaker_failures
        cooldown = float(stores.circuit_breaker_cooldown_minutes * 60)

        self.checkers = []
        if stores.epic_enabled:
            self.checkers.append(EpicChecker(ttl, failures, cooldown))
        if stores.steam_enabled:
            self.checkers.append(SteamChecker(ttl, failures, cooldown))
        if stores.gog_enabled:
            self.checkers.append(GOGChecker(ttl, failures, cooldown))
        if stores.gamerpower_enabled:
            self.checkers.append(GamerPowerChecker(ttl, failures, cooldown))

    async def fetch_all(
        self, force_refresh: bool = False
    ) -> tuple[list[Game], dict[str, tuple[int, str | None]]]:
        """Query all enabled checkers concurrently and return deduplicated games and per-store status."""
        tasks = [checker.fetch(force_refresh=force_refresh) for checker in self.checkers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        combined_games: list[Game] = []
        store_statuses: dict[str, tuple[int, str | None]] = {}

        for checker, res in zip(self.checkers, results, strict=False):
            if isinstance(res, BaseException):
                logger.error("Checker [%s] raised unhandled exception: %s", checker.name, res)
                store_statuses[checker.name] = (0, str(res))
            else:
                store_statuses[checker.name] = (len(res), checker.last_error)
                for game in res:
                    # Deduplicate across stores using fuzzy title matching
                    existing = next(
                        (g for g in combined_games if titles_match(g.title, game.title)),
                        None,
                    )
                    if existing is None:
                        combined_games.append(game)
                    elif existing.original_price in [
                        "Free",
                        "100% off",
                    ] and game.original_price not in ["Free", "100% off"]:
                        existing.original_price = game.original_price

        return combined_games, store_statuses


__all__ = [
    "BaseChecker",
    "CheckerRegistry",
    "DEFAULT_CHECKERS",
    "EpicChecker",
    "GOGChecker",
    "GamerPowerChecker",
    "SteamChecker",
]
