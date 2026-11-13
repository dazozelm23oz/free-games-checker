"""GOG.com giveaway and free promotion checker."""

from __future__ import annotations

import re
from typing import ClassVar

from free_games_checker.checkers.base import BaseChecker
from free_games_checker.models.game import Game
from free_games_checker.utils.http import fetch_json, get_http_client
from free_games_checker.utils.logging import get_logger

logger = get_logger("checkers.gog")

GOG_GP_URL = "https://www.gamerpower.com/api/giveaways?platform=gog"
GOG_HOME_URL = "https://www.gog.com/"


class GOGChecker(BaseChecker):
    """Scrapes GOG frontpage giveaway promotions and verified GOG giveaways."""

    name: ClassVar[str] = "GOG"

    async def _fetch_impl(self) -> list[Game]:
        games: list[Game] = []

        # 1. Check GamerPower verified GOG platform giveaways
        data = await fetch_json(GOG_GP_URL)
        if data and isinstance(data, list):
            for item in data:
                g_type = str(item.get("type", "")).lower()
                if g_type not in ["game", "full game"]:
                    continue

                title = str(item.get("title", ""))
                clean_title = re.sub(
                    r"\s*\(gog\)\s*giveaway.*$", "", title, flags=re.IGNORECASE
                ).strip()

                games.append(
                    Game(
                        id=f"gog:{item.get('id', clean_title)}",
                        title=clean_title,
                        store="GOG",
                        url=item.get("open_giveaway_url") or "https://www.gog.com",
                        thumbnail=item.get("image"),
                        end_date=item.get("end_date") if item.get("end_date") != "N/A" else None,
                        original_price=item.get("worth", "$9.99"),
                        description=item.get("description"),
                    )
                )

        # 2. Check GOG homepage for active banner giveaways if not found yet
        if not games:
            try:
                client = await get_http_client()
                resp = await client.get(GOG_HOME_URL, timeout=10.0)
                if resp.status_code == 200:
                    text = resp.text
                    # Search for giveaway banner title or claim link
                    banner_match = re.search(
                        r'giveaway[^\n]{0,200}?"title"\s*:\s*"([^"]+)"',
                        text,
                        re.IGNORECASE,
                    )
                    if banner_match:
                        title = banner_match.group(1).strip()
                        games.append(
                            Game(
                                id=f"gog:{title.lower()}",
                                title=title,
                                store="GOG",
                                url="https://www.gog.com/#giveaway",
                                original_price="Free",
                                description="Active frontpage giveaway on GOG.com",
                            )
                        )
            except Exception as e:
                logger.debug("GOG homepage probe failed: %s", e)

        return games
