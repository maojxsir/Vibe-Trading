"""CLI entry point for the limit-up screener tracking pool update.

独立于扫描运行的跟踪池更新入口，供 cron 每日收盘后调度：
对池中活跃标的取日线，按规则（连续创新低 / 均线空头排列 / 30 日到期）剔除或保留。
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
AGENT_DIR = HERE.parent
sys.path.insert(0, str(AGENT_DIR))

try:
    from dotenv import load_dotenv

    load_dotenv(AGENT_DIR / ".env")
except ImportError:
    pass

from src.screener import tracking_update  # noqa: E402
from src.screener.store import (  # noqa: E402
    ScreenerStore,
    normalize_query_date,
    normalize_trade_date,
)


def _resolve_trade_date(trade_date: str | None) -> str:
    """解析判定交易日：参数 → 面板 meta latest → 昨天，与扫描保持一致。"""
    if trade_date:
        return normalize_query_date(trade_date)
    try:
        meta = ScreenerStore().read_meta()
        latest = str(meta.get("latest_trade_date") or "").strip()
        if latest:
            return normalize_query_date(latest)
    except Exception:  # noqa: BLE001 - meta 不可用时退回昨天
        pass
    return (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Update the limit-up screener tracking pool (no scan)."
    )
    parser.add_argument(
        "--date",
        dest="trade_date",
        metavar="YYYY-MM-DD",
        help="Evaluation trade date (default: latest available in store)",
    )
    args = parser.parse_args(argv)

    trade_date = _resolve_trade_date(args.trade_date)

    # 复用扫描同源的 Tushare 面板：先确保本地 parquet 含足够历史（算 MA60），
    # 再把 store 传给判定。Tushare/缓存不可用时只告警，逐只退回 loader。
    store = ScreenerStore()
    try:
        end_td = normalize_trade_date(trade_date)
        store.ensure_panel_history(end_td, tracking_update.TRACKING_MIN_HISTORY_DAYS)
        store.ensure_fresh(end_td)
    except Exception as exc:  # noqa: BLE001 - 面板回填失败不阻断判定
        print(f"warn: panel refresh skipped: {exc}", file=sys.stderr)

    summary = tracking_update.run(trade_date, store=store)
    print(f"{trade_date} {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
