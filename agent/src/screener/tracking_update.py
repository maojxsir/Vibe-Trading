"""打板跟踪池：入池与每日规则判定编排。

职责：
- ``enter_pool``：把一次扫描命中的股票加入跟踪池（已在跟踪的不重置 day0）。
- ``run``：对池中活跃标的取日线、跑 :mod:`tracking_rules`、按规则剔除/到期/保留，写回 MongoDB。

取价优先复用扫描已加载的 Tushare 面板（``ScreenerStore`` 的本地 parquet 缓存，
与扫描同源且含足够历史以算 MA60）；面板缺失或不可用时，再逐只退回既有 fallback
链（MongoDB → Tushare → mootdx → akshare）。
所有 MongoDB 操作为 best-effort：不可用时跳过并告警，绝不中断扫描主流程。
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

import pandas as pd

from backtest.loaders.registry import resolve_loader
from src.data import mongodb_stock
from src.screener import tracking_rules

if TYPE_CHECKING:
    from src.screener.store import ScreenerStore

logger = logging.getLogger(__name__)

MAX_DAYS_ENV = "SCREENER_TRACKING_MAX_DAYS"
NEW_LOW_STREAK_ENV = "SCREENER_TRACKING_NEW_LOW_STREAK"
DEFAULT_MAX_DAYS = 30
DEFAULT_NEW_LOW_STREAK = 3

# 取价窗口：MA60 需要约 60 个交易日，叠加 day0 跟踪期与节假日留足余量。
_FETCH_CALENDAR_DAYS = 200
# 独立 CLI 取价时，面板需回填的最少交易日数（覆盖 MA60 + 跟踪窗口）。
TRACKING_MIN_HISTORY_DAYS = 90
# history 轨迹保留上限，防止文档无限增长。
_HISTORY_CAP = 40


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
        return value if value > 0 else default
    except ValueError:
        return default


def max_days() -> int:
    return _int_env(MAX_DAYS_ENV, DEFAULT_MAX_DAYS)


def new_low_streak() -> int:
    return _int_env(NEW_LOW_STREAK_ENV, DEFAULT_NEW_LOW_STREAK)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _ts_code(bare: str) -> str:
    if bare.startswith(("8", "4", "92")):
        return f"{bare}.BJ"
    suffix = "SH" if bare.startswith(("6", "9")) else "SZ"
    return f"{bare}.{suffix}"


def _fetch_ohlcv(code: str, end_date: str) -> pd.DataFrame:
    """取单只 A 股日线（升序，含足够历史以算 MA60）。失败返回空表。"""
    bare = mongodb_stock.bare_symbol(code)
    if not bare:
        return pd.DataFrame()
    end = pd.Timestamp(end_date).date()
    start = end - timedelta(days=_FETCH_CALENDAR_DAYS)
    try:
        loader = resolve_loader("a_share")
        frames = loader.fetch(
            [bare, _ts_code(bare)],
            start.strftime("%Y-%m-%d"),
            end.strftime("%Y-%m-%d"),
            interval="1D",
        )
    except Exception as exc:  # noqa: BLE001 - 单只取价失败不影响其它标的
        logger.debug("tracking fetch ohlcv failed (%s): %s", bare, exc)
        return pd.DataFrame()

    df = frames.get(bare)
    if df is None or df.empty:
        df = frames.get(_ts_code(bare))
    return df if df is not None else pd.DataFrame()


def _load_pool_panel(
    store: "ScreenerStore | None",
    pool: list[dict[str, Any]],
    end_date: str,
) -> dict[str, pd.DataFrame]:
    """批量取池内标的日线（复用扫描的 Tushare 面板缓存，一次 DuckDB 查询取全量历史）。

    返回 ``{bare_code: DataFrame}``；``store`` 为空、无分区或查询失败时返回空字典，
    由调用方逐只退回 :func:`_fetch_ohlcv`。
    """
    if store is None or not pool:
        return {}
    codes: list[str] = []
    for doc in pool:
        bare = mongodb_stock.bare_symbol(str(doc.get("_id") or doc.get("code") or ""))
        if bare:
            codes.append(bare)
    if not codes:
        return {}
    end = pd.Timestamp(end_date).date()
    start = end - timedelta(days=_FETCH_CALENDAR_DAYS)
    try:
        return store.load_panel(
            codes, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
        )
    except Exception as exc:  # noqa: BLE001 - 面板取价失败逐只退回 loader
        logger.warning("tracking panel load failed: %s", exc)
        return {}


def _new_tracking_doc(item: dict[str, Any], trade_date: str) -> dict[str, Any]:
    code = mongodb_stock.bare_symbol(str(item.get("code", "")))
    now = _utc_now_iso()
    return {
        "_id": code,
        "code": code,
        "name": item.get("name"),
        "board": item.get("board"),
        "status": "tracking",
        "day0_date": trade_date,
        "entry_score": item.get("score"),
        "entry_signals": item.get("signals"),
        "trading_days_tracked": 0,
        "last_eval_date": trade_date,
        "last_close": item.get("price"),
        "min_close_since_entry": None,
        "consec_new_low": 0,
        "ma": {},
        "bearish_ma": False,
        "removed_reason": None,
        "removed_date": None,
        "history": [],
        "createdAt": now,
        "updatedAt": now,
    }


def enter_pool(items: list[dict[str, Any]], trade_date: str) -> int:
    """把扫描命中股票加入跟踪池；已在跟踪的仅刷新展示字段，不重置 day0。

    返回新入池股票数量。MongoDB 不可用时返回 0。
    """
    if not items or not mongodb_stock.is_mongodb_available():
        return 0

    mongodb_stock.ensure_screener_indexes()
    existing = {
        str(doc.get("_id")): doc for doc in mongodb_stock.get_tracking_pool(None)
    }

    to_write: list[dict[str, Any]] = []
    new_count = 0
    for item in items:
        code = mongodb_stock.bare_symbol(str(item.get("code", "")))
        if not code:
            continue
        prev = existing.get(code)
        if prev is not None and prev.get("status") == "tracking":
            # 已在跟踪：仅更新展示字段，保留 day0 与历史。
            prev["name"] = item.get("name", prev.get("name"))
            prev["board"] = item.get("board", prev.get("board"))
            to_write.append(prev)
        else:
            # 新入池，或此前已剔除/到期后再次命中：以新一轮重新计数。
            to_write.append(_new_tracking_doc(item, trade_date))
            new_count += 1

    mongodb_stock.bulk_upsert_tracking(to_write)
    return new_count


def _decide(result: dict[str, Any], doc_max_days: int) -> tuple[str, str | None]:
    """根据判定结果返回 (status, removed_reason)。"""
    if result.get("new_low_hit"):
        return "removed", "consec_new_low"
    if result.get("bearish_ma"):
        return "removed", "bearish_ma"
    if int(result.get("trading_days_tracked", 0)) >= doc_max_days:
        return "expired", "expired_30d"
    return "tracking", None


def _append_history(doc: dict[str, Any], trade_date: str, result: dict[str, Any]) -> None:
    history = list(doc.get("history") or [])
    entry = {
        "date": trade_date,
        "close": result.get("last_close"),
        "consec_new_low": result.get("consec_new_low"),
        "bearish_ma": result.get("bearish_ma"),
    }
    # 同一交易日重复判定则替换末条，避免重复累积。
    if history and history[-1].get("date") == trade_date:
        history[-1] = entry
    else:
        history.append(entry)
    doc["history"] = history[-_HISTORY_CAP:]


def run(trade_date: str, *, store: "ScreenerStore | None" = None) -> dict[str, int]:
    """对跟踪池活跃标的执行一次规则判定并写回。返回统计摘要。

    ``store`` 提供时优先从扫描同源的 Tushare 面板批量取价（含足够历史以算 MA60），
    缺失标的再逐只退回 loader fallback 链。
    """
    summary = {"evaluated": 0, "removed": 0, "expired": 0, "kept": 0, "skipped": 0}
    if not mongodb_stock.is_mongodb_available():
        logger.info("tracking update skipped: MongoDB unavailable")
        return summary

    doc_max_days = max_days()
    streak = new_low_streak()
    pool = mongodb_stock.get_tracking_pool("tracking")
    panel_map = _load_pool_panel(store, pool, trade_date)
    updated: list[dict[str, Any]] = []

    for doc in pool:
        code = str(doc.get("_id") or doc.get("code") or "")
        day0 = str(doc.get("day0_date") or trade_date)
        ohlcv = panel_map.get(mongodb_stock.bare_symbol(code))
        if ohlcv is None or ohlcv.empty:
            ohlcv = _fetch_ohlcv(code, trade_date)
        result = tracking_rules.evaluate(ohlcv, day0, new_low_streak=streak)
        if not result.get("has_data"):
            summary["skipped"] += 1
            continue

        summary["evaluated"] += 1
        status, reason = _decide(result, doc_max_days)

        doc["status"] = status
        doc["trading_days_tracked"] = result["trading_days_tracked"]
        doc["last_eval_date"] = trade_date
        doc["last_close"] = result["last_close"]
        doc["min_close_since_entry"] = result["min_close_since_entry"]
        doc["consec_new_low"] = result["consec_new_low"]
        doc["ma"] = result["ma"]
        doc["bearish_ma"] = result["bearish_ma"]
        _append_history(doc, trade_date, result)

        if status == "tracking":
            summary["kept"] += 1
        else:
            doc["removed_reason"] = reason
            doc["removed_date"] = trade_date
            if status == "removed":
                summary["removed"] += 1
            else:
                summary["expired"] += 1

        updated.append(doc)

    if updated:
        mongodb_stock.bulk_upsert_tracking(updated)
    logger.info("tracking update %s: %s", trade_date, summary)
    return summary
