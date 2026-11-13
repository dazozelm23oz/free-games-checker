"""System tray integration and desktop notifications."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon, QWidget

if TYPE_CHECKING:
    from free_games_checker.models.game import Game


def create_default_tray_icon() -> QIcon:
    """Generate a clean procedural game controller icon for the system tray."""
    pix = QPixmap(32, 32)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#3574f0"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(2, 6, 28, 20, 6, 6)
    painter.setBrush(QColor("#ffffff"))
    # D-pad and buttons
    painter.drawRect(6, 14, 6, 4)
    painter.drawRect(7, 13, 4, 6)
    painter.drawEllipse(20, 13, 4, 4)
    painter.drawEllipse(23, 16, 4, 4)
    painter.end()
    return QIcon(pix)


class AppTrayIcon(QSystemTrayIcon):
    """System tray icon with right-click menu and notifications."""

    check_now_requested = Signal()
    settings_requested = Signal()
    toggle_window_requested = Signal()
    quit_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        icon = create_default_tray_icon()
        super().__init__(icon, parent)
        self.setToolTip("Free Games Checker")

        menu = QMenu()
        menu.setStyleSheet("""
            QMenu { background-color: #2b2d30; color: #ffffff; border: 1px solid #3c3f41; padding: 4px; }
            QMenu::item:selected { background-color: #3574f0; }
        """)

        self.action_toggle = QAction("Show / Hide Window", self)
        self.action_toggle.triggered.connect(self.toggle_window_requested.emit)
        menu.addAction(self.action_toggle)

        menu.addSeparator()

        self.action_check = QAction("⚡ Check Now", self)
        self.action_check.triggered.connect(self.check_now_requested.emit)
        menu.addAction(self.action_check)

        self.action_settings = QAction("⚙️ Settings", self)
        self.action_settings.triggered.connect(self.settings_requested.emit)
        menu.addAction(self.action_settings)

        menu.addSeparator()

        self.action_quit = QAction("❌ Quit", self)
        self.action_quit.triggered.connect(self.quit_requested.emit)
        menu.addAction(self.action_quit)

        self.setContextMenu(menu)
        self.activated.connect(self._on_activated)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in [
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ]:
            self.toggle_window_requested.emit()

    def notify_new_games(self, games: list[Game]) -> None:
        """Display system tray balloon notification."""
        if not games or not self.isVisible():
            return
        title = f"🎮 {len(games)} New Free Game{'s' if len(games) > 1 else ''} Found!"
        titles = ", ".join(g.title for g in games[:3])
        if len(games) > 3:
            titles += f" and {len(games) - 3} more"
        self.showMessage(title, titles, QSystemTrayIcon.MessageIcon.Information, 7000)
