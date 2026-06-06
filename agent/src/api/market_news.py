"""Pure news-fetching/parsing for the 新闻 (news) page.

Kept free of FastAPI so parsing can be unit-tested without the web framework.
Fetches the free Sina rolling finance news feed (JSON) and normalizes it into
``{source, time, title, summary, url, tickers}`` rows. ``tickers`` is a best
effort keyword match against the watchlist names so news can be tagged.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List

import httpx

# Sina rolling news, lid=2509 is the finance channel. Free, no key.
_SINA_NEWS_URL = (
    "https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2509&num=20&page=1"
)

# Names used to tag a headline with related tickers (best effort substring match).
WATCHLIST_NAMES: List[str] = [
    "绿的谐波", "三花智控", "拓普集团", "双环传动", "汇川技术", "兆威机电",
    "中际旭创", "沪电股份", "胜宏科技", "天孚通信", "寒武纪", "海光信息",
    "光模块", "减速器", "丝杠", "PCB", "人形机器人", "算力", "AI芯片",
]


def _fmt_time(ctime: object) -> str:
    """Sina ctime is an epoch-second string; format to ``YYYY-MM-DD HH:MM``."""
    try:
        return datetime.fromtimestamp(int(str(ctime))).strftime("%Y-%m-%d %H:%M")
    except (ValueError, OSError, TypeError):
        return ""


def tag_tickers(text: str) -> List[str]:
    return [name for name in WATCHLIST_NAMES if name in text]


def parse_sina_news(payload: Dict) -> List[Dict[str, object]]:
    """Parse a Sina rolling-news JSON payload into normalized news rows."""
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
        })
    return rows


async def fetch_news() -> List[Dict[str, object]]:
    async with httpx.AsyncClient(timeout=8.0, headers={"User-Agent": "Mozilla/5.0"}) as client:
        resp = await client.get(_SINA_NEWS_URL)
        resp.raise_for_status()
        payload = resp.json()
    return parse_sina_news(payload)
