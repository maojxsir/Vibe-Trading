"""Tests for ScreenerSignalEngine backtest signal generation."""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest

from src.screener.backtest_signal import ScreenerSignalEngine
from src.screener.config import ScreenerConfig


def _make_df(n: int, start: str = "2025-01-02") -> pd.DataFrame:
    dates = pd.date_range(start, periods=n, freq="B")
    return pd.DataFrame(
        {
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "pre_close": 99.0,
            "vol": 1_000_000.0,
            "turnover_rate": 5.0,
            "pct_chg": 1.0,
        },
        index=dates,
    )


def _signals_frame(
    index: pd.Index,
    *,
    scores: list[float | None],
    veto_low: list[bool] | None = None,
    veto_dist: list[bool] | None = None,
) -> pd.DataFrame:
    """Build a minimal signals_df where score_row returns ``scores`` per row."""
    n = len(index)
    veto_low = veto_low or [False] * n
    veto_dist = veto_dist or [False] * n
    rows: list[dict] = []
    for i in range(n):
        target = scores[i]
        if target is None:
            sig = 0.0
        else:
            sig = min(1.0, max(0.0, target / 100.0))
        rows.append(
            {
                "signal_limitup": sig,
                "signal_volume": sig,
                "signal_gap": sig,
                "signal_yang": sig,
                "veto_low_position": veto_low[i],
                "veto_distribution": veto_dist[i],
                "position_pct": 0.5,
                "untradable": False,
            }
        )
    return pd.DataFrame(rows, index=index)


@pytest.fixture
def engine() -> ScreenerSignalEngine:
    return ScreenerSignalEngine(
        ScreenerConfig(score_threshold=70.0),
        hold_days=5,
        score_threshold=70.0,
    )


def test_generate_returns_series_per_code(engine: ScreenerSignalEngine) -> None:
    df_a = _make_df(10)
    df_b = _make_df(8)
    data_map = {"600519.SH": df_a, "300308": df_b}

    with patch(
        "src.screener.backtest_signal.compute_signal_series",
        side_effect=lambda df, **kwargs: _signals_frame(
            df.index, scores=[50.0] * len(df)
        ),
    ):
        result = engine.generate(data_map)

    assert set(result.keys()) == {"600519.SH", "300308"}
    for key, series in result.items():
        assert isinstance(series, pd.Series)
        assert series.index.equals(data_map[key].index)
        assert series.dtype == float


def test_entry_on_high_score_holds_for_hold_days(
    engine: ScreenerSignalEngine,
) -> None:
    df = _make_df(12)
    scores = [50.0] * 12
    scores[3] = 90.0

    with patch(
        "src.screener.backtest_signal.compute_signal_series",
        return_value=_signals_frame(df.index, scores=scores),
    ):
        result = engine.generate({"600519": df})

    series = result["600519"]
    assert series.iloc[3:8].tolist() == [1.0] * 5
    assert series.iloc[8] == 0.0
    assert series.iloc[:3].tolist() == [0.0] * 3


def test_missing_required_never_entry(engine: ScreenerSignalEngine) -> None:
    df = _make_df(10)
    rows = []
    for i in range(10):
        rows.append(
            {
                "signal_limitup": 0.0,
                "signal_volume": 1.0,
                "signal_gap": 1.0,
                "signal_yang": 1.0,
                "veto_low_position": False,
                "veto_distribution": False,
                "position_pct": 0.5,
                "untradable": False,
            }
        )

    with patch(
        "src.screener.backtest_signal.compute_signal_series",
        return_value=pd.DataFrame(rows, index=df.index),
    ):
        result = engine.generate({"600519": df})

    assert result["600519"].tolist() == [0.0] * 10


def test_veto_days_never_entry(engine: ScreenerSignalEngine) -> None:
    df = _make_df(10)
    scores = [50.0] * 10
    scores[2] = 95.0
    veto_low = [False] * 10
    veto_low[2] = True

    with patch(
        "src.screener.backtest_signal.compute_signal_series",
        return_value=_signals_frame(
            df.index,
            scores=scores,
            veto_low=veto_low,
        ),
    ):
        result = engine.generate({"600519": df})

    assert result["600519"].tolist() == [0.0] * 10
