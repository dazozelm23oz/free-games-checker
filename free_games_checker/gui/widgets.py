"""Custom PySide6 UI widgets (GameCardWidget, StoreFilterBar, SearchBar, StatusBadges)."""

from __future__ import annotations

import webbrowser
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from free_games_checker.gui.details_dialog import GameDetailsDialog
from free_games_checker.models.game import Game
from free_games_checker.utils.image_cache import ImageCache

if TYPE_CHECKING:
    pass


class GameCardWidget(QFrame):
    """Modern card widget with artwork preview, store branding, and urgency badges."""

    claim_requested = Signal(Game)
    mark_claimed_requested = Signal(Game)

    def __init__(self, game: Game, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.game = game
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setObjectName("GameCard")
        self.setStyleSheet("""
            QFrame#GameCard {
                background-color: #242731;
                border: 1px solid #323644;
                border-radius: 10px;
                padding: 10px;
                margin: 4px;
            }
            QFrame#GameCard:hover {
                border: 1px solid #4a5168;
                background-color: #2a2e3a;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(16)

        # 1. 16:9 Thumbnail Banner
        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(160, 90)
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.setStyleSheet("background-color: #171920; border-radius: 6px;")
        self._set_placeholder_thumbnail()
        layout.addWidget(self.thumb_label)

        # 2. Game Information Area
        info_layout = QVBoxLayout()
        info_layout.setSpacing(6)

        # Store badge + Title row
        title_row = QHBoxLayout()
        title_row.setSpacing(8)

        # Store badge with platform brand styling
        store_lower = game.store.lower()
        if "epic" in store_lower:
            bg_color = "#202020"
            border_color = "#444444"
        elif "steam" in store_lower:
            bg_color = "#172b44"
            border_color = "#2a475e"
        elif "gog" in store_lower:
            bg_color = "#5c1d7a"
            border_color = "#7b26a3"
        else:
            bg_color = "#1e3a5f"
            border_color = "#2d5a92"

        self.store_badge = QLabel(game.store)
        self.store_badge.setStyleSheet(f"""
            background-color: {bg_color};
            color: #ffffff;
            font-size: 11px;
            font-weight: bold;
            padding: 3px 6px;
            border-radius: 4px;
            border: 1px solid {border_color};
        """)
        title_row.addWidget(self.store_badge)

        self.title_label = QLabel(game.title)
        self.title_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: #ffffff;")
        self.title_label.setWordWrap(True)
        title_row.addWidget(self.title_label, stretch=1)

        info_layout.addLayout(title_row)

        # Tags & Urgency row
        tag_row = QHBoxLayout()
        tag_row.setSpacing(10)

        # Price tag: Strikethrough price + FREE (100% OFF)
        self.price_label = QLabel()
        self.price_label.setTextFormat(Qt.TextFormat.RichText)
        if game.original_price and game.original_price.strip() and game.original_price != "$0.00":
            self.price_label.setText(
                f"<span style='color: #90a4ae;'><s>{game.original_price}</s></span>  "
                f"<b style='color: #00e676;'>FREE (100% OFF)</b>"
            )
        else:
            self.price_label.setText("<b style='color: #00e676;'>FREE</b>")
        self.price_label.setStyleSheet("font-size: 12px;")
        tag_row.addWidget(self.price_label)

        # Expiration Urgency Pill
        if game.end_date:
            exp_text = f"⏳ Ends: {game.end_date[:10] if 'T' in game.end_date else game.end_date}"
            self.exp_pill = QLabel(exp_text)
            self.exp_pill.setStyleSheet("""
                background-color: #3e2723;
                color: #ffb74d;
                font-size: 11px;
                font-weight: bold;
                padding: 2px 6px;
                border-radius: 4px;
                border: 1px solid #ff9800;
            """)
            tag_row.addWidget(self.exp_pill)

        tag_row.addStretch(1)
        info_layout.addLayout(tag_row)

        # Short description snippet
        if game.description:
            clean_desc = game.description.replace("\n", " ").strip()
            if len(clean_desc) > 90:
                clean_desc = clean_desc[:87] + "..."
            desc_lbl = QLabel(clean_desc)
            desc_lbl.setStyleSheet("color: #90a4ae; font-size: 11px;")
            info_layout.addWidget(desc_lbl)

        layout.addLayout(info_layout, stretch=1)

        # 3. Actions Column
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(6)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.claim_btn = QPushButton("🎁 Claim Game")
        self.claim_btn.setFixedWidth(130)
        self.claim_btn.setStyleSheet("""
            QPushButton {
                background-color: #00c853;
                color: white;
                font-weight: bold;
                padding: 6px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #00e676; }
            QPushButton:pressed { background-color: #00b248; }
        """)
        self.claim_btn.clicked.connect(self._on_claim_clicked)
        btn_layout.addWidget(self.claim_btn)

        action_sub_row = QHBoxLayout()
        action_sub_row.setSpacing(4)

        self.details_btn = QPushButton("ℹ️ Details")
        self.details_btn.setStyleSheet("""
            QPushButton {
                background-color: #2e3440;
                color: #88c0d0;
                padding: 4px 6px;
                border-radius: 4px;
                border: 1px solid #434c5e;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #3b4252; color: #eceff4; }
        """)
        self.details_btn.clicked.connect(self._open_details)
        action_sub_row.addWidget(self.details_btn)

        self.mark_btn = QPushButton("✓ Claimed")
        self.mark_btn.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                color: #d1d5db;
                padding: 4px 6px;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #4b5563; }
        """)
        self.mark_btn.clicked.connect(lambda: self.mark_claimed_requested.emit(self.game))
        action_sub_row.addWidget(self.mark_btn)

        btn_layout.addLayout(action_sub_row)
        layout.addLayout(btn_layout)

        # Connect image loader
        if game.thumbnail:
            cache = ImageCache.get_instance()
            pix = cache.get_pixmap(game.thumbnail)
            if pix:
                self._update_thumbnail(game.thumbnail, pix)
            else:
                cache.image_loaded.connect(self._update_thumbnail)

    def _set_placeholder_thumbnail(self) -> None:
        pix = QPixmap(160, 90)
        pix.fill(QColor("#171920"))
        painter = QPainter(pix)
        painter.setPen(QColor("#546e7a"))
        painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "🎮 Free Game")
        painter.end()
        self.thumb_label.setPixmap(pix)

    def _update_thumbnail(self, url: str, pixmap: QPixmap) -> None:
        if self.game.thumbnail == url:
            scaled = pixmap.scaled(
                160,
                90,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.thumb_label.setPixmap(scaled)

    def _open_details(self) -> None:
        dlg = GameDetailsDialog(self.game, self)
        dlg.claim_confirmed.connect(self.mark_claimed_requested.emit)
        dlg.exec()

    def _on_claim_clicked(self) -> None:
        if self.game.url:
            webbrowser.open(self.game.url)
        reply = QMessageBox.question(
            self,
            "Claim Confirmation",
            f"Opened '{self.game.title}' in your web browser.\n\nDid you claim it? Mark as claimed now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.claim_requested.emit(self.game)


class StoreFilterBar(QWidget):
    """Horizontal filter bar for stores (All, Epic, Steam, GOG, GamerPower)."""

    filter_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        stores = ["All Stores", "Epic Games", "Steam", "GOG", "GamerPower"]
        for idx, store in enumerate(stores):
            btn = QPushButton(store)
            btn.setCheckable(True)
            if idx == 0:
                btn.setChecked(True)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #242731;
                    color: #a0aec0;
                    border: 1px solid #323644;
                    padding: 6px 14px;
                    border-radius: 14px;
                    font-weight: 500;
                }
                QPushButton:checked {
                    background-color: #3574f0;
                    color: white;
                    border: 1px solid #3574f0;
                }
                QPushButton:hover:!checked {
                    background-color: #2e323e;
                    color: white;
                }
            """)
            self.btn_group.addButton(btn, idx)
            layout.addWidget(btn)

        layout.addStretch(1)
        self.btn_group.buttonClicked.connect(lambda b: self.filter_changed.emit(b.text()))


class SearchBar(QLineEdit):
    """Debounced search input box with clear button."""

    search_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setPlaceholderText("🔍 Search free games by title... (Ctrl+F)")
        self.setClearButtonEnabled(True)
        self.setStyleSheet("""
            QLineEdit {
                background-color: #171920;
                color: #ffffff;
                border: 1px solid #323644;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #3574f0;
            }
        """)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self._emit_search)
        self.textChanged.connect(self._on_text_changed)

    def _on_text_changed(self) -> None:
        self._timer.start()

    def _emit_search(self) -> None:
        self.search_changed.emit(self.text().strip())


class SortDropdown(QComboBox):
    """Sorting selector for game deals."""

    sort_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.addItems(
            [
                "Sort: Newest First",
                "Sort: Highest Value ($)",
                "Sort: Ending Soonest",
                "Sort: Title (A-Z)",
            ]
        )
        self.setStyleSheet("""
            QComboBox {
                background-color: #242731;
                color: #ffffff;
                border: 1px solid #323644;
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 12px;
            }
        """)
        self.currentTextChanged.connect(self.sort_changed.emit)
