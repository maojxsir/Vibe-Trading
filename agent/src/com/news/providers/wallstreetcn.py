"""Wallstreetcn (华尔街见闻) live flash provider."""

from __future__ import annotations

import html
import re
from typing import Dict, List

import httpx

from src.com.news.tags import tag_tickers

_WSCN_URL = (
    "https://api-one-wscn.awtmt.com/apiv1/content/lives"
    "?channel=a-stock-channel&client=pc&limit=30"
)
_SUPPLIER = "wallstreetcn"
_UA = {"User-Agent": "Mozilla/5.0"}
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    plain = _TAG_RE.sub("", text or "")
    return html.unescape(plain).strip()


def parse_wallstreetcn_payload(payload: Dict) -> List[Dict[str, object]]:
    items = (((payload or {}).get("data") or {}).get("items")) or []
    rows: List[Dict[str, object]] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        title = (it.get("title") or "").strip()
        content = _strip_html(str(it.get("content") or ""))
        headline = title or content[:80]
        if not headline:
            continue
        summary = content if title else content[80:240].strip()
        ts = str(it.get("display_time") or it.get("created_at") or "")
        time_str = ts[:16].replace("T", " ") if ts else ""
        uri = str(it.get("uri") or "")
        url = f"https://wallstreetcn.com{uri}" if uri.startswith("/") else uri
        blob = f"{headline} {summary}"
        rows.append({
            "source": "华尔街见闻",
            "time": time_str,
            "title": headline,
            "summary": summary,
            "url": url,
            "tickers": tag_tickers(blob),
            "supplier": _SUPPLIER,
        })
    return rows


async def fetch_wallstreetcn() -> Dict[str, object]:
    try:
        async with httpx.AsyncClient(timeout=8.0, headers=_UA) as client:
            resp = await client.get(_WSCN_URL)
            resp.raise_for_status()
            rows = parse_wallstreetcn_payload(resp.json())
        if not rows:
            return {"rows": [], "ok": [], "errors": {_SUPPLIER: "empty payload"}}
        return {"rows": rows, "ok": [_SUPPLIER], "errors": {}}
    except Exception as exc:  # noqa: BLE001
        return {"rows": [], "ok": [], "errors": {_SUPPLIER: str(exc)}}
