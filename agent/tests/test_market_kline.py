"""Tests for market K-line fetch helpers."""

from __future__ import annotations

import pandas as pd
import pytest

from src.api import market_kline


def test_normalize_bare_code():
    assert market_kline.normalize_bare_code("688017") == "688017"
    assert market_kline.normalize_bare_code("sh688017") == "688017"
    assert market_kline.normalize_bare_code("SZ300308") == "300308"
    assert market_kline.normalize_bare_code("abc") is None


def test_dataframe_to_bars():
    idx = pd.date_range("2025-06-01", periods=2, freq="D")
    df = pd.DataFrame(
        {
            "open": [10.0, 11.0],
            "high": [10.5, 11.5],
            "low": [9.5, 10.5],
            "close": [10.2, 11.2],
            "volume": [1000, 2000],
        },
        index=idx,
    )
    bars = market_kline.dataframe_to_bars(df)
    assert len(bars) == 2
    assert bars[0]["time"] == "2025-06-01"
    assert bars[0]["close"] == 10.2
    assert bars[1]["volume"] == 2000


class _FakeLoader:
    name = "fake"

    def fetch(self, codes, start_date, end_date, *, interval="1D", fields=None):
        idx = pd.date_range(start_date, periods=3, freq="D")
        df = pd.DataFrame(
            {
                "open": [1.0, 2.0, 3.0],
                "high": [1.1, 2.1, 3.1],
                "low": [0.9, 1.9, 2.9],
                "close": [1.0, 2.0, 3.0],
                "volume": [100, 200, 300],
            },
            index=idx,
        )
        return {"688017": df}


def test_fetch_kline_success(monkeypatch):
    monkeypatch.setattr(market_kline, "lookup_symbol_name", lambda code, fallback=None: "绿的谐波")
    monkeypatch.setattr(
        "backtest.loaders.registry.resolve_loader",
        lambda market: _FakeLoader(),
    )
    payload = market_kline.fetch_kline("688017", days=30)
    assert payload["stale"] is False
    assert payload["code"] == "688017"
    assert payload["name"] == "绿的谐波"
    assert payload["source"] == "fake"
    assert len(payload["bars"]) == 3


def test_fetch_kline_invalid_code():
    payload = market_kline.fetch_kline("bad")
    assert payload["stale"] is True
    assert payload["bars"] == []
    assert payload["error"] == "invalid code"
