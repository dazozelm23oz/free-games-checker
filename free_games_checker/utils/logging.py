"""Structured rotating file and console logging."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from free_games_checker.models.config import AppConfig

_INITIALIZED = False


def get_logs_dir() -> Path:
    """Return user application logs directory."""
    logs_dir = AppConfig.get_default_config_dir() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def setup_logging(log_level: int = logging.INFO) -> None:
    """Initialize root logger with console and rotating file handlers."""
    global _INITIALIZED
    if _INITIALIZED:
        return

    logs_dir = get_logs_dir()
    log_file = logs_dir / "app.log"

    root_logger = logging.getLogger("free_games_checker")
    root_logger.setLevel(log_level)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] (%(name)s:%(funcName)s:%(lineno)d) - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Rotating file handler (5MB per file, keeping 5 backups)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    _INITIALIZED = True


def get_logger(name: str) -> logging.Logger:
    """Get a namespaced logger instance."""
    setup_logging()
    return logging.getLogger(f"free_games_checker.{name}")
