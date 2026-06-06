"""Merge and dedupe normalized news rows from multiple providers."""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

_WS_RE = re.compile(r"\s+")


def normalize_title(title: str) -> str:
    """Collapse whitespace for fuzzy dedupe keys."""
    return _WS_RE.sub("", (title or "").strip())


def merge_news_rows(
    batches: List[Tuple[str, List[Dict[str, object]]]],
    *,
    limit: int = 80,
) -> List[Dict[str, object]]:
    """Merge provider batches, dedupe by title, sort newest first."""
    merged: List[Dict[str, object]] = []
    seen_titles: set[str] = set()
    seen_urls: set[str] = set()

    for _provider_id, rows in batches:
        for row in rows:
            title_key = normalize_title(str(row.get("title") or ""))
            url = str(row.get("url") or "").strip()
            if not title_key:
                continue
            if title_key in seen_titles:
                continue
            if url and url in seen_urls:
                continue
            seen_titles.add(title_key)
            if url:
                seen_urls.add(url)
            merged.append(row)

    merged.sort(key=lambda r: str(r.get("time") or ""), reverse=True)
    return merged[:limit]
