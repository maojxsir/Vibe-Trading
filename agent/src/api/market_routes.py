"""Read-only market overview proxy route.

Wraps the pure quote logic in :mod:`src.api.market_quotes` with a FastAPI
router. No auth: this is public market data, on par with ``/health`` and
``/skills``.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List

from fastapi import APIRouter, Query

from src.api.market_news import fetch_news
from src.api.market_quotes import OVERVIEW_CODES, fetch_quotes

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market", tags=["market"])

# Cap how many codes a single quote request may ask for (abuse / URL length).
_MAX_CODES = 60


@router.get("/overview")
async def market_overview() -> Dict[str, object]:
    """Return live quotes for the overview codes; flag ``stale`` on failure."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        quotes = await fetch_quotes(OVERVIEW_CODES)
        if not quotes:
            raise ValueError("empty quote payload")
        return {"quotes": quotes, "updatedAt": now, "source": "腾讯财经", "stale": False}
    except Exception as exc:  # noqa: BLE001 - degrade gracefully, FE falls back to seed
        logger.warning("market_overview upstream failed: %s", exc)
        return {"quotes": {}, "updatedAt": now, "source": "腾讯财经", "stale": True}


@router.get("/quotes")
async def market_quotes(codes: str = Query("", description="Comma-separated Tencent codes")) -> Dict[str, object]:
    """Return live quotes for arbitrary ``codes`` (e.g. ``sh688017,sz300308``)."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    wanted: List[str] = [c.strip() for c in codes.split(",") if c.strip()][:_MAX_CODES]
    if not wanted:
        return {"quotes": {}, "updatedAt": now, "source": "腾讯财经", "stale": False}
    try:
        quotes = await fetch_quotes(wanted)
        if not quotes:
            raise ValueError("empty quote payload")
        return {"quotes": quotes, "updatedAt": now, "source": "腾讯财经", "stale": False}
    except Exception as exc:  # noqa: BLE001
        logger.warning("market_quotes upstream failed: %s", exc)
        return {"quotes": {}, "updatedAt": now, "source": "腾讯财经", "stale": True}


@router.get("/news")
async def market_news() -> Dict[str, object]:
    """Return a live finance news feed; flag ``stale`` on failure (FE seeds)."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        items = await fetch_news()
        if not items:
            raise ValueError("empty news payload")
        return {"items": items, "updatedAt": now, "source": "新浪财经", "stale": False}
    except Exception as exc:  # noqa: BLE001
        logger.warning("market_news upstream failed: %s", exc)
        return {"items": [], "updatedAt": now, "source": "新浪财经", "stale": True}
