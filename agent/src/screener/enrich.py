"""Best-effort metadata enrichment for screener result items.

为每个命中项补充展示字段：
- ``industry``：行业板块（Tushare ``stock_basic.industry``）
- ``main_business``：主营业务（Tushare ``stock_company.main_business``）
- ``market_cap``：总市值（元，``daily_basic.total_mv`` 万元 → 元）
- ``price``：现价（``daily_basic.close``）
- ``pe_ttm``：市盈率 TTM（``daily_basic.pe_ttm``）
- ``quarter_growth``：最近季度增速（单季净利润同比 ``fina_indicator.q_profit_yoy``，%）

所有抓取均为“尽力而为”：任一数据源失败只会让对应字段为空，绝不会中断扫描主流程。
行情/估值/市值走 ``daily_basic`` 批量一次取全市场；季度增速无 VIP 权限，按命中股逐个
拉取 ``fina_indicator`` 并按代码缓存 24h，带时间预算，失败留空。
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any

import pandas as pd

from src.screener.store import bare_code, normalize_trade_date, to_ts_code

logger = logging.getLogger(__name__)

_META_TTL_S = 24 * 60 * 60
_meta_cache: dict[str, dict[str, str]] | None = None
_meta_cache_at = 0.0

# 季度增速逐股拉取：无 VIP 批量权限，且逐股会触发每分钟限频，因此结果落盘缓存，
# 每轮扫描在时间预算内补一批，跨扫描/重启累积，季度数据少变，TTL 取 7 天。
_GROWTH_TTL_S = 7 * 24 * 60 * 60
_GROWTH_FETCH_BUDGET_S = 240.0
GROWTH_THROTTLE_S = 0.35


def growth_cache_path() -> Path:
    """季度增速磁盘缓存路径。"""
    return Path.home() / ".vibe-trading" / "screener" / "growth_cache.json"


def reset_cache() -> None:
    """清空进程内静态元数据缓存（测试用）。"""
    global _meta_cache, _meta_cache_at
    _meta_cache = None
    _meta_cache_at = 0.0


def _load_static_meta(pro) -> dict[str, dict[str, str]]:
    """返回 {bare_code: {industry, main_business}}，带 24h 进程内缓存。"""
    global _meta_cache, _meta_cache_at
    now = time.time()
    if _meta_cache is not None and now - _meta_cache_at < _META_TTL_S:
        return _meta_cache

    meta: dict[str, dict[str, str]] = {}

    try:
        basic = pro.stock_basic(list_status="L", fields="ts_code,symbol,industry")
        for row in basic.to_dict("records"):
            code = bare_code(str(row.get("symbol") or row.get("ts_code") or ""))
            if not code:
                continue
            meta.setdefault(code, {})["industry"] = str(row.get("industry") or "").strip()
    except Exception as exc:  # noqa: BLE001 - 行业缺失不致命
        logger.warning("screener enrich: stock_basic industry failed: %s", exc)

    try:
        comp = pro.stock_company(fields="ts_code,main_business")
        for row in comp.to_dict("records"):
            code = bare_code(str(row.get("ts_code") or ""))
            if not code:
                continue
            meta.setdefault(code, {})["main_business"] = str(
                row.get("main_business") or ""
            ).strip()
    except Exception as exc:  # noqa: BLE001 - 主营业务缺失不致命
        logger.warning("screener enrich: stock_company main_business failed: %s", exc)

    _meta_cache = meta
    _meta_cache_at = now
    return meta


def _to_float(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _load_quote(pro, trade_date: str) -> dict[str, dict[str, float | None]]:
    """返回 {bare_code: {price, pe_ttm, market_cap}}，daily_basic 批量一次取全市场。"""
    td = normalize_trade_date(trade_date)
    out: dict[str, dict[str, float | None]] = {}
    try:
        df = pro.daily_basic(trade_date=td, fields="ts_code,close,pe_ttm,total_mv")
        for row in df.to_dict("records"):
            code = bare_code(str(row.get("ts_code") or ""))
            if not code:
                continue
            mv = _to_float(row.get("total_mv"))
            out[code] = {
                "price": _to_float(row.get("close")),
                "pe_ttm": _to_float(row.get("pe_ttm")),
                # Tushare total_mv 单位为万元，转换为元
                "market_cap": mv * 1e4 if mv is not None else None,
            }
    except Exception as exc:  # noqa: BLE001 - 行情/估值缺失不致命
        logger.warning("screener enrich: daily_basic failed: %s", exc)
    return out


def _latest_quarter_growth(pro, ts_code: str) -> float | None:
    """取该股最新报告期的单季净利润同比（q_profit_yoy, %）。"""
    df = pro.fina_indicator(ts_code=ts_code, fields="ts_code,end_date,q_profit_yoy")
    if df is None or getattr(df, "empty", True):
        return None
    df = df.dropna(subset=["end_date"])
    if df.empty:
        return None
    row = df.sort_values("end_date").iloc[-1]
    return _to_float(row.get("q_profit_yoy"))


def _read_growth_cache() -> dict[str, dict[str, Any]]:
    path = growth_cache_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("screener enrich: growth cache read failed: %s", exc)
        return {}
    return data if isinstance(data, dict) else {}


def _write_growth_cache(cache: dict[str, dict[str, Any]]) -> None:
    path = growth_cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    tmp.write_text(
        json.dumps(cache, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    os.replace(tmp, path)


def _load_growth(pro, items: list[dict[str, Any]]) -> dict[str, float]:
    """逐股拉取最近季度增速；磁盘缓存优先，预算内补未命中项，跨扫描累积。

    成功结果（含数据本身为空）写入缓存；抓取异常不写缓存，留待下次重试。
    """
    now = time.time()
    deadline = now + _GROWTH_FETCH_BUDGET_S
    cache = _read_growth_cache()
    out: dict[str, float] = {}
    dirty = False

    for item in items:
        code = bare_code(str(item.get("code", "")))
        if not code:
            continue
        ent = cache.get(code)
        if isinstance(ent, dict) and now - float(ent.get("ts", 0) or 0) < _GROWTH_TTL_S:
            val = ent.get("v")
            if val is not None:
                out[code] = float(val)
            continue
        if time.time() > deadline:
            continue  # 预算用尽，未命中项留待下次扫描补齐
        try:
            val = _latest_quarter_growth(pro, to_ts_code(code))
        except Exception as exc:  # noqa: BLE001 - 抓取异常不缓存，下次重试
            logger.warning("screener enrich: growth skip %s: %s", code, exc)
            continue
        cache[code] = {"v": val, "ts": time.time()}
        dirty = True
        if val is not None:
            out[code] = val
        time.sleep(GROWTH_THROTTLE_S)

    if dirty:
        try:
            _write_growth_cache(cache)
        except OSError as exc:
            logger.warning("screener enrich: growth cache write failed: %s", exc)
    return out


def enrich_items(
    items: list[dict[str, Any]],
    trade_date: str,
    pro,
) -> list[dict[str, Any]]:
    """就地为命中项补充行业/主营/市值/现价/PE(TTM)/季度增速字段。"""
    if not items:
        return items

    static = _load_static_meta(pro)
    quote = _load_quote(pro, trade_date)
    growth = _load_growth(pro, items)

    for item in items:
        code = bare_code(str(item.get("code", "")))
        meta = static.get(code, {})
        item["industry"] = meta.get("industry", "")
        item["main_business"] = meta.get("main_business", "")
        q = quote.get(code, {})
        item["price"] = q.get("price")
        item["pe_ttm"] = q.get("pe_ttm")
        item["market_cap"] = q.get("market_cap")
        item["quarter_growth"] = growth.get(code)
    return items
