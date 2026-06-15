"""Tests for MongoDB stock loader and helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from backtest.loaders.mongodb_loader import DataLoader
from src.data import mongodb_stock


@pytest.fixture(autouse=True)
def _reset_mongo_cache() -> None:
    mongodb_stock.reset_cached_connection()
    yield
    mongodb_stock.reset_cached_connection()


def test_bare_symbol_and_ts_code() -> None:
    assert mongodb_stock.bare_symbol("600519.SH") == "600519"
    assert mongodb_stock.to_ts_code("000001") == "000001.SZ"


def test_daily_quotes_to_ohlcv() -> None:
    frame = pd.DataFrame(
        [
            {
                "trade_date": "20240603",
                "open": 10.0,
                "high": 11.0,
                "low": 9.5,
                "close": 10.5,
                "vol": 100.0,
            }
        ]
    )
    ohlcv = mongodb_stock.daily_quotes_to_ohlcv(frame)
    assert list(ohlcv.columns) == ["open", "high", "low", "close", "volume"]
    assert len(ohlcv) == 1
    assert ohlcv.iloc[0]["volume"] == 10000.0


def test_loader_fetch_triggers_on_demand_sync(monkeypatch: pytest.MonkeyPatch) -> None:
    loader = DataLoader()
    empty = pd.DataFrame()
    full = mongodb_stock.daily_quotes_to_ohlcv(
        pd.DataFrame(
            [
                {
                    "trade_date": "20240601",
                    "open": 1,
                    "high": 2,
                    "low": 1,
                    "close": 2,
                    "volume": 100,
                },
                {
                    "trade_date": "20240603",
                    "open": 2,
                    "high": 3,
                    "low": 2,
                    "close": 3,
                    "volume": 200,
                },
            ]
        )
    )

    calls = {"sync": 0, "fetch": 0}

    def _fetch(_code: str, _start: str, _end: str) -> pd.DataFrame:
        calls["fetch"] += 1
        return full if calls["fetch"] > 1 else empty

    monkeypatch.setattr(mongodb_stock, "is_mongodb_available", lambda: True)
    monkeypatch.setattr(mongodb_stock, "fetch_daily_ohlcv", _fetch)
    monkeypatch.setattr(
        mongodb_stock,
        "coverage_is_sufficient",
        lambda frame, *_args, **_kwargs: frame is not None and not frame.empty,
    )

    def _sync(*_args, **_kwargs) -> bool:
        calls["sync"] += 1
        return True

    monkeypatch.setattr(mongodb_stock, "trigger_symbol_sync", _sync)

    result = loader.fetch(["600519"], "2024-06-01", "2024-06-03")
    assert calls["sync"] == 1
    assert "600519.SH" in result
    assert len(result["600519.SH"]) == 2


def test_loader_unavailable_without_mongo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mongodb_stock, "is_mongodb_available", lambda: False)
    loader = DataLoader()
    assert loader.is_available() is False


def test_registry_prefers_mongodb_when_available() -> None:
    from backtest.loaders.registry import FALLBACK_CHAINS, _ensure_registered, LOADER_REGISTRY

    _ensure_registered()
    assert "mongodb" in LOADER_REGISTRY
    assert FALLBACK_CHAINS["a_share"][0] == "mongodb"
