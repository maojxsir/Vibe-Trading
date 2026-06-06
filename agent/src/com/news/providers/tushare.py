"""Optional Tushare news provider (requires token + news API permission)."""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Dict, List

from src.com.news.tags import tag_tickers

# Fast sources with good A-share coverage; skipped when token missing.
_TUSHARE_SRCS = (
    ("tushare_cls", "cls", "财联社"),
    ("tushare_eastmoney", "eastmoney", "东方财富"),
    ("tushare_sina", "sina", "新浪财经"),
)
_PLACEHOLDERS = {"", "your-tushare-token"}


def _token_ok() -> bool:
    token = (os.environ.get("TUSHARE_TOKEN") or "").strip()
    return bool(token) and token not in _PLACEHOLDERS


def parse_tushare_rows(df, *, supplier: str, source_label: str) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    if df is None or getattr(df, "empty", True):
        return rows
    for rec in df.to_dict("records"):
        title = str(rec.get("title") or "").strip()
        content = str(rec.get("content") or "").strip()
        headline = title or content[:80]
        if not headline:
            continue
        summary = content if title else content[80:240].strip()
        dt = str(rec.get("datetime") or "")[:16]
        blob = f"{headline} {summary}"
        rows.append({
            "source": source_label,
            "time": dt,
            "title": headline,
            "summary": summary,
            "url": "",
            "tickers": tag_tickers(blob),
            "supplier": supplier,
        })
    return rows


async def fetch_tushare_news() -> Dict[str, object]:
    if not _token_ok():
        return {"rows": [], "ok": [], "errors": {}, "skipped": True}

    import asyncio

    def _pull() -> Dict[str, object]:
        import tushare as ts

        pro = ts.pro_api(os.environ["TUSHARE_TOKEN"].strip())
        end = datetime.now()
        start = end - timedelta(hours=24)
        start_s = start.strftime("%Y-%m-%d %H:%M:%S")
        end_s = end.strftime("%Y-%m-%d %H:%M:%S")
        all_rows: List[Dict[str, object]] = []
        ok: List[str] = []
        errors: Dict[str, str] = {}
        for supplier, src, label in _TUSHARE_SRCS:
            try:
                df = pro.news(src=src, start_date=start_s, end_date=end_s)
                rows = parse_tushare_rows(df, supplier=supplier, source_label=label)
                if rows:
                    all_rows.extend(rows)
                    ok.append(supplier)
                else:
                    errors[supplier] = "empty payload"
            except Exception as exc:  # noqa: BLE001
                errors[supplier] = str(exc)
        return {"rows": all_rows, "ok": ok, "errors": errors}

    return await asyncio.to_thread(_pull)
