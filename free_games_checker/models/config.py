"""Configuration models and TOML persistence."""

from __future__ import annotations

import os
from pathlib import Path

import tomlkit
from pydantic import BaseModel, Field


class SchedulerConfig(BaseModel):
    """Scheduler settings for background giveaway polling."""

    check_interval_hours: int = Field(default=6, ge=1, le=48)
    timezone: str = Field(default="Africa/Cairo")
    run_at_startup: bool = Field(default=True)


class UiConfig(BaseModel):
    """User interface preferences."""

    theme: str = Field(default="dark")  # dark, light, system
    minimize_to_tray: bool = Field(default=True)
    close_to_tray: bool = Field(default=True)
    start_minimized: bool = Field(default=False)
    first_run_completed: bool = Field(default=False)


class NotificationConfig(BaseModel):
    """Notification channels configuration."""

    desktop_enabled: bool = Field(default=True)
    discord_enabled: bool = Field(default=False)
    discord_webhook_url: str = Field(default="")
    telegram_enabled: bool = Field(default=False)
    telegram_bot_token: str = Field(default="")
    telegram_chat_id: str = Field(default="")
    email_enabled: bool = Field(default=False)
    smtp_host: str = Field(default="")
    smtp_port: int = Field(default=587)
    smtp_user: str = Field(default="")
    smtp_password: str = Field(default="")
    smtp_to_email: str = Field(default="")


class StoresConfig(BaseModel):
    """Store checker configurations."""

    epic_enabled: bool = Field(default=True)
    steam_enabled: bool = Field(default=True)
    gog_enabled: bool = Field(default=True)
    gamerpower_enabled: bool = Field(default=True)
    cache_ttl_minutes: int = Field(default=15, ge=1, le=1440)
    circuit_breaker_failures: int = Field(default=3, ge=1)
    circuit_breaker_cooldown_minutes: int = Field(default=15, ge=1)


class AppConfig(BaseModel):
    """Master application configuration."""

    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    ui: UiConfig = Field(default_factory=UiConfig)
    notifications: NotificationConfig = Field(default_factory=NotificationConfig)
    stores: StoresConfig = Field(default_factory=StoresConfig)

    @classmethod
    def get_default_config_dir(cls) -> Path:
        """Return the standard user configuration directory."""
        if os.name == "nt":
            base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        else:
            base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
        config_dir = Path(base) / "free_games_checker"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    @classmethod
    def get_default_config_path(cls) -> Path:
        """Return the default config.toml file path."""
        return cls.get_default_config_dir() / "config.toml"

    @classmethod
    def load(cls, path: Path | str | None = None) -> AppConfig:
        """Load configuration from TOML file, creating defaults if missing."""
        target_path = Path(path) if path else cls.get_default_config_path()
        if not target_path.exists():
            config = cls()
            config.save(target_path)
            return config

        try:
            with open(target_path, encoding="utf-8") as f:
                data = tomlkit.load(f)
            return cls.model_validate(data)
        except Exception:
            # Fall back to default on corrupt config
            return cls()

    def save(self, path: Path | str | None = None) -> None:
        """Persist configuration to TOML file atomically."""
        target_path = Path(path) if path else self.get_default_config_path()
        target_path.parent.mkdir(parents=True, exist_ok=True)

        data = self.model_dump(mode="python")
        doc = tomlkit.document()
        for section, section_data in data.items():
            table = tomlkit.table()
            for key, val in section_data.items():
                table.add(key, val)
            doc.add(section, table)

        temp_path = target_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            tomlkit.dump(doc, f)
        temp_path.replace(target_path)
