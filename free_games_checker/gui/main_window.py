"""Main PySide6 application window."""

from __future__ import annotations

import asyncio
import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QCloseEvent, QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from free_games_checker.checkers import CheckerRegistry
from free_games_checker.gui.first_run_dialog import FirstRunDialog
from free_games_checker.gui.settings_dialog import SettingsDialog
from free_games_checker.gui.tray_icon import AppTrayIcon, create_default_tray_icon
from free_games_checker.gui.widgets import (
    GameCardWidget,
    SearchBar,
    SortDropdown,
    StoreFilterBar,
)
from free_games_checker.models.config import AppConfig
from free_games_checker.models.game import Game
from free_games_checker.services.notifier import NotificationService
from free_games_checker.services.scheduler import AppScheduler
from free_games_checker.services.store import ClaimStore
from free_games_checker.utils.logging import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger("gui.main_window")


class WorkerSignals(QObject):
    """Signals emitted by background check worker."""

    started = Signal()
    finished = Signal(list, dict)  # games, statuses
    error = Signal(str)


class CheckWorker(QThread):
    """Background thread worker for fetching all store promotions."""

    def __init__(self, registry: CheckerRegistry, force_refresh: bool = False) -> None:
        super().__init__()
        self.registry = registry
        self.force_refresh = force_refresh
        self.signals = WorkerSignals()

    def run(self) -> None:
        self.signals.started.emit()
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            games, statuses = loop.run_until_complete(
                self.registry.fetch_all(force_refresh=self.force_refresh)
            )
            loop.close()
            self.signals.finished.emit(games, statuses)
        except Exception as e:
            logger.error("Worker error: %s", e)
            self.signals.error.emit(str(e))


