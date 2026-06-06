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
from pydantic import BaseModel

from src.api.market_quotes import OVERVIEW_CODES, fetch_quotes

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market", tags=["market"])


class GenerateChainRequest(BaseModel):
    topic: str


class SuggestTopicsRequest(BaseModel):
    hint: str = ""


class GenerateModuleStocksRequest(BaseModel):
    theme: str
    module: str

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
    except Exception as exc:  # noqa: BLE001 - degrade gracefully, FE shows empty quotes
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
    """Return merged finance news; flag ``stale`` when all suppliers fail."""
    from src.com.news import fetch_merged_news

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        merged = await fetch_merged_news(limit=80)
        items = merged.get("items") or []
        if not items:
            raise ValueError("empty news payload")
        return {
            "items": items,
            "updatedAt": merged.get("updatedAt") or now,
            "source": merged.get("source") or "com/news",
            "stale": False,
            "providers": merged.get("providers") or {},
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("market_news upstream failed: %s", exc)
        return {"items": [], "updatedAt": now, "source": "com/news", "stale": True, "providers": {}}


@router.post("/logic-chain/generate")
async def logic_chain_generate(req: GenerateChainRequest) -> Dict[str, object]:
    """Run the Vibe-Trading agent to research ``topic`` into a logic chain.

    Requires a configured LLM provider. On any failure (no key, agent error,
    unparseable answer) returns ``error`` + empty graph so the frontend keeps
    the user's current board.
    """
    import asyncio

    from src.api.logic_chain import generate_logic_chain

    topic = (req.topic or "").strip()
    if not topic:
        return {"nodes": [], "edges": [], "error": "topic 不能为空"}
    try:
        # Agent runs are blocking and can take a while; keep the event loop free.
        chain = await asyncio.to_thread(generate_logic_chain, topic)
        return {"nodes": chain["nodes"], "edges": chain["edges"], "error": None}
    except Exception as exc:  # noqa: BLE001 - degrade gracefully
        logger.warning("logic_chain_generate failed for %r: %s", topic, exc)
        return {"nodes": [], "edges": [], "error": f"生成失败: {exc}"}


@router.post("/logic-chain/suggest-topics")
async def logic_chain_suggest_topics(req: SuggestTopicsRequest) -> Dict[str, object]:
    """Recommend logic-chain topic titles via the agent."""
    import asyncio

    from src.api.logic_chain import suggest_logic_chain_topics

    hint = (req.hint or "").strip()
    try:
        topics = await asyncio.to_thread(suggest_logic_chain_topics, hint)
        return {"topics": topics, "error": None}
    except Exception as exc:  # noqa: BLE001
        logger.warning("logic_chain_suggest_topics failed: %s", exc)
        return {"topics": [], "error": f"推荐失败: {exc}"}


@router.post("/module-stocks/generate")
async def module_stocks_generate(req: GenerateModuleStocksRequest) -> Dict[str, object]:
    """Run the agent to refresh a single industry-chain module watchlist."""
    import asyncio

    from src.api.module_stocks import generate_module_stocks

    theme = (req.theme or "").strip()
    module = (req.module or "").strip()
    if not theme or not module:
        return {"stocks": [], "error": "theme 与 module 不能为空"}
    try:
        stocks = await asyncio.to_thread(generate_module_stocks, theme, module)
        return {"stocks": stocks, "error": None}
    except Exception as exc:  # noqa: BLE001
        logger.warning("module_stocks_generate failed for %r/%r: %s", theme, module, exc)
        return {"stocks": [], "error": f"生成失败: {exc}"}
