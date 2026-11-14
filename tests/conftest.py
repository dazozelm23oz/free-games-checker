"""Pytest test fixtures and configuration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from PySide6.QtWidgets import QApplication

from free_games_checker.models.config import AppConfig
from free_games_checker.services.store import ClaimStore

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """Fixture providing a QApplication instance for GUI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def tmp_config_dir(tmp_path: Path) -> Path:
    """Temporary configuration directory."""
    conf_dir = tmp_path / "free_games_checker"
    conf_dir.mkdir(parents=True, exist_ok=True)
    return conf_dir


@pytest.fixture
def test_config(tmp_config_dir: Path) -> AppConfig:
    """Isolated AppConfig instance pointing to temporary directory."""
    cfg = AppConfig()
    cfg.save(tmp_config_dir / "config.toml")
    return cfg


@pytest.fixture
def test_store(tmp_config_dir: Path) -> ClaimStore:
    """Isolated ClaimStore pointing to temporary directory."""
    return ClaimStore(file_path=tmp_config_dir / "claimed_games.json")


@pytest.fixture
def epic_fixture() -> dict[str, Any]:
    with open(FIXTURES_DIR / "epic_response.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def steam_fixture() -> dict[str, Any]:
    with open(FIXTURES_DIR / "steam_response.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def gamerpower_fixture() -> list[dict[str, Any]]:
    with open(FIXTURES_DIR / "gamerpower_response.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def gog_fixture() -> list[dict[str, Any]]:
    with open(FIXTURES_DIR / "gog_response.json", encoding="utf-8") as f:
        return json.load(f)
