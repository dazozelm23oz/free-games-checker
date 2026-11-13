"""Epic Games Store free promotions checker."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, ClassVar

from free_games_checker.checkers.base import BaseChecker
from free_games_checker.models.game import Game
from free_games_checker.utils.http import fetch_json
from free_games_checker.utils.logging import get_logger

logger = get_logger("checkers.epic")

EPIC_PROMOTIONS_URL = (
    "https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions"
    "?locale=en-US&country=US&allowCountries=US"
)


class EpicChecker(BaseChecker):
    """Fetches currently free games directly from Epic Games Store Promotions API."""

    name: ClassVar[str] = "Epic Games"

    def _is_expired(self, date_str: str | None) -> bool:
        if not date_str:
            return False
        try:
            clean_str = date_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_str)
            return dt < datetime.now(UTC)
        except Exception:
            return False

    def _get_thumbnail(self, item: dict[str, Any]) -> str | None:
        images = item.get("keyImages", [])
        preferred_types = [
            "Thumbnail",
            "OfferImageWide",
            "DieselStoreFrontWide",
            "VaultClosed",
            "DieselStoreFrontTall",
        ]
        for p_type in preferred_types:
            for img in images:
                if img.get("type") == p_type and img.get("url"):
                    return str(img["url"])
        if images and images[0].get("url"):
            return str(images[0]["url"])
        return None

    def _get_slug(self, item: dict[str, Any]) -> str | None:
        slug = item.get("productSlug")
        if slug:
            return str(slug)
        mappings = item.get("catalogNs", {}).get("mappings", [])
        if mappings and mappings[0].get("pageSlug"):
            return str(mappings[0]["pageSlug"])
        if item.get("urlSlug"):
            return str(item["urlSlug"])
        return None

    def _get_original_price(self, item: dict[str, Any]) -> str:
        price_data = item.get("price", {}).get("totalPrice", {})
        original = price_data.get("originalPrice")
        currency = price_data.get("currencyCode", "USD")
        if original and original > 0:
            val = original / 100.0
            return f"${val:.2f}" if currency == "USD" else f"{val:.2f} {currency}"
        return "$14.99"

    async def _fetch_impl(self) -> list[Game]:
        data = await fetch_json(EPIC_PROMOTIONS_URL)
        if not data or "data" not in data:
            return []

        elements = (
            data.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", [])
        )
        games: list[Game] = []

        for item in elements:
            promotions = item.get("promotions")
            if not promotions:
                continue

            offers = promotions.get("promotionalOffers") or []
            if not offers or not offers[0].get("promotionalOffers"):
                continue

            po = offers[0]["promotionalOffers"][0]
            discount = po.get("discountSetting", {}).get("discountPercentage")
            if discount != 0:
                continue

            end_date = po.get("endDate")
            if self._is_expired(end_date):
                continue

            title = item.get("title", "Unknown Title")
            slug = self._get_slug(item)
            link = (
                f"https://store.epicgames.com/p/{slug}"
                if slug
                else "https://store.epicgames.com/free-games"
            )
            thumbnail = self._get_thumbnail(item)
            price = self._get_original_price(item)

            games.append(
                Game(
                    id=f"epic:{slug or title}",
                    title=title,
                    store="Epic Games Store",
                    url=link,
                    thumbnail=thumbnail,
                    end_date=end_date,
                    original_price=price,
                    description=item.get("description"),
                )
            )

        return games
