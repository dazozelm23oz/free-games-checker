"""In-memory image cache with asynchronous background loading."""

from __future__ import annotations

import asyncio
from typing import ClassVar

import httpx
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QPixmap

from free_games_checker.utils.http import get_http_client
from free_games_checker.utils.logging import get_logger

logger = get_logger("image_cache")


class ImageCache(QObject):
    """Caches pixmaps in memory and emits signals when downloaded."""

    image_loaded = Signal(str, QPixmap)  # url, pixmap

    _instance: ClassVar[ImageCache | None] = None
    _cache: dict[str, QPixmap] = {}
    _in_progress: set[str] = set()

    @classmethod
    def get_instance(cls) -> ImageCache:
        """Singleton accessor."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_pixmap(self, url: str) -> QPixmap | None:
        """Return cached pixmap if available, otherwise initiate async download."""
        if not url:
            return None
        if url in self._cache:
            return self._cache[url]

        if url not in self._in_progress:
            self._in_progress.add(url)
            asyncio.create_task(self._fetch_image(url))
        return None

    async def _fetch_image(self, url: str) -> None:
        try:
            client = await get_http_client()
            resp = await client.get(url, timeout=10.0)
            if resp.status_code == 200:
                pixmap = QPixmap()
                if pixmap.loadFromData(resp.content):
                    self._cache[url] = pixmap
                    self.image_loaded.emit(url, pixmap)
        except (TimeoutError, httpx.HTTPError) as err:
            logger.debug("Failed to download image %s: %s", url, err)
        finally:
            self._in_progress.discard(url)
