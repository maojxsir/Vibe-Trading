"""Tests for screener background scan orchestration."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path


def test_clear_stale_lock_removes_old_lock(tmp_path, monkeypatch):
    from src.api import screener_service

    root = tmp_path / "screener"
    root.mkdir()
    lock = root / "scan.lock"
    lock.write_text('{"startedAt":"2020-01-01T00:00:00+00:00"}', encoding="utf-8")
    old = time.time() - 7201
    Path(lock).touch()
    import os

    os.utime(lock, (old, old))

    monkeypatch.setattr(screener_service, "screener_state_root", lambda: root)
    screener_service._clear_stale_lock(max_age_seconds=7200)
    assert not lock.is_file()


def test_trigger_refresh_runs_scan_subprocess(tmp_path, monkeypatch):
    from src.api import screener_service

    root = tmp_path / "screener"
    monkeypatch.setattr(screener_service, "screener_state_root", lambda: root)
    monkeypatch.setattr(screener_service, "_scan_script_path", lambda: tmp_path / "run_screener.py")

    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):  # noqa: ANN001
        calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0, stdout=str(tmp_path / "out.json"), stderr="")

    monkeypatch.setattr(screener_service.subprocess, "run", fake_run)

    status_code, body = screener_service.trigger_refresh()
    assert status_code == 202
    assert body["accepted"] is True

    thread = screener_service.threading.enumerate()[-1]
    thread.join(timeout=5)
    assert calls, "expected subprocess scan invocation"

    status = json.loads((root / "status.json").read_text(encoding="utf-8"))
    assert status["state"] == "done"
    assert not (root / "scan.lock").is_file()
