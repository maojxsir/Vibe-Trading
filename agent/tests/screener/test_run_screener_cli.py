"""Tests for scripts/run_screener.py CLI."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest

AGENT_DIR = Path(__file__).resolve().parents[2]
SCRIPT_PATH = AGENT_DIR / "scripts" / "run_screener.py"


@pytest.fixture
def run_screener_module():
    spec = importlib.util.spec_from_file_location("run_screener_cli", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_main_prints_result_path(run_screener_module, capsys) -> None:
    fake_path = Path("/tmp/screener_2025-06-13.json")
    with patch.object(run_screener_module, "run", return_value=fake_path) as mock_run:
        rc = run_screener_module.main([])

    assert rc == 0
    mock_run.assert_called_once_with(
        run_screener_module.ScreenerConfig(),
        trade_date=None,
    )
    assert capsys.readouterr().out.strip() == str(fake_path)


def test_main_passes_trade_date(run_screener_module, capsys) -> None:
    fake_path = Path("/tmp/screener_2025-06-01.json")
    with patch.object(run_screener_module, "run", return_value=fake_path) as mock_run:
        rc = run_screener_module.main(["--date", "2025-06-01"])

    assert rc == 0
    mock_run.assert_called_once_with(
        run_screener_module.ScreenerConfig(),
        trade_date="2025-06-01",
    )
    assert capsys.readouterr().out.strip() == str(fake_path)
