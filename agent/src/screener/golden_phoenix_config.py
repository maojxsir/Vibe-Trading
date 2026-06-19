"""Configuration for the Golden Phoenix N-shaped limit-up screener."""

from __future__ import annotations

from dataclasses import dataclass

GOLDEN_PHOENIX_POLICY_VERSION = 1


@dataclass
class GoldenPhoenixConfig:
    """Tunable thresholds for the Golden Phoenix screener."""

    lookback_days: int = 15
    min_callback_days: int = 3
    max_callback_days: int = 9
    min_gap_days: int = 4
    max_gap_days: int = 10
    first_board_quiet_days: int = 5
    lifeline_tolerance: float = 0.01
    limit_price_tolerance: float = 0.011
    shrink_volume_ratio: float = 0.8
    breakout_volume_ratio: float = 1.5
    pullback_body_pct: float = 3.0
    exclude_st: bool = True
    exclude_delisting: bool = True
    history_trading_days: int = 60
