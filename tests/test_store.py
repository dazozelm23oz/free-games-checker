"""Tests for persistent claim store and recovery."""

from pathlib import Path

import pytest

from free_games_checker.models.game import Game
from free_games_checker.services.store import ClaimStore


def test_claim_store_add_and_check(tmp_path: Path) -> None:
    store_file = tmp_path / "claimed.json"
    store = ClaimStore(store_file)

    game = Game(
        id="test:1",
        title="Super Game 3D",
        store="Epic Games Store",
        url="https://example.com/game",
        original_price="$19.99",
    )

    assert store.is_claimed("Super Game 3D") is False
    assert store.add_claimed(game) is True
    assert store.is_claimed("Super Game 3D") is True
    assert store.is_claimed("super game 3d (epic games) giveaway") is True

    # Re-adding returns False
    assert store.add_claimed(game) is False
    assert len(store.get_all_claimed()) == 1


def test_claim_store_remove(tmp_path: Path) -> None:
    store_file = tmp_path / "claimed.json"
    store = ClaimStore(store_file)

    game = Game(
        id="test:2", title="Removal Test Game", store="Steam", url="", original_price="$9.99"
    )
    store.add_claimed(game)
    assert store.is_claimed("Removal Test Game") is True

    assert store.remove_claimed("Removal Test Game") is True
    assert store.is_claimed("Removal Test Game") is False
    assert store.remove_claimed("Non Existent Game") is False


def test_total_money_saved(tmp_path: Path) -> None:
    store_file = tmp_path / "claimed.json"
    store = ClaimStore(store_file)

    g1 = Game(id="1", title="Game 1", store="Epic", url="", original_price="$14.99")
    g2 = Game(id="2", title="Game 2", store="Steam", url="", original_price="$29.50")
    g3 = Game(id="3", title="Game 3", store="GOG", url="", original_price="Free")

    store.add_claimed(g1)
    store.add_claimed(g2)
    store.add_claimed(g3)

    assert store.get_total_money_saved() == 44.49


def test_corrupt_file_recovery(tmp_path: Path) -> None:
    store_file = tmp_path / "claimed_corrupt.json"
    with open(store_file, "w") as f:
        f.write("{ invalid json corrupted content !!")

    store = ClaimStore(store_file)
    assert len(store.get_all_claimed()) == 0

    # Verify backup was created
    backups = list(tmp_path.glob("claimed_corrupt.bak.*"))
    assert len(backups) == 1


def test_claim_store_legacy_migration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_dir = tmp_path / "user_config"
    config_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        "free_games_checker.models.config.AppConfig.get_default_config_dir",
        classmethod(lambda cls: config_dir),
    )

    work_dir = tmp_path / "work"
    work_dir.mkdir(parents=True, exist_ok=True)
    legacy_file = work_dir / "claimed_games.json"
    legacy_file.write_text(
        "{\n"
        '  "tracking_started": "2024-01-01",\n'
        '  "claimed_games": [\n'
        "    {\n"
        '      "id": "legacy:1",\n'
        '      "title": "Legacy Migrated Game",\n'
        '      "store": "Epic Games",\n'
        '      "url": "https://epicgames.com",\n'
        '      "original_price": "$19.99"\n'
        "    }\n"
        "  ]\n"
        "}\n"
    )
    monkeypatch.chdir(work_dir)

    store = ClaimStore()
    target_path = config_dir / "claimed_games.json"
    assert store.file_path == target_path
    assert target_path.exists()
    assert store.is_claimed("Legacy Migrated Game") is True
    assert len(store.get_all_claimed()) == 1
