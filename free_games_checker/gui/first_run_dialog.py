"""First run onboarding setup wizard."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from free_games_checker.models.config import AppConfig


class FirstRunDialog(QDialog):
    """First-run wizard prompting for initial preferences."""

    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Welcome to Free Games Checker!")
        self.resize(480, 360)
        self.setStyleSheet("""
            QDialog { background-color: #1e1f22; color: #ffffff; }
            QLabel { color: #d1d5db; }
            QLineEdit, QComboBox { background-color: #2b2d30; color: #ffffff; border: 1px solid #3c3f41; padding: 6px; border-radius: 4px; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        # Welcome Header
        header = QLabel("🎮 Welcome to Free Games Checker")
        header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        header.setStyleSheet("color: #3574f0;")
        layout.addWidget(header)

        sub = QLabel(
            "Track 100% free PC games from Epic Games, Steam, GOG, and giveaways.\n"
            "Let's configure your basic preferences before getting started."
        )
        sub.setWordWrap(True)
        layout.addWidget(sub)

        # Form
        form = QFormLayout()

        self.tz_combo = QComboBox()
        self.tz_combo.setEditable(True)
        self.tz_combo.addItems(
            [
                "Africa/Cairo",
                "UTC",
                "Europe/London",
                "Europe/Berlin",
                "America/New_York",
                "America/Los_Angeles",
                "Asia/Tokyo",
            ]
        )
        self.tz_combo.setCurrentText(self.config.scheduler.timezone)
        form.addRow("Your Timezone:", self.tz_combo)

        self.desktop_cb = QCheckBox("Enable Desktop Notifications on new giveaways")
        self.desktop_cb.setChecked(True)
        form.addRow("", self.desktop_cb)

        self.discord_edit = QLineEdit()
        self.discord_edit.setPlaceholderText("Optional Discord webhook URL")
        form.addRow("Discord Webhook:", self.discord_edit)

        layout.addLayout(form)
        layout.addStretch(1)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self.finish_btn = QPushButton("Get Started 🚀")
        self.finish_btn.setStyleSheet(
            "background-color: #3574f0; color: white; font-weight: bold; padding: 8px 18px; border-radius: 4px;"
        )
        self.finish_btn.clicked.connect(self._finish)
        btn_row.addWidget(self.finish_btn)

        layout.addLayout(btn_row)

    def _finish(self) -> None:
        self.config.scheduler.timezone = self.tz_combo.currentText().strip()
        self.config.notifications.desktop_enabled = self.desktop_cb.isChecked()
        url = self.discord_edit.text().strip()
        if url:
            self.config.notifications.discord_enabled = True
            self.config.notifications.discord_webhook_url = url
        self.config.ui.first_run_completed = True
        self.config.save()
        self.accept()
