"""A-share symbol index and search helpers for holdings editing.

The production index comes from Tushare ``stock_basic`` and is cached in
process. Tests pass explicit rows, so ranking stays deterministic and does not
touch network or credentials.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Iterable, Mapping, Sequence

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 24 * 60 * 60
_cache_rows: list[dict[str, str]] | None = None
_cache_at = 0.0

_SEED_RECORDS = [
    {"symbol": "688017", "name": "绿的谐波", "cnspell": "LDXB", "ts_code": "688017.SH"},
    {"symbol": "002472", "name": "双环传动", "cnspell": "SHCD", "ts_code": "002472.SZ"},
    {"symbol": "601689", "name": "拓普集团", "cnspell": "TPJT", "ts_code": "601689.SH"},
    {"symbol": "002050", "name": "三花智控", "cnspell": "SHZK", "ts_code": "002050.SZ"},
    {"symbol": "300124", "name": "汇川技术", "cnspell": "HCKJ", "ts_code": "300124.SZ"},
    {"symbol": "003021", "name": "兆威机电", "cnspell": "ZWJD", "ts_code": "003021.SZ"},
    {"symbol": "300308", "name": "中际旭创", "cnspell": "ZJXC", "ts_code": "300308.SZ"},
    {"symbol": "002463", "name": "沪电股份", "cnspell": "HDGF", "ts_code": "002463.SZ"},
    {"symbol": "300476", "name": "胜宏科技", "cnspell": "SHKJ", "ts_code": "300476.SZ"},
    {"symbol": "300394", "name": "天孚通信", "cnspell": "TFTX", "ts_code": "300394.SZ"},
    {"symbol": "688256", "name": "寒武纪", "cnspell": "HWJ", "ts_code": "688256.SH"},
]


def _rows_from_records(records: Iterable[Mapping[str, object]]) -> list[dict[str, str]]:
    """Normalize Tushare-like records into frontend wire rows."""
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for record in records:
        code = str(record.get("symbol") or record.get("code") or "").strip()
        if "." in code:
            code = code.split(".", 1)[0]
        code = "".join(ch for ch in code if ch.isdigit())
        name = str(record.get("name") or "").strip()
        if len(code) != 6 or not name or code in seen:
            continue
        ts_code = str(record.get("ts_code") or "").strip()
        if not ts_code:
            suffix = "SH" if code.startswith(("6", "9")) else "SZ"
            ts_code = f"{code}.{suffix}"
        row: dict[str, str] = {
            "code": code,
            "name": name,
            "ts_code": ts_code,
            "cnspell": str(record.get("cnspell") or "").strip().upper(),
        }
        list_date = str(record.get("list_date") or "").strip()
        if list_date:
            row["list_date"] = list_date
        rows.append(row)
        seen.add(code)
    return rows


def _seed_rows() -> list[dict[str, str]]:
    return _rows_from_records(_SEED_RECORDS)


def default_boost_codes() -> set[str]:
    """Codes that should appear as empty-query suggestions."""
    return {row["code"] for row in _seed_rows()}


def _merge_seed_rows(rows: Sequence[dict[str, str]]) -> list[dict[str, str]]:
    seen = {row["code"] for row in rows}
    merged = list(rows)
    for row in _seed_rows():
        if row["code"] not in seen:
            merged.append(row)
            seen.add(row["code"])
    return merged


def load_index(force: bool = False) -> list[dict[str, str]]:
    """Load and cache the full A-share index.

    If Tushare is unavailable, returns the curated seed rows so the holdings UI
    remains usable for the dashboard's core symbols.
    """
    global _cache_rows, _cache_at
    now = time.time()
    if not force and _cache_rows is not None and now - _cache_at < _CACHE_TTL_SECONDS:
        return list(_cache_rows)

    token = os.getenv("TUSHARE_TOKEN", "").strip()
    try:
        if not token:
            raise RuntimeError("TUSHARE_TOKEN is not configured")
        import tushare as ts  # type: ignore

        pro = ts.pro_api(token)
        df = pro.stock_basic(
            list_status="L",
            fields="ts_code,symbol,name,cnspell,list_date",
        )
        rows = _rows_from_records(df.to_dict("records"))
        if not rows:
            raise RuntimeError("empty Tushare stock_basic response")
        _cache_rows = _merge_seed_rows(rows)
    except Exception as exc:  # noqa: BLE001 - UI can still use seed suggestions
        logger.warning("A-share symbol index fallback to seeds: %s", exc)
        _cache_rows = _seed_rows()

    _cache_at = now
    return list(_cache_rows)


def search_symbols(
    q: str,
    rows: Sequence[Mapping[str, str]],
    *,
    boost: set[str] | None = None,
    limit: int = 12,
) -> list[dict[str, str]]:
    """Search by 6-digit code, pinyin abbreviation, or Chinese name."""
    query = (q or "").strip()
    query_upper = query.upper()
    boosted = boost or set()
    normalized_rows = _rows_from_records(rows)

    if not query:
        return [row for row in normalized_rows if row["code"] in boosted][:limit]

    ranked: list[tuple[int, int, str, dict[str, str]]] = []
    for row in normalized_rows:
        code = row["code"]
        name = row["name"]
        cnspell = row["cnspell"].upper()
        tier: int | None = None
        if code.startswith(query):
            tier = 0
        elif cnspell.startswith(query_upper):
            tier = 1
        elif query in name:
            tier = 2
        if tier is None:
            continue
        ranked.append((tier, 0 if code in boosted else 1, code, row))

    ranked.sort(key=lambda item: item[:3])
    return [row for *_prefix, row in ranked[:limit]]
