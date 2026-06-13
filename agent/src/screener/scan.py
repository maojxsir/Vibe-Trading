"""Orchestrate the A-share limit-up screener scan pipeline."""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.screener.config import SCREENER_POLICY_VERSION, ScreenerConfig
from src.screener.enrich import enrich_items
from src.screener.scoring import score_latest
from src.screener.tracking import update_membership
from src.screener.signals import compute_signal_series
from src.screener.store import ScreenerStore, normalize_query_date, normalize_trade_date
from src.screener.universe import build_universe

logger = logging.getLogger(__name__)

SOURCE_NAME = "tushare"


def screener_results_root() -> Path:
    """Return the directory for persisted screener scan JSON results."""
    return Path.home() / ".vibe-trading" / "screener" / "results"


def result_path(trade_date: str) -> Path:
    """Return the JSON path for one trade date (``YYYY-MM-DD`` or ``YYYYMMDD``)."""
    iso = normalize_query_date(trade_date)
    return screener_results_root() / f"screener_{iso}.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _resolve_trade_date(trade_date: str | None, store: ScreenerStore) -> str:
    """Resolve the scan trade date as ``YYYY-MM-DD``."""
    if trade_date:
        return normalize_query_date(trade_date)

    meta = store.read_meta()
    latest = str(meta.get("latest_trade_date") or "").strip()
    if latest:
        return normalize_query_date(latest)

    return (date.today() - pd.Timedelta(days=1)).strftime("%Y-%m-%d")


def _benchmark_index_code(config: ScreenerConfig) -> str:
    text = str(config.benchmark_index or "000300").strip().upper()
    if "." in text:
        return text.split(".", 1)[0]
    return text


def _panel_start_date(trade_date: str, config: ScreenerConfig) -> str:
    """Estimate calendar start date for enough trading history."""
    end_ts = pd.Timestamp(trade_date)
    calendar_days = int(config.position_lookback * 1.6) + config.gap_lookback + 30
    start_ts = end_ts - pd.Timedelta(days=calendar_days)
    return start_ts.strftime("%Y-%m-%d")


def _config_params_snapshot(config: ScreenerConfig) -> dict[str, Any]:
    """Serialize tunable config fields for result provenance."""
    return {
        "weights": dict(config.weights),
        "limitup_window": config.limitup_window,
        "vol_recent_window": config.vol_recent_window,
        "vol_prior_window": config.vol_prior_window,
        "vol_expansion_min": config.vol_expansion_min,
        "vol_expansion_full": config.vol_expansion_full,
        "vol_ma_long": config.vol_ma_long,
        "gap_lookback": config.gap_lookback,
        "gap_hold_days": config.gap_hold_days,
        "yang_min_streak": config.yang_min_streak,
        "position_lookback": config.position_lookback,
        "position_veto_pct": config.position_veto_pct,
        "overheat_veto_enabled": config.overheat_veto_enabled,
        "overheat_short_lookback": config.overheat_short_lookback,
        "overheat_short_gain": config.overheat_short_gain,
        "overheat_long_lookback": config.overheat_long_lookback,
        "overheat_long_gain": config.overheat_long_gain,
        "overheat_base_lookback": config.overheat_base_lookback,
        "overheat_base_gain": config.overheat_base_gain,
        "score_threshold": config.score_threshold,
        "benchmark_index": config.benchmark_index,
        "exclude_st": config.exclude_st,
        "exclude_delisting": config.exclude_delisting,
        "membership_max_days": config.membership_max_days,
        "exclude_new_days": config.exclude_new_days,
        "required_signals": list(config.required_signals),
        "optional_signals": list(config.optional_signals),
        "required_signal_min": config.required_signal_min,
        "policy_version": SCREENER_POLICY_VERSION,
    }


def _min_history_trading_days(config: ScreenerConfig) -> int:
    """Minimum settled trading days needed for required signals to be valid."""
    return (
        max(
            config.vol_recent_window + config.vol_prior_window,
            config.vol_ma_long,
            config.limitup_window,
            config.gap_lookback,
        )
        + 5
    )


def _target_history_trading_days(config: ScreenerConfig) -> int:
    """Comfortable history depth for stable position percentile and vetoes.

    Bounded so the one-time backfill stays fast; deeper context mainly sharpens
    ``position_pct`` and the overheat veto's long-lookback return, both of which
    degrade gracefully when shallow.
    """
    overheat_max = max(
        config.overheat_short_lookback,
        config.overheat_long_lookback,
        config.overheat_base_lookback,
    )
    needed = max(
        _min_history_trading_days(config) * 2,
        overheat_max + 25,
        60,
    )
    return min(config.position_lookback, needed)


