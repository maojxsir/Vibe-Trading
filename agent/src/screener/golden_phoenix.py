"""Golden Phoenix (N-shaped double limit-up) pattern detection."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Optional

import pandas as pd

from src.screener.board import _is_st_name, detect_board, limit_up_threshold
from src.screener.golden_phoenix_config import GoldenPhoenixConfig


@dataclass(frozen=True)
class GoldenPhoenixSignals:
    """Auxiliary signal flags used for ranking."""

    shrink_volume: bool = False
    volume_breakout: bool = False
    ma_bullish: bool = False


@dataclass(frozen=True)
class GoldenPhoenixMatch:
    """One screened symbol that matches the Golden Phoenix pattern."""

    code: str
    name: str
    status: str
    score: float
    t0_date: str
    t1_date: Optional[str]
    lifeline: float
    callback_days: int
    gap_days: int
    price: Optional[float]
    change_pct: Optional[float]
    one_word_first_board: bool
    signals: GoldenPhoenixSignals
    trade_date: str
    board: str = ""

    def to_item_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["signals"] = asdict(self.signals)
        return payload


def _bare_code(code: str) -> str:
    text = str(code or "").strip().upper()
    if "." in text:
        text = text.split(".", 1)[0]
    return text


def _round_limit_price(pre_close: float, ratio: float) -> float:
    return round(pre_close * (1.0 + ratio), 2)


def prepare_panel(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize screener panel OHLCV for pattern detection."""
    work = df.copy()
    if not isinstance(work.index, pd.DatetimeIndex):
        if "trade_date" in work.columns:
            work["trade_date"] = pd.to_datetime(work["trade_date"])
            work = work.set_index("trade_date")
        else:
            work.index = pd.to_datetime(work.index)
    work.index = work.index.normalize()
    work = work.sort_index()
    if "volume" not in work.columns and "vol" in work.columns:
        work["volume"] = work["vol"]
    for col in ("open", "high", "low", "close", "pre_close", "volume", "pct_chg"):
        if col in work.columns:
            work[col] = pd.to_numeric(work[col], errors="coerce")
    work = work.dropna(subset=["open", "high", "low", "close"])
    work = work.reset_index().rename(columns={"index": "date", "trade_date": "date"})
    if "date" not in work.columns:
        work = work.rename(columns={work.columns[0]: "date"})
    work["date"] = pd.to_datetime(work["date"]).dt.normalize()
    return work.sort_values("date").reset_index(drop=True)


def annotate_limit_up(df: pd.DataFrame, code: str, name: str, config: GoldenPhoenixConfig) -> pd.DataFrame:
    """Add limit-up helper columns to the OHLCV frame."""
    work = prepare_panel(df)
    ratio = limit_up_threshold(code, name) / 100.0
    if "pre_close" in work.columns and work["pre_close"].notna().any():
        pre_close = work["pre_close"]
    else:
        pre_close = work["close"].shift(1)
    work["pre_close"] = pre_close
    work["limit_up_price"] = pre_close.apply(
        lambda x: _round_limit_price(float(x), ratio) if pd.notna(x) else None
    )
    work["is_limit_up"] = (
        work["limit_up_price"].notna()
        & ((work["close"] - work["limit_up_price"]).abs() <= config.limit_price_tolerance)
    )
    return work


def _body_gain_pct(row: pd.Series) -> float:
    if row["open"] <= 0:
        return 0.0
    return (row["close"] - row["open"]) / row["open"] * 100.0


def _is_one_word_board(row: pd.Series, config: GoldenPhoenixConfig) -> bool:
    if not bool(row.get("is_limit_up")):
        return False
    limit_price = row.get("limit_up_price")
    if limit_price is None or pd.isna(limit_price):
        return False
    return (
        abs(row["open"] - limit_price) <= config.limit_price_tolerance
        and abs(row["close"] - limit_price) <= config.limit_price_tolerance
        and abs(row["low"] - row["high"]) <= config.limit_price_tolerance
    )


def _has_valid_pullback(work: pd.DataFrame, start_idx: int, end_idx: int, config: GoldenPhoenixConfig) -> bool:
    if end_idx <= start_idx:
        return False
    segment = work.iloc[start_idx:end_idx]
    for _, row in segment.iterrows():
        if row["close"] < row["open"] or _body_gain_pct(row) < config.pullback_body_pct:
            return True
    return False


def _lifeline_intact(
    work: pd.DataFrame,
    start_idx: int,
    end_idx: int,
    lifeline: float,
    config: GoldenPhoenixConfig,
) -> bool:
    for idx in range(start_idx, end_idx + 1):
        close_price = float(work.iloc[idx]["close"])
        if close_price < lifeline - config.lifeline_tolerance:
            return False
    return True


