"""Configuration defaults for the A-share limit-up screener."""

from __future__ import annotations

from dataclasses import dataclass, field

# Bump when screening policy changes so persisted JSON can be marked stale.
SCREENER_POLICY_VERSION = 7


@dataclass
class ScreenerConfig:
    """Tunable parameters for limit-up screening and scoring."""

    limitup_window: int = 20
    # 量能主算法：近 vol_recent_window 日均量 ÷ 再往前 vol_prior_window 日均量。
    # 倍数达到 vol_expansion_full（默认 2.0=翻倍）给满分，1.0~2.0 线性给分。
    vol_recent_window: int = 30
    vol_prior_window: int = 30
    # 倍数 ≤ 1.5（放大不足 50%）→ 0 分，过不了必选门槛而被排除；
    # 倍数 ≥ 2.0（翻倍）→ 满分；中间线性。即“量能必须放大 >50% 才算成立”。
    vol_expansion_min: float = 1.5
    vol_expansion_full: float = 2.0
    # vol_ma_long 仍用于跳空确认与出货否决的“量 vs 20 日均量”判断。
    vol_ma_long: int = 20
    gap_lookback: int = 20
    gap_hold_days: int = 3
    yang_min_streak: int = 4
    position_lookback: int = 250
    position_veto_pct: float = 0.85
    position_full_pct: float = 0.70
    # 过热否决：短期累计涨幅过大（已大涨/高位）直接排除，与位置分位互补，
    # 因为暴涨后小幅回落的票位置分位会掉到阈值以下而漏网。
    overheat_veto_enabled: bool = True
    overheat_short_lookback: int = 20
    overheat_short_gain: float = 0.60  # 近 20 交易日涨幅 ≥ +60% 即排除
    overheat_long_lookback: int = 60
    overheat_long_gain: float = 1.00  # 近 60 交易日涨幅 ≥ +100% 即排除
    # 长周期：抓“慢牛已走完一大段”的高位票（近 20/60 日不极端、但 120 日翻倍以上）。
    # 刚启动的打板票 120 日涨幅接近 0，不会被误伤。
    overheat_base_lookback: int = 120
    overheat_base_gain: float = 1.00  # 近 120 交易日涨幅 ≥ +100% 即排除
    score_threshold: float = 70.0
    # Required signals must exceed ``required_signal_min`` to enter the result set.
    required_signals: tuple[str, ...] = ("limitup", "volume")
    optional_signals: tuple[str, ...] = ("gap", "yang")
    required_signal_min: float = 0.01
    weights: dict = field(
        default_factory=lambda: {
            # Required signals dominate ranking; optional signals are bonus only.
            "limitup": 0.35,
            "volume": 0.35,
            "gap": 0.15,
            "yang": 0.15,
        }
    )
    benchmark_index: str = "000300.SH"
    exclude_st: bool = True
    # 排除退市/退市整理期股票（名称含“退市”或以“退”结尾，如 605081 退市太和）。
    exclude_delisting: bool = True
    exclude_new_days: int = 0
    limit_up_tolerance: float = 0.3
    # 连续入选天数达到该值显示“删除”，超过则从结果中剔除（第 max+1 天移出）。
    membership_max_days: int = 30
