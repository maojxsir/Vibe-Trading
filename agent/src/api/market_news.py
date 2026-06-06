"""Backward-compatible news helpers.

New code should use :mod:`src.com.news` for multi-source merge. This module
re-exports parsing helpers used by tests and a thin ``fetch_news`` wrapper.
"""

from __future__ import annotations

from typing import Dict, List

from src.com.news import fetch_merged_news
from src.com.news.providers.sina import parse_sina_payload
from src.com.news.tags import WATCHLIST_NAMES, tag_tickers


def parse_sina_news(payload: Dict) -> List[Dict[str, object]]:
    """Parse Sina JSON (legacy name for unit tests)."""
    return parse_sina_payload(payload, supplier="sina_finance")


async def fetch_news() -> List[Dict[str, object]]:
    """Return merged news rows (delegates to com layer)."""
    result = await fetch_merged_news(limit=80)
    return list(result.get("items") or [])


__all__ = ["WATCHLIST_NAMES", "fetch_news", "parse_sina_news", "tag_tickers"]
