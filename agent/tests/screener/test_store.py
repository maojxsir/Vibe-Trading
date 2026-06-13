"""Tests for screener panel storage."""

from __future__ import annotations

import pandas as pd
import pytest

import src.screener.store as store_module
from src.screener.store import ScreenerStore, bare_code


@pytest.fixture
def cache_root(tmp_path, monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv(store_module.SCREENER_CACHE_ENV, str(tmp_path))
    monkeypatch.setattr(store_module.time, "sleep", lambda *_args, **_kwargs: None)
    return str(tmp_path)


def _sample_partition_frame(
    trade_date: str,
    *,
    ts_code: str = "600519.SH",
    close: float = 100.0,
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ts_code": [ts_code],
            "trade_date": [trade_date],
            "open": [99.0],
            "high": [101.0],
            "low": [98.0],
            "close": [close],
            "pre_close": [98.0],
            "pct_chg": [2.04],
            "vol": [1000.0],
            "amount": [100000.0],
            "turnover_rate": [1.5],
        }
    )


def test_write_daily_partition_and_load_panel_one_code(cache_root: str) -> None:
    screener = ScreenerStore()
    screener.write_daily_partition("2024-06-03", _sample_partition_frame("20240603"))

    panel = screener.load_panel(["600519"], "2024-06-01", "2024-06-05")

    assert set(panel.keys()) == {"600519"}
    frame = panel["600519"]
    assert list(frame.columns) == [
        "open",
        "high",
        "low",
        "close",
        "pre_close",
        "pct_chg",
        "vol",
        "amount",
        "turnover_rate",
    ]
    assert len(frame) == 1
    assert frame.iloc[0]["close"] == pytest.approx(100.0)
    assert bare_code("600519.SH") == "600519"


def test_load_panel_empty_when_no_partitions(cache_root: str) -> None:
    screener = ScreenerStore()
    assert screener.load_panel(["600519"], "2024-06-01", "2024-06-05") == {}


def test_meta_read_write_roundtrip(cache_root: str) -> None:
    screener = ScreenerStore()
    assert screener.read_meta() == {}

    payload = {"latest_trade_date": "20240603", "source": "tushare"}
    screener.write_meta(payload)
    assert screener.read_meta() == payload


def test_ensure_fresh_with_mock_pro_fetches_two_dates(cache_root: str) -> None:
    class _MockPro:
        def __init__(self) -> None:
            self.daily_calls: list[str] = []
            self.basic_calls: list[str] = []

        def trade_cal(self, exchange, start_date, end_date, is_open):
            return pd.DataFrame(
                {
                    "cal_date": ["20240102", "20240103"],
                    "is_open": ["1", "1"],
                }
            )

        def daily(self, trade_date=None, fields=None):
            self.daily_calls.append(trade_date)
            return pd.DataFrame(
                {
                    "ts_code": ["600519.SH", "000001.SZ"],
                    "trade_date": [trade_date, trade_date],
                    "open": [10.0, 20.0],
                    "high": [11.0, 21.0],
                    "low": [9.0, 19.0],
                    "close": [10.5, 20.5],
                    "pre_close": [10.0, 20.0],
                    "pct_chg": [5.0, 2.5],
                    "vol": [100.0, 200.0],
                    "amount": [1000.0, 2000.0],
                }
            )

        def daily_basic(self, trade_date=None, fields=None):
            self.basic_calls.append(trade_date)
            return pd.DataFrame(
                {
                    "ts_code": ["600519.SH", "000001.SZ"],
                    "trade_date": [trade_date, trade_date],
                    "turnover_rate": [1.2, 2.3],
                }
            )

    screener = ScreenerStore()
    screener.write_meta({"latest_trade_date": "20240101"})
    mock_pro = _MockPro()

    screener.ensure_fresh("2024-01-03", pro=mock_pro)

    assert mock_pro.daily_calls == ["20240102", "20240103"]
    assert mock_pro.basic_calls == ["20240102", "20240103"]
    assert screener.partition_path("20240102").is_file()
    assert screener.partition_path("20240103").is_file()
    assert screener.read_meta()["latest_trade_date"] == "20240103"

    panel = screener.load_panel(["600519"], "2024-01-01", "2024-01-05")
    assert "600519" in panel
    assert len(panel["600519"]) == 2


def test_ensure_panel_history_bootstraps_missing_dates(cache_root: str) -> None:
    class _MockPro:
        def __init__(self) -> None:
            self.daily_calls: list[str] = []

        def trade_cal(self, exchange, start_date, end_date, is_open):
            return pd.DataFrame(
                {
                    "cal_date": ["20240102", "20240103", "20240104"],
                    "is_open": ["1", "1", "1"],
                }
            )

        def daily(self, trade_date=None, fields=None):
            self.daily_calls.append(trade_date)
            return _sample_partition_frame(trade_date)

        def daily_basic(self, trade_date=None, fields=None):
            return pd.DataFrame(
                {
                    "ts_code": ["600519.SH"],
                    "trade_date": [trade_date],
                    "turnover_rate": [1.2],
                }
            )

    screener = ScreenerStore()
    mock_pro = _MockPro()

    screener.ensure_panel_history("2024-01-04", 3, pro=mock_pro)

    assert mock_pro.daily_calls == ["20240102", "20240103", "20240104"]
    assert screener.partition_path("20240102").is_file()
    assert screener.partition_path("20240103").is_file()
    assert screener.partition_path("20240104").is_file()
    assert screener.read_meta()["latest_trade_date"] == "20240104"
