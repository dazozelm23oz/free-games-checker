"""Resilient HTTP client with connection pooling, retries, and backoff."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from free_games_checker.utils.logging import get_logger

logger = get_logger("http")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 FreeGamesChecker/1.0"
)

_CLIENT: httpx.AsyncClient | None = None
_CLIENT_LOCK = asyncio.Lock()


async def get_http_client() -> httpx.AsyncClient:
    """Get or create singleton httpx.AsyncClient."""
    global _CLIENT
    if _CLIENT is None or _CLIENT.is_closed:
        async with _CLIENT_LOCK:
            if _CLIENT is None or _CLIENT.is_closed:
                _CLIENT = httpx.AsyncClient(
                    headers={"User-Agent": USER_AGENT},
                    timeout=httpx.Timeout(15.0, connect=10.0),
                    follow_redirects=True,
                    limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
                )
    return _CLIENT


async def close_http_client() -> None:
    """Close singleton httpx.AsyncClient if active."""
    global _CLIENT
    if _CLIENT is not None and not _CLIENT.is_closed:
        await _CLIENT.aclose()
        _CLIENT = None


async def fetch_json(url: str, params: dict[str, Any] | None = None) -> Any:
    """Fetch URL with retries on network failures, 5xx, or 429 rate limits."""
    client = await get_http_client()

    retryer = AsyncRetrying(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1.0, max=10.0),
        retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
        reraise=True,
    )

    async for attempt in retryer:
        with attempt:
            resp = await client.get(url, params=params)
            if resp.status_code == 429:
                retry_after = float(resp.headers.get("Retry-After", 5.0))
                logger.warning("Rate limited (429) on %s. Sleeping %s seconds", url, retry_after)
                await asyncio.sleep(min(retry_after, 15.0))
                resp.raise_for_status()
            resp.raise_for_status()
            return resp.json()
    return None