class MainWindow(QMainWindow):
    """Primary desktop interface for Free Games Checker."""

    def __init__(
        self,
        config: AppConfig | None = None,
        store: ClaimStore | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.config = config or AppConfig.load()
        self.store = store or ClaimStore()
        self.registry = CheckerRegistry(self.config)
        self.notifier = NotificationService(self.config.notifications)

        self.active_games: list[Game] = []
        self.current_filter_store = "All Stores"
        self.current_search_query = ""
        self.current_sort = "Sort: Newest First"
        self.last_check_time: str = "Never"
        self._worker: CheckWorker | None = None

        self.setWindowTitle("🎮 Free Games Checker")
        self.resize(880, 700)
        self.setWindowIcon(create_default_tray_icon())
        self._apply_theme()

        self._build_ui()
        self._setup_shortcuts()
        self._init_tray()
        self._init_scheduler()

        if not self.config.ui.first_run_completed:
            self._show_first_run()

        # Initial check
        self.check_now(force=False)

    def _apply_theme(self) -> None:
        self.setStyleSheet("""
            QMainWindow { background-color: #171920; }
            QWidget { color: #ffffff; font-family: 'Segoe UI', Arial, sans-serif; }
            QTabWidget::pane { border: none; background: #171920; }
            QTabBar::tab { background: #242731; color: #a0aec0; padding: 10px 22px; font-weight: bold; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 4px; font-size: 13px; }
            QTabBar::tab:selected { background: #3574f0; color: #ffffff; }
            QScrollArea { border: none; background-color: transparent; }
            QStatusBar { background: #242731; color: #a0aec0; font-size: 11px; }
        """)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(10)

        # 1. Header Toolbar
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        app_title = QLabel("🎮 Free PC Games")
        app_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title_box.addWidget(app_title)

        self.subtitle = QLabel("Live giveaways from Epic Games, Steam, GOG & Aggregators")
        self.subtitle.setStyleSheet("color: #8c9299; font-size: 12px;")
        title_box.addWidget(self.subtitle)
        header.addLayout(title_box)

        header.addStretch(1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.setFixedWidth(120)
        self.progress_bar.setFixedHeight(16)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        header.addWidget(self.progress_bar)

        self.check_btn = QPushButton("⚡ Check Now")
        self.check_btn.setStyleSheet(
            "background-color: #3574f0; color: white; font-weight: bold; padding: 7px 16px; border-radius: 4px;"
        )
        self.check_btn.clicked.connect(lambda: self.check_now(force=True))
        header.addWidget(self.check_btn)

        self.export_btn = QPushButton("💾 Export")
        self.export_btn.setStyleSheet(
            "background-color: #242731; border: 1px solid #323644; padding: 7px 12px; border-radius: 4px;"
        )
        self.export_btn.clicked.connect(self._on_export_clicked)
        header.addWidget(self.export_btn)

        self.settings_btn = QPushButton("⚙️ Settings")
        self.settings_btn.setStyleSheet(
            "background-color: #242731; border: 1px solid #323644; padding: 7px 12px; border-radius: 4px;"
        )
        self.settings_btn.clicked.connect(self._open_settings)
        header.addWidget(self.settings_btn)

        main_layout.addLayout(header)

        # 2. Metrics Summary Ribbon
        self.metrics_ribbon = QLabel("✨ 0 Active Giveaways Available • Total Value: $0.00")
        self.metrics_ribbon.setStyleSheet("""
            QLabel {
                background-color: #1e222d;
                color: #00e676;
                font-weight: bold;
                font-size: 12px;
                padding: 7px 12px;
                border-radius: 6px;
                border: 1px solid #2d3242;
            }
        """)
        main_layout.addWidget(self.metrics_ribbon)

        # 3. Filter & Search row
        filter_row = QHBoxLayout()
        self.filter_bar = StoreFilterBar()
        self.filter_bar.filter_changed.connect(self._on_filter_store_changed)
        filter_row.addWidget(self.filter_bar)

        self.sort_dropdown = SortDropdown()
        self.sort_dropdown.sort_changed.connect(self._on_sort_changed)
        filter_row.addWidget(self.sort_dropdown)

        self.search_bar = SearchBar()
        self.search_bar.search_changed.connect(self._on_search_query_changed)
        self.search_bar.setFixedWidth(230)
        filter_row.addWidget(self.search_bar)

        main_layout.addLayout(filter_row)

        # 4. Main Tabs
        self.tabs = QTabWidget()

        # Tab 1: Available Games
        self.available_tab = QWidget()
        avail_layout = QVBoxLayout(self.available_tab)
        avail_layout.setContentsMargins(0, 8, 0, 0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.cards_layout = QVBoxLayout(self.scroll_content)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(8)
        self.cards_layout.addStretch(1)
        self.scroll_area.setWidget(self.scroll_content)
        avail_layout.addWidget(self.scroll_area)

        self.tabs.addTab(self.available_tab, "🟢 Available Now (0)")

        # Tab 2: Claimed History
        self.history_tab = QWidget()
        hist_layout = QVBoxLayout(self.history_tab)
        hist_layout.setContentsMargins(0, 8, 0, 0)

        # Money Saved Banner
        self.money_saved_banner = QFrame()
        self.money_saved_banner.setStyleSheet("""
            QFrame { background-color: #1b382b; border: 1px solid #2e7d32; border-radius: 6px; padding: 12px; }
        """)
        banner_layout = QHBoxLayout(self.money_saved_banner)
        self.money_saved_label = QLabel("💰 Total Money Saved: $0.00")
        self.money_saved_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.money_saved_label.setStyleSheet("color: #3dd68c;")
        banner_layout.addWidget(self.money_saved_label)

        self.rank_label = QLabel("🏆 Level: Looter")
        self.rank_label.setStyleSheet("color: #ffd54f; font-weight: bold; font-size: 12px;")
        banner_layout.addWidget(self.rank_label)

        banner_layout.addStretch(1)
        hist_layout.addWidget(self.money_saved_banner)

        # Claimed Table
        self.claimed_table = QTableWidget()
        self.claimed_table.setColumnCount(5)
        self.claimed_table.setHorizontalHeaderLabels(
            ["Title", "Store", "Original Value", "Claimed Date", "Action"]
        )
        self.claimed_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.claimed_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.claimed_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self.claimed_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        self.claimed_table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.ResizeToContents
        )
        self.claimed_table.setStyleSheet("""
            QTableWidget { background-color: #242731; gridline-color: #323644; border: 1px solid #323644; }
            QHeaderView::section { background-color: #171920; color: #a0aec0; padding: 6px; border: 1px solid #323644; }
        """)
        hist_layout.addWidget(self.claimed_table)

        self.tabs.addTab(self.history_tab, "📜 Claimed History (0)")

        main_layout.addWidget(self.tabs, stretch=1)

        # 5. Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label, stretch=1)
        self.store_health_label = QLabel("")
        self.status_bar.addPermanentWidget(self.store_health_label)

    def _setup_shortcuts(self) -> None:
        """Register keyboard shortcuts for fast navigation."""
        sc_f = QShortcut(QKeySequence("Ctrl+F"), self)
        sc_f.activated.connect(self._focus_search)
        sc_k = QShortcut(QKeySequence("Ctrl+K"), self)
        sc_k.activated.connect(self._focus_search)

    def _focus_search(self) -> None:
        self.search_bar.setFocus()
        self.search_bar.selectAll()

    def _init_tray(self) -> None:
        self.tray = AppTrayIcon(self)
        self.tray.check_now_requested.connect(lambda: self.check_now(force=True))
        self.tray.settings_requested.connect(self._open_settings)
        self.tray.toggle_window_requested.connect(self._toggle_window)
        self.tray.quit_requested.connect(self._quit_app)
        self.tray.show()

    def _init_scheduler(self) -> None:
        self.scheduler = AppScheduler(
            self.config.scheduler,
            check_callback=lambda: self.check_now(force=True),
        )
        self.scheduler.start()

    def _show_first_run(self) -> None:
        wizard = FirstRunDialog(self.config, self)
        wizard.exec()

    def check_now(self, force: bool = True) -> None:
        """Trigger background check for free games."""
        if self._worker is not None and self._worker.isRunning():
            return

        self.progress_bar.show()
        self.check_btn.setEnabled(False)
        self.status_label.setText("Checking stores for active promotions...")

        self._worker = CheckWorker(self.registry, force_refresh=force)
        self._worker.signals.finished.connect(self._on_check_finished)
        self._worker.signals.error.connect(self._on_check_error)
        self._worker.start()

    def _on_check_finished(
        self, games: list[Game], statuses: dict[str, tuple[int, str | None]]
    ) -> None:
        self.progress_bar.hide()
        self.check_btn.setEnabled(True)
        self.last_check_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.active_games = games
        self._render_available_cards()
        self._render_claimed_history()

        # Update Store Health Statuses in Statusbar
        health_parts = []
        for name, (count, err) in statuses.items():
            if err:
                health_parts.append(f"{name}: ⚠ {err[:15]}")
            else:
                health_parts.append(f"{name}: ✓ {count}")
        self.store_health_label.setText(" | ".join(health_parts))

        # Check for newly discovered unclaimed games to notify
        unclaimed_now = [g for g in games if not self.store.is_claimed(g.title)]
        if unclaimed_now:
            if self.config.notifications.desktop_enabled:
                self.tray.notify_new_games(unclaimed_now)
            # Dispatch async external notifiers in background thread
            import threading

            def _dispatch_bg() -> None:
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self.notifier.dispatch(unclaimed_now))
                    loop.close()
                except Exception as e:
                    logger.debug("Failed background notification dispatch: %s", e)

            threading.Thread(target=_dispatch_bg, daemon=True).start()

        next_run = self.scheduler.get_next_run_time()
        next_run_str = next_run.strftime("%H:%M") if next_run else "N/A"
        self.status_label.setText(
            f"Last checked: {self.last_check_time} | Next check: {next_run_str}"
        )

    def _on_check_error(self, err_msg: str) -> None:
        self.progress_bar.hide()
        self.check_btn.setEnabled(True)
        self.status_label.setText(f"Check failed: {err_msg}")
        QMessageBox.warning(
            self, "Check Failed", f"Encountered error while checking stores:\n{err_msg}"
        )

    def _sort_games(self, games: list[Game]) -> list[Game]:
        """Sort games list based on user dropdown selection."""
        sorted_list = list(games)
        if self.current_sort == "Sort: Highest Value ($)":

            def _parse_val(g: Game) -> float:
                m = re.search(r"(\d+(?:\.\d{1,2})?)", g.original_price or "")
                return float(m.group(1)) if m else 0.0

            sorted_list.sort(key=_parse_val, reverse=True)
        elif self.current_sort == "Sort: Ending Soonest":
            sorted_list.sort(key=lambda g: g.end_date or "9999-12-31")
        elif self.current_sort == "Sort: Title (A-Z)":
            sorted_list.sort(key=lambda g: g.title.lower())
        return sorted_list

    def _render_available_cards(self) -> None:
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

        unclaimed_games = [g for g in self.active_games if not self.store.is_claimed(g.title)]

        # Calculate total available free value
        total_avail_val = 0.0
        for g in unclaimed_games:
            m = re.search(r"(\d+(?:\.\d{1,2})?)", g.original_price or "")
            if m:
                try:
                    total_avail_val += float(m.group(1))
                except ValueError:
                    pass

        self.metrics_ribbon.setText(
            f"✨ {len(unclaimed_games)} Active Giveaway{'s' if len(unclaimed_games) != 1 else ''} Available • "
            f"Total Value: ${total_avail_val:.2f} • Last Synced: {self.last_check_time}"
        )

        # Apply store filter & search filter
        filtered: list[Game] = []
        for g in unclaimed_games:
            if self.current_filter_store != "All Stores":
                if self.current_filter_store.lower() not in g.store.lower():
                    continue
            if self.current_search_query:
                if self.current_search_query.lower() not in g.title.lower():
                    continue
            filtered.append(g)

        filtered = self._sort_games(filtered)
        self.tabs.setTabText(0, f"🟢 Available Now ({len(unclaimed_games)})")

        if not filtered:
            empty_label = QLabel(
                "🎉 You're all caught up! No unclaimed free games currently available."
                if not unclaimed_games
                else "No games match your current filter."
            )
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet("color: #8c9299; font-size: 14px; padding: 40px;")
            self.cards_layout.insertWidget(0, empty_label)
            return

        for idx, game in enumerate(filtered):
            card = GameCardWidget(game)
            card.claim_requested.connect(self._on_game_claimed)
            card.mark_claimed_requested.connect(self._on_game_claimed)
            self.cards_layout.insertWidget(idx, card)

    def _render_claimed_history(self) -> None:
        claimed = self.store.get_all_claimed()
        self.tabs.setTabText(1, f"📜 Claimed History ({len(claimed)})")

        # Update saved money banner & rank
        saved_val = self.store.get_total_money_saved()
        self.money_saved_label.setText(f"💰 Total Money Saved: ${saved_val:.2f}")

        # Gamified Loot Rank
        if saved_val > 500:
            rank = "👑 Legendary Hoarder"
        elif saved_val > 200:
            rank = "💎 Master Collector"
        elif saved_val > 50:
            rank = "🏹 Seasoned Looter"
        else:
            rank = "🌱 Novice Looter"
        self.rank_label.setText(f"🏆 Rank: {rank} ({len(claimed)} Games)")

        self.claimed_table.setRowCount(len(claimed))
        for row, g in enumerate(claimed):
            title_item = QTableWidgetItem(g.title)
            store_item = QTableWidgetItem(g.store)
            price_item = QTableWidgetItem(g.original_price or "Free")
            date_item = QTableWidgetItem(g.claimed_at or "N/A")

            self.claimed_table.setItem(row, 0, title_item)
            self.claimed_table.setItem(row, 1, store_item)
            self.claimed_table.setItem(row, 2, price_item)
            self.claimed_table.setItem(row, 3, date_item)

            unclaim_btn = QPushButton("Remove")
            unclaim_btn.setStyleSheet(
                "background-color: #4b5054; color: white; padding: 2px 6px; border-radius: 3px;"
            )
            unclaim_btn.clicked.connect(lambda _, title=g.title: self._on_unclaim(title))
            self.claimed_table.setCellWidget(row, 4, unclaim_btn)

    def _on_game_claimed(self, game: Game) -> None:
        self.store.add_claimed(game)
        self._render_available_cards()
        self._render_claimed_history()

    def _on_unclaim(self, title: str) -> None:
        reply = QMessageBox.question(
            self,
            "Remove Claimed Game",
            f"Are you sure you want to remove '{title}' from your claimed history?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.store.remove_claimed(title)
            self._render_available_cards()
            self._render_claimed_history()

    def _on_filter_store_changed(self, store_name: str) -> None:
        self.current_filter_store = store_name
        self._render_available_cards()

    def _on_sort_changed(self, sort_name: str) -> None:
        self.current_sort = sort_name
        self._render_available_cards()

    def _on_search_query_changed(self, query: str) -> None:
        self.current_search_query = query
        self._render_available_cards()

    def _on_export_clicked(self) -> None:
        path, sel_filter = QFileDialog.getSaveFileName(
            self,
            "Export Games",
            str(Path.home() / "free_games.csv"),
            "CSV Files (*.csv);;JSON Files (*.json)",
        )
        if not path:
            return

        try:
            if path.endswith(".json") or "JSON" in sel_filter:
                data = [g.to_dict() for g in self.active_games]
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
            else:
                with open(path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Title", "Store", "Original Value", "Expires", "URL"])
                    for g in self.active_games:
                        writer.writerow(
                            [g.title, g.store, g.original_price, g.end_date or "", g.url]
                        )
            QMessageBox.information(
                self, "Export Complete", f"Successfully exported games to {path}!"
            )
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Could not export file: {e}")

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self.config, self)
        if dlg.exec():
            # Update scheduler & registry
            self.scheduler.reschedule(
                self.config.scheduler.check_interval_hours,
                self.config.scheduler.timezone,
            )
            self.registry._init_checkers()
            self.notifier.config = self.config.notifications

    def _toggle_window(self) -> None:
        if self.isVisible():
            self.hide()
        else:
            self.showNormal()
            self.activateWindow()

    def _quit_app(self) -> None:
        self.scheduler.stop()
        self.tray.hide()
        self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.config.ui.close_to_tray and self.tray.isVisible():
            event.ignore()
            self.hide()
            self.tray.showMessage(
                "Free Games Checker",
                "App minimized to system tray. Right-click tray icon to open or quit.",
                create_default_tray_icon(),
                2000,
            )
        else:
            self.scheduler.stop()
            event.accept()
