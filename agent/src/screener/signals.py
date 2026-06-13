"""Pure signal functions for the A-share limit-up screener."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.screener.board import is_limit_up
from src.screener.config import ScreenerConfig

OUTPUT_COLUMNS = [
    "signal_limitup",
    "signal_volume",
    "signal_gap",
    "signal_yang",
    "veto_low_position",
    "veto_distribution",
    "veto_overextended",
    "position_pct",
    "untradable",
]


def compute_signal_series(
    df: pd.DataFrame,
    *,
    code: str,
    name: str,
    config: ScreenerConfig,
    index_ret: pd.Series | None = None,
) -> pd.DataFrame:
    """Return DataFrame indexed by trade_date with signal and veto columns.

    Columns: signal_limitup, signal_volume, signal_gap, signal_yang,
    veto_low_position, veto_distribution, position_pct, untradable.
    All signal_* in [0, 1]. veto_* are bool. position_pct in [0, 1].
    """
    work = _prepare_ohlcv(df)

    signal_limitup = _compute_limitup_signal(work, code, name, config)
    signal_volume = _compute_volume_signal(work, config)
    signal_gap = _compute_gap_signal(work, config)
    signal_yang = _compute_yang_signal(work, config, index_ret)
    position_pct = _compute_position_pct(work, config)
    veto_low_position = pd.Series(
        [bool(x) for x in position_pct > config.position_veto_pct],
        index=work.index,
        dtype=object,
    )
    veto_distribution = pd.Series(
        [bool(x) for x in _compute_veto_distribution(work, config)],
        index=work.index,
        dtype=object,
    )
    veto_overextended = pd.Series(
        [bool(x) for x in _compute_veto_overextended(work, config)],
        index=work.index,
        dtype=object,
    )
    untradable = pd.Series(
        [bool(x) for x in _compute_untradable(work, code, name, config)],
        index=work.index,
        dtype=object,
    )

    return pd.DataFrame(
        {
            "signal_limitup": signal_limitup,
            "signal_volume": signal_volume,
            "signal_gap": signal_gap,
            "signal_yang": signal_yang,
            "veto_low_position": veto_low_position,
            "veto_distribution": veto_distribution,
            "veto_overextended": veto_overextended,
            "position_pct": position_pct,
            "untradable": untradable,
        },
        index=work.index,
    )


def _prepare_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names and derive pct_chg when missing."""
    work = df.copy()
    if "vol" not in work.columns and "volume" in work.columns:
        work["vol"] = work["volume"]
    if "pct_chg" not in work.columns:
        if "pre_close" in work.columns:
            work["pct_chg"] = (work["close"] - work["pre_close"]) / work[
                "pre_close"
            ] * 100.0
        else:
            work["pct_chg"] = work["close"].pct_change() * 100.0
    if "turnover_rate" not in work.columns:
        work["turnover_rate"] = np.nan
    return work


def _limitup_quality(row: pd.Series) -> float:
    """Score limit-up day quality from turnover and close-near-high."""
    turnover = row.get("turnover_rate", np.nan)
    high = row["high"]
    low = row["low"]
    close = row["close"]
    rng = high - low
    close_near_high = (close - low) / rng >= 0.8 if rng > 0 else True

    if pd.isna(turnover):
        return 0.7 if close_near_high else 0.5

    quality = 0.5
    if 3.0 <= turnover <= 15.0 and close_near_high:
        quality = 1.0
    elif turnover < 1.0:
        quality = 0.5
    elif close_near_high:
        quality = 0.8
    return quality


def _limitup_recency_decay(days_since: int) -> float:
    """Decay factor based on days since the most recent limit-up."""
    if days_since < 0:
        return 0.0
    if days_since <= 5:
        return 1.0
    if days_since <= 10:
        return 0.8
    if days_since <= 20:
        return 0.6
    return 0.0


def _compute_limitup_signal(
    df: pd.DataFrame,
    code: str,
    name: str,
    config: ScreenerConfig,
) -> pd.Series:
    """Rolling limit-up window with quality and recency decay."""
    n = len(df)
    tolerance = config.limit_up_tolerance
    window = config.limitup_window
    limit_up_flags = df["pct_chg"].apply(
        lambda x: is_limit_up(x, code, name, tolerance=tolerance)
        if pd.notna(x)
        else False
    )
    scores = np.zeros(n, dtype=float)

    for i in range(n):
        start = max(0, i - window + 1)
        best = 0.0
        for j in range(start, i + 1):
            if not limit_up_flags.iloc[j]:
                continue
            quality = _limitup_quality(df.iloc[j])
            days_since = i - j
            decay = _limitup_recency_decay(days_since)
            best = max(best, quality * decay)
        scores[i] = best

    return pd.Series(scores, index=df.index, name="signal_limitup")


