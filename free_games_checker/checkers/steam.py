"""Steam Store 100% off promotions checker."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import ClassVar

from free_games_checker.checkers.base import BaseChecker
from free_games_checker.models.game import Game
from free_games_checker.utils.http import fetch_json
from free_games_checker.utils.logging import get_logger

logger = get_logger("checkers.steam")

STEAM_FEATURED_URL = "https://store.steampowered.com/api/featuredcategories"


class SteamChecker(BaseChecker):
    """Scrapes Steam specials API for 100% discounted free-to-keep titles."""

    name: ClassVar[str] = "Steam"

    async def _fetch_impl(self) -> list[Game]:
        data = await fetch_json(STEAM_FEATURED_URL)
        if not data or not isinstance(data, dict):
            return []

        specials = data.get("specials", {}).get("items", [])
        games: list[Game] = []

        for item in specials:
            discount_percent = item.get("discount_percent", 0)
            orig_price = item.get("original_price", 0)
            final_price = item.get("final_price", 0)

            # Check for 100% discount or free deal with original price > 0
            if discount_percent == 100 or (final_price == 0 and orig_price > 0):
                app_id = str(item.get("id"))
                title = str(item.get("name", "Unknown Steam Game"))
                currency = item.get("currency", "USD")
                formatted_price = (
                    f"${orig_price / 100:.2f}"
                    if currency == "USD"
                    else f"{orig_price / 100:.2f} {currency}"
                )

                exp_ts = item.get("discount_expiration")
                end_date_str = None
                if exp_ts:
                    end_date_str = datetime.fromtimestamp(exp_ts, tz=UTC).isoformat()

                thumbnail = (
                    item.get("large_capsule_image")
                    or item.get("header_image")
                    or item.get("small_capsule_image")
                )

                games.append(
                    Game(
                        id=f"steam:{app_id}",
                        title=title,
                        store="Steam",
                        url=f"https://store.steampowered.com/app/{app_id}/",
                        thumbnail=thumbnail,
                        end_date=end_date_str,
                        original_price=formatted_price,
                        description=f"100% off on Steam (Save {formatted_price})",
                    )
                )

        return games
