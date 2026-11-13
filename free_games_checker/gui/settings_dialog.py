"""Settings dialog for configuring schedules, stores, and notifications."""

from __future__ import annotations

import asyncio
import os
import subprocess
from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from free_games_checker.models.config import AppConfig
from free_games_checker.models.game import Game
from free_games_checker.services.notifier import DiscordNotifier
from free_games_checker.utils.logging import get_logs_dir

if TYPE_CHECKING:
    pass


class SettingsDialog(QDialog):
    """Configuration management dialog."""

    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Settings - Free Games Checker")
        self.resize(550, 480)
        self.setStyleSheet("""
            QDialog { background-color: #1e1f22; color: #ffffff; }
            QLabel { color: #d1d5db; }
            QGroupBox { color: #ffffff; font-weight: bold; border: 1px solid #3c3f41; border-radius: 6px; margin-top: 10px; padding-top: 15px; }
            QLineEdit, QSpinBox, QComboBox { background-color: #2b2d30; color: #ffffff; border: 1px solid #3c3f41; padding: 4px 8px; border-radius: 4px; }
            QTabWidget::pane { border: 1px solid #3c3f41; background: #2b2d30; }
            QTabBar::tab { background: #1e1f22; color: #a9b7c6; padding: 8px 16px; border: 1px solid #3c3f41; }
            QTabBar::tab:selected { background: #2b2d30; color: #ffffff; border-bottom: 2px solid #3574f0; }
        """)

        layout = QVBoxLayout(self)

        tabs = QTabWidget()
        tabs.addTab(self._create_general_tab(), "General")
        tabs.addTab(self._create_stores_tab(), "Stores")
        tabs.addTab(self._create_notifications_tab(), "Notifications")
        layout.addWidget(tabs)

        # Bottom buttons
        bottom_row = QHBoxLayout()
        self.logs_btn = QPushButton("📁 Open Logs")
        self.logs_btn.clicked.connect(self._open_logs_folder)
        bottom_row.addWidget(self.logs_btn)

        self.config_btn = QPushButton("📄 Open Config Folder")
        self.config_btn.clicked.connect(self._open_config_folder)
        bottom_row.addWidget(self.config_btn)

        bottom_row.addStretch(1)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        bottom_row.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setStyleSheet(
            "background-color: #3574f0; color: white; font-weight: bold; padding: 6px 14px; border-radius: 4px;"
        )
        self.save_btn.clicked.connect(self._save_settings)
        bottom_row.addWidget(self.save_btn)

        layout.addLayout(bottom_row)

    def _create_general_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Scheduler Group
        sched_group = QGroupBox("Check Frequency & Schedule")
        sched_form = QFormLayout(sched_group)

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 48)
        self.interval_spin.setValue(self.config.scheduler.check_interval_hours)
        self.interval_spin.setSuffix(" hours")
        sched_form.addRow("Check Interval:", self.interval_spin)

        self.tz_combo = QComboBox()
        self.tz_combo.setEditable(True)
        common_timezones = [
            "Africa/Cairo",
            "UTC",
            "Europe/London",
            "Europe/Berlin",
            "America/New_York",
            "America/Los_Angeles",
            "Asia/Tokyo",
            "Asia/Dubai",
        ]
        if self.config.scheduler.timezone not in common_timezones:
            common_timezones.insert(0, self.config.scheduler.timezone)
        self.tz_combo.addItems(common_timezones)
        self.tz_combo.setCurrentText(self.config.scheduler.timezone)
        sched_form.addRow("Timezone:", self.tz_combo)

        layout.addWidget(sched_group)

        # Behavior Group
        beh_group = QGroupBox("Window & Tray Behavior")
        beh_layout = QVBoxLayout(beh_group)

        self.close_to_tray_cb = QCheckBox("Minimize to system tray when closing window")
        self.close_to_tray_cb.setChecked(self.config.ui.close_to_tray)
        beh_layout.addWidget(self.close_to_tray_cb)

        self.start_minimized_cb = QCheckBox("Start minimized in system tray")
        self.start_minimized_cb.setChecked(self.config.ui.start_minimized)
        beh_layout.addWidget(self.start_minimized_cb)

        layout.addWidget(beh_group)
        layout.addStretch(1)
        return widget

    def _create_stores_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        store_group = QGroupBox("Active Store Checkers")
        store_layout = QVBoxLayout(store_group)

        self.epic_cb = QCheckBox("Epic Games Store")
        self.epic_cb.setChecked(self.config.stores.epic_enabled)
        store_layout.addWidget(self.epic_cb)

        self.steam_cb = QCheckBox("Steam Store")
        self.steam_cb.setChecked(self.config.stores.steam_enabled)
        store_layout.addWidget(self.steam_cb)

        self.gog_cb = QCheckBox("GOG.com")
        self.gog_cb.setChecked(self.config.stores.gog_enabled)
        store_layout.addWidget(self.gog_cb)

        self.gp_cb = QCheckBox("GamerPower Aggregator (Steam / Epic / GOG giveaways)")
        self.gp_cb.setChecked(self.config.stores.gamerpower_enabled)
        store_layout.addWidget(self.gp_cb)

        layout.addWidget(store_group)

        cache_group = QGroupBox("Caching & Performance")
        cache_form = QFormLayout(cache_group)

        self.cache_ttl_spin = QSpinBox()
        self.cache_ttl_spin.setRange(1, 1440)
        self.cache_ttl_spin.setValue(self.config.stores.cache_ttl_minutes)
        self.cache_ttl_spin.setSuffix(" minutes")
        cache_form.addRow("Store Cache TTL:", self.cache_ttl_spin)

        layout.addWidget(cache_group)
        layout.addStretch(1)
        return widget

    def _create_notifications_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.desktop_cb = QCheckBox("Enable Desktop Notifications")
        self.desktop_cb.setChecked(self.config.notifications.desktop_enabled)
        layout.addWidget(self.desktop_cb)

        # Discord Group
        discord_group = QGroupBox("Discord Webhook")
        discord_layout = QVBoxLayout(discord_group)

        self.discord_cb = QCheckBox("Enable Discord Notifications")
        self.discord_cb.setChecked(self.config.notifications.discord_enabled)
        discord_layout.addWidget(self.discord_cb)

        url_row = QHBoxLayout()
        self.discord_url_edit = QLineEdit(self.config.notifications.discord_webhook_url)
        self.discord_url_edit.setPlaceholderText("https://discord.com/api/webhooks/...")
        url_row.addWidget(self.discord_url_edit)

        self.test_discord_btn = QPushButton("Test")
        self.test_discord_btn.clicked.connect(self._test_discord_webhook)
        url_row.addWidget(self.test_discord_btn)
        discord_layout.addLayout(url_row)
        layout.addWidget(discord_group)

        # Telegram Group
        tg_group = QGroupBox("Telegram Bot")
        tg_form = QFormLayout(tg_group)

        self.tg_cb = QCheckBox("Enable Telegram Notifications")
        self.tg_cb.setChecked(self.config.notifications.telegram_enabled)
        tg_form.addRow("", self.tg_cb)

        self.tg_token_edit = QLineEdit(self.config.notifications.telegram_bot_token)
        self.tg_token_edit.setPlaceholderText("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
        tg_form.addRow("Bot Token:", self.tg_token_edit)

        self.tg_chat_edit = QLineEdit(self.config.notifications.telegram_chat_id)
        self.tg_chat_edit.setPlaceholderText("Chat or Channel ID")
        tg_form.addRow("Chat ID:", self.tg_chat_edit)
        layout.addWidget(tg_group)

        layout.addStretch(1)
        return widget

    def _test_discord_webhook(self) -> None:
        url = self.discord_url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "Missing URL", "Please enter a valid Discord webhook URL.")
            return

        test_game = Game(
            id="test:1",
            title="Test Game Offer",
            store="Free Games Checker",
            url="https://github.com/dazozelm23oz/free-games-checker",
            original_price="$19.99",
        )

        async def _run_test() -> bool:
            notifier = DiscordNotifier(url)
            return await notifier.notify([test_game])

        try:
            success = asyncio.run(_run_test())
            if success:
                QMessageBox.information(self, "Success", "Test notification sent to Discord!")
            else:
                QMessageBox.warning(
                    self, "Failed", "Could not send webhook. Check URL and connectivity."
                )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error sending test notification: {e}")

    def _open_logs_folder(self) -> None:
        logs_dir = get_logs_dir()
        if os.name == "nt":
            os.startfile(str(logs_dir))  # type: ignore[attr-defined]
        else:
            subprocess.run(["xdg-open", str(logs_dir)], check=False)

    def _open_config_folder(self) -> None:
        config_dir = AppConfig.get_default_config_dir()
        if os.name == "nt":
            os.startfile(str(config_dir))  # type: ignore[attr-defined]
        else:
            subprocess.run(["xdg-open", str(config_dir)], check=False)

    def _save_settings(self) -> None:
        # Scheduler
        self.config.scheduler.check_interval_hours = self.interval_spin.value()
        self.config.scheduler.timezone = self.tz_combo.currentText().strip()

        # UI
        self.config.ui.close_to_tray = self.close_to_tray_cb.isChecked()
        self.config.ui.start_minimized = self.start_minimized_cb.isChecked()

        # Stores
        self.config.stores.epic_enabled = self.epic_cb.isChecked()
        self.config.stores.steam_enabled = self.steam_cb.isChecked()
        self.config.stores.gog_enabled = self.gog_cb.isChecked()
        self.config.stores.gamerpower_enabled = self.gp_cb.isChecked()
        self.config.stores.cache_ttl_minutes = self.cache_ttl_spin.value()

        # Notifications
        self.config.notifications.desktop_enabled = self.desktop_cb.isChecked()
        self.config.notifications.discord_enabled = self.discord_cb.isChecked()
        self.config.notifications.discord_webhook_url = self.discord_url_edit.text().strip()
        self.config.notifications.telegram_enabled = self.tg_cb.isChecked()
        self.config.notifications.telegram_bot_token = self.tg_token_edit.text().strip()
        self.config.notifications.telegram_chat_id = self.tg_chat_edit.text().strip()

        self.config.save()
        self.accept()
