"""Tests for screener membership (consecutive-day) tracking."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.screener.tracking import update_membership


@pytest.fixture
def state_path(tmp_path) -> Path:
    return tmp_path / "membership.json"


def _items(*codes: str) -> list[dict]:
    return [{"code": c, "name": c} for c in codes]


def test_first_appearance_is_new(state_path: Path) -> None:
    items = update_membership(_items("600519", "300308"), "2026-06-10", path=state_path)
    by_code = {it["code"]: it for it in items}
    assert by_code["600519"]["membership_days"] == 1
    assert by_code["600519"]["membership_status"] == "新增"
    assert by_code["300308"]["membership_status"] == "新增"


def test_same_trade_date_rescan_does_not_increment(state_path: Path) -> None:
    update_membership(_items("600519"), "2026-06-10", path=state_path)
    items = update_membership(_items("600519"), "2026-06-10", path=state_path)
    assert items[0]["membership_days"] == 1
    assert items[0]["membership_status"] == "新增"


def test_consecutive_dates_increment(state_path: Path) -> None:
    update_membership(_items("600519"), "2026-06-10", path=state_path)
    items = update_membership(_items("600519"), "2026-06-11", path=state_path)
    assert items[0]["membership_days"] == 2
    assert items[0]["membership_status"] == "2天"


def test_streak_breaks_when_absent_then_resets(state_path: Path) -> None:
    update_membership(_items("600519"), "2026-06-10", path=state_path)
    # 6-11 当天未入选 -> 连续中断
    update_membership(_items("300308"), "2026-06-11", path=state_path)
    # 6-12 再次入选 -> 重新“新增”
    items = update_membership(_items("600519"), "2026-06-12", path=state_path)
    assert items[0]["membership_days"] == 1
    assert items[0]["membership_status"] == "新增"


def test_day_max_shows_delete_then_removed(state_path: Path) -> None:
    code = "600519"
    # 用 max_days=3 加速：第3天显示“删除”，第4天剔除
    dates = ["2026-06-01", "2026-06-02", "2026-06-03"]
    last_items: list[dict] = []
    for d in dates:
        last_items = update_membership(_items(code), d, max_days=3, path=state_path)
    assert last_items[0]["membership_days"] == 3
    assert last_items[0]["membership_status"] == "删除"

    # 第 4 天：超过上限 -> 从结果剔除
    removed = update_membership(_items(code), "2026-06-04", max_days=3, path=state_path)
    assert removed == []
    # 状态文件里也不再保留该 code
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert code not in state["codes"]


def test_empty_items(state_path: Path) -> None:
    assert update_membership([], "2026-06-10", path=state_path) == []
