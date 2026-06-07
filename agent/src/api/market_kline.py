"""Daily OHLCV bars for frontend K-line drawer."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd

from src.api import symbol_index

logger = logging.getLogger(__name__)

_MAX_DAYS = 500
_DEFAULT_DAYS = 365
_BARE_CODE = re.compile(r"^\d{6}$")


def normalize_bare_code(code: str) -> Optional[str]:
    """Strip exchange prefix and return a 6-digit A-share code, or None."""
    raw = (code or "").strip().lower()
    if raw.startswith(("sh", "sz", "bj")) and len(raw) > 2:
        raw = raw[2:]
    digits = "".join(ch for ch in raw if ch.isdigit())
    if not _BARE_CODE.match(digits):
        return None
    return digits


def lookup_symbol_name(code: str, fallback: Optional[str] = None) -> Optional[str]:
    """Resolve display name from the cached symbol index."""
    for row in symbol_index.load_index():
        if row.get("code") == code:
            return row.get("name") or fallback
    return fallback


def dataframe_to_bars(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Convert loader OHLCV frame to frontend ``PriceBar`` wire rows."""
    bars: List[Dict[str, Any]] = []
    for ts, row in df.iterrows():
        if hasattr(ts, "strftime"):
            time_str = ts.strftime("%Y-%m-%d")
        else:
            time_str = str(ts)[:10]
        bars.append(
            {
                "time": time_str,
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row.get("volume", 0) or 0),
            }
        )
    return bars


def fetch_kline(code: str, days: int = _DEFAULT_DAYS) -> Dict[str, Any]:
    """Fetch daily bars for one A-share symbol."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    bare = normalize_bare_code(code)
    if not bare:
        return {
            "code": (code or "").strip(),
            "name": None,
            "bars": [],
            "source": "",
            "stale": True,
            "updatedAt": now,
            "error": "invalid code",
        }

    window = max(1, min(int(days), _MAX_DAYS))
    end = datetime.now().date()
    start = end - timedelta(days=window)
    start_date = start.strftime("%Y-%m-%d")
    end_date = end.strftime("%Y-%m-%d")

    try:
        from backtest.loaders.registry import resolve_loader

        loader = resolve_loader("a_share")
        suffix = "SH" if bare.startswith(("6", "9")) else "SZ"
        ts_code = f"{bare}.{suffix}"
        frames = loader.fetch([bare, ts_code], start_date, end_date, interval="1D")
        df = frames.get(bare)
        if df is None or df.empty:
            df = frames.get(ts_code)
        if df is None or df.empty:
            return {
                "code": bare,
                "name": lookup_symbol_name(bare),
                "bars": [],
                "source": getattr(loader, "name", ""),
                "stale": True,
                "updatedAt": now,
                "error": "no data",
            }

        bars = dataframe_to_bars(df)
        return {
            "code": bare,
            "name": lookup_symbol_name(bare),
            "bars": bars,
            "source": getattr(loader, "name", ""),
            "stale": False,
            "updatedAt": now,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001 - degrade for UI
        logger.warning("fetch_kline failed for %r: %s", code, exc)
        return {
            "code": bare,
            "name": lookup_symbol_name(bare),
            "bars": [],
            "source": "",
            "stale": True,
            "updatedAt": now,
            "error": str(exc),
        }
