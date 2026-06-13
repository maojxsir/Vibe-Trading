"""Tests for screener scan orchestration."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.screener.config import ScreenerConfig
from src.screener.scan import load_latest_result, load_result, run, screener_results_root
from src.screener.store import ScreenerStore


def _make_df(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df.set_index("trade_date").sort_index()


def _date_seq(start: str, n: int) -> list[pd.Timestamp]:
    base = pd.Timestamp(start)
    return [base + pd.Timedelta(days=i) for i in range(n)]


def _flat_ohlcv(
    dates: list[pd.Timestamp],
    *,
    close: float = 100.0,
    vol: float = 1_000_000.0,
    turnover_rate: float = 5.0,
) -> list[dict]:
    rows: list[dict] = []
    prev = close * 0.99
    for i, dt in enumerate(dates):
        o = prev
        c = close
        rows.append(
            {
                "trade_date": dt,
                "open": o,
                "high": max(o, c) + 0.5,
                "low": min(o, c) - 0.5,
                "close": c,
                "pre_close": prev,
                "vol": vol,
                "turnover_rate": turnover_rate,
                "pct_chg": (c - prev) / prev * 100,
            }
        )
        prev = c
    return rows


def _limitup_panel() -> pd.DataFrame:
    """近乎走平、近 30 日量能翻倍、且最近有一个涨停日的合格标的。

    历史长度需覆盖量能主算法的 recent+prior 窗口（30+30），价格走平以避免触发
    高位/过热否决，仅靠“涨停 + 量能放大”通过必选。
    """
    n = 70
    # 末日落在扫描交易日 2024-01-26（避免被 _slice_panel_to_trade_date 截断）
    dates = _date_seq("2023-11-18", n)
    rows: list[dict] = []
    price = 100.0
    for i, dt in enumerate(dates):
        prev = price
        price = 100.0 + (0.2 if i % 2 == 0 else -0.2)
        vol = 1_000_000.0 if i < n - 30 else 2_200_000.0  # 最近 30 日量能翻倍
        rows.append(
            {
                "trade_date": dt,
                "open": prev,
                "high": max(prev, price) + 0.3,
                "low": min(prev, price) - 0.3,
                "close": price,
                "pre_close": prev,
                "vol": vol,
                "turnover_rate": 5.0,
                "pct_chg": (price - prev) / prev * 100,
            }
        )

    limit_idx = n - 8  # 距末日 7 个交易日，limitup 信号仍有效
    prev_close = rows[limit_idx - 1]["close"]
    limit_close = round(prev_close * 1.099, 2)
    rows[limit_idx].update(
        {
            "open": round(prev_close * 1.03, 2),
            "high": limit_close,
            "low": round(prev_close * 1.02, 2),
            "close": limit_close,
            "pct_chg": 9.9,
            "turnover_rate": 8.0,
            "pre_close": prev_close,
        }
    )
    pullback = limit_close
    for i in range(limit_idx + 1, n):
        pullback = max(prev_close, pullback * 0.985)
        rows[i]["pre_close"] = rows[i - 1]["close"]
        rows[i]["close"] = round(pullback, 2)
        rows[i]["open"] = round(pullback - 0.2, 2)
        rows[i]["high"] = round(pullback + 0.4, 2)
        rows[i]["low"] = round(pullback - 0.4, 2)
        rows[i]["vol"] = 2_200_000.0
        rows[i]["pct_chg"] = (
            (rows[i]["close"] - rows[i]["pre_close"]) / rows[i]["pre_close"] * 100
        )
    return _make_df(rows)


def _flat_panel() -> pd.DataFrame:
    dates = _date_seq("2023-11-18", 70)
    return _make_df(_flat_ohlcv(dates))


@pytest.fixture
def config() -> ScreenerConfig:
    return ScreenerConfig()


@pytest.fixture
def results_root(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "results"
    monkeypatch.setattr("src.screener.scan.screener_results_root", lambda: root)
    return root


def test_run_writes_sorted_json_with_limitup_leader(
    config: ScreenerConfig,
    results_root,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trade_date = "2024-01-26"
    universe = [
        {
            "code": "600519",
            "name": "贵州茅台",
            "ts_code": "600519.SH",
            "board": "主板",
        },
        {
            "code": "000001",
            "name": "平安银行",
            "ts_code": "000001.SZ",
            "board": "主板",
        },
    ]
    panels = {
        "600519": _limitup_panel(),
        "000001": _flat_panel(),
    }

    monkeypatch.setattr("src.screener.scan.build_universe", lambda *_args, **_kwargs: universe)
    # 富化依赖 Tushare 网络，单测里置空，保证 hermetic。
    monkeypatch.setattr(
        "src.screener.scan.enrich_items",
        lambda items, *_args, **_kwargs: items,
    )
    # 连续入选跟踪会写入真实 home 目录，单测里置空为直通。
    monkeypatch.setattr(
        "src.screener.scan.update_membership",
        lambda items, *_args, **_kwargs: items,
    )
    monkeypatch.setattr(
        ScreenerStore,
        "ensure_fresh",
        lambda self, *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        ScreenerStore,
        "ensure_panel_history",
        lambda self, *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        ScreenerStore,
        "load_panel",
        lambda self, codes, start, end: {
            code: panels[code] for code in codes if code in panels
        },
    )
    monkeypatch.setattr(
        ScreenerStore,
        "load_index_series",
        lambda self, start, end, index_code="000300": pd.Series(dtype=float),
    )
    monkeypatch.setattr(
        ScreenerStore,
        "read_meta",
        lambda self: {"latest_trade_date": "20240126"},
    )

    out_path = run(config, trade_date=trade_date, store=ScreenerStore())

    assert out_path == results_root / "screener_2024-01-26.json"
    assert out_path.is_file()

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["tradeDate"] == "2024-01-26"
    assert payload["source"] == "tushare"
    assert payload["skipped"] == 0
    assert "filtered_count" in payload
    assert payload["universe_count"] == 2
    assert payload["matched_count"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["code"] == "600519"
    assert payload["filtered_count"] >= 1
    assert payload["items"][0]["signals"]["limitup"] > 0

    scores = [item["score"] for item in payload["items"]]
    assert scores == sorted(scores, reverse=True)
    assert scores[0] > 0

    loaded = load_result("2024-01-26")
    assert loaded == payload
    assert load_latest_result() == payload


def test_load_result_missing_returns_none(results_root) -> None:
    assert load_result("2026-01-01") is None
    assert load_latest_result() is None