def _compute_volume_signal(df: pd.DataFrame, config: ScreenerConfig) -> pd.Series:
    """Volume expansion: recent-window avg volume vs the prior-window avg volume.

    ``ratio = mean(vol over last vol_recent_window) /
    mean(vol over the vol_prior_window bars immediately before that)``.

    Graded score: 0 at ``vol_expansion_min`` (no expansion), 1.0 at
    ``vol_expansion_full`` (e.g. 2x = doubled), linear in between. Using two
    equal-length windows of 20-day-scale averages makes the signal robust to a
    single blow-off day (it is diluted across the whole recent window).
    """
    recent = config.vol_recent_window
    prior = config.vol_prior_window
    needed = recent + prior
    if recent <= 0 or prior <= 0 or len(df) < needed:
        return pd.Series(0.0, index=df.index, name="signal_volume")

    vol = df["vol"]
    recent_avg = vol.rolling(recent, min_periods=recent).mean()
    prior_avg = vol.shift(recent).rolling(prior, min_periods=prior).mean()
    ratio = recent_avg / prior_avg.replace(0, np.nan)

    span = config.vol_expansion_full - config.vol_expansion_min
    if span <= 0:
        score = (ratio >= config.vol_expansion_full).astype(float)
    else:
        score = ((ratio - config.vol_expansion_min) / span).clip(0.0, 1.0)
    score = score.fillna(0.0)
    return pd.Series(score.to_numpy(), index=df.index, name="signal_volume")


def _gap_day_score(
    df: pd.DataFrame,
    gap_idx: int,
    as_of_idx: int,
    config: ScreenerConfig,
) -> float:
    """Score a single up-gap as of as_of_idx (no look-ahead)."""
    if gap_idx <= 0 or gap_idx > as_of_idx:
        return 0.0

    prev_high = df.iloc[gap_idx - 1]["high"]
    gap_low = df.iloc[gap_idx]["low"]
    if gap_low <= prev_high:
        return 0.0

    hold_end = min(gap_idx + config.gap_hold_days, as_of_idx)
    if hold_end < gap_idx + config.gap_hold_days:
        return 0.0

    lows_after = df.iloc[gap_idx + 1 : hold_end + 1]["low"]
    if (lows_after < prev_high).any():
        return 0.0

    vol_ma_long = df["vol"].rolling(config.vol_ma_long, min_periods=1).mean()
    gap_vol = df.iloc[gap_idx]["vol"]
    ma20 = vol_ma_long.iloc[gap_idx]
    volume_confirm = gap_vol >= ma20 * 1.5 if pd.notna(ma20) and ma20 > 0 else False
    return 1.0 if volume_confirm else 0.6


def _compute_gap_signal(df: pd.DataFrame, config: ScreenerConfig) -> pd.Series:
    """Up-gap signal with hold confirmation and volume check."""
    n = len(df)
    scores = np.zeros(n, dtype=float)

    for i in range(n):
        start = max(1, i - config.gap_lookback + 1)
        best = 0.0
        for j in range(start, i + 1):
            best = max(best, _gap_day_score(df, j, i, config))
        scores[i] = best

    return pd.Series(scores, index=df.index, name="signal_gap")


def _yang_streak_and_body(df: pd.DataFrame, end_idx: int) -> tuple[int, float]:
    """Longest yang streak ending at end_idx and mean body quality in that streak."""
    streak = 0
    bodies: list[float] = []
    for j in range(end_idx, -1, -1):
        row = df.iloc[j]
        o, c, h, l = row["open"], row["close"], row["high"], row["low"]
        if c <= o:
            break
        streak += 1
        rng = h - l
        body = abs(c - o) / rng if rng > 0 else 0.0
        bodies.append(body)

    mean_body = float(np.mean(bodies)) if bodies else 0.0
    return streak, mean_body


def _relative_strength_bonus(
    df: pd.DataFrame,
    end_idx: int,
    streak: int,
    index_ret: pd.Series | None,
) -> float:
    """Bonus when stock outperforms index over the yang streak window."""
    if index_ret is None or streak <= 0:
        return 0.0
    start_idx = max(0, end_idx - streak + 1)
    dates = df.index[start_idx : end_idx + 1]
    aligned_index = index_ret.reindex(dates)
    if aligned_index.isna().all():
        return 0.0

    stock_ret = (
        df.iloc[end_idx]["close"] / df.iloc[start_idx]["close"] - 1.0
        if df.iloc[start_idx]["close"] > 0
        else 0.0
    )
    index_cum = float((1.0 + aligned_index.fillna(0.0)).prod() - 1.0)
    if stock_ret > index_cum:
        return 0.15
    return 0.0