def _compute_signals(
    work: pd.DataFrame,
    t0_idx: int,
    t1_idx: Optional[int],
    cur_idx: int,
    config: GoldenPhoenixConfig,
) -> GoldenPhoenixSignals:
    end_idx = t1_idx if t1_idx is not None else cur_idx
    pullback_start = t0_idx + 1
    pullback_end = max(pullback_start, end_idx)
    shrink_volume = False
    volume_breakout = False

    if "volume" in work.columns and pullback_end > pullback_start:
        first_vol = float(work.iloc[t0_idx]["volume"] or 0)
        segment = work.iloc[pullback_start:pullback_end]
        if first_vol > 0 and not segment.empty:
            mean_vol = float(segment["volume"].mean())
            shrink_volume = mean_vol < first_vol * config.shrink_volume_ratio
            if t1_idx is not None and t1_idx > pullback_start:
                second_vol = float(work.iloc[t1_idx]["volume"] or 0)
                volume_breakout = mean_vol > 0 and second_vol > mean_vol * config.breakout_volume_ratio

    ma_bullish = False
    if len(work) >= 10:
        ma5 = work["close"].rolling(5).mean()
        ma10 = work["close"].rolling(10).mean()
        if pd.notna(ma5.iloc[cur_idx]) and pd.notna(ma10.iloc[cur_idx]):
            ma_bullish = float(ma5.iloc[cur_idx]) >= float(ma10.iloc[cur_idx])

    return GoldenPhoenixSignals(
        shrink_volume=shrink_volume,
        volume_breakout=volume_breakout,
        ma_bullish=ma_bullish,
    )


def _score_match(
    status: str,
    one_word_first_board: bool,
    signals: GoldenPhoenixSignals,
    gap_days: int,
    config: GoldenPhoenixConfig,
) -> float:
    if status == "confirmed":
        score = 100.0
    else:
        mid = (config.min_gap_days + config.max_gap_days) / 2.0
        distance = abs(gap_days - mid)
        score = max(55.0, 80.0 - distance * 3.0)

    if one_word_first_board:
        score -= 8.0
    if signals.shrink_volume:
        score += 3.0
    if signals.volume_breakout:
        score += 5.0
    if signals.ma_bullish:
        score += 3.0
    return round(min(100.0, max(0.0, score)), 1)


def detect_golden_phoenix(
    df: pd.DataFrame,
    *,
    code: str,
    name: str,
    trade_date: str,
    config: GoldenPhoenixConfig | None = None,
) -> Optional[GoldenPhoenixMatch]:
    """Detect the best Golden Phoenix match for one symbol on ``trade_date``."""
    cfg = config or GoldenPhoenixConfig()
    if cfg.exclude_st and _is_st_name(name):
        return None

    work = annotate_limit_up(df, code, name, cfg)
    if work.empty:
        return None

    end_ts = pd.Timestamp(trade_date).normalize()
    eligible = work[work["date"] <= end_ts]
    if eligible.empty:
        return None

    cur_idx = len(eligible) - 1
    lookback_start = max(0, cur_idx - cfg.lookback_days + 1)

    best: Optional[GoldenPhoenixMatch] = None
    for t0_idx in range(cur_idx, lookback_start - 1, -1):
        row0 = eligible.iloc[t0_idx]
        if not bool(row0["is_limit_up"]):
            continue

        quiet_start = max(0, t0_idx - cfg.first_board_quiet_days)
        if eligible.iloc[quiet_start:t0_idx]["is_limit_up"].any():
            continue

        lifeline = float(row0["high"])
        gap_days = cur_idx - t0_idx
        callback_days = max(0, gap_days - 1)
        t0_date = row0["date"].strftime("%Y-%m-%d")

        if not _lifeline_intact(eligible, t0_idx + 1, cur_idx, lifeline, cfg):
            continue

        today_limit_up = bool(eligible.iloc[cur_idx]["is_limit_up"])
        status: Optional[str] = None
        t1_idx: Optional[int] = None

        if today_limit_up and cfg.min_gap_days <= gap_days <= cfg.max_gap_days:
            if not _has_valid_pullback(eligible, t0_idx + 1, cur_idx, cfg):
                continue
            pullback = eligible.iloc[t0_idx + 1:cur_idx]
            if not pullback.empty and float(pullback["close"].mean()) >= float(eligible.iloc[cur_idx]["close"]):
                continue
            status = "confirmed"
            t1_idx = cur_idx
        elif (
            not today_limit_up
            and cfg.min_callback_days <= callback_days <= cfg.max_callback_days
            and gap_days < cfg.max_gap_days
        ):
            if not _has_valid_pullback(eligible, t0_idx + 1, cur_idx, cfg):
                continue
            status = "watch"
        else:
            continue

        one_word = _is_one_word_board(row0, cfg)
        signals = _compute_signals(eligible, t0_idx, t1_idx, cur_idx, cfg)
        score = _score_match(status, one_word, signals, gap_days, cfg)
        cur_row = eligible.iloc[cur_idx]
        price = float(cur_row["close"])
        pre_close = cur_row.get("pre_close")
        change_pct = None
        if pre_close is not None and pd.notna(pre_close) and float(pre_close) > 0:
            change_pct = round((price / float(pre_close) - 1.0) * 100.0, 2)

        candidate = GoldenPhoenixMatch(
            code=_bare_code(code),
            name=name,
            status=status,
            score=score,
            t0_date=t0_date,
            t1_date=eligible.iloc[t1_idx]["date"].strftime("%Y-%m-%d") if t1_idx is not None else None,
            lifeline=round(lifeline, 2),
            callback_days=callback_days,
            gap_days=gap_days,
            price=round(price, 2),
            change_pct=change_pct,
            one_word_first_board=one_word,
            signals=signals,
            trade_date=end_ts.strftime("%Y-%m-%d"),
            board=detect_board(code, name),
        )

        if best is None or candidate.score > best.score:
            best = candidate
            if status == "confirmed":
                break

    return best
