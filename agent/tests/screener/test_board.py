"""Tests for A-share board detection and limit-up helpers."""

from __future__ import annotations

import pytest

from src.screener.board import detect_board, is_limit_up, limit_up_threshold


def test_detect_board_chinext() -> None:
    assert detect_board("300308", "中际旭创") == "创业板"


def test_detect_board_chinext_with_suffix() -> None:
    assert detect_board("300308.SZ", "中际旭创") == "创业板"


def test_detect_board_star_market() -> None:
    assert detect_board("688981", "中芯国际") == "科创板"
    assert detect_board("688981.SH", "中芯国际") == "科创板"


def test_detect_board_beijing_exchange() -> None:
    assert detect_board("920799", "示例北交所") == "北交所"
    assert detect_board("830799.BJ", "示例北交所") == "北交所"
    assert detect_board("430047", "示例北交所") == "北交所"


def test_detect_board_main_board() -> None:
    assert detect_board("600519", "贵州茅台") == "主板"
    assert detect_board("000001.SZ", "平安银行") == "主板"


def test_detect_board_st_from_name() -> None:
    assert detect_board("600519", "*ST茅台") == "ST"
    assert detect_board("300308", "ST中际") == "ST"


def test_limit_up_main_board() -> None:
    assert limit_up_threshold("600519", "贵州茅台") == 10.0


@pytest.mark.parametrize(
    "code, name, expected",
    [
        ("688981", "中芯国际", 20.0),
        ("300308", "中际旭创", 20.0),
        ("920799", "示例北交所", 30.0),
        ("600519", "*ST茅台", 5.0),
    ],
)
def test_limit_up_threshold_by_board(code: str, name: str, expected: float) -> None:
    assert limit_up_threshold(code, name) == expected


def test_is_limit_up_with_tolerance() -> None:
    assert is_limit_up(pct_chg=9.75, code="600519", name="贵州茅台") is True
    assert is_limit_up(pct_chg=9.0, code="600519", name="贵州茅台") is False


def test_is_limit_up_star_market() -> None:
    assert is_limit_up(pct_chg=19.8, code="688981", name="中芯国际") is True
    assert is_limit_up(pct_chg=19.0, code="688981", name="中芯国际") is False


def test_is_limit_up_st() -> None:
    assert is_limit_up(pct_chg=4.8, code="600519", name="*ST茅台") is True
    assert is_limit_up(pct_chg=4.0, code="600519", name="*ST茅台") is False
