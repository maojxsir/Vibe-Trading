"""Tests for A-share screener signal computation."""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import pytest

from src.screener.board import is_limit_up
from src.screener.config import ScreenerConfig
from src.screener.signals import compute_signal_series


def _make_df(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df.set_index("trade_date").sort_index()


def _date_seq(start: str, n: int) -> list[pd.Timestamp]:
    base = pd.Timestamp(start)
    return [base + pd.Timedelta(days=i) for i in range(n)]


def _flat_ohlcv(
    dates: list[pd.Timestamp],
    *,
    close: float = 100.0,
    vol: float = 1_000_000.0,
    turnover_rate: float = 5.0,
) -> list[dict]:
    """Build flat OHLCV rows with small daily variation."""
    rows: list[dict] = []
    prev = close * 0.99
    for i, dt in enumerate(dates):
        o = prev
        c = close if i == len(dates) - 1 else close
        rows.append(
            {
                "trade_date": dt,
                "open": o,
                "high": max(o, c) + 0.5,
                "low": min(o, c) - 0.5,
                "close": c,
                "pre_close": prev,
                "vol": vol,
                "turnover_rate": turnover_rate,
                "pct_chg": (c - prev) / prev * 100,
            }
        )
        prev = c
    return rows


EXPECTED_COLUMNS = {
    "signal_limitup",
    "signal_volume",
    "signal_gap",
    "signal_yang",
    "veto_low_position",
    "veto_distribution",
    "veto_overextended",
    "position_pct",
    "untradable",
}


@pytest.fixture
def config() -> ScreenerConfig:
    return ScreenerConfig()


def test_output_schema(config: ScreenerConfig) -> None:
    dates = _date_seq("2024-01-02", 30)
    df = _make_df(_flat_ohlcv(dates))
    result = compute_signal_series(
        df, code="600519", name="贵州茅台", config=config
    )
    assert set(result.columns) == EXPECTED_COLUMNS
    assert result.index.equals(df.index)
    for col in ("signal_limitup", "signal_volume", "signal_gap", "signal_yang"):
        assert (result[col] >= 0).all()
        assert (result[col] <= 1).all()
    assert (result["position_pct"] >= 0).all()
    assert (result["position_pct"] <= 1).all()


def test_limitup_main_board_triggers_signal(config: ScreenerConfig) -> None:
    """One 9.8% limit-up day on 600519 should produce signal_limitup > 0."""
    dates = _date_seq("2024-01-02", 25)
    rows = _flat_ohlcv(dates, close=100.0, vol=1_000_000.0, turnover_rate=5.0)
    limit_idx = 15
    prev_close = rows[limit_idx - 1]["close"]
    limit_close = prev_close * 1.098
    rows[limit_idx].update(
        {
            "open": prev_close * 1.02,
            "high": limit_close,
            "low": prev_close * 1.01,
            "close": limit_close,
            "pct_chg": 9.8,
            "turnover_rate": 8.0,
            "pre_close": prev_close,
        }
    )
    for i in range(limit_idx + 1, len(rows)):
        prev = rows[i - 1]["close"]
        rows[i]["pre_close"] = prev
        rows[i]["close"] = prev
        rows[i]["open"] = prev
        rows[i]["high"] = prev + 0.5
        rows[i]["low"] = prev - 0.5
        rows[i]["pct_chg"] = 0.0

    df = _make_df(rows)
    result = compute_signal_series(
        df, code="600519", name="贵州茅台", config=config
    )
    limit_date = dates[limit_idx]
    assert is_limit_up(9.8, "600519", "贵州茅台")
    assert result.loc[limit_date, "signal_limitup"] > 0
    assert result.loc[dates[limit_idx + 3], "signal_limitup"] > 0


def test_limitup_chinext_19pct_not_limit_up(config: ScreenerConfig) -> None:
    """19% on chinext 300308 is below 20% threshold — no limit-up signal."""
    dates = _date_seq("2024-01-02", 25)
    rows = _flat_ohlcv(dates, close=50.0, vol=2_000_000.0, turnover_rate=10.0)
    limit_idx = 15
    prev_close = rows[limit_idx - 1]["close"]
    limit_close = prev_close * 1.19
    rows[limit_idx].update(
        {
            "open": prev_close * 1.05,
            "high": limit_close,
            "low": prev_close * 1.03,
            "close": limit_close,
            "pct_chg": 19.0,
            "turnover_rate": 10.0,
            "pre_close": prev_close,
        }
    )
    df = _make_df(rows)
    result = compute_signal_series(
        df, code="300308", name="中际旭创", config=config
    )
    assert is_limit_up(19.0, "300308", "中际旭创") is False
    assert result.loc[dates[limit_idx], "signal_limitup"] == 0.0


def test_volume_insufficient_history_zero(config: ScreenerConfig) -> None:
    """Fewer than recent+prior window bars must not emit a fake volume score."""
    dates = _date_seq("2024-01-02", 40)  # < 30 + 30
    df = _make_df(_flat_ohlcv(dates))
    result = compute_signal_series(
        df, code="600519", name="贵州茅台", config=config
    )
    assert (result["signal_volume"] == 0.0).all()


def test_volume_recent_double_prior_full_signal(config: ScreenerConfig) -> None:
    """Recent 30-day avg volume = 2x the prior 30-day avg -> full volume score."""
    dates = _date_seq("2024-01-02", 65)
    base_vol = 1_000_000.0
    rows = _flat_ohlcv(dates, vol=base_vol)
    # 最近 30 个交易日量能翻倍（前 30 日为基准量）
    for i in range(len(rows) - 30, len(rows)):
        rows[i]["vol"] = base_vol * 2.0
    df = _make_df(rows)
    result = compute_signal_series(
        df, code="600519", name="贵州茅台", config=config
    )
    assert result.iloc[-1]["signal_volume"] == pytest.approx(1.0)


def test_volume_recent_no_expansion_zero(config: ScreenerConfig) -> None:
    """Flat volume (recent ≈ prior) yields ~0 volume score."""
    dates = _date_seq("2024-01-02", 65)
    df = _make_df(_flat_ohlcv(dates, vol=1_000_000.0))
    result = compute_signal_series(
        df, code="600519", name="贵州茅台", config=config
    )
    assert result.iloc[-1]["signal_volume"] == pytest.approx(0.0)


def test_volume_recent_partial_expansion_graded(config: ScreenerConfig) -> None:
    """Recent avg = 1.75x prior avg -> graded ~0.5 between min(1.5x) and full(2x)."""
    dates = _date_seq("2024-01-02", 65)
    base_vol = 1_000_000.0
    rows = _flat_ohlcv(dates, vol=base_vol)
    for i in range(len(rows) - 30, len(rows)):
        rows[i]["vol"] = base_vol * 1.75
    df = _make_df(rows)
    result = compute_signal_series(
        df, code="600519", name="贵州茅台", config=config
    )
    assert result.iloc[-1]["signal_volume"] == pytest.approx(0.5, abs=0.05)


def test_volume_below_50pct_expansion_zero(config: ScreenerConfig) -> None:
    """Recent avg only +30% over prior (1.3x < 1.5x floor) -> 0 score (excluded)."""
    dates = _date_seq("2024-01-02", 65)
    base_vol = 1_000_000.0
    rows = _flat_ohlcv(dates, vol=base_vol)
    for i in range(len(rows) - 30, len(rows)):
        rows[i]["vol"] = base_vol * 1.3
    df = _make_df(rows)
    result = compute_signal_series(
        df, code="600519", name="贵州茅台", config=config
    )
    assert result.iloc[-1]["signal_volume"] == pytest.approx(0.0)


def test_gap_unfilled_high_signal(config: ScreenerConfig) -> None:
    """Up gap followed by 3 days without fill should yield signal_gap > 0."""
    dates = _date_seq("2024-01-02", 30)
    rows = _flat_ohlcv(dates, close=100.0, vol=1_000_000.0)
    gap_idx = 20
    prev_high = rows[gap_idx - 1]["high"]
    gap_low = prev_high + 2.0
    gap_close = gap_low + 3.0
    rows[gap_idx].update(
        {
            "open": gap_low + 0.5,
            "low": gap_low,
            "high": gap_close + 1.0,
            "close": gap_close,
            "vol": 2_500_000.0,
            "pct_chg": 3.0,
        }
    )
    hold_close = gap_close
    for offset in range(1, 4):
        idx = gap_idx + offset
        rows[idx].update(
            {
                "open": hold_close,
                "low": prev_high + 0.5,
                "high": hold_close + 1.0,
                "close": hold_close,
                "vol": 1_200_000.0,
                "pct_chg": 0.0,
            }
        )
    df = _make_df(rows)
    result = compute_signal_series(
        df, code="600519", name="贵州茅台", config=config
    )
    assert result.loc[dates[gap_idx + 3], "signal_gap"] > 0


def test_yang_four_streak_high_signal(config: ScreenerConfig) -> None:
    """Four consecutive yang lines should yield high signal_yang."""
    dates = _date_seq("2024-01-02", 20)
    rows: list[dict] = []
    price = 100.0
    for i, dt in enumerate(dates):
        if i >= 12:
            o = price
            c = price + 2.0
            price = c
        else:
            o = price
            c = price - 0.5
            price = c
        rows.append(
            {
                "trade_date": dt,
                "open": o,
                "high": max(o, c) + 0.3,
                "low": min(o, c) - 0.3,
                "close": c,
                "pre_close": o,
                "vol": 1_000_000.0,
                "turnover_rate": 5.0,
                "pct_chg": (c - o) / o * 100,
            }
        )
    df = _make_df(rows)
    result = compute_signal_series(
        df, code="600519", name="贵州茅台", config=config
    )
    assert result.iloc[-1]["signal_yang"] >= 0.7


def test_veto_low_position_at_high(config: ScreenerConfig) -> None:
    """Price at 250-day high should trigger veto_low_position."""
    dates = _date_seq("2023-01-02", 260)
    rows: list[dict] = []
    for i, dt in enumerate(dates):
        close = 50.0 + i * 0.2
        rows.append(
            {
                "trade_date": dt,
                "open": close - 0.1,
                "high": close + 0.5,
                "low": close - 0.5,
                "close": close,
                "pre_close": close - 0.1,
                "vol": 1_000_000.0,
                "turnover_rate": 5.0,
                "pct_chg": 0.2,
            }
        )
    df = _make_df(rows)
    result = compute_signal_series(
        df, code="600519", name="贵州茅台", config=config
    )
    assert result.iloc[-1]["veto_low_position"] is True
    assert result.iloc[-1]["position_pct"] > config.position_veto_pct


def test_veto_distribution_long_upper_wicks(config: ScreenerConfig) -> None:
    """Volume spikes with long upper wicks and weak close trigger veto."""
    dates = _date_seq("2024-01-02", 40)
    rows = _flat_ohlcv(dates, close=100.0, vol=1_000_000.0)
    spike_indices = [10, 15, 20, 25, 30]
    for idx in spike_indices:
        o = rows[idx]["close"]
        rows[idx].update(
            {
                "open": o,
                "high": o + 8.0,
                "low": o - 1.0,
                "close": o + 0.5,
                "vol": 5_000_000.0,
                "turnover_rate": 15.0,
                "pct_chg": 0.5,
            }
        )
    df = _make_df(rows)
    result = compute_signal_series(
        df, code="600519", name="贵州茅台", config=config
    )
    assert result.iloc[-1]["veto_distribution"] is True


def test_veto_overextended_on_big_runup(config: ScreenerConfig) -> None:
    """A stock that more than doubled over the long lookback is vetoed."""
    dates = _date_seq("2024-01-02", 80)
    rows: list[dict] = []
    price = 10.0
    for i, dt in enumerate(dates):
        prev = price
        price = price * 1.02  # ~+345% over 80 bars, well past +100%/60d
        rows.append(
            {
                "trade_date": dt,
                "open": prev,
                "high": price + 0.1,
                "low": prev - 0.1,
                "close": price,
                "pre_close": prev,
                "vol": 1_000_000.0,
                "turnover_rate": 5.0,
                "pct_chg": (price - prev) / prev * 100,
            }
        )
    df = _make_df(rows)
    result = compute_signal_series(
        df, code="600519", name="贵州茅台", config=config
    )
    assert result.iloc[-1]["veto_overextended"] is True


def test_veto_overextended_base_window_catches_slow_bull(config: ScreenerConfig) -> None:
    """A name that doubled over ~120 days but is calm recently is still vetoed."""
    dates = _date_seq("2024-01-02", 140)
    rows: list[dict] = []
    price = 10.0
    for i, dt in enumerate(dates):
        prev = price
        # 前 120 根稳步翻倍多，最近 20 根基本走平（短/长窗口不触发，仅长周期触发）
        price = price * 1.012 if i < 120 else price * 1.001
        rows.append(
            {
                "trade_date": dt,
                "open": prev,
                "high": max(prev, price) + 0.05,
                "low": min(prev, price) - 0.05,
                "close": price,
                "pre_close": prev,
                "vol": 1_000_000.0,
                "turnover_rate": 5.0,
                "pct_chg": (price - prev) / prev * 100,
            }
        )
    df = _make_df(rows)
    result = compute_signal_series(
        df, code="600519", name="贵州茅台", config=config
    )
    last = result.iloc[-1]
    assert last["veto_overextended"] is True


def test_veto_overextended_disabled(config: ScreenerConfig) -> None:
    """No overheat veto fires for a flat name, and the column stays boolean."""
    dates = _date_seq("2024-01-02", 70)
    df = _make_df(_flat_ohlcv(dates))
    result = compute_signal_series(
        df, code="600519", name="贵州茅台", config=config
    )
    assert bool(result.iloc[-1]["veto_overextended"]) is False


def test_no_lookahead_limitup(config: ScreenerConfig) -> None:
    """Limit-up on day T must not affect signal on day T-1."""
    dates = _date_seq("2024-01-02", 25)
    rows = _flat_ohlcv(dates, close=100.0)
    limit_idx = 15
    prev_close = rows[limit_idx - 1]["close"]
    limit_close = prev_close * 1.098
    rows[limit_idx].update(
        {
            "open": prev_close * 1.02,
            "high": limit_close,
            "low": prev_close * 1.01,
            "close": limit_close,
            "pct_chg": 9.8,
            "turnover_rate": 8.0,
            "pre_close": prev_close,
        }
    )
    df = _make_df(rows)
    result = compute_signal_series(
        df, code="600519", name="贵州茅台", config=config
    )
    assert result.loc[dates[limit_idx - 1], "signal_limitup"] == 0.0
    assert result.loc[dates[limit_idx], "signal_limitup"] > 0.0
