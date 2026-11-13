"""Claimed games persistence and recovery store."""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from pathlib import Path

from free_games_checker.models.config import AppConfig
from free_games_checker.models.game import Game, titles_match
from free_games_checker.utils.logging import get_logger

logger = get_logger("services.store")


class ClaimStore:
    """Thread-safe persistent store for claimed games with corrupt file recovery."""

    def __init__(self, file_path: Path | str | None = None) -> None:
        if file_path:
            self.file_path = Path(file_path)
            self._allow_migration = False
        else:
            self.file_path = AppConfig.get_default_config_dir() / "claimed_games.json"
            self._allow_migration = True

        self.claimed_games: list[Game] = []
        self.tracking_started: str = datetime.now().strftime("%Y-%m-%d")
        self._load()

    def _auto_migrate_legacy(self) -> None:
        """Migrate legacy claimed_games.json if found in parent or sidecar folders."""
        if not self._allow_migration:
            return
        legacy_candidates = [
            Path.cwd() / "claimed_games.json",
            Path(__file__).resolve().parent.parent.parent / "claimed_games.json",
        ]
        for candidate in legacy_candidates:
            if candidate.exists() and candidate.resolve() != self.file_path.resolve():
                try:
                    logger.info("Migrating legacy claimed games from %s", candidate)
                    shutil.copy2(candidate, self.file_path)
                    break
                except Exception as e:
                    logger.warning("Failed legacy migration from %s: %s", candidate, e)

    def _load(self) -> None:
        if not self.file_path.exists():
            self._auto_migrate_legacy()

        if not self.file_path.exists():
            self.claimed_games = []
            self._save()
            return

        try:
            with open(self.file_path, encoding="utf-8") as f:
                data = json.load(f)
            self.tracking_started = data.get("tracking_started", self.tracking_started)
            raw_games = data.get("claimed_games", [])
            self.claimed_games = [Game.from_dict(g) for g in raw_games]
        except (json.JSONDecodeError, OSError) as err:
            logger.error("Corrupt claimed_games.json detected: %s. Backing up and resetting.", err)
            backup = self.file_path.with_suffix(f".bak.{int(datetime.now().timestamp())}")
            try:
                shutil.copy2(self.file_path, backup)
            except Exception:
                pass
            self.claimed_games = []
            self._save()

    def _save(self) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "tracking_started": self.tracking_started,
            "claimed_games": [g.to_dict() for g in self.claimed_games],
        }
        temp_file = self.file_path.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        temp_file.replace(self.file_path)

    def is_claimed(self, title: str) -> bool:
        """Check if a title matches any recorded claimed game."""
        return any(titles_match(title, g.title) for g in self.claimed_games)

    def add_claimed(self, game: Game) -> bool:
        """Mark game as claimed. Returns True if added, False if already claimed."""
        if self.is_claimed(game.title):
            return False

        today = datetime.now().strftime("%Y-%m-%d")
        claimed_game = Game(
            id=game.id,
            title=game.title,
            store=game.store,
            url=game.url,
            thumbnail=game.thumbnail,
            end_date=game.end_date,
            original_price=game.original_price,
            claimed=True,
            claimed_at=today,
            description=game.description,
        )
        self.claimed_games.append(claimed_game)
        self._save()
        logger.info("Marked '%s' as claimed.", game.title)
        return True

    def remove_claimed(self, title: str) -> bool:
        """Remove a game from claimed history."""
        orig_count = len(self.claimed_games)
        self.claimed_games = [g for g in self.claimed_games if not titles_match(title, g.title)]
        if len(self.claimed_games) < orig_count:
            self._save()
            logger.info("Removed '%s' from claimed history.", title)
            return True
        return False

    def get_all_claimed(self) -> list[Game]:
        """Return all claimed games sorted with newest first."""
        return list(reversed(self.claimed_games))

    def get_total_money_saved(self) -> float:
        """Calculate total monetary value of all claimed games."""
        total = 0.0
        for g in self.claimed_games:
            price_str = g.original_price or ""
            # Extract numerical price using regex
            match = re.search(r"(\d+(?:\.\d{1,2})?)", price_str)
            if match:
                try:
                    total += float(match.group(1))
                except ValueError:
                    continue
        return total
