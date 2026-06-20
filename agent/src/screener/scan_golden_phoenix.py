"""Orchestrate the Golden Phoenix batch scan pipeline."""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.screener.config import ScreenerConfig
from src.screener.enrich import enrich_items
from src.screener.golden_phoenix import detect_golden_phoenix
from src.screener.golden_phoenix_config import GOLDEN_PHOENIX_POLICY_VERSION, GoldenPhoenixConfig
from src.screener.store import ScreenerStore, normalize_query_date, normalize_trade_date
from src.screener.universe import build_universe

logger = logging.getLogger(__name__)

SOURCE_NAME = "tushare"


def golden_phoenix_results_root() -> Path:
    """Return the directory for persisted Golden Phoenix scan JSON results."""
    return Path.home() / ".vibe-trading" / "screener" / "golden_phoenix" / "results"


def result_path(trade_date: str) -> Path:
    """Return the JSON path for one trade date."""
    iso = normalize_query_date(trade_date)
    return golden_phoenix_results_root() / f"golden_phoenix_{iso}.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _resolve_trade_date(trade_date: str | None, store: ScreenerStore) -> str:
    if trade_date:
        return normalize_query_date(trade_date)
    meta = store.read_meta()
    latest = str(meta.get("latest_trade_date") or "").strip()
    if latest:
        return normalize_query_date(latest)
    return (date.today() - pd.Timedelta(days=1)).strftime("%Y-%m-%d")


def _panel_start_date(trade_date: str, config: GoldenPhoenixConfig) -> str:
    end_ts = pd.Timestamp(trade_date)
    calendar_days = int(config.history_trading_days * 1.6) + 30
    return (end_ts - pd.Timedelta(days=calendar_days)).strftime("%Y-%m-%d")


def _config_params_snapshot(config: GoldenPhoenixConfig) -> dict[str, Any]:
    return {
        "lookback_days": config.lookback_days,
        "min_callback_days": config.min_callback_days,
        "max_callback_days": config.max_callback_days,
        "min_gap_days": config.min_gap_days,
        "max_gap_days": config.max_gap_days,
        "exclude_st": config.exclude_st,
        "exclude_delisting": config.exclude_delisting,
        "policy_version": GOLDEN_PHOENIX_POLICY_VERSION,
    }


def _slice_panel_to_trade_date(panel: pd.DataFrame, trade_date: str) -> pd.DataFrame:
    if panel.empty:
        return panel
    end = pd.Timestamp(trade_date).normalize()
    work = panel.copy()
    if not isinstance(work.index, pd.DatetimeIndex):
        work.index = pd.to_datetime(work.index)
    work.index = work.index.normalize()
    return work.loc[work.index <= end].sort_index()


def _json_default(obj: Any) -> Any:
    """Convert non-standard types (e.g. numpy integers/floats) to JSON-safe values."""
    try:
        import numpy as np

        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.bool_):
            return bool(obj)
    except ImportError:
        pass
    raise TypeError(
        f"Object of type {type(obj).__name__} is not JSON serializable"
    )


def _write_result_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    unique = f"{os.getpid()}.{uuid.uuid4().hex}"
    tmp_path = path.with_name(f"{path.name}.{unique}.tmp")
    tmp_path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=_json_default),
        encoding="utf-8",
    )
    os.replace(tmp_path, path)


def _read_result_file(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("golden phoenix result read failed (%s): %s", path, exc)
        return None
    return payload if isinstance(payload, dict) else None


def run(
    config: GoldenPhoenixConfig,
    *,
    trade_date: str | None = None,
    store: ScreenerStore | None = None,
) -> Path:
    """Full Golden Phoenix scan. Returns path to written JSON."""
    panel_store = store or ScreenerStore()
    resolved_trade_date = _resolve_trade_date(trade_date, panel_store)
    end_td = normalize_trade_date(resolved_trade_date)

    panel_store.ensure_panel_history(end_td, config.history_trading_days)
    panel_store.ensure_fresh(end_td)

    as_of = pd.Timestamp(resolved_trade_date).date()
    universe_cfg = ScreenerConfig(
        exclude_st=config.exclude_st,
        exclude_delisting=config.exclude_delisting,
    )
    universe = build_universe(universe_cfg, as_of=as_of)
    codes = [entry["code"] for entry in universe]

    start = _panel_start_date(resolved_trade_date, config)
    panels = panel_store.load_panel(codes, start, resolved_trade_date)

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
            match = detect_golden_phoenix(
                sliced,
                code=code,
                name=entry["name"],
                trade_date=resolved_trade_date,
                config=config,
            )
        except (ValueError, KeyError, TypeError) as exc:
            logger.debug("golden phoenix skip %s: %s", code, exc)
            skipped += 1
            continue

        if match is None:
            filtered_count += 1
            continue

        item = match.to_item_dict()
        item["trade_date"] = resolved_trade_date
        items.append(item)

    items.sort(
        key=lambda row: (
            row.get("status") != "confirmed",
            -float(row.get("score", 0)),
        )
    )

    try:
        enrich_items(items, resolved_trade_date, panel_store.pro_client())
    except Exception as exc:  # noqa: BLE001
        logger.warning("golden phoenix enrich skipped: %s", exc)

    payload: dict[str, Any] = {
        "strategy": "limit_up_golden_phoenix",
        "tradeDate": resolved_trade_date,
        "items": items,
        "params": _config_params_snapshot(config),
        "source": SOURCE_NAME,
        "degraded": False,
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
    return _read_result_file(result_path(trade_date))


def load_latest_result() -> dict[str, Any] | None:
    root = golden_phoenix_results_root()
    if not root.is_dir():
        return None
    for path in sorted(root.glob("golden_phoenix_*.json"), reverse=True):
        payload = _read_result_file(path)
        if payload is not None:
            return payload
    return None
