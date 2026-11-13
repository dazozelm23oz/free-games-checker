"""GamerPower giveaways aggregator checker."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any, ClassVar

from free_games_checker.checkers.base import BaseChecker
from free_games_checker.models.game import Game
from free_games_checker.utils.http import fetch_json
from free_games_checker.utils.logging import get_logger

logger = get_logger("checkers.gamerpower")

GAMERPOWER_API = "https://www.gamerpower.com/api/giveaways"


def is_key_giveaway(item: dict[str, Any]) -> bool:
    """Filter out giveaways requiring external registration, keys, or social tasks."""
    title = str(item.get("title", "")).lower()
    g_type = str(item.get("type", "")).lower()
    desc = str(item.get("description", "")).lower()
    instructions = str(item.get("instructions", "")).lower()

    if re.search(r"\bkeys?\b", title) or "key" in g_type:
        return True
    key_phrases = [
        "unlock your key",
        "redeem your",
        "steam key",
        "claim a key",
        "to unlock a key",
        "game key",
        "product key",
    ]
    return any(p in desc or p in instructions for p in key_phrases)


class GamerPowerChecker(BaseChecker):
    """Aggregates verified full-game giveaways from GamerPower API."""

    name: ClassVar[str] = "GamerPower"

    def _is_expired(self, date_str: str | None) -> bool:
        if not date_str or date_str == "N/A":
            return False
        try:
            if "T" in date_str:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            else:
                dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
            return dt < datetime.now(UTC)
        except Exception:
            return False

    async def _fetch_impl(self) -> list[Game]:
        games: list[Game] = []
        platforms = ["steam", "epic-games-store", "gog"]

        for plat in platforms:
            url = f"{GAMERPOWER_API}?platform={plat}"
            data = await fetch_json(url)
            if not data or not isinstance(data, list):
                continue

            for item in data:
                if is_key_giveaway(item):
                    continue

                g_type = str(item.get("type", "")).lower()
                if g_type not in ["game", "full game"]:
                    continue

                end_date = item.get("end_date")
                if self._is_expired(end_date):
                    continue

                title = item.get("title", "Untitled Game")
                # Clean giveaway suffixes
                clean_title = re.sub(
                    r"\s*\((?:steam|epic games|gog)\)\s*giveaway.*$",
                    "",
                    title,
                    flags=re.IGNORECASE,
                ).strip()

                claim_url = (
                    item.get("open_giveaway_url")
                    or item.get("gamerpower_url")
                    or "https://www.gamerpower.com"
                )
                worth = item.get("worth", "$14.99")
                if worth == "N/A":
                    worth = "$14.99"

                games.append(
                    Game(
                        id=f"gamerpower:{item.get('id', clean_title)}",
                        title=clean_title,
                        store=item.get("platforms") or "PC",
                        url=claim_url,
                        thumbnail=item.get("image"),
                        end_date=end_date if end_date != "N/A" else None,
                        original_price=worth,
                        description=item.get("description"),
                    )
                )

        return games