def _detect_degraded(panels: dict[str, pd.DataFrame], config: ScreenerConfig) -> bool:
    """True when most symbols lack enough OHLCV history for reliable required signals.

    The benchmark index only feeds the optional yang relative-strength bonus, so a
    missing index is intentionally not treated as a degraded scan.
    """
    min_rows = _min_history_trading_days(config)
    counts = [len(panel) for panel in panels.values() if panel is not None and not panel.empty]
    if not counts:
        return True
    counts.sort()
    median_rows = counts[len(counts) // 2]
    return median_rows < min_rows


def _slice_panel_to_trade_date(panel: pd.DataFrame, trade_date: str) -> pd.DataFrame:
    """Keep rows on or before ``trade_date``."""
    if panel.empty:
        return panel
    end = pd.Timestamp(trade_date).normalize()
    work = panel.copy()
    if not isinstance(work.index, pd.DatetimeIndex):
        work.index = pd.to_datetime(work.index)
    work.index = work.index.normalize()
    return work.loc[work.index <= end].sort_index()


def _write_result_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    unique = f"{os.getpid()}.{uuid.uuid4().hex}"
    tmp_path = path.with_name(f"{path.name}.{unique}.tmp")
    tmp_path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    os.replace(tmp_path, path)


def _read_result_file(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("screener result read failed (%s): %s", path, exc)
        return None
    return payload if isinstance(payload, dict) else None


def run(
    config: ScreenerConfig,
    *,
    trade_date: str | None = None,
    store: ScreenerStore | None = None,
) -> Path:
    """Full scan pipeline. Returns path to written JSON."""
    panel_store = store or ScreenerStore()
    resolved_trade_date = _resolve_trade_date(trade_date, panel_store)
    end_td = normalize_trade_date(resolved_trade_date)

    panel_store.ensure_panel_history(end_td, _target_history_trading_days(config))
    panel_store.ensure_fresh(end_td)

    as_of = pd.Timestamp(resolved_trade_date).date()
    universe = build_universe(config, as_of=as_of)
    codes = [entry["code"] for entry in universe]

    start = _panel_start_date(resolved_trade_date, config)
    panels = panel_store.load_panel(codes, start, resolved_trade_date)
    index_ret = panel_store.load_index_series(
        start,
        resolved_trade_date,
        index_code=_benchmark_index_code(config),
    )

    items: list[dict[str, Any]] = []
    skipped = 0
    filtered_count = 0

    for entry in universe:
        code = entry["code"]
        panel = panels.get(code)
        if panel is None or panel.empty:
            skipped += 1
            continue

        sliced = _slice_panel_to_trade_date(panel, resolved_trade_date)
        if sliced.empty:
            skipped += 1
            continue

        try:
            signals_df = compute_signal_series(
                sliced,
                code=code,
                name=entry["name"],
                config=config,
                index_ret=index_ret,
            )
            scored = score_latest(signals_df, config)
        except (ValueError, KeyError, TypeError) as exc:
            logger.debug("screener skip %s: %s", code, exc)
            skipped += 1
            continue

        if scored["filtered"]:
            filtered_count += 1
            continue

        score = scored["score"]
        if score is None:
            filtered_count += 1
            continue

        items.append(
            {
                "code": code,
                "name": entry["name"],
                "board": entry["board"],
                "score": float(score),
                "signals": scored["signals"],
                "vetoes": scored["vetoes"],
                "position_pct": scored["position_pct"],
                "untradable": scored["untradable"],
                "trade_date": resolved_trade_date,
            }
        )

    items.sort(key=lambda row: row["score"], reverse=True)

    # 尽力而为地补充行业 / 主营业务 / 市值；任何失败都不影响选股结果。
    try:
        enrich_items(items, resolved_trade_date, panel_store.pro_client())
    except Exception as exc:  # noqa: BLE001 - enrichment is best-effort
        logger.warning("screener enrich skipped: %s", exc)

    # 连续入选天数跟踪：标注 新增/N天/删除，并剔除超过上限的标的。
    try:
        items = update_membership(
            items, resolved_trade_date, max_days=config.membership_max_days
        )
    except Exception as exc:  # noqa: BLE001 - tracking is best-effort
        logger.warning("screener membership tracking skipped: %s", exc)

    degraded = _detect_degraded(panels, config)

    payload: dict[str, Any] = {
        "tradeDate": resolved_trade_date,
        "items": items,
        "params": _config_params_snapshot(config),
        "source": SOURCE_NAME,
        "degraded": degraded,
        "updatedAt": _utc_now_iso(),
        "universe_count": len(universe),
        "matched_count": len(items),
        "skipped": skipped,
        "filtered_count": filtered_count,
    }

    out_path = result_path(resolved_trade_date)
    _write_result_atomic(out_path, payload)
    return out_path


def load_result(trade_date: str) -> dict[str, Any] | None:
    """Load one scan result by trade date (``YYYY-MM-DD``)."""
    return _read_result_file(result_path(trade_date))


def load_latest_result() -> dict[str, Any] | None:
    """Load the most recent scan result JSON, if any."""
    root = screener_results_root()
    if not root.is_dir():
        return None

    candidates = sorted(root.glob("screener_*.json"), reverse=True)
    for path in candidates:
        payload = _read_result_file(path)
        if payload is not None:
            return payload
    return None
