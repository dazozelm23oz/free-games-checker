"""GUI smoke tests using pytest-qt in headless offscreen mode."""

from pathlib import Path
from unittest.mock import patch

from pytestqt.qtbot import QtBot

from free_games_checker.gui.main_window import MainWindow
from free_games_checker.gui.settings_dialog import SettingsDialog
from free_games_checker.gui.widgets import GameCardWidget, SearchBar, StoreFilterBar
from free_games_checker.models.config import AppConfig
from free_games_checker.models.game import Game
from free_games_checker.services.store import ClaimStore


def test_game_card_widget(qtbot: QtBot) -> None:
    game = Game(
        id="card_test:1",
        title="Card Test Title",
        store="Epic Games Store",
        url="https://example.com/card",
        original_price="$14.99",
    )
    widget = GameCardWidget(game)
    qtbot.addWidget(widget)

    assert widget.title_label.text() == "Card Test Title"
    assert widget.store_badge.text() == "Epic Games Store"
    assert "$14.99" in widget.price_label.text()

    # Test mark claimed signal
    with qtbot.waitSignal(widget.mark_claimed_requested, timeout=1000):
        widget.mark_btn.click()


def test_store_filter_bar(qtbot: QtBot) -> None:
    bar = StoreFilterBar()
    qtbot.addWidget(bar)

    with qtbot.waitSignal(bar.filter_changed, timeout=1000) as blocker:
        # Click the Steam filter button (index 2)
        btn = bar.btn_group.button(2)
        assert btn is not None
        btn.click()
    assert blocker.args == ["Steam"]


def test_search_bar(qtbot: QtBot) -> None:
    bar = SearchBar()
    qtbot.addWidget(bar)

    with qtbot.waitSignal(bar.search_changed, timeout=1500) as blocker:
        bar.setText("witcher")
    assert blocker.args == ["witcher"]


def test_settings_dialog_saves(tmp_path: Path, qtbot: QtBot) -> None:
    conf_file = tmp_path / "config.toml"
    cfg = AppConfig()
    cfg.save(conf_file)

    dlg = SettingsDialog(cfg)
    qtbot.addWidget(dlg)

    dlg.interval_spin.setValue(18)
    dlg.tz_combo.setCurrentText("Europe/London")
    dlg.epic_cb.setChecked(False)
    dlg.save_btn.click()

    assert cfg.scheduler.check_interval_hours == 18
    assert cfg.scheduler.timezone == "Europe/London"
    assert cfg.stores.epic_enabled is False


def test_main_window_renders_cards(tmp_path: Path, qtbot: QtBot) -> None:
    cfg = AppConfig()
    cfg.ui.first_run_completed = True
    store = ClaimStore(tmp_path / "claimed.json")

    with patch.object(MainWindow, "check_now"):
        win = MainWindow(config=cfg, store=store)
        qtbot.addWidget(win)

        mock_game = Game(
            id="win:1",
            title="Window Rendered Game",
            store="Epic Games Store",
            url="https://example.com",
            original_price="$19.99",
        )
        win._on_check_finished([mock_game], {"Epic Games": (1, None)})

        # Check Available tab text
        assert "Available Now (1)" in win.tabs.tabText(0)

        # Mark as claimed
        win._on_game_claimed(mock_game)
        assert "Available Now (0)" in win.tabs.tabText(0)
        assert "Claimed History (1)" in win.tabs.tabText(1)
        assert store.is_claimed("Window Rendered Game") is True

        win.scheduler.stop()
        win.tray.hide()


def test_game_details_dialog(qtbot: QtBot) -> None:
    from free_games_checker.gui.details_dialog import GameDetailsDialog

    game = Game(
        id="details:1",
        title="Details Dialog Game",
        store="Epic Games Store",
        url="https://example.com/details",
        original_price="$19.99",
        description="A fun test adventure.",
    )
    dlg = GameDetailsDialog(game)
    qtbot.addWidget(dlg)

    assert dlg.title_lbl.text() == "Details Dialog Game"
    assert "$19.99" in dlg.val_lbl.text()

    with qtbot.waitSignal(dlg.claim_confirmed, timeout=1000) as blocker:
        dlg.mark_btn.click()
    assert blocker.args[0].title == "Details Dialog Game"


def test_first_run_dialog(qtbot: QtBot) -> None:
    from free_games_checker.gui.first_run_dialog import FirstRunDialog

    cfg = AppConfig()
    dlg = FirstRunDialog(cfg)
    qtbot.addWidget(dlg)

    dlg.tz_combo.setCurrentText("America/New_York")
    dlg.discord_edit.setText("https://discord.com/api/webhooks/test")
    dlg.finish_btn.click()

    assert cfg.ui.first_run_completed is True
    assert cfg.scheduler.timezone == "America/New_York"
    assert cfg.notifications.discord_enabled is True
    assert cfg.notifications.discord_webhook_url == "https://discord.com/api/webhooks/test"


def test_main_window_export_csv(tmp_path: Path, qtbot: QtBot) -> None:
    cfg = AppConfig()
    cfg.ui.first_run_completed = True
    store = ClaimStore(tmp_path / "claimed.json")

    with patch.object(MainWindow, "check_now"):
        win = MainWindow(config=cfg, store=store)
        qtbot.addWidget(win)

        mock_game = Game(
            id="export:1",
            title="Exported Game Title",
            store="Steam",
            url="https://example.com/export",
            original_price="$29.99",
        )
        win.active_games = [mock_game]

        export_file = tmp_path / "exported.csv"
        with patch(
            "PySide6.QtWidgets.QFileDialog.getSaveFileName",
            return_value=(str(export_file), "CSV Files (*.csv)"),
        ):
            with patch("PySide6.QtWidgets.QMessageBox.information"):
                win._on_export_clicked()

        assert export_file.exists()
        content = export_file.read_text(encoding="utf-8")
        assert "Exported Game Title" in content
        assert "Steam" in content
        assert "$29.99" in content

        win.scheduler.stop()
        win.tray.hide()


def test_game_details_dialog(qtbot: QtBot) -> None:
    from free_games_checker.gui.details_dialog import GameDetailsDialog

    game = Game(
        id="details:1",
        title="Details Dialog Game",
        store="Epic Games Store",
        url="https://example.com/details",
        original_price="$19.99",
        description="A fun test adventure.",
    )
    dlg = GameDetailsDialog(game)
    qtbot.addWidget(dlg)

    assert dlg.title_lbl.text() == "Details Dialog Game"
    assert "$19.99" in dlg.val_lbl.text()

    with qtbot.waitSignal(dlg.claim_confirmed, timeout=1000) as blocker:
        dlg.mark_btn.click()
    assert blocker.args[0].title == "Details Dialog Game"
