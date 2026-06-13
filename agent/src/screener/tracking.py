"""Persistent membership tracking for screener results.

记录每只股票“连续被选出”的天数（按交易日推进），并据此给出状态：
- 第 1 天：``新增``
- 第 2..(max-1) 天：``N天``
- 第 max 天（默认 30）：``删除``（最后一天仍展示，提示即将剔除）
- 超过 max 天（第 max+1 天起）：直接从结果中剔除

判定按交易日推进：同一交易日重复扫描不累加；某交易日未入选则连续中断，
下次入选重新从“新增”计数。状态文件：``~/.vibe-trading/screener/membership.json``。
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_MAX_DAYS = 30


def membership_state_path() -> Path:
    """连续入选跟踪状态文件路径。"""
    return Path.home() / ".vibe-trading" / "screener" / "membership.json"


def _read_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("membership state read failed (%s): %s", path, exc)
        return {}
    return data if isinstance(data, dict) else {}


def _write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    tmp.write_text(
        json.dumps(state, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    os.replace(tmp, path)


def _status_for(days: int, max_days: int) -> str:
    if days <= 1:
        return "新增"
    if days >= max_days:
        return "删除"
    return f"{days}天"


def update_membership(
    items: list[dict[str, Any]],
    trade_date: str,
    *,
    max_days: int = DEFAULT_MAX_DAYS,
    path: Path | None = None,
) -> list[dict[str, Any]]:
    """更新并就地标注连续入选天数；返回剔除“超期”项后的结果列表。

    为每个保留项写入 ``membership_days`` 与 ``membership_status``，并把连续天数
    超过 ``max_days`` 的标的从返回列表中移除（第 max+1 天剔除）。
    """
    state_path = path or membership_state_path()
    state = _read_state(state_path)
    prev_codes = state.get("codes")
    if not isinstance(prev_codes, dict):
        prev_codes = {}

    new_codes: dict[str, Any] = {}
    kept: list[dict[str, Any]] = []

    for item in items:
        code = str(item.get("code", ""))
        if not code:
            continue
        prev = prev_codes.get(code)
        if isinstance(prev, dict):
            first_date = str(prev.get("first_date") or trade_date)
            last_date = str(prev.get("last_date") or "")
            prev_days = int(prev.get("days") or 1)
            if last_date == trade_date:
                days = prev_days  # 同一交易日重复扫描，不累加
            elif last_date and trade_date > last_date:
                days = prev_days + 1
            else:
                days = prev_days
        else:
            first_date = trade_date
            days = 1

        if days > max_days:
            # 第 max+1 天起：剔除，并从跟踪中遗忘（再次入选则重新计数）
            continue

        item["membership_days"] = days
        item["membership_status"] = _status_for(days, max_days)
        new_codes[code] = {
            "first_date": first_date,
            "last_date": trade_date,
            "days": days,
        }
        kept.append(item)

    _write_state(state_path, {"last_trade_date": trade_date, "codes": new_codes})
    return kept
