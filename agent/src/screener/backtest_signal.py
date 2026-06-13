"""Screener signal engine for vectorized backtests."""

from __future__ import annotations

import pandas as pd

from src.screener.config import ScreenerConfig
from src.screener.scoring import apply_vetoes, passes_required_signals, score_row
from src.screener.signals import compute_signal_series
from src.screener.store import bare_code


def _parse_code_name(key: str) -> tuple[str, str]:
    """Derive bare code and display name from a ts_code or bare symbol key."""
    code = bare_code(key)
    return code, code


def _entry_mask(
    signals_df: pd.DataFrame,
    config: ScreenerConfig,
    *,
    score_threshold: float,
) -> pd.Series:
    """True on bars where score passes threshold and no veto applies."""
    entries: list[bool] = []
    for _, row in signals_df.iterrows():
        raw_score = score_row(row, config)
        final_score = apply_vetoes(raw_score, row, config)
        entries.append(
            passes_required_signals(row, config)
            and final_score is not None
            and float(final_score) >= score_threshold
        )
    return pd.Series(entries, index=signals_df.index, dtype=bool)


def _apply_hold(entry_mask: pd.Series, hold_days: int) -> pd.Series:
    """Hold signal 1.0 for ``hold_days`` bars after each entry trigger."""
    hold_days = max(1, int(hold_days))
    values: list[float] = []
    hold_remaining = 0
    for should_enter in entry_mask:
        if hold_remaining > 0:
            values.append(1.0)
            hold_remaining -= 1
        elif should_enter:
            values.append(1.0)
            hold_remaining = hold_days - 1
        else:
            values.append(0.0)
    return pd.Series(values, index=entry_mask.index, dtype=float)


class ScreenerSignalEngine:
    """Generate per-symbol long signals from screener scores with fixed hold."""

    def __init__(
        self,
        config: ScreenerConfig | None = None,
        *,
        hold_days: int = 5,
        score_threshold: float | None = None,
    ) -> None:
        self._config = config or ScreenerConfig()
        self._hold_days = max(1, int(hold_days))
        self._score_threshold = (
            float(score_threshold)
            if score_threshold is not None
            else float(self._config.score_threshold)
        )

    @property
    def hold_days(self) -> int:
        return self._hold_days

    @property
    def score_threshold(self) -> float:
        return self._score_threshold

    def generate(self, data_map: dict[str, pd.DataFrame]) -> dict[str, pd.Series]:
        """Score each bar and emit 1.0 long signals with simple hold logic."""
        signals: dict[str, pd.Series] = {}
        for key, df in data_map.items():
            if df is None or df.empty:
                signals[key] = pd.Series(dtype=float)
                continue

            code, name = _parse_code_name(key)
            signals_df = compute_signal_series(
                df,
                code=code,
                name=name,
                config=self._config,
                index_ret=None,
            )
            entries = _entry_mask(
                signals_df,
                self._config,
                score_threshold=self._score_threshold,
            )
            signals[key] = _apply_hold(entries, self._hold_days)
        return signals
