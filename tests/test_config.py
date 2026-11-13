"""Tests for configuration parsing and TOML persistence."""

from pathlib import Path

from free_games_checker.models.config import AppConfig


def test_default_config() -> None:
    config = AppConfig()
    assert config.scheduler.check_interval_hours == 6
    assert config.scheduler.timezone == "Africa/Cairo"
    assert config.stores.epic_enabled is True
    assert config.stores.steam_enabled is True
    assert config.notifications.desktop_enabled is True
    assert config.notifications.discord_enabled is False


def test_config_roundtrip(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    cfg = AppConfig()
    cfg.scheduler.check_interval_hours = 12
    cfg.scheduler.timezone = "Europe/Berlin"
    cfg.notifications.discord_enabled = True
    cfg.notifications.discord_webhook_url = "https://discord.com/api/webhooks/123/xyz"
    cfg.save(config_file)

    loaded = AppConfig.load(config_file)
    assert loaded.scheduler.check_interval_hours == 12
    assert loaded.scheduler.timezone == "Europe/Berlin"
    assert loaded.notifications.discord_enabled is True
    assert loaded.notifications.discord_webhook_url == "https://discord.com/api/webhooks/123/xyz"


def test_corrupt_config_fallback(tmp_path: Path) -> None:
    config_file = tmp_path / "corrupt_config.toml"
    with open(config_file, "w") as f:
        f.write("corrupted [[[ toml syntax")

    loaded = AppConfig.load(config_file)
    assert loaded.scheduler.check_interval_hours == 6
