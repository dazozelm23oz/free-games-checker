"""Custom PySide6 UI widgets (GameCardWidget, StoreFilterBar, SearchBar, StatusBadges)."""

from __future__ import annotations

import webbrowser
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from free_games_checker.models.game import Game
from free_games_checker.utils.image_cache import ImageCache

if TYPE_CHECKING:
    pass


class GameCardWidget(QFrame):
    """Card widget representing an individual free game deal."""

    claim_requested = Signal(Game)
    mark_claimed_requested = Signal(Game)

    def __init__(self, game: Game, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.game = game
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setObjectName("GameCard")
        self.setStyleSheet("""
            QFrame#GameCard {
                background-color: #2b2d30;
                border: 1px solid #3c3f41;
                border-radius: 8px;
                padding: 10px;
                margin: 4px;
            }
            QFrame#GameCard:hover {
                border: 1px solid #4e5254;
                background-color: #313438;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(14)

        # 1. Thumbnail
        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(140, 80)
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.setStyleSheet("background-color: #1e1f22; border-radius: 4px;")
        self._set_placeholder_thumbnail()
        layout.addWidget(self.thumb_label)

        # 2. Game Info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        # Store badge + Title
        title_row = QHBoxLayout()
        self.store_badge = QLabel(game.store)
        self.store_badge.setStyleSheet("""
            background-color: #0e639c;
            color: #ffffff;
            font-size: 11px;
            font-weight: bold;
            padding: 2px 6px;
            border-radius: 4px;
        """)
        title_row.addWidget(self.store_badge)

        self.title_label = QLabel(game.title)
        self.title_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: #ffffff;")
        self.title_label.setWordWrap(True)
        title_row.addWidget(self.title_label, stretch=1)
        info_layout.addLayout(title_row)

        # Meta info (Original Price & Expiration)
        meta_row = QHBoxLayout()
        meta_row.setSpacing(10)

        price_text = f"Worth: {game.original_price} (100% OFF)"
        self.price_label = QLabel(price_text)
        self.price_label.setStyleSheet("color: #3dd68c; font-weight: bold; font-size: 12px;")
        meta_row.addWidget(self.price_label)

        if game.end_date:
            exp_text = f"Expires: {game.end_date}"
            self.exp_label = QLabel(exp_text)
            self.exp_label.setStyleSheet("color: #a9b7c6; font-size: 11px;")
            meta_row.addWidget(self.exp_label)

        meta_row.addStretch(1)
        info_layout.addLayout(meta_row)

        layout.addLayout(info_layout, stretch=1)

        # 3. Actions
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(6)

        self.claim_btn = QPushButton("🎁 Claim Game")
        self.claim_btn.setFixedWidth(130)
        self.claim_btn.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32;
                color: white;
                font-weight: bold;
                padding: 6px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #388e3c; }
            QPushButton:pressed { background-color: #1b5e20; }
        """)
        self.claim_btn.clicked.connect(self._on_claim_clicked)
        btn_layout.addWidget(self.claim_btn)

        self.mark_btn = QPushButton("✓ Mark Claimed")
        self.mark_btn.setFixedWidth(130)
        self.mark_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c3f41;
                color: #d1d5db;
                padding: 4px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #4b5054; }
        """)
        self.mark_btn.clicked.connect(lambda: self.mark_claimed_requested.emit(self.game))
        btn_layout.addWidget(self.mark_btn)

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
        pix = QPixmap(140, 80)
        pix.fill(QColor("#1e1f22"))
        painter = QPainter(pix)
        painter.setPen(QColor("#6c757d"))
        painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "🎮")
        painter.end()
        self.thumb_label.setPixmap(pix)

    def _update_thumbnail(self, url: str, pixmap: QPixmap) -> None:
        if self.game.thumbnail == url:
            scaled = pixmap.scaled(
                140,
                80,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.thumb_label.setPixmap(scaled)

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
                    background-color: #2b2d30;
                    color: #a9b7c6;
                    border: 1px solid #3c3f41;
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
                    background-color: #383a3e;
                    color: white;
                }
            """)
            self.btn_group.addButton(btn, idx)
            layout.addWidget(btn)

        layout.addStretch(1)
        self.btn_group.buttonClicked.connect(lambda b: self.filter_changed.emit(b.text()))


class SearchBar(QLineEdit):
    """Debounced search input box."""

    search_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setPlaceholderText("🔍 Search free games by title...")
        self.setClearButtonEnabled(True)
        self.setStyleSheet("""
            QLineEdit {
                background-color: #1e1f22;
                color: #ffffff;
                border: 1px solid #3c3f41;
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
