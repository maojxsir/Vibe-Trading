"""Tests for Golden Phoenix screener detection."""

from __future__ import annotations

import pandas as pd

from src.screener.golden_phoenix import detect_golden_phoenix


def _build_confirmed_pattern_df() -> pd.DataFrame:
    rows = [
        {"date": "2026-06-01", "open": 8.8, "high": 9.0, "low": 8.7, "close": 9.0, "vol": 800_000},
        {"date": "2026-06-02", "open": 9.0, "high": 9.9, "low": 8.95, "close": 9.9, "vol": 1_500_000},
    ]
    lifeline = 9.9
    for day in ["2026-06-03", "2026-06-04", "2026-06-05", "2026-06-06", "2026-06-09", "2026-06-10"]:
        close = round(lifeline - 0.005, 2)
        rows.append(
            {
                "date": day,
                "open": close + 0.08,
                "high": lifeline,
                "low": close - 0.04,
                "close": close,
                "vol": 700_000,
            }
        )
    pre = rows[-1]["close"]
    second_limit = round(pre * 1.10, 2)
    rows.append(
        {
            "date": "2026-06-11",
            "open": pre,
            "high": second_limit,
            "low": pre * 0.99,
            "close": second_limit,
            "vol": 1_800_000,
        }
    )
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")


def test_detect_confirmed_second_board() -> None:
    match = detect_golden_phoenix(
        _build_confirmed_pattern_df(),
        code="600000",
        name="测试股份",
        trade_date="2026-06-11",
    )
    assert match is not None
    assert match.status == "confirmed"
    assert match.t0_date == "2026-06-02"
    assert match.score >= 90


def test_detect_watch_pool() -> None:
    df = _build_confirmed_pattern_df()
    df = df[df.index <= pd.Timestamp("2026-06-10")]
    match = detect_golden_phoenix(
        df,
        code="600000",
        name="测试股份",
        trade_date="2026-06-10",
    )
    assert match is not None
    assert match.status == "watch"


def test_reject_broken_lifeline() -> None:
    df = _build_confirmed_pattern_df()
    df.loc[pd.Timestamp("2026-06-05"), "close"] = 9.70
    match = detect_golden_phoenix(
        df,
        code="600000",
        name="测试股份",
        trade_date="2026-06-11",
    )
    assert match is None
