"""Tests for screener tracking rules (consecutive new lows / bearish MA)."""

from __future__ import annotations

import pandas as pd

from src.screener import tracking_rules


def _ohlcv(closes: list[float], start: str = "2026-06-01") -> pd.DataFrame:
    """构造仅含 close 的日线表，按交易日（自然日近似）升序索引。"""
    idx = pd.bdate_range(start=start, periods=len(closes))
    return pd.DataFrame({"close": closes}, index=idx)


def test_consecutive_new_lows_hits_streak() -> None:
    # day0=首日 100；随后逐日创新低：99, 98, 97 -> 连续 3 日创新低。
    df = _ohlcv([100, 99, 98, 97])
    res = tracking_rules.evaluate(df, "2026-06-01", new_low_streak=3)
    assert res["consec_new_low"] == 3
    assert res["new_low_hit"] is True
    assert res["min_close_since_entry"] == 97


def test_new_low_streak_resets_on_bounce() -> None:
    # 100, 99(新低), 100(反弹，非新低) -> 末尾连续创新低为 0。
    df = _ohlcv([100, 99, 100])
    res = tracking_rules.evaluate(df, "2026-06-01", new_low_streak=3)
    assert res["consec_new_low"] == 0
    assert res["new_low_hit"] is False


def test_new_low_below_streak_not_hit() -> None:
    # 仅连续 2 日创新低，阈值 3 -> 未命中。
    df = _ohlcv([100, 99, 98])
    res = tracking_rules.evaluate(df, "2026-06-01", new_low_streak=3)
    assert res["consec_new_low"] == 2
    assert res["new_low_hit"] is False


def test_new_low_window_starts_at_day0() -> None:
    # day0 之前的低点不参与“入池以来新低”判断：
    # 序列前段下跌到很低，day0 之后温和回升，则不应判为创新低。
    closes = [50, 45, 40] + [60, 61, 62, 63]
    df = _ohlcv(closes, start="2026-05-01")
    day0 = df.index[3].strftime("%Y-%m-%d")
    res = tracking_rules.evaluate(df, day0, new_low_streak=3)
    assert res["consec_new_low"] == 0
    assert res["min_close_since_entry"] == 60


def test_bearish_ma_strict_alignment() -> None:
    # 单调下跌 80 日 -> MA5<MA10<MA20<MA60 成立。
    closes = [float(200 - i) for i in range(80)]
    df = _ohlcv(closes)
    res = tracking_rules.evaluate(df, df.index[-1].strftime("%Y-%m-%d"))
    assert res["bearish_ma"] is True
    ma = res["ma"]
    assert ma["ma5"] < ma["ma10"] < ma["ma20"] < ma["ma60"]


def test_bullish_ma_not_bearish() -> None:
    # 单调上涨 80 日 -> 多头排列，bearish_ma=False。
    closes = [float(100 + i) for i in range(80)]
    df = _ohlcv(closes)
    res = tracking_rules.evaluate(df, df.index[-1].strftime("%Y-%m-%d"))
    assert res["bearish_ma"] is False


def test_insufficient_history_no_bearish() -> None:
    # 不足 60 日：即使下跌也不判定空头排列（避免误剔）。
    closes = [float(100 - i) for i in range(30)]
    df = _ohlcv(closes)
    res = tracking_rules.evaluate(df, df.index[0].strftime("%Y-%m-%d"))
    assert res["bearish_ma"] is False
    assert res["ma"]["ma60"] is None
    assert res["ma"]["ma5"] is not None


def test_empty_ohlcv_returns_no_data() -> None:
    res = tracking_rules.evaluate(pd.DataFrame(), "2026-06-01")
    assert res["has_data"] is False
    assert res["new_low_hit"] is False
    assert res["bearish_ma"] is False


def test_trading_days_tracked_counts_from_day0() -> None:
    df = _ohlcv([100, 99, 98, 101, 102])
    res = tracking_rules.evaluate(df, "2026-06-01")
    # 5 个交易日，day0 记为 0 -> 4。
    assert res["trading_days_tracked"] == 4


def test_day0_before_data_start_uses_all_history() -> None:
    # day0 早于现有数据起点：整段都视为跟踪期。
    df = _ohlcv([100, 99, 98, 97], start="2026-06-10")
    res = tracking_rules.evaluate(df, "2026-01-01", new_low_streak=3)
    assert res["trading_days_tracked"] == 3
    assert res["consec_new_low"] == 3


def test_day0_after_last_bar_no_tracking_days() -> None:
    # day0 晚于最后可用交易日（入池后停牌）：尚无跟踪数据，
    # trading_days_tracked=0、不创新低，但 MA 仍按历史计算（此处不足 60 日故为 None）。
    df = _ohlcv([100, 99, 98, 97], start="2026-06-01")
    last = df.index[-1]
    day0 = (last + pd.Timedelta(days=7)).strftime("%Y-%m-%d")
    res = tracking_rules.evaluate(df, day0, new_low_streak=3)
    assert res["has_data"] is True
    assert res["trading_days_tracked"] == 0
    assert res["consec_new_low"] == 0
    assert res["new_low_hit"] is False
    assert res["last_close"] == 97
