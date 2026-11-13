"""Tests for notification dispatchers."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from free_games_checker.models.config import NotificationConfig
from free_games_checker.models.game import Game
from free_games_checker.services.notifier import (
    DesktopNotifier,
    DiscordNotifier,
    NotificationService,
    TelegramNotifier,
)


@pytest.mark.asyncio
async def test_discord_notifier_success() -> None:
    notifier = DiscordNotifier("https://discord.com/api/webhooks/mock")
    game = Game(id="1", title="Free Test Game", store="Epic Games", url="https://example.com")

    mock_resp = MagicMock()
    mock_resp.status_code = 204

    with patch(
        "free_games_checker.services.notifier.get_http_client", new_callable=AsyncMock
    ) as mock_get_client:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_get_client.return_value = mock_client

        res = await notifier.notify([game])
        assert res is True
        mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_telegram_notifier_success() -> None:
    notifier = TelegramNotifier("bot1234", "chat5678")
    game = Game(id="1", title="Free TG Game", store="Steam", url="https://example.com")

    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch(
        "free_games_checker.services.notifier.get_http_client", new_callable=AsyncMock
    ) as mock_get_client:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_get_client.return_value = mock_client

        res = await notifier.notify([game])
        assert res is True
        mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_desktop_notifier_success() -> None:
    notifier = DesktopNotifier()
    game = Game(id="1", title="Desktop Test Game", store="GOG", url="https://example.com")

    with patch("subprocess.run") as mock_sub:
        res = await notifier.notify([game])
        assert res is True
        mock_sub.assert_called_once()


@pytest.mark.asyncio
async def test_notification_service_coordination() -> None:
    cfg = NotificationConfig(
        desktop_enabled=True,
        discord_enabled=True,
        discord_webhook_url="https://discord.com/mock",
    )
    service = NotificationService(cfg)
    game = Game(id="1", title="Multi Channel Game", store="Epic", url="https://example.com")

    with patch.object(DiscordNotifier, "notify", new_callable=AsyncMock) as mock_discord:
        mock_discord.return_value = True
        results = await service.dispatch([game])
        assert results.get("Discord") is True
