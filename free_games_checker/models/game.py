"""Data models for games, stores, and deal metadata."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from rapidfuzz import fuzz


def normalize_title(title: str) -> str:
    """Normalize game titles by removing noise words, edition suffixes, and punctuation."""
    if not title:
        return ""
    t = title.lower()
    noise_patterns = [
        r"\(epic games\) giveaway",
        r"\(steam\) giveaway",
        r"\(gog\) giveaway",
        r"giveaway",
        r"playtest",
        r"standard edition",
        r"digital edition",
        r"enhanced edition",
        r"definitive edition",
        r"anniversary edition",
        r"game of the year edition",
        r"goty",
    ]
    for pattern in noise_patterns:
        t = re.sub(pattern, "", t, flags=re.IGNORECASE)
    # Remove non-alphanumeric characters except spaces
    cleaned = re.sub(r"[^a-z0-9]", "", t)
    return cleaned.strip()


def titles_match(t1: str, t2: str, threshold: float = 85.0) -> bool:
    """Fuzzy title matching across stores with prefix matching and rapidfuzz fallback."""
    n1 = normalize_title(t1)
    n2 = normalize_title(t2)
    if not n1 or not n2:
        return False
    if n1 == n2:
        return True
    if (n1.startswith(n2) or n2.startswith(n1)) and min(len(n1), len(n2)) >= 4:
        return True
    return fuzz.token_sort_ratio(n1, n2) >= threshold


@dataclass(slots=True)
class Game:
    """Represents a free game offer from a supported gaming store."""

    id: str
    title: str
    store: str  # Epic Games Store, Steam, GOG, etc.
    url: str
    thumbnail: str | None = None
    end_date: str | None = None  # ISO format string or human date
    original_price: str = "Free"
    claimed: bool = False
    claimed_at: str | None = None
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert game model to dictionary representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Game:
        """Create game instance from dictionary with backward compatibility."""
        return cls(
            id=data.get("id") or str(hash(f"{data.get('title')}:{data.get('store')}")),
            title=data.get("title", "Untitled Game"),
            store=data.get("store") or data.get("platform", "Unknown Store"),
            url=data.get("url", ""),
            thumbnail=data.get("thumbnail"),
            end_date=data.get("end_date"),
            original_price=data.get("original_price") or data.get("worth", "Free"),
            claimed=bool(data.get("claimed", False)),
            claimed_at=data.get("claimed_at"),
            description=data.get("description"),
        )
