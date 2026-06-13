"""Tests for screener result metadata enrichment (industry / main business / cap)."""

from __future__ import annotations

import pandas as pd
import pytest

from src.screener import enrich
from src.screener.enrich import enrich_items


class _FakePro:
    """Minimal Tushare stub returning canned frames."""

    def __init__(self) -> None:
        self.daily_basic_calls: list[str] = []
        self.fina_calls: list[str] = []

    def stock_basic(self, list_status=None, fields=None):
        return pd.DataFrame(
            {
                "ts_code": ["600519.SH", "300308.SZ"],
                "symbol": ["600519", "300308"],
                "industry": ["白酒", "光模块"],
            }
        )

    def stock_company(self, fields=None):
        return pd.DataFrame(
            {
                "ts_code": ["600519.SH", "300308.SZ"],
                "main_business": ["茅台酒及系列酒的生产与销售", "光通信收发模块研发制造"],
            }
        )

    def daily_basic(self, trade_date=None, fields=None):
        self.daily_basic_calls.append(trade_date)
        return pd.DataFrame(
            {
                "ts_code": ["600519.SH", "300308.SZ"],
                "close": [1500.0, 120.5],
                "pe_ttm": [22.5, 45.1],
                "total_mv": [200_000_000.0, 30_000_000.0],  # 万元
            }
        )

    def fina_indicator(self, ts_code=None, fields=None):
        self.fina_calls.append(ts_code)
        known = {"600519.SH": 1.37, "300308.SZ": 88.0}
        if ts_code not in known:
            return pd.DataFrame(columns=["ts_code", "end_date", "q_profit_yoy"])
        return pd.DataFrame(
            {
                "ts_code": [ts_code, ts_code],
                "end_date": ["20251231", "20260331"],
                "q_profit_yoy": [-30.0, known[ts_code]],
            }
        )


@pytest.fixture(autouse=True)
def _clear_cache(monkeypatch, tmp_path) -> None:
    enrich.reset_cache()
    monkeypatch.setattr(enrich, "GROWTH_THROTTLE_S", 0.0)
    # 隔离磁盘增速缓存，避免污染真实 home。
    monkeypatch.setattr(
        enrich, "growth_cache_path", lambda: tmp_path / "growth_cache.json"
    )
    yield
    enrich.reset_cache()


def test_enrich_items_adds_fields() -> None:
    items = [
        {"code": "600519", "name": "贵州茅台"},
        {"code": "300308", "name": "中际旭创"},
    ]
    pro = _FakePro()

    enrich_items(items, "2026-06-11", pro)

    assert items[0]["industry"] == "白酒"
    assert items[0]["main_business"].startswith("茅台酒")
    # total_mv 万元 -> 元
    assert items[0]["market_cap"] == pytest.approx(200_000_000.0 * 1e4)
    assert items[0]["price"] == pytest.approx(1500.0)
    assert items[0]["pe_ttm"] == pytest.approx(22.5)
    # 取最新报告期(20260331)的单季净利润同比
    assert items[0]["quarter_growth"] == pytest.approx(1.37)
    assert items[1]["industry"] == "光模块"
    assert items[1]["market_cap"] == pytest.approx(30_000_000.0 * 1e4)
    assert items[1]["price"] == pytest.approx(120.5)
    assert items[1]["quarter_growth"] == pytest.approx(88.0)
    assert pro.daily_basic_calls == ["20260611"]


def test_enrich_items_missing_code_gets_empty_fields() -> None:
    items = [{"code": "000001", "name": "平安银行"}]
    enrich_items(items, "2026-06-11", _FakePro())

    assert items[0]["industry"] == ""
    assert items[0]["main_business"] == ""
    assert items[0]["market_cap"] is None
    assert items[0]["price"] is None
    assert items[0]["pe_ttm"] is None
    assert items[0]["quarter_growth"] is None


def test_enrich_items_tolerates_source_failure() -> None:
    class _BrokenPro:
        def stock_basic(self, **_kwargs):
            raise RuntimeError("boom")

        def stock_company(self, **_kwargs):
            raise RuntimeError("boom")

        def daily_basic(self, **_kwargs):
            raise RuntimeError("boom")

        def fina_indicator(self, **_kwargs):
            raise RuntimeError("boom")

    items = [{"code": "600519", "name": "贵州茅台"}]
    # 不抛异常，字段降级为空
    enrich_items(items, "2026-06-11", _BrokenPro())

    assert items[0]["industry"] == ""
    assert items[0]["main_business"] == ""
    assert items[0]["market_cap"] is None
    assert items[0]["price"] is None
    assert items[0]["pe_ttm"] is None
    assert items[0]["quarter_growth"] is None


def test_enrich_items_empty_list_noop() -> None:
    assert enrich_items([], "2026-06-11", _FakePro()) == []
