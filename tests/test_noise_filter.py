"""Tests for noise filtering, key giveaways, and title normalization."""

from free_games_checker.checkers.gamerpower import is_key_giveaway
from free_games_checker.models.game import normalize_title, titles_match


def test_is_key_giveaway_detection() -> None:
    # Keys in title
    assert is_key_giveaway({"title": "Free Steam Key Giveaway"}) is True
    assert is_key_giveaway({"type": "Steam Key"}) is True

    # Keys in instructions or description
    assert (
        is_key_giveaway({"title": "Game Name", "instructions": "To unlock a key, do XYZ"}) is True
    )
    assert (
        is_key_giveaway({"title": "Game Name", "description": "Redeem your product key now"})
        is True
    )

    # Legitimate direct game offer
    assert (
        is_key_giveaway(
            {
                "title": "Knightica",
                "type": "Game",
                "description": "Direct store giveaway on Epic",
                "instructions": "Click Claim on Epic Games Store",
            }
        )
        is False
    )


def test_normalize_title() -> None:
    assert normalize_title("Sker Ritual (Steam) Giveaway") == "skerritual"
    assert normalize_title("Home: Definitive Edition (Epic Games) Giveaway") == "home"
    assert (
        normalize_title("Idle Champions of the Forgotten Realms!")
        == "idlechampionsoftheforgottenrealms"
    )


def test_titles_match() -> None:
    assert titles_match("Sker Ritual", "Sker Ritual (Epic Games) Giveaway") is True
    assert titles_match("Knightica", "Knightica") is True
    assert titles_match("Doom Eternal: Deluxe Edition", "Doom Eternal") is True
    assert titles_match("Random Game A", "Totally Different Game B") is False
