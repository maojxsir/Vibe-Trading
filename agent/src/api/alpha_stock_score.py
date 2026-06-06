"""Composite Alpha Zoo factor scores for a watchlist of A-share codes.

Uses the same bench pipeline as ``POST /alpha/bench`` (``run_bench`` on a zoo +
universe) to pick validated *alive* alphas, then combines them with
``ZooSignalEngine`` into a cross-sectional composite signal. Returns the latest
composite value and CSI300 percentile for each requested code.

Requires ``TUSHARE_TOKEN`` for the csi300 universe panel (same as bench).
Results are cached in-process for ``CACHE_TTL_SEC`` to avoid re-running a full
gtja191 bench on every dashboard poll.
"""

from __future__ import annotations

import importlib.util
import logging
import re
import threading
import time
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

CACHE_TTL_SEC = 6 * 3600
MAX_ALPHAS = 15
DEFAULT_ZOO = "gtja191"
DEFAULT_UNIVERSE = "csi300"
DEFAULT_PERIOD = "2024-2025"

_BENCH_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_CACHE_LOCK = threading.Lock()

_BARE_CODE = re.compile(r"^(\d{6})")


def to_ts_code(code: str) -> str:
    """Normalize bare A-share code to Tushare ``ts_code`` (e.g. ``688017.SH``)."""
    c = code.strip().upper()
    if "." in c:
        return c
    m = _BARE_CODE.match(c.split(".")[0])
    if not m:
        return c
    num = m.group(1)
    if num.startswith(("60", "68", "11", "51", "58", "90")):
        return f"{num}.SH"
    if num.startswith(("00", "30", "12", "15", "16", "18", "20", "39")):
        return f"{num}.SZ"
    if num.startswith(("8", "4", "92")):
        return f"{num}.BJ"
    return f"{num}.SH"


def bare_code(code: str) -> str:
    """Return six-digit code without exchange suffix."""
    c = code.strip().upper()
    if "." in c:
        return c.split(".")[0]
    m = _BARE_CODE.match(c)
    return m.group(1) if m else c


def score_label(percentile: float) -> str:
    if percentile >= 70:
        return "偏强"
    if percentile >= 40:
        return "中性"
    return "偏弱"


def _cache_key(zoo: str, universe: str, period: str) -> str:
    return f"{zoo}|{universe}|{period}"


