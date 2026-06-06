"""Common (com) API — multi-source aggregated market data."""

from __future__ import annotations

import logging
from typing import Dict

from fastapi import APIRouter, Query

from src.com.news import fetch_merged_news

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/com", tags=["com"])


@router.get("/news")
async def com_news(limit: int = Query(80, ge=1, le=200)) -> Dict[str, object]:
    """Merged finance news from every configured supplier."""
    try:
        return await fetch_merged_news(limit=limit)
    except Exception as exc:  # noqa: BLE001
        logger.warning("com_news failed: %s", exc)
        return {
            "items": [],
            "updatedAt": "",
            "source": "com/news",
            "stale": True,
            "providers": {},
            "supplierCount": 0,
            "error": str(exc),
        }
