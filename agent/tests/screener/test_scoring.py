"""Tests for A-share screener weighted scoring."""

from __future__ import annotations

import pandas as pd
import pytest

from src.screener.config import ScreenerConfig
from src.screener.scoring import apply_vetoes, passes_required_signals, score_latest, score_row


@pytest.fixture
def config() -> ScreenerConfig:
    return ScreenerConfig()


def test_score_row_all_ones(config: ScreenerConfig) -> None:
    row = {
        "signal_limitup": 1.0,
        "signal_volume": 1.0,
        "signal_gap": 1.0,
        "signal_yang": 1.0,
    }
    assert score_row(row, config) == 100.0


def test_score_row_spec_example(config: ScreenerConfig) -> None:
    row = {
        "signal_limitup": 1.0,
        "signal_volume": 0.8,
        "signal_gap": 0.6,
        "signal_yang": 1.0,
    }
    # 100 * (0.35*1.0 + 0.35*0.8 + 0.15*0.6 + 0.15*1.0) = 87.0
    assert score_row(row, config) == pytest.approx(87.0)


def test_apply_vetoes_low_position(config: ScreenerConfig) -> None:
    row = {"veto_low_position": True, "veto_distribution": False}
    assert apply_vetoes(90.0, row, config) is None


def test_apply_vetoes_distribution(config: ScreenerConfig) -> None:
    row = {"veto_low_position": False, "veto_distribution": True}
    assert apply_vetoes(90.0, row, config) is None


def test_apply_vetoes_overextended(config: ScreenerConfig) -> None:
    row = {
        "veto_low_position": False,
        "veto_distribution": False,
        "veto_overextended": True,
    }
    assert apply_vetoes(90.0, row, config) is None


def test_apply_vetoes_passes_through(config: ScreenerConfig) -> None:
    row = {"veto_low_position": False, "veto_distribution": False}
    assert apply_vetoes(90.0, row, config) == 90.0


def test_score_latest_last_row(config: ScreenerConfig) -> None:
    signals_df = pd.DataFrame(
        [
            {
                "signal_limitup": 0.5,
                "signal_volume": 0.5,
                "signal_gap": 0.5,
                "signal_yang": 0.5,
                "veto_low_position": False,
                "veto_distribution": False,
                "position_pct": 0.4,
                "untradable": False,
            },
            {
                "signal_limitup": 1.0,
                "signal_volume": 0.8,
                "signal_gap": 0.6,
                "signal_yang": 1.0,
                "veto_low_position": False,
                "veto_distribution": False,
                "position_pct": 0.62,
                "untradable": True,
            },
        ]
    )

    result = score_latest(signals_df, config)

    assert result["score"] == pytest.approx(87.0)
    assert result["filtered"] is False
    assert result["required_passed"] is True
    assert result["filter_reason"] is None
    assert result["signals"] == {
        "limitup": 1.0,
        "volume": 0.8,
        "gap": 0.6,
        "yang": 1.0,
    }
    assert result["vetoes"] == {
        "low_position": False,
        "distribution": False,
        "overextended": False,
    }
    assert result["position_pct"] == pytest.approx(0.62)
    assert result["untradable"] is True


def test_score_latest_vetoed(config: ScreenerConfig) -> None:
    signals_df = pd.DataFrame(
        [
            {
                "signal_limitup": 1.0,
                "signal_volume": 1.0,
                "signal_gap": 1.0,
                "signal_yang": 1.0,
                "veto_low_position": True,
                "veto_distribution": False,
                "position_pct": 0.95,
                "untradable": False,
            }
        ]
    )

    result = score_latest(signals_df, config)

    assert result["score"] is None
    assert result["filtered"] is True
    assert result["filter_reason"] == "veto"
    assert result["vetoes"]["low_position"] is True


def test_passes_required_signals_both_required(config: ScreenerConfig) -> None:
    row = {"signal_limitup": 0.5, "signal_volume": 0.2}
    assert passes_required_signals(row, config) is True


def test_passes_required_signals_missing_limitup(config: ScreenerConfig) -> None:
    row = {"signal_limitup": 0.0, "signal_volume": 0.8}
    assert passes_required_signals(row, config) is False


def test_passes_required_signals_missing_volume(config: ScreenerConfig) -> None:
    row = {"signal_limitup": 0.9, "signal_volume": 0.0}
    assert passes_required_signals(row, config) is False


def test_score_latest_missing_required(config: ScreenerConfig) -> None:
    signals_df = pd.DataFrame(
        [
            {
                "signal_limitup": 0.0,
                "signal_volume": 0.8,
                "signal_gap": 1.0,
                "signal_yang": 1.0,
                "veto_low_position": False,
                "veto_distribution": False,
                "position_pct": 0.5,
                "untradable": False,
            }
        ]
    )

    result = score_latest(signals_df, config)

    assert result["filtered"] is True
    assert result["filter_reason"] == "missing_required"
    assert result["required_passed"] is False
    assert result["score"] == pytest.approx(score_row(signals_df.iloc[-1], config))
