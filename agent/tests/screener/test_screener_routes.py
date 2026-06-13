"""Tests for screener HTTP routes."""

from __future__ import annotations


def _route_client(*, remote: bool = False):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from src.api.market_routes import router

    app = FastAPI()
    app.include_router(router)
    client_host = ("203.0.113.10", 50000) if remote else ("testclient", 50000)
    return TestClient(app, client=client_host)


def test_market_screener_empty_returns_stale(monkeypatch):
    from src.api import screener_service

    monkeypatch.setattr(screener_service, "load_latest_result", lambda: None)
    monkeypatch.setattr(screener_service, "load_result", lambda _date: None)

    response = _route_client().get("/market/screener")
    assert response.status_code == 200
    body = response.json()
    assert body["stale"] is True
    assert body["items"] == []


def test_market_screener_with_latest_result(monkeypatch):
    from src.api import screener_service
    from src.screener.config import SCREENER_POLICY_VERSION

    sample = {
        "tradeDate": "2024-01-26",
        "items": [
            {
                "code": "600519",
                "name": "贵州茅台",
                "board": "main",
                "score": 88.5,
                "signals": {"limitup": 1},
                "vetoes": [],
                "position_pct": 42.0,
                "untradable": False,
                "trade_date": "2024-01-26",
            }
        ],
        "params": {
            "score_threshold": 60,
            "policy_version": SCREENER_POLICY_VERSION,
            "exclude_st": True,
            "required_signals": ["limitup", "volume"],
            "optional_signals": ["gap", "yang"],
        },
        "source": "tushare",
        "degraded": False,
        "updatedAt": "2024-01-26T12:00:00+00:00",
        "skipped": 0,
        "filtered_count": 1,
        "matched_count": 1,
        "universe_count": 2,
    }
    monkeypatch.setattr(screener_service, "load_latest_result", lambda: sample)
    monkeypatch.setattr(screener_service, "load_result", lambda _date: sample)

    response = _route_client().get("/market/screener")
    assert response.status_code == 200
    body = response.json()
    assert body["stale"] is False
    assert len(body["items"]) == 1
    assert body["items"][0]["code"] == "600519"


def test_market_screener_legacy_result_marked_stale(monkeypatch):
    from src.api import screener_service

    legacy = {
        "tradeDate": "2026-06-12",
        "items": [{"code": "000056", "name": "*ST皇庭", "board": "ST", "score": 41.7}],
        "params": {"exclude_st": False, "weights": {"limitup": 0.25}},
        "source": "tushare",
        "degraded": True,
        "updatedAt": "2026-06-12T12:00:00+00:00",
        "skipped": 0,
        "filtered_count": 0,
        "matched_count": 5512,
        "universe_count": 5528,
    }
    monkeypatch.setattr(screener_service, "load_latest_result", lambda: legacy)
    monkeypatch.setattr(screener_service, "load_result", lambda _date: legacy)

    response = _route_client().get("/market/screener")
    assert response.status_code == 200
    body = response.json()
    assert body["stale"] is True
    assert body["stale_reason"] == "policy_updated"
    assert body["items"] == []
    assert body["matched_count"] == 0


def test_market_screener_status_idle(monkeypatch):
    from src.api import screener_service

    monkeypatch.setattr(screener_service, "get_status", lambda: {
        "state": "idle",
        "progress": 0,
        "message": "",
        "updatedAt": "2024-01-26T12:00:00+00:00",
    })

    response = _route_client().get("/market/screener/status")
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "idle"
    assert body["progress"] == 0


def test_market_screener_refresh_requires_auth_remote(monkeypatch):
    import api_server

    monkeypatch.setenv("API_AUTH_KEY", "secret")
    monkeypatch.setattr(api_server, "_API_KEY", "secret")

    response = _route_client(remote=True).post("/market/screener/refresh")
    assert response.status_code == 401
