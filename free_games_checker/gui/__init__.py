"""GUI package."""

from free_games_checker.gui.details_dialog import GameDetailsDialog
from free_games_checker.gui.first_run_dialog import FirstRunDialog
from free_games_checker.gui.main_window import MainWindow
from free_games_checker.gui.settings_dialog import SettingsDialog
from free_games_checker.gui.tray_icon import AppTrayIcon, create_default_tray_icon
from free_games_checker.gui.widgets import (
    GameCardWidget,
    SearchBar,
    SortDropdown,
    StoreFilterBar,
)

__all__ = [
    "AppTrayIcon",
    "FirstRunDialog",
    "GameCardWidget",
    "GameDetailsDialog",
    "MainWindow",
    "SearchBar",
    "SettingsDialog",
    "SortDropdown",
    "StoreFilterBar",
    "create_default_tray_icon",
]
