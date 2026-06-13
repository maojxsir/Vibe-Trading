"""Tests for screener universe construction."""

from __future__ import annotations

from datetime import date

import pytest

from src.api import symbol_index
from src.screener.config import ScreenerConfig
from src.screener.universe import build_universe

MOCK_INDEX = [
    {
        "code": "600519",
        "name": "贵州茅台",
        "ts_code": "600519.SH",
        "cnspell": "GZMT",
        "list_date": "20010425",
    },
    {
        "code": "300308",
        "name": "中际旭创",
        "ts_code": "300308.SZ",
        "cnspell": "ZJXC",
        "list_date": "20120410",
    },
    {
        "code": "920001",
        "name": "示例北交所",
        "ts_code": "920001.BJ",
        "cnspell": "SLBJS",
        "list_date": "20230101",
    },
    {
        "code": "600000",
        "name": "*ST示例",
        "ts_code": "600000.SH",
        "cnspell": "STSL",
        "list_date": "19991110",
    },
    {
        "code": "600001",
        "name": "新上市股",
        "ts_code": "600001.SH",
        "cnspell": "XSSG",
        "list_date": "20250501",
    },
    {
        "code": "605081",
        "name": "退市太和",
        "ts_code": "605081.SH",
        "cnspell": "TSTH",
        "list_date": "20200101",
    },
]


@pytest.fixture(autouse=True)
def _patch_load_index(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(symbol_index, "load_index", lambda force=False: list(MOCK_INDEX))


def test_build_universe_boards() -> None:
    rows = build_universe(ScreenerConfig(exclude_st=False), as_of=date(2025, 6, 13))
    by_code = {row["code"]: row for row in rows}

    assert by_code["600519"]["board"] == "主板"
    assert by_code["300308"]["board"] == "创业板"
    assert by_code["920001"]["board"] == "北交所"


def test_build_universe_default_excludes_st() -> None:
    rows = build_universe(ScreenerConfig(), as_of=date(2025, 6, 13))
    codes = {row["code"] for row in rows}
    assert "600000" not in codes


def test_build_universe_default_excludes_delisting() -> None:
    rows = build_universe(ScreenerConfig(), as_of=date(2025, 6, 13))
    codes = {row["code"] for row in rows}
    assert "605081" not in codes  # 退市太和
    assert "600519" in codes


def test_build_universe_keep_delisting_when_disabled() -> None:
    config = ScreenerConfig(exclude_delisting=False)
    rows = build_universe(config, as_of=date(2025, 6, 13))
    codes = {row["code"] for row in rows}
    assert "605081" in codes


def test_build_universe_exclude_st() -> None:
    config = ScreenerConfig(exclude_st=True)
    rows = build_universe(config, as_of=date(2025, 6, 13))
    codes = {row["code"] for row in rows}

    assert "600000" not in codes
    assert "600519" in codes


def test_build_universe_exclude_new_days() -> None:
    config = ScreenerConfig(exclude_new_days=60)
    rows = build_universe(config, as_of=date(2025, 6, 13))
    codes = {row["code"] for row in rows}

    assert "600001" not in codes
    assert "600519" in codes
