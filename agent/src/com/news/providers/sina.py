"""Sina rolling news feed provider(s)."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List

import httpx

from src.com.news.tags import tag_tickers

# lid=2509 finance; lid=2510 A-share / market headlines. Free, no key.
_SINA_FEEDS = (
    ("sina_finance", "https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2509&num=30&page={page}"),
    ("sina_stock", "https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2510&num=30&page={page}"),
)
_PAGES = (1, 2)
_UA = {"User-Agent": "Mozilla/5.0"}


def _fmt_time(ctime: object) -> str:
    try:
        return datetime.fromtimestamp(int(str(ctime))).strftime("%Y-%m-%d %H:%M")
    except (ValueError, OSError, TypeError):
        return ""


def parse_sina_payload(payload: Dict, *, supplier: str) -> List[Dict[str, object]]:
    """Parse a Sina rolling-news JSON payload into normalized rows."""
    items = (((payload or {}).get("result") or {}).get("data")) or []
    rows: List[Dict[str, object]] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        title = (it.get("title") or "").strip()
        if not title:
            continue
        summary = (it.get("intro") or "").strip()
        rows.append({
            "source": it.get("media_name") or "新浪财经",
            "time": _fmt_time(it.get("ctime")),
            "title": title,
            "summary": summary,
            "url": it.get("url") or "",
            "tickers": tag_tickers(f"{title} {summary}"),
            "supplier": supplier,
        })
    return rows


async def fetch_sina_feed(supplier: str, url_template: str) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    async with httpx.AsyncClient(timeout=8.0, headers=_UA) as client:
        for page in _PAGES:
            resp = await client.get(url_template.format(page=page))
            resp.raise_for_status()
            rows.extend(parse_sina_payload(resp.json(), supplier=supplier))
    return rows


async def fetch_all_sina() -> Dict[str, object]:
    """Fetch every configured Sina channel; return rows + per-feed status."""
    all_rows: List[Dict[str, object]] = []
    feeds_ok: List[str] = []
    errors: Dict[str, str] = {}
    for supplier, tmpl in _SINA_FEEDS:
        try:
            rows = await fetch_sina_feed(supplier, tmpl)
            if rows:
                all_rows.extend(rows)
                feeds_ok.append(supplier)
            else:
                errors[supplier] = "empty payload"
        except Exception as exc:  # noqa: BLE001
            errors[supplier] = str(exc)
    return {"rows": all_rows, "ok": feeds_ok, "errors": errors}
