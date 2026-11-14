"""In-memory image cache with QThreadPool background loading."""

from __future__ import annotations

from typing import ClassVar

import httpx
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtGui import QPixmap

from free_games_checker.utils.logging import get_logger

logger = get_logger("image_cache")


class _ImageWorkerSignals(QObject):
    """Signals for background image download worker."""

    success = Signal(str, bytes)  # url, image_data
    failed = Signal(str)  # url

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)


class _ImageDownloadRunnable(QRunnable):
    """QRunnable for fetching image bytes off the UI thread via QThreadPool."""

    def __init__(self, url: str, signals: _ImageWorkerSignals) -> None:
        super().__init__()
        self.url = url
        self.signals = signals

    def run(self) -> None:
        try:
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                resp = client.get(self.url)
                if resp.status_code == 200:
                    try:
                        self.signals.success.emit(self.url, resp.content)
                    except RuntimeError:
                        pass
                    return
        except Exception as err:
            logger.debug("Failed to download image %s: %s", self.url, err)
        try:
            self.signals.failed.emit(self.url)
        except RuntimeError:
            pass


class ImageCache(QObject):
    """Caches pixmaps in memory and loads missing ones concurrently using QThreadPool."""

    image_loaded = Signal(str, QPixmap)  # url, pixmap

    _instance: ClassVar[ImageCache | None] = None

    def __init__(self) -> None:
        super().__init__()
        self._cache: dict[str, QPixmap] = {}
        self._in_progress: set[str] = set()
        self._signals = _ImageWorkerSignals(self)
        self._signals.success.connect(self._on_download_success)
        self._signals.failed.connect(self._on_download_failed)

    @classmethod
    def get_instance(cls) -> ImageCache:
        """Singleton accessor."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_pixmap(self, url: str) -> QPixmap | None:
        """Return cached pixmap if available, otherwise dispatch QThreadPool worker."""
        if not url:
            return None
        if url in self._cache:
            return self._cache[url]

        if url not in self._in_progress:
            self._in_progress.add(url)
            runnable = _ImageDownloadRunnable(url, self._signals)
            QThreadPool.globalInstance().start(runnable)
        return None

    def _on_download_success(self, url: str, data: bytes) -> None:
        self._in_progress.discard(url)
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            self._cache[url] = pixmap
            self.image_loaded.emit(url, pixmap)

    def _on_download_failed(self, url: str) -> None:
        self._in_progress.discard(url)
