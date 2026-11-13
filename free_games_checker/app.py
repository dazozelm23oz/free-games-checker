"""QApplication bootstrap and headless entrypoint."""

from __future__ import annotations

import asyncio
import sys

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from free_games_checker.checkers import CheckerRegistry
from free_games_checker.gui.main_window import MainWindow
from free_games_checker.models.config import AppConfig
from free_games_checker.services.store import ClaimStore
from free_games_checker.utils.http import close_http_client
from free_games_checker.utils.logging import get_logger, setup_logging

logger = get_logger("app")


def apply_dark_theme(app: QApplication) -> None:
    """Apply modern dark palette to QApplication."""
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(30, 31, 34))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Base, QColor(43, 45, 48))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(30, 31, 34))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Button, QColor(43, 45, 48))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.ColorRole.Link, QColor(53, 116, 240))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(53, 116, 240))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)


def run_headless(config: AppConfig, store: ClaimStore) -> int:
    """Run check without GUI, print results, and dispatch notifications."""
    print("## 🎮 Free PC Games Status Report (Headless Mode)\n")

    registry = CheckerRegistry(config)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    games, statuses = loop.run_until_complete(registry.fetch_all(force_refresh=True))

    unclaimed = [g for g in games if not store.is_claimed(g.title)]
    claimed = [g for g in games if store.is_claimed(g.title)]

    print("### 🟢 Ready to Claim (Available Now & Not Yet Claimed)\n")
    if unclaimed:
        for g in unclaimed:
            print(f"- **[{g.title}]({g.url})** (Value: {g.original_price})")
            print(f"  - **Platform:** {g.store}")
            print(f"  - **Expires:** {g.end_date or 'Limited time'}")
            print(f"  - **Direct Claim Link:** {g.url}\n")
    else:
        print("🎉 You have claimed all currently active free games!\n")

    print("### ✅ Available Now & Already Claimed\n")
    if claimed:
        for g in claimed:
            print(f"- **[{g.title}]({g.url})** ({g.store})")
        print()
    else:
        print("None of the currently active giveaways have been marked as claimed yet.\n")

    print("### 📊 Store Status Summary\n")
    for name, (count, err) in statuses.items():
        status_sym = f"⚠ Error ({err})" if err else f"✓ {count} games"
        print(f"- **{name}:** {status_sym}")

    loop.run_until_complete(close_http_client())
    loop.close()
    return 0


def main() -> int:
    """Entry point for Free Games Checker application."""
    setup_logging()
    config = AppConfig.load()
    store = ClaimStore()

    args = sys.argv[1:]
    if "--headless" in args or "--check" in args:
        return run_headless(config, store)

    if "--list-claimed" in args:
        print(f"### Claimed Games History (Tracking started: {store.tracking_started})\n")
        for g in store.get_all_claimed():
            print(f"- ✅ **{g.title}** ({g.store}) — Claimed on {g.claimed_at or 'N/A'}")
        return 0

    if "--claim" in args:
        idx = args.index("--claim")
        if idx + 1 < len(args):
            from free_games_checker.models.game import Game

            title = args[idx + 1]
            platform = "PC"
            if "--platform" in args:
                p_idx = args.index("--platform")
                if p_idx + 1 < len(args):
                    platform = args[p_idx + 1]
            game = Game(id=f"cli:{title}", title=title, store=platform, url="")
            if store.add_claimed(game):
                print(f"Marked '{title}' as claimed.")
            else:
                print(f"'{title}' is already claimed.")
            return 0

    # Start PySide6 Desktop GUI Application
    instance = QApplication.instance()
    app = instance if isinstance(instance, QApplication) else QApplication(sys.argv)
    apply_dark_theme(app)

    window = MainWindow(config=config, store=store)

    if not config.ui.start_minimized:
        window.show()

    exit_code = app.exec()

    # Graceful cleanup
    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(close_http_client())
        loop.close()
    except Exception:
        pass

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
