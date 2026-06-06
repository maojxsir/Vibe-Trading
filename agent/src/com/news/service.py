"""Multi-source news aggregation entry point."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Dict, List

from src.com.news.merge import merge_news_rows
from src.com.news.providers.sina import fetch_all_sina
from src.com.news.providers.tushare import fetch_tushare_news
from src.com.news.providers.wallstreetcn import fetch_wallstreetcn

logger = logging.getLogger(__name__)

_DEFAULT_LIMIT = 80


async def fetch_merged_news(*, limit: int = _DEFAULT_LIMIT) -> Dict[str, object]:
    """Pull every configured provider in parallel, merge, dedupe, sort."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sina, wscn, ts = await asyncio.gather(
        fetch_all_sina(),
        fetch_wallstreetcn(),
        fetch_tushare_news(),
        return_exceptions=True,
    )

    batches: List[tuple[str, List[Dict[str, object]]]] = []
    providers_meta: Dict[str, Dict[str, object]] = {}

    for label, result in (("sina", sina), ("wallstreetcn", wscn), ("tushare", ts)):
        if isinstance(result, Exception):
            logger.warning("news provider %s failed: %s", label, result)
            providers_meta[label] = {"ok": False, "count": 0, "error": str(result)}
            continue
        if not isinstance(result, dict):
            continue
        rows = list(result.get("rows") or [])
        if rows:
            batches.append((label, rows))
        per_supplier: Dict[str, int] = {}
        for row in rows:
            sid = str(row.get("supplier") or label)
            per_supplier[sid] = per_supplier.get(sid, 0) + 1
        for pid in result.get("ok") or []:
            providers_meta[str(pid)] = {
                "ok": True,
                "count": per_supplier.get(str(pid), 0),
                "error": None,
            }
        for pid, err in (result.get("errors") or {}).items():
            providers_meta[str(pid)] = {"ok": False, "count": 0, "error": err}

    items = merge_news_rows(batches, limit=limit)
    ok_ids = [pid for pid, meta in providers_meta.items() if meta.get("ok")]
    stale = len(items) == 0

    source_labels = {
        "sina_finance": "新浪财经",
        "sina_stock": "新浪A股",
        "wallstreetcn": "华尔街见闻",
        "tushare_cls": "财联社",
        "tushare_eastmoney": "东方财富",
        "tushare_sina": "Tushare·新浪",
    }
    active_sources = [source_labels.get(pid, pid) for pid in ok_ids]

    return {
        "items": items,
        "updatedAt": now,
        "source": " · ".join(active_sources) if active_sources else "com/news",
        "stale": stale,
        "providers": providers_meta,
        "supplierCount": len(items),
    }
