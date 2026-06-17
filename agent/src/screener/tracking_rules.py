"""打板跟踪的剔除规则计算（纯函数，无 I/O）。

两条价格规则（均基于收盘价）：

- 连续创新低：从入池日（day0）起，连续 ``new_low_streak`` 个交易日创“入池以来
  收盘新低”（当日收盘 < 此前所有跟踪日的最低收盘）。
- 均线空头排列：``MA5 < MA10 < MA20 < MA60``（四线严格空头排列）。数据不足 60 个
  交易日时不判定为空头（避免数据不足导致误剔）。

函数只接收 OHLCV 与参数、返回判定字段，便于单元测试覆盖各分支。
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

DEFAULT_NEW_LOW_STREAK = 3
DEFAULT_MA_WINDOWS = (5, 10, 20, 60)


def _normalized_index(ohlcv: pd.DataFrame) -> pd.DataFrame:
    """返回按日期升序、DatetimeIndex 归一化到自然日的副本。"""
    work = ohlcv.copy()
    if not isinstance(work.index, pd.DatetimeIndex):
        work.index = pd.to_datetime(work.index)
    work.index = work.index.normalize()
    return work.sort_index()


def _consecutive_new_lows(closes: list[float]) -> tuple[int, float]:
    """计算跟踪期收盘序列的“末尾连续创新低天数”与期间最低收盘。

    约定：day0（序列首日）作为基准，不计为创新低事件；自第二日起，若当日收盘
    严格低于此前所有日的最低收盘，则记为一次创新低。返回 (末尾连续创新低天数, 最低收盘)。
    """
    if not closes:
        return 0, float("nan")

    running_min = closes[0]
    flags: list[bool] = [False]  # 首日为基准
    for close in closes[1:]:
        is_new_low = close < running_min
        flags.append(is_new_low)
        if close < running_min:
            running_min = close

    consec = 0
    for flag in reversed(flags):
        if flag:
            consec += 1
        else:
            break
    return consec, float(min(closes))


def _bearish_ma(closes: pd.Series, windows: tuple[int, ...]) -> tuple[bool, dict[str, float | None]]:
    """计算最新一根的各周期均线，并判断是否严格空头排列。

    数据不足最长周期时，``bearish`` 返回 False，对应均线值为 None。
    """
    ma_values: dict[str, float | None] = {}
    computed: list[float] = []
    enough = len(closes) >= max(windows)
    for window in windows:
        key = f"ma{window}"
        if len(closes) >= window:
            value = float(closes.rolling(window, min_periods=window).mean().iloc[-1])
            ma_values[key] = value
            computed.append(value)
        else:
            ma_values[key] = None

    bearish = False
    if enough and len(computed) == len(windows) and not any(np.isnan(v) for v in computed):
        # 严格空头排列：短周期均线依次低于长周期均线。
        bearish = all(computed[i] < computed[i + 1] for i in range(len(computed) - 1))
    return bearish, ma_values


def evaluate(
    ohlcv: pd.DataFrame,
    day0_date: str,
    *,
    new_low_streak: int = DEFAULT_NEW_LOW_STREAK,
    ma_windows: tuple[int, ...] = DEFAULT_MA_WINDOWS,
) -> dict[str, Any]:
    """对单只股票计算跟踪判定字段。

    参数：
        ohlcv: 含 ``close`` 列、按交易日索引的日线数据（需包含 day0 之前的历史以算 MA60）。
        day0_date: 入池日（``YYYY-MM-DD``），用于界定“入池以来”的新低窗口。
        new_low_streak: 连续创新低触发阈值。
        ma_windows: 均线周期，默认 (5, 10, 20, 60)。

    返回字段：
        last_close, min_close_since_entry, consec_new_low, trading_days_tracked,
        ma(dict), bearish_ma(bool), new_low_hit(bool), has_data(bool)。
    """
    empty = {
        "last_close": None,
        "min_close_since_entry": None,
        "consec_new_low": 0,
        "trading_days_tracked": 0,
        "ma": {f"ma{w}": None for w in ma_windows},
        "bearish_ma": False,
        "new_low_hit": False,
        "has_data": False,
    }
    if ohlcv is None or ohlcv.empty or "close" not in ohlcv.columns:
        return empty

    work = _normalized_index(ohlcv)
    closes_all = pd.to_numeric(work["close"], errors="coerce").dropna()
    if closes_all.empty:
        return empty

    day0 = pd.Timestamp(day0_date).normalize()
    tracking_closes = closes_all.loc[closes_all.index >= day0]
    if tracking_closes.empty:
        if day0 < closes_all.index[0]:
            # day0 早于现有数据起点：以全部可用数据作为跟踪期。
            tracking_closes = closes_all
        else:
            # day0 晚于最后可用交易日（如入池后停牌）：尚无跟踪数据，
            # 以最后一根收盘作为基准（trading_days_tracked=0），避免误判到期/创新低。
            tracking_closes = closes_all.iloc[-1:]

    consec_new_low, min_close = _consecutive_new_lows([float(c) for c in tracking_closes])
    bearish, ma_values = _bearish_ma(closes_all, ma_windows)

    return {
        "last_close": float(closes_all.iloc[-1]),
        "min_close_since_entry": min_close,
        "consec_new_low": int(consec_new_low),
        "trading_days_tracked": int(max(0, len(tracking_closes) - 1)),
        "ma": ma_values,
        "bearish_ma": bool(bearish),
        "new_low_hit": bool(consec_new_low >= new_low_streak),
        "has_data": True,
    }
