"""Build the A-share screening universe from the symbol index."""

from __future__ import annotations

from datetime import date, datetime

from src.api import symbol_index
from src.screener.board import _is_delisting_name, _is_st_name, detect_board
from src.screener.config import ScreenerConfig


def _parse_list_date(raw: str | None) -> date | None:
    """Parse Tushare ``YYYYMMDD`` list dates; return None when missing or invalid."""
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y%m%d").date()
    except ValueError:
        return None


def _is_recent_listing(list_date: date | None, as_of: date, exclude_new_days: int) -> bool:
    """True when the listing falls within ``exclude_new_days`` calendar days of ``as_of``."""
    if exclude_new_days <= 0 or list_date is None:
        return False
    return (as_of - list_date).days <= exclude_new_days


def build_universe(config: ScreenerConfig, *, as_of: date | None = None) -> list[dict]:
    """Return list of {code, name, ts_code, board, list_date?}.

    Uses symbol_index.load_index().
    If config.exclude_st: skip names containing ST/*ST.
    If config.exclude_delisting: skip delisting names (含“退市”或以“退”结尾).
    If config.exclude_new_days > 0: skip if listed within N calendar days of as_of
    (default today).
    Attach board via detect_board(code, name).
    """
    reference = as_of or date.today()
    universe: list[dict] = []

    for row in symbol_index.load_index():
        code = row["code"]
        name = row["name"]

        if config.exclude_st and _is_st_name(name):
            continue

        if config.exclude_delisting and _is_delisting_name(name):
            continue

        parsed_list_date = _parse_list_date(row.get("list_date"))
        if _is_recent_listing(parsed_list_date, reference, config.exclude_new_days):
            continue

        entry: dict = {
            "code": code,
            "name": name,
            "ts_code": row["ts_code"],
            "board": detect_board(code, name),
        }
        list_date_raw = str(row.get("list_date") or "").strip()
        if list_date_raw:
            entry["list_date"] = list_date_raw

        universe.append(entry)

    return universe
