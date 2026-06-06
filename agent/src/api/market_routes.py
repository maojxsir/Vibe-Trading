"""Read-only market overview proxy route.

Wraps the pure quote logic in :mod:`src.api.market_quotes` with a FastAPI
router. No auth: this is public market data, on par with ``/health`` and
``/skills``.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict

from fastapi import APIRouter

from src.api.market_quotes import OVERVIEW_CODES, fetch_quotes

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market", tags=["market"])


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
