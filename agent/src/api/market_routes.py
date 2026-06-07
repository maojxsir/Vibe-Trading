"""Read-only market overview proxy route.

Wraps the pure quote logic in :mod:`src.api.market_quotes` with a FastAPI
router. No auth: this is public market data, on par with ``/health`` and
``/skills``.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List

from fastapi import APIRouter, HTTPException, Query, UploadFile, status
from pydantic import BaseModel

from src.api import holdings_parse, symbol_index
from src.api.market_quotes import OVERVIEW_CODES, fetch_quotes

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market", tags=["market"])
holdings_router = APIRouter(prefix="/holdings", tags=["holdings"])


class GenerateChainRequest(BaseModel):
    topic: str


class SuggestTopicsRequest(BaseModel):
    hint: str = ""


class GenerateModuleStocksRequest(BaseModel):
    theme: str
    module: str

# Cap how many codes a single quote request may ask for (abuse / URL length).
_MAX_CODES = 60
_MAX_SCREENSHOT_BYTES = 8 * 1024 * 1024
_ALLOWED_SCREENSHOT_TYPES = {"image/jpeg", "image/png", "image/webp"}


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


@router.get("/kline")
async def market_kline(
    code: str = Query("", description="Bare or prefixed A-share code, e.g. 688017"),
    days: int = Query(365, ge=1, le=500, description="Lookback window in calendar days"),
) -> Dict[str, object]:
    """Return daily OHLCV bars for one symbol (K-line drawer)."""
    import asyncio

    from src.api.market_kline import fetch_kline

    bare = (code or "").strip()
    if not bare:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return {
            "code": "",
            "name": None,
            "bars": [],
            "source": "",
            "stale": True,
            "updatedAt": now,
            "error": "code required",
        }
    return await asyncio.to_thread(fetch_kline, bare, days)


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


@router.get("/symbols/search")
async def symbols_search(
    q: str = Query("", description="Code, Chinese name, or pinyin abbreviation"),
    boost: str = Query("", description="Comma-separated boosted bare six-digit codes"),
    limit: int = Query(12, ge=1, le=30),
) -> Dict[str, object]:
    """Search the cached A-share symbol index for holdings autocomplete."""
    boost_codes = {c.strip() for c in boost.split(",") if c.strip()}
    if not q.strip() and not boost_codes:
        boost_codes = symbol_index.default_boost_codes()
    try:
        rows = symbol_index.load_index()
        results = symbol_index.search_symbols(q, rows, boost=boost_codes, limit=limit)
        return {"status": "ok", "results": results}
    except Exception as exc:  # noqa: BLE001 - keep UI resilient
        logger.warning("symbols_search failed: %s", exc)
        return {"status": "error", "results": [], "message": "标的库暂不可用"}


@holdings_router.post("/parse-screenshot")
async def holdings_parse_screenshot(
    file: UploadFile,
    existing_codes: str = Query("", description="Comma-separated existing holding codes"),
) -> Dict[str, object]:
    """Parse a broker holdings screenshot into preview rows."""
    if file.content_type not in _ALLOWED_SCREENSHOT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unsupported_image_type")
    data = await file.read()
    if len(data) > _MAX_SCREENSHOT_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="file_too_large")
    try:
        parsed = holdings_parse.parse_holdings_image(data)
    except ValueError as exc:
        code = str(exc).split(":", 1)[0]
        http_status = status.HTTP_400_BAD_REQUEST if code in {"ocr_empty", "ocr_failed"} else status.HTTP_422_UNPROCESSABLE_ENTITY
        raise HTTPException(status_code=http_status, detail=code) from exc
    except Exception as exc:  # noqa: BLE001
        logger.warning("holdings_parse_screenshot failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="parse_failed") from exc

    existing = {c.strip() for c in existing_codes.split(",") if c.strip()}
    rows = parsed.get("rows", [])
    if existing:
        for row in rows:
            if isinstance(row, dict):
                row["action"] = "update" if str(row.get("code") or "") in existing else "append"
    return {"status": "ok", "rows": rows, "meta": parsed.get("meta", {})}


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
