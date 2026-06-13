"""Weighted scoring for the A-share limit-up screener."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.screener.config import ScreenerConfig

_SIGNAL_COLUMNS = {
    "limitup": "signal_limitup",
    "volume": "signal_volume",
    "gap": "signal_gap",
    "yang": "signal_yang",
}

_VETO_COLUMNS = {
    "low_position": "veto_low_position",
    "distribution": "veto_distribution",
    "overextended": "veto_overextended",
}


def passes_required_signals(row: dict | pd.Series, config: ScreenerConfig) -> bool:
    """True when every required signal meets ``required_signal_min``."""
    minimum = float(config.required_signal_min)
    for key in config.required_signals:
        column = _SIGNAL_COLUMNS.get(key)
        if column is None:
            continue
        if float(_cell(row, column, 0.0)) < minimum:
            return False
    return True


def _cell(row: dict | pd.Series, key: str, default: Any = 0.0) -> Any:
    """Read one field from a dict-like row."""
    if isinstance(row, pd.Series):
        return row[key] if key in row.index else default
    return row.get(key, default)


def _as_bool(value: Any) -> bool:
    """Coerce veto/untradable flags to bool."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return False
    return bool(value)


def score_row(row: dict | pd.Series, config: ScreenerConfig) -> float:
    """Weighted sum 0-100 from signal_limitup, signal_volume, signal_gap, signal_yang."""
    weights = config.weights
    weighted = (
        weights["limitup"] * float(_cell(row, "signal_limitup", 0.0))
        + weights["volume"] * float(_cell(row, "signal_volume", 0.0))
        + weights["gap"] * float(_cell(row, "signal_gap", 0.0))
        + weights["yang"] * float(_cell(row, "signal_yang", 0.0))
    )
    return float(weighted * 100.0)


def apply_vetoes(
    score: float,
    row: dict | pd.Series,
    config: ScreenerConfig,
) -> float | None:
    """Return None when any veto column is True; else return the score."""
    _ = config
    for column in _VETO_COLUMNS.values():
        if _as_bool(_cell(row, column)):
            return None
    return score


def score_latest(signals_df: pd.DataFrame, config: ScreenerConfig) -> dict:
    """Take last row of signals_df, return scored result with signal/veto breakdown."""
    if signals_df.empty:
        raise ValueError("signals_df must not be empty")

    row = signals_df.iloc[-1]
    raw_score = score_row(row, config)
    required_passed = passes_required_signals(row, config)
    final_score = apply_vetoes(raw_score, row, config)

    filtered = not required_passed or final_score is None
    filter_reason: str | None = None
    if not required_passed:
        filter_reason = "missing_required"
    elif final_score is None:
        filter_reason = "veto"

    return {
        "score": final_score,
        "filtered": filtered,
        "filter_reason": filter_reason,
        "required_passed": required_passed,
        "signals": {
            key: float(_cell(row, col, 0.0))
            for key, col in _SIGNAL_COLUMNS.items()
        },
        "vetoes": {
            key: _as_bool(_cell(row, col))
            for key, col in _VETO_COLUMNS.items()
        },
        "position_pct": float(_cell(row, "position_pct", 0.0)),
        "untradable": _as_bool(_cell(row, "untradable")),
    }