def _load_zoo_signal_engine():
    path = (
        Path(__file__).resolve().parents[1]
        / "skills"
        / "multi-factor"
        / "zoo_signal_engine.py"
    )
    spec = importlib.util.spec_from_file_location("zoo_signal_engine", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load ZooSignalEngine from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.ZooSignalEngine


def _get_alive_alpha_ids(
    zoo: str, universe: str, period: str, *, max_alphas: int
) -> tuple[list[str], dict[str, Any]]:
    """Run (or reuse cached) bench and return top alive alpha ids by IR."""
    key = _cache_key(zoo, universe, period)
    now = time.time()
    with _CACHE_LOCK:
        hit = _BENCH_CACHE.get(key)
        if hit is not None and hit[0] > now:
            rows = hit[1]
        else:
            rows = None

    bench_meta: dict[str, Any] = {
        "zoo": zoo,
        "universe": universe,
        "period": period,
        "cached": rows is not None,
    }

    if rows is None:
        from src.factors.bench_runner import run_bench

        result = run_bench(zoo=zoo, universe=universe, period=period, top=max_alphas)
        if result.get("status") != "ok":
            raise RuntimeError(result.get("error") or "bench failed")
        rows = result.get("rows") or []
        bench_meta.update(
            {
                "alive": result.get("alive", 0),
                "reversed": result.get("reversed", 0),
                "dead": result.get("dead", 0),
                "n_alphas_tested": result.get("n_alphas_tested", 0),
                "wall_seconds": result.get("wall_seconds"),
                "cached": False,
            }
        )
        with _CACHE_LOCK:
            _BENCH_CACHE[key] = (now + CACHE_TTL_SEC, rows)
    else:
        alive_n = sum(1 for r in rows if r.get("_category") == "alive")
        bench_meta.update({"alive": alive_n, "cached": True})

    alive = [r for r in rows if r.get("_category") == "alive"]
    alive.sort(key=lambda r: r.get("ir", 0), reverse=True)
    if not alive:
        # Degrade to top IR rows when categorisation yields no alive bucket.
        fallback = sorted(rows, key=lambda r: r.get("ir", 0), reverse=True)
        alive = fallback[:max_alphas]
    alpha_ids = [r["id"] for r in alive[:max_alphas]]
    bench_meta["n_alphas_used"] = len(alpha_ids)
    return alpha_ids, bench_meta


def _latest_scores(composite: pd.DataFrame) -> tuple[pd.Timestamp | None, pd.Series]:
    """Pick the most recent date row with at least one valid score."""
    if composite.empty:
        return None, pd.Series(dtype=float)
    for idx in reversed(composite.index.tolist()):
        row = composite.loc[idx]
        if row.notna().any():
            return idx, row
    return None, pd.Series(dtype=float)


def score_stocks(
    codes: list[str],
    *,
    zoo: str = DEFAULT_ZOO,
    universe: str = DEFAULT_UNIVERSE,
    period: str = DEFAULT_PERIOD,
    max_alphas: int = MAX_ALPHAS,
) -> dict[str, Any]:
    """Score watchlist codes using bench-validated alphas + composite signal."""
    if not codes:
        return {
            "status": "ok",
            "stale": False,
            "scores": {},
            "meta": {"zoo": zoo, "universe": universe, "period": period},
        }

    ts_codes = [to_ts_code(c) for c in codes]
    bare_to_ts = {bare_code(c): to_ts_code(c) for c in codes}

    try:
        alpha_ids, bench_meta = _get_alive_alpha_ids(
            zoo, universe, period, max_alphas=max_alphas
        )
        if not alpha_ids:
            return {
                "status": "error",
                "stale": True,
                "error": "no alphas available after bench",
                "scores": {},
                "meta": bench_meta,
            }

        from src.tools.alpha_bench_tool import _load_universe_panel

        panel = _load_universe_panel(universe, period)
        ZooSignalEngine = _load_zoo_signal_engine()
        engine = ZooSignalEngine.from_zoo(tuple(alpha_ids), standardize=True)
        composite = engine.compute_signal(panel)

        as_of, latest_row = _latest_scores(composite)
        if as_of is None or latest_row.empty:
            return {
                "status": "error",
                "stale": True,
                "error": "composite signal empty",
                "scores": {},
                "meta": bench_meta,
            }

        valid = latest_row.dropna()
        scores: dict[str, Any] = {}
        for bare, ts in bare_to_ts.items():
            raw = latest_row.get(ts)
            if raw is None or (isinstance(raw, float) and pd.isna(raw)):
                # Column may be missing if code not in csi300 panel.
                scores[bare] = None
                continue
            raw_f = float(raw)
            if valid.empty:
                pct = 50.0
            else:
                pct = float((valid <= raw_f).mean() * 100.0)
            score100 = int(round(pct))
            scores[bare] = {
                "code": bare,
                "ts_code": ts,
                "composite": round(raw_f, 4),
                "score": score100,
                "percentile": round(pct, 1),
                "label": score_label(pct),
            }

        bench_meta["as_of"] = pd.Timestamp(as_of).strftime("%Y-%m-%d")
        return {
            "status": "ok",
            "stale": False,
            "scores": scores,
            "meta": bench_meta,
        }
    except Exception as exc:  # noqa: BLE001 — surface as stale envelope
        logger.exception("alpha stock score failed")
        return {
            "status": "error",
            "stale": True,
            "error": str(exc),
            "scores": {},
            "meta": {"zoo": zoo, "universe": universe, "period": period},
        }
