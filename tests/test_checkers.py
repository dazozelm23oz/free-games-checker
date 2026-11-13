"""Unit tests for store checkers and circuit breaker."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from free_games_checker.checkers import (
    CheckerRegistry,
    EpicChecker,
    GamerPowerChecker,
    SteamChecker,
)
from free_games_checker.checkers.base import CircuitBreaker
from free_games_checker.models.config import AppConfig


def test_circuit_breaker_lifecycle() -> None:
    breaker = CircuitBreaker(failure_threshold=2, cooldown_seconds=0.1)
    assert breaker.state == "CLOSED"
    assert breaker.can_execute() is True

    # 1 failure
    breaker.record_failure()
    assert breaker.state == "CLOSED"
    assert breaker.can_execute() is True

    # 2 failures -> trips to OPEN
    breaker.record_failure()
    assert breaker.state == "OPEN"
    assert breaker.can_execute() is False

    # Simulate cooldown
    import time

    time.sleep(0.12)
    assert breaker.can_execute() is True
    assert breaker.state == "HALF_OPEN"

    # Success resets to CLOSED
    breaker.record_success()
    assert breaker.state == "CLOSED"
    assert breaker.failure_count == 0


@pytest.mark.asyncio
async def test_epic_checker_parsing(epic_fixture: dict[str, Any]) -> None:
    checker = EpicChecker()
    with patch("free_games_checker.checkers.epic.fetch_json", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = epic_fixture
        games = await checker.fetch(force_refresh=True)

        assert len(games) == 1
        g = games[0]
        assert g.title == "Mock Epic Free Game"
        assert g.store == "Epic Games Store"
        assert g.original_price == "$29.99"
        assert "mock-epic-free-game" in g.url
        assert g.thumbnail == "https://cdn.example.com/mock.jpg"


@pytest.mark.asyncio
async def test_steam_checker_parsing(steam_fixture: dict[str, Any]) -> None:
    checker = SteamChecker()
    with patch(
        "free_games_checker.checkers.steam.fetch_json", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = steam_fixture
        games = await checker.fetch(force_refresh=True)

        assert len(games) == 1
        g = games[0]
        assert g.title == "Mock Steam Free Deal"
        assert g.store == "Steam"
        assert g.original_price == "$19.99"
        assert "123456" in g.url


@pytest.mark.asyncio
async def test_gamerpower_checker_filtering(gamerpower_fixture: list[dict[str, Any]]) -> None:
    checker = GamerPowerChecker()
    with patch(
        "free_games_checker.checkers.gamerpower.fetch_json", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = gamerpower_fixture
        games = await checker.fetch(force_refresh=True)

        # Out of 3 items: 1 full game, 1 key/playtest (filtered), 1 dlc (filtered)
        # Because GamerPower checker iterates 3 platforms in mock, each platform returns 1 match
        assert len(games) >= 1
        titles = [g.title for g in games]
        assert "Mock Full Giveaway Game" in titles[0]
        assert not any("DLC" in t for t in titles)
        assert not any("Key" in t for t in titles)


@pytest.mark.asyncio
async def test_checker_registry_orchestration(
    test_config: AppConfig, epic_fixture: dict[str, Any]
) -> None:
    registry = CheckerRegistry(test_config)
    with (
        patch("free_games_checker.checkers.epic.fetch_json", new_callable=AsyncMock) as mock_epic,
        patch("free_games_checker.checkers.steam.fetch_json", new_callable=AsyncMock) as mock_steam,
        patch(
            "free_games_checker.checkers.gamerpower.fetch_json", new_callable=AsyncMock
        ) as mock_gp,
        patch("free_games_checker.checkers.gog.fetch_json", new_callable=AsyncMock) as mock_gog,
    ):
        mock_epic.return_value = epic_fixture
        mock_steam.return_value = {"specials": {"items": []}}
        mock_gp.return_value = []
        mock_gog.return_value = []

        games, statuses = await registry.fetch_all(force_refresh=True)
        assert len(games) == 1
        assert "Epic Games" in statuses
        assert statuses["Epic Games"][0] == 1
