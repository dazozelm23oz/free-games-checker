"""Detailed game information and redemption guide dialog."""

from __future__ import annotations

import webbrowser
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from free_games_checker.models.game import Game
from free_games_checker.utils.image_cache import ImageCache

if TYPE_CHECKING:
    pass


class GameDetailsDialog(QDialog):
    """Rich modal window showcasing game artwork, description, and claim instructions."""

    claim_confirmed = Signal(Game)

    def __init__(self, game: Game, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.game = game
        self.setWindowTitle(f"{game.title} - Free Games Checker")
        self.resize(600, 520)
        self.setStyleSheet("""
            QDialog { background-color: #1a1d24; color: #ffffff; }
            QLabel { color: #d1d5db; font-size: 13px; }
            QScrollArea { border: none; background: transparent; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # 1. Hero Banner
        self.banner_label = QLabel()
        self.banner_label.setFixedHeight(180)
        self.banner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.banner_label.setStyleSheet("background-color: #12141a; border-radius: 8px;")
        layout.addWidget(self.banner_label)
        self._load_banner()

        # 2. Title & Metadata
        title_row = QHBoxLayout()
        self.title_lbl = QLabel(game.title)
        self.title_lbl.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        self.title_lbl.setStyleSheet("color: #ffffff;")
        self.title_lbl.setWordWrap(True)
        title_row.addWidget(self.title_lbl, stretch=1)

        store_color = "#3574f0"
        if "epic" in game.store.lower():
            store_color = "#2a2a2a"
        elif "steam" in game.store.lower():
            store_color = "#1b2838"
        elif "gog" in game.store.lower():
            store_color = "#7a2b9a"

        self.store_badge = QLabel(f" {game.store} ")
        self.store_badge.setStyleSheet(f"""
            background-color: {store_color};
            color: #ffffff;
            font-size: 12px;
            font-weight: bold;
            padding: 4px 8px;
            border-radius: 4px;
            border: 1px solid #4a5060;
        """)
        title_row.addWidget(self.store_badge)
        layout.addLayout(title_row)

        # Value & Deadline Row
        meta_frame = QFrame()
        meta_frame.setStyleSheet("""
            QFrame { background-color: #21242d; border-radius: 6px; padding: 8px; }
        """)
        meta_layout = QHBoxLayout(meta_frame)

        val_text = f"Worth: {game.original_price} (100% OFF)"
        self.val_lbl = QLabel(val_text)
        self.val_lbl.setStyleSheet("color: #00e676; font-weight: bold; font-size: 13px;")
        meta_layout.addWidget(self.val_lbl)

        meta_layout.addStretch(1)

        if game.end_date:
            exp_lbl = QLabel(f"⏳ Expires: {game.end_date}")
            exp_lbl.setStyleSheet("color: #ffb300; font-weight: bold; font-size: 12px;")
            meta_layout.addWidget(exp_lbl)

        layout.addWidget(meta_frame)

        # 3. Scrollable Description & Instructions
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(10)

        desc_text = game.description or "No description provided for this giveaway."
        desc_lbl = QLabel(desc_text)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("line-height: 1.4; color: #cfd8dc;")
        scroll_layout.addWidget(desc_lbl)

        # Instructions / Redemption Guide
        guide_box = QFrame()
        guide_box.setStyleSheet("background-color: #171920; border-radius: 6px; padding: 10px;")
        guide_layout = QVBoxLayout(guide_box)
        guide_title = QLabel("📋 How to Claim:")
        guide_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        guide_title.setStyleSheet("color: #ffffff;")
        guide_layout.addWidget(guide_title)

        steps = [
            f"1. Click '🎁 Claim on {game.store}' below to open the official store page.",
            "2. Log in with your account if prompted.",
            "3. Add the title to your library for $0.00 (free to keep forever).",
            "4. Click '✓ Mark Claimed' here to track your savings!",
        ]
        for step in steps:
            s_lbl = QLabel(step)
            s_lbl.setStyleSheet("color: #b0bec5; font-size: 12px;")
            guide_layout.addWidget(s_lbl)

        scroll_layout.addWidget(guide_box)
        scroll_layout.addStretch(1)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, stretch=1)

        # 4. Action Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.close_btn = QPushButton("Close")
        self.close_btn.setStyleSheet("""
            QPushButton { background-color: #2b2e38; color: #b0bec5; padding: 8px 16px; border-radius: 4px; border: 1px solid #3c404d; }
            QPushButton:hover { background-color: #383c48; color: #ffffff; }
        """)
        self.close_btn.clicked.connect(self.accept)
        btn_row.addWidget(self.close_btn)

        btn_row.addStretch(1)

        self.mark_btn = QPushButton("✓ Mark Claimed")
        self.mark_btn.setStyleSheet("""
            QPushButton { background-color: #374151; color: #ffffff; padding: 8px 16px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #4b5563; }
        """)
        self.mark_btn.clicked.connect(self._on_mark_clicked)
        btn_row.addWidget(self.mark_btn)

        self.claim_btn = QPushButton(f"🎁 Claim on {game.store}")
        self.claim_btn.setStyleSheet("""
            QPushButton { background-color: #00c853; color: white; padding: 8px 20px; border-radius: 4px; font-weight: bold; font-size: 13px; }
            QPushButton:hover { background-color: #00e676; }
            QPushButton:pressed { background-color: #00b248; }
        """)
        self.claim_btn.clicked.connect(self._on_claim_clicked)
        btn_row.addWidget(self.claim_btn)

        layout.addLayout(btn_row)

    def _load_banner(self) -> None:
        if self.game.thumbnail:
            pix = ImageCache.get_instance().get_pixmap(self.game.thumbnail)
            if pix:
                scaled = pix.scaled(
                    560,
                    180,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.banner_label.setPixmap(scaled)
            else:
                ImageCache.get_instance().image_loaded.connect(self._on_image_loaded)
        else:
            self.banner_label.setText("🎮 No Banner Available")

    def _on_image_loaded(self, url: str, pixmap: QPixmap) -> None:
        if self.game.thumbnail == url:
            scaled = pixmap.scaled(
                560,
                180,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.banner_label.setPixmap(scaled)

    def _on_claim_clicked(self) -> None:
        if self.game.url:
            webbrowser.open(self.game.url)

    def _on_mark_clicked(self) -> None:
        self.claim_confirmed.emit(self.game)
        self.accept()
