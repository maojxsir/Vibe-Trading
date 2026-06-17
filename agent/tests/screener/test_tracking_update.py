"""Tests for screener tracking pool orchestration (enter_pool / run / decide)."""

from __future__ import annotations

import pandas as pd
import pytest

from src.screener import tracking_update


def _ohlcv(closes: list[float], start: str = "2026-06-01") -> pd.DataFrame:
    idx = pd.bdate_range(start=start, periods=len(closes))
    return pd.DataFrame({"close": closes}, index=idx)


@pytest.fixture
def mongo_stub(monkeypatch):
    """用内存结构替换 mongodb_stock 的连接与读写，捕获写入文档。"""
    state: dict[str, object] = {"pool": [], "written": []}

    def fake_available() -> bool:
        return True

    def fake_get_pool(status=None):
        if status is None:
            return list(state["pool"])
        return [d for d in state["pool"] if d.get("status") == status]

    def fake_bulk(docs):
        docs = list(docs)
        state["written"] = docs
        # 同步回内存池，模拟 upsert 落库。
        by_id = {str(d.get("_id") or d.get("code")): d for d in state["pool"]}
        for doc in docs:
            by_id[str(doc.get("_id") or doc.get("code"))] = doc
        state["pool"] = list(by_id.values())
        return len(docs)

    monkeypatch.setattr(tracking_update.mongodb_stock, "is_mongodb_available", fake_available)
    monkeypatch.setattr(tracking_update.mongodb_stock, "get_tracking_pool", fake_get_pool)
    monkeypatch.setattr(tracking_update.mongodb_stock, "bulk_upsert_tracking", fake_bulk)
    monkeypatch.setattr(tracking_update.mongodb_stock, "ensure_screener_indexes", lambda: None)
    return state


def test_decide_new_low_first() -> None:
    result = {"new_low_hit": True, "bearish_ma": True, "trading_days_tracked": 40}
    assert tracking_update._decide(result, 30) == ("removed", "consec_new_low")


def test_decide_bearish_ma() -> None:
    result = {"new_low_hit": False, "bearish_ma": True, "trading_days_tracked": 5}
    assert tracking_update._decide(result, 30) == ("removed", "bearish_ma")


def test_decide_expired() -> None:
    result = {"new_low_hit": False, "bearish_ma": False, "trading_days_tracked": 30}
    assert tracking_update._decide(result, 30) == ("expired", "expired_30d")


def test_decide_keep_tracking() -> None:
    result = {"new_low_hit": False, "bearish_ma": False, "trading_days_tracked": 5}
    assert tracking_update._decide(result, 30) == ("tracking", None)


def test_enter_pool_adds_new_and_keeps_existing(mongo_stub, monkeypatch) -> None:
    state = mongo_stub
    state["pool"] = [
        {"_id": "600519", "code": "600519", "name": "贵州茅台", "status": "tracking",
         "day0_date": "2026-06-01", "history": []},
    ]
    items = [
        {"code": "600519", "name": "贵州茅台", "board": "主板", "score": 80},
        {"code": "300308", "name": "中际旭创", "board": "创业板", "score": 75},
    ]
    new_count = tracking_update.enter_pool(items, "2026-06-10")
    assert new_count == 1
    by_id = {d["_id"]: d for d in state["pool"]}
    # 已在跟踪的保留 day0 不重置。
    assert by_id["600519"]["day0_date"] == "2026-06-01"
    # 新入池 day0 为本次交易日。
    assert by_id["300308"]["day0_date"] == "2026-06-10"
    assert by_id["300308"]["status"] == "tracking"


def test_enter_pool_retracks_removed_code(mongo_stub) -> None:
    state = mongo_stub
    state["pool"] = [
        {"_id": "600519", "code": "600519", "status": "removed",
         "day0_date": "2026-05-01", "removed_reason": "bearish_ma", "history": []},
    ]
    items = [{"code": "600519", "name": "贵州茅台", "board": "主板", "score": 80}]
    new_count = tracking_update.enter_pool(items, "2026-06-10")
    assert new_count == 1
    doc = {d["_id"]: d for d in state["pool"]}["600519"]
    assert doc["status"] == "tracking"
    assert doc["day0_date"] == "2026-06-10"
    assert doc["removed_reason"] is None


def test_run_removes_on_new_low(mongo_stub, monkeypatch) -> None:
    state = mongo_stub
    state["pool"] = [
        {"_id": "600519", "code": "600519", "status": "tracking",
         "day0_date": "2026-06-01", "history": []},
    ]
    monkeypatch.setattr(
        tracking_update, "_fetch_ohlcv",
        lambda code, end: _ohlcv([100, 99, 98, 97]),
    )
    summary = tracking_update.run("2026-06-04")
    assert summary["removed"] == 1
    doc = {d["_id"]: d for d in state["pool"]}["600519"]
    assert doc["status"] == "removed"
    assert doc["removed_reason"] == "consec_new_low"
    assert doc["removed_date"] == "2026-06-04"


def test_run_expires_after_max_days(mongo_stub, monkeypatch) -> None:
    state = mongo_stub
    state["pool"] = [
        {"_id": "600519", "code": "600519", "status": "tracking",
         "day0_date": "2026-06-01", "history": []},
    ]
    monkeypatch.setattr(tracking_update, "max_days", lambda: 3)
    # 平盘：无连续创新低、历史不足以判空头，仅靠 30(=3) 日上限到期。
    monkeypatch.setattr(
        tracking_update, "_fetch_ohlcv",
        lambda code, end: _ohlcv([100, 100, 100, 100, 100]),
    )
    summary = tracking_update.run("2026-06-05")
    assert summary["expired"] == 1
    doc = {d["_id"]: d for d in state["pool"]}["600519"]
    assert doc["status"] == "expired"
    assert doc["removed_reason"] == "expired_30d"


def test_run_keeps_when_no_trigger(mongo_stub, monkeypatch) -> None:
    state = mongo_stub
    state["pool"] = [
        {"_id": "600519", "code": "600519", "status": "tracking",
         "day0_date": "2026-06-01", "history": []},
    ]
    monkeypatch.setattr(
        tracking_update, "_fetch_ohlcv",
        lambda code, end: _ohlcv([100, 101, 102, 103]),
    )
    summary = tracking_update.run("2026-06-04")
    assert summary["kept"] == 1
    doc = {d["_id"]: d for d in state["pool"]}["600519"]
    assert doc["status"] == "tracking"
    assert len(doc["history"]) == 1


def test_run_skips_when_no_data(mongo_stub, monkeypatch) -> None:
    state = mongo_stub
    state["pool"] = [
        {"_id": "600519", "code": "600519", "status": "tracking",
         "day0_date": "2026-06-01", "history": []},
    ]
    monkeypatch.setattr(tracking_update, "_fetch_ohlcv", lambda code, end: pd.DataFrame())
    summary = tracking_update.run("2026-06-04")
    assert summary["skipped"] == 1
    assert summary["evaluated"] == 0


def test_run_skipped_when_mongo_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(
        tracking_update.mongodb_stock, "is_mongodb_available", lambda: False
    )
    summary = tracking_update.run("2026-06-04")
    assert summary == {"evaluated": 0, "removed": 0, "expired": 0, "kept": 0, "skipped": 0}
