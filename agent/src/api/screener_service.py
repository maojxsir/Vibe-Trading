"""Screener API service — read persisted results, status, and trigger scans."""

from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.screener.config import SCREENER_POLICY_VERSION, ScreenerConfig
from src.screener.scan import (
    _config_params_snapshot,
    load_latest_result,
    load_result,
    run,
    screener_results_root,
)

logger = logging.getLogger(__name__)

_STATE_LOCK = threading.Lock()


def screener_state_root() -> Path:
    """Return the screener runtime directory for status and lock files."""
    return Path.home() / ".vibe-trading" / "screener"


def status_path() -> Path:
    """Return the screener scan status JSON path."""
    return screener_state_root() / "status.json"


def lock_path() -> Path:
    """Return the screener scan lock file path."""
    return screener_state_root() / "scan.lock"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    unique = f"{os.getpid()}.{uuid.uuid4().hex}"
    tmp_path = path.with_name(f"{path.name}.{unique}.tmp")
    tmp_path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    os.replace(tmp_path, path)


def _read_status_file() -> dict[str, Any] | None:
    path = status_path()
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("screener status read failed (%s): %s", path, exc)
        return None
    return payload if isinstance(payload, dict) else None


def _write_status(*, state: str, progress: int, message: str) -> None:
    payload = {
        "state": state,
        "progress": max(0, min(100, int(progress))),
        "message": message,
        "updatedAt": _utc_now_iso(),
    }
    _write_json_atomic(status_path(), payload)


def _result_policy_stale(raw: dict[str, Any]) -> bool:
    """True when persisted results were produced under an outdated screening policy."""
    params = raw.get("params")
    if not isinstance(params, dict):
        return True
    if params.get("policy_version") != SCREENER_POLICY_VERSION:
        return True
    expected = _config_params_snapshot(ScreenerConfig())
    for key in ("exclude_st", "required_signals", "optional_signals"):
        if params.get(key) != expected.get(key):
            return True
    return False


def _empty_payload() -> dict[str, Any]:
    return {
        "tradeDate": "",
        "items": [],
        "params": {},
        "source": "",
        "degraded": False,
        "updatedAt": _utc_now_iso(),
        "skipped": 0,
        "filtered_count": 0,
        "universe_count": 0,
        "matched_count": 0,
        "stale": True,
    }


def _to_api_payload(raw: dict[str, Any] | None) -> dict[str, Any]:
    if not raw:
        return _empty_payload()
    payload = dict(raw)
    if _result_policy_stale(raw):
        payload["stale"] = True
        payload["stale_reason"] = "policy_updated"
        payload["items"] = []
        payload["matched_count"] = 0
        return payload
    payload["stale"] = False
    payload.pop("stale_reason", None)
    return payload


def get_screener_payload(date: str = "") -> dict[str, Any]:
    """Load screener results for API responses."""
    query = (date or "").strip()
    if query:
        raw = load_result(query)
    else:
        raw = load_latest_result()
    return _to_api_payload(raw)


def get_status() -> dict[str, Any]:
    """Return current screener scan status for the Web UI."""
    default = {
        "state": "idle",
        "progress": 0,
        "message": "",
        "updatedAt": _utc_now_iso(),
    }

    with _STATE_LOCK:
        if lock_path().is_file():
            status = _read_status_file() or default
            status["state"] = "running"
            status.setdefault("progress", 0)
            status.setdefault("message", "")
            status.setdefault("updatedAt", _utc_now_iso())
            return status

        status = _read_status_file()
        if status is None:
            return default

        state = str(status.get("state") or "idle")
        if state not in {"idle", "running", "failed", "done"}:
            state = "idle"
        return {
            "state": state,
            "progress": int(status.get("progress") or 0),
            "message": str(status.get("message") or ""),
            "updatedAt": str(status.get("updatedAt") or _utc_now_iso()),
        }


def _release_lock() -> None:
    try:
        lock_path().unlink(missing_ok=True)
    except OSError as exc:
        logger.warning("screener lock release failed: %s", exc)


def _run_scan_worker() -> None:
    try:
        _write_status(state="running", progress=0, message="scan started")
        run(ScreenerConfig())
        _write_status(state="done", progress=100, message="scan complete")
    except Exception as exc:  # noqa: BLE001 - surface failure via status.json
        logger.exception("screener refresh failed")
        _write_status(state="failed", progress=0, message=str(exc))
    finally:
        with _STATE_LOCK:
            _release_lock()


def trigger_refresh() -> tuple[int, dict[str, Any]]:
    """Start a background screener scan when no lock is held."""
    with _STATE_LOCK:
        if lock_path().is_file():
            return 409, {"accepted": False, "message": "scan already running"}

        screener_state_root().mkdir(parents=True, exist_ok=True)
        _write_json_atomic(lock_path(), {"startedAt": _utc_now_iso()})
        _write_status(state="running", progress=0, message="scan accepted")

    thread = threading.Thread(target=_run_scan_worker, name="screener-scan", daemon=True)
    thread.start()
    return 202, {"accepted": True}


def results_root() -> Path:
    """Expose the persisted results directory used by scan.py."""
    return screener_results_root()