def _compute_yang_signal(
    df: pd.DataFrame,
    config: ScreenerConfig,
    index_ret: pd.Series | None,
) -> pd.Series:
    """Consecutive yang-line score with body quality and relative strength."""
    n = len(df)
    scores = np.zeros(n, dtype=float)
    min_streak = config.yang_min_streak

    for i in range(n):
        streak, body = _yang_streak_and_body(df, i)
        if streak < min_streak:
            scores[i] = 0.0
            continue
        streak_score = float(np.clip((streak - min_streak + 1) / 4.0, 0.0, 1.0))
        body_score = float(np.clip(body, 0.0, 1.0))
        rs_bonus = _relative_strength_bonus(df, i, streak, index_ret)
        scores[i] = float(np.clip(0.6 * streak_score + 0.3 * body_score + rs_bonus, 0.0, 1.0))

    return pd.Series(scores, index=df.index, name="signal_yang")


def _compute_position_pct(df: pd.DataFrame, config: ScreenerConfig) -> pd.Series:
    """Rolling percentile of close within the position lookback window."""
    lookback = config.position_lookback
    close = df["close"]
    rolling_min = close.rolling(lookback, min_periods=1).min()
    rolling_max = close.rolling(lookback, min_periods=1).max()
    span = rolling_max - rolling_min
    pct = (close - rolling_min) / span.replace(0, np.nan)
    return pct.fillna(0.5).clip(0.0, 1.0).rename("position_pct")


def _is_distribution_bar(row: pd.Series) -> bool:
    """True when close is in lower half of range with a long upper shadow."""
    o, h, l, c = row["open"], row["high"], row["low"], row["close"]
    mid = (h + l) / 2.0
    rng = h - l
    if rng <= 0:
        return False
    upper_shadow = h - max(o, c)
    close_lower_half = c < mid
    long_upper = upper_shadow / rng >= 0.4
    return bool(close_lower_half and long_upper)


def _compute_veto_distribution(df: pd.DataFrame, config: ScreenerConfig) -> pd.Series:
    """Veto when recent volume spikes show distribution patterns."""
    vol = df["vol"]
    vol_ma_long = vol.rolling(config.vol_ma_long, min_periods=1).mean()
    is_spike = vol >= vol_ma_long * 2.0

    n = len(df)
    vetoes = np.zeros(n, dtype=bool)

    spike_flags = is_spike.to_numpy()
    dist_flags = df.apply(_is_distribution_bar, axis=1).to_numpy()

    for i in range(n):
        spike_indices = [j for j in range(i + 1) if spike_flags[j]]
        recent = spike_indices[-5:]
        if len(recent) < 3:
            vetoes[i] = False
            continue
        dist_count = sum(1 for j in recent if dist_flags[j])
        vetoes[i] = dist_count / len(recent) >= 0.6

    return pd.Series(vetoes, index=df.index, name="veto_distribution")


def _compute_overheat_window(
    close: pd.Series,
    lookback: int,
    gain_threshold: float,
) -> pd.Series:
    """True where return over ``lookback`` trading days reaches ``gain_threshold``.

    Insufficient history yields NaN return -> no veto (we never veto on unknowns).
    """
    if lookback <= 0:
        return pd.Series(False, index=close.index)
    ret = close / close.shift(lookback) - 1.0
    return (ret >= gain_threshold).fillna(False)


def _compute_veto_overextended(df: pd.DataFrame, config: ScreenerConfig) -> pd.Series:
    """Veto already-overextended names by short/long cumulative gain.

    Targets the "huge run-up, slight pullback" pattern that slips under the
    position-percentile veto because the pullback lowers the percentile.
    """
    n = len(df)
    if not config.overheat_veto_enabled:
        return pd.Series([False] * n, index=df.index, name="veto_overextended")

    close = df["close"]
    short_hot = _compute_overheat_window(
        close, config.overheat_short_lookback, config.overheat_short_gain
    )
    long_hot = _compute_overheat_window(
        close, config.overheat_long_lookback, config.overheat_long_gain
    )
    base_hot = _compute_overheat_window(
        close, config.overheat_base_lookback, config.overheat_base_gain
    )
    veto = (short_hot | long_hot | base_hot).astype(bool)
    return pd.Series(veto.to_numpy(), index=df.index, name="veto_overextended")


def _compute_untradable(
    df: pd.DataFrame,
    code: str,
    name: str,
    config: ScreenerConfig,
) -> pd.Series:
    """Flag days where limit-up makes buying impractical."""
    tolerance = config.limit_up_tolerance
    limit_up = df["pct_chg"].apply(
        lambda x: is_limit_up(x, code, name, tolerance=tolerance)
        if pd.notna(x)
        else False
    )
    one_word = (
        limit_up
        & (df["open"] == df["high"])
        & (df["high"] == df["low"])
        & (df["low"] == df["close"])
    )
    low_turnover = df.get("turnover_rate", pd.Series(np.nan, index=df.index)) < 1.0
    sealed = limit_up & ((df["open"] == df["close"]) | low_turnover)
    return (one_word | sealed).rename("untradable")
