"""MongoDB stock_data access and on-demand sync bridge.

Reads from the ``stock_data`` database populated by ``tools/stock_data_sync.py``.
When configured, Vibe-Trading prefers MongoDB over live Tushare calls.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Optional

import pandas as pd

logger = logging.getLogger(__name__)

MONGO_URI_ENV = "MONGO_URI"
MONGO_DB_ENV = "MONGO_DB"
USE_MONGODB_ENV = "VIBE_USE_MONGODB"
ON_DEMAND_SYNC_ENV = "VIBE_MONGODB_ON_DEMAND_SYNC"
DEFAULT_MONGO_URI = "mongodb://localhost:27017"
DEFAULT_MONGO_DB = "stock_data"
DATA_SOURCE = "tushare"

# 打板筛选/跟踪集合（与 tools/stock_data_sync.py 共用 stock_data 库）。
SCREENER_RESULTS_COLL = "screener_results"
SCREENER_TRACKING_COLL = "screener_tracking"


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def mongodb_enabled() -> bool:
    """Return True when MongoDB reads are enabled."""
    explicit = os.getenv(USE_MONGODB_ENV, "").strip()
    if explicit:
        return _truthy(explicit)
    uri = os.getenv(MONGO_URI_ENV, "").strip()
    return bool(uri)


def on_demand_sync_enabled() -> bool:
    """Return True when missing MongoDB rows should trigger sync."""
    explicit = os.getenv(ON_DEMAND_SYNC_ENV, "").strip()
    if explicit:
        return _truthy(explicit)
    return mongodb_enabled()


def mongo_uri() -> str:
    return os.getenv(MONGO_URI_ENV, DEFAULT_MONGO_URI).strip() or DEFAULT_MONGO_URI


def mongo_db_name() -> str:
    return os.getenv(MONGO_DB_ENV, DEFAULT_MONGO_DB).strip() or DEFAULT_MONGO_DB


def bare_symbol(code: str) -> str:
    """Normalize an A-share code to 6 digits."""
    text = str(code).strip().upper()
    if "." in text:
        text = text.split(".", 1)[0]
    digits = "".join(ch for ch in text if ch.isdigit())
    return digits.zfill(6)[-6:] if digits else text


def to_ts_code(code: str) -> str:
    """Map a bare or full code to Tushare ``ts_code`` form."""
    text = str(code).strip().upper()
    if "." in text:
        return text
    symbol = bare_symbol(text)
    if symbol.startswith(("8", "4", "92")):
        return f"{symbol}.BJ"
    suffix = "SH" if symbol.startswith(("6", "9")) else "SZ"
    return f"{symbol}.{suffix}"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _sync_script_path() -> Path:
    return _project_root() / "tools" / "stock_data_sync.py"


_FAIL_BACKOFF_S = 30.0
_fail_until = 0.0

@lru_cache(maxsize=1)
def _get_db():
    """Return a cached MongoDB database handle, with failure backoff."""
    global _fail_until
    import pymongo

    now = time.monotonic()
    if now < _fail_until:
        raise ConnectionError("MongoDB unavailable (cached backoff)")

    try:
        client = pymongo.MongoClient(
            mongo_uri(),
            serverSelectionTimeoutMS=5000,
        )
        client.server_info()
        return client[mongo_db_name()]
    except Exception:
        _fail_until = now + _FAIL_BACKOFF_S
        raise


def is_mongodb_available() -> bool:
    """Return True when MongoDB is enabled and reachable."""
    if not mongodb_enabled():
        return False
    try:
        _get_db()
        return True
    except Exception as exc:
        logger.debug("MongoDB unavailable: %s", exc)
        return False


def _ymd(value: str) -> str:
    return pd.Timestamp(value).strftime("%Y%m%d")


def _iso(value: str) -> str:
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def fetch_daily_quotes(
    code: str,
    start_date: str,
    end_date: str,
    *,
    period: str = "daily",
) -> pd.DataFrame:
    """Load OHLCV rows for one symbol from ``stock_daily_quotes``."""
    if not is_mongodb_available():
        return pd.DataFrame()

    symbol = bare_symbol(code)
    start_td = _ymd(start_date)
    end_td = _ymd(end_date)
    query: dict[str, Any] = {
        "symbol": symbol,
        "period": period,
        "data_source": DATA_SOURCE,
        "trade_date": {"$gte": start_td, "$lte": end_td},
    }
    rows = list(
        _get_db()["stock_daily_quotes"]
        .find(query, {"_id": 0})
        .sort("trade_date", 1)
    )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def daily_quotes_to_ohlcv(frame: pd.DataFrame) -> pd.DataFrame:
    """Convert MongoDB daily quote documents to loader OHLCV frame."""
    if frame is None or frame.empty:
        return pd.DataFrame()

    work = frame.copy()
    work["trade_date"] = pd.to_datetime(work["trade_date"].astype(str), format="%Y%m%d")
    work = work.set_index("trade_date").sort_index()

    if "volume" in work.columns:
        volume = pd.to_numeric(work["volume"], errors="coerce")
    else:
        volume = pd.to_numeric(work.get("vol"), errors="coerce")
        volume = volume * 100

    ohlcv = pd.DataFrame(
        {
            "open": pd.to_numeric(work.get("open"), errors="coerce"),
            "high": pd.to_numeric(work.get("high"), errors="coerce"),
            "low": pd.to_numeric(work.get("low"), errors="coerce"),
            "close": pd.to_numeric(work.get("close"), errors="coerce"),
            "volume": volume,
        },
        index=work.index,
    )
    return ohlcv.dropna(subset=["open", "high", "low", "close"])


def fetch_daily_ohlcv(code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Return normalized OHLCV for one symbol."""
    frame = fetch_daily_quotes(code, start_date, end_date)
    return daily_quotes_to_ohlcv(frame)


def fetch_trade_date_panel(trade_date: str) -> pd.DataFrame:
    """Return one full-market daily panel for screener parquet backfill."""
    if not is_mongodb_available():
        return pd.DataFrame()

    td = _ymd(trade_date)
    rows = list(
        _get_db()["stock_daily_quotes"]
        .find(
            {
                "trade_date": td,
                "period": "daily",
                "data_source": DATA_SOURCE,
            },
            {"_id": 0},
        )
    )
    if not rows:
        return pd.DataFrame()

    frame = pd.DataFrame(rows)
    frame["ts_code"] = frame["symbol"].map(lambda sym: to_ts_code(str(sym)))
    frame["trade_date"] = td
    for column in ("open", "high", "low", "close", "pre_close", "pct_chg", "vol", "amount"):
        if column not in frame.columns:
            frame[column] = pd.NA
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if "turnover_rate" not in frame.columns:
        frame["turnover_rate"] = pd.NA
    keep = [
        "ts_code",
        "trade_date",
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
    return frame[keep]


def fetch_basic_info_records(*, list_status: str = "L") -> list[dict[str, Any]]:
    """Load A-share basic info rows from ``stock_basic_info``."""
    if not is_mongodb_available():
        return []

    query: dict[str, Any] = {"source": DATA_SOURCE}
    if list_status:
        query["list_status"] = list_status
    rows = list(_get_db()["stock_basic_info"].find(query, {"_id": 0}))
    result: list[dict[str, Any]] = []
    for row in rows:
        symbol = bare_symbol(str(row.get("symbol") or row.get("ts_code") or ""))
        name = str(row.get("name") or "").strip()
        if len(symbol) != 6 or not name:
            continue
        ts_code = str(row.get("ts_code") or to_ts_code(symbol)).strip()
        item = {
            "symbol": symbol,
            "ts_code": ts_code,
            "name": name,
            "cnspell": str(row.get("cnspell") or "").strip().upper(),
            "list_date": str(row.get("list_date") or "").strip(),
            "industry": str(row.get("industry") or "").strip(),
        }
        result.append(item)
    return result


def coverage_is_sufficient(
    frame: pd.DataFrame,
    start_date: str,
    end_date: str,
    *,
    min_rows: int = 1,
) -> bool:
    """Heuristic: MongoDB slice is usable when it has rows through the recent window.

    Stocks listed after ``start_date`` are allowed — only the end of the range
    must be sufficiently fresh for UI/backtest use.
    """
    if frame is None or frame.empty:
        return False
    if len(frame) < min_rows:
        return False
    end_ts = pd.Timestamp(end_date)
    index = frame.index
    if index.max() < end_ts - pd.Timedelta(days=14):
        return False
    return True


def trigger_symbol_sync(
    symbols: Iterable[str],
    *,
    start_date: str = "",
    end_date: str = "",
    include_financial: bool = False,
) -> bool:
    """Run ``tools/stock_data_sync.py`` for missing symbols."""
    if not on_demand_sync_enabled():
        return False

    script = _sync_script_path()
    if not script.is_file():
        logger.warning("stock sync script not found: %s", script)
        return False

    codes = sorted({bare_symbol(code) for code in symbols if bare_symbol(code)})
    if not codes:
        return False

    if not end_date:
        end_date = datetime.now().strftime("%Y%m%d")
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")

    cmd = [
        sys.executable,
        str(script),
        "--symbol",
        ",".join(codes),
        "--kline",
        "--start",
        _ymd(start_date),
        "--end",
        _ymd(end_date),
    ]
    if include_financial:
        cmd.append("--financial")

    env = os.environ.copy()
    env.setdefault(MONGO_URI_ENV, mongo_uri())
    env.setdefault(MONGO_DB_ENV, mongo_db_name())

    try:
        completed = subprocess.run(
            cmd,
            cwd=str(_project_root()),
            env=env,
            capture_output=True,
            text=True,
            timeout=1800,
            check=False,
        )
    except Exception as exc:
        logger.warning("on-demand stock sync failed: %s", exc)
        return False

    if completed.returncode != 0:
        logger.warning(
            "on-demand stock sync exited %s: %s",
            completed.returncode,
            (completed.stderr or completed.stdout or "").strip()[:500],
        )
        return False
    return True


# ---------------------------------------------------------------------------
# 打板筛选结果 + 跟踪池：stock_data 库内的 CRUD
#
# 设计见 docs/superpowers/specs/2026-06-17-screener-mongodb-tracking-design.md。
# 所有写入都是 best-effort：MongoDB 不可用时返回假值并告警，绝不抛给扫描主流程。
# ---------------------------------------------------------------------------


def _utc_now_iso() -> str:
    """返回不含微秒的 UTC ISO 时间串，用于 updatedAt/createdAt。"""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_screener_indexes() -> None:
    """为跟踪池建立查询索引（status / day0_date）。失败仅告警。"""
    if not is_mongodb_available():
        return
    try:
        coll = _get_db()[SCREENER_TRACKING_COLL]
        coll.create_index("status")
        coll.create_index("day0_date")
    except Exception as exc:  # noqa: BLE001 - 索引创建失败不阻断主流程
        logger.warning("ensure_screener_indexes failed: %s", exc)


def save_screener_result(payload: dict[str, Any]) -> bool:
    """把一次扫描结果快照 upsert 到 ``screener_results``（_id=tradeDate）。

    与本地 JSON 双写，二者互不依赖；MongoDB 失败不影响 JSON 落盘。
    """
    trade_date = str(payload.get("tradeDate") or "").strip()
    if not trade_date:
        return False
    if not is_mongodb_available():
        return False
    try:
        doc = dict(payload)
        doc["_id"] = trade_date
        doc["updatedAt"] = doc.get("updatedAt") or _utc_now_iso()
        _get_db()[SCREENER_RESULTS_COLL].replace_one(
            {"_id": trade_date}, doc, upsert=True
        )
        return True
    except Exception as exc:  # noqa: BLE001 - 结果持久化是 best-effort
        logger.warning("save_screener_result failed (%s): %s", trade_date, exc)
        return False


def get_screener_result(trade_date: str) -> Optional[dict[str, Any]]:
    """按交易日读取一次扫描结果快照，不存在或不可用时返回 None。"""
    iso = str(trade_date or "").strip()
    if not iso or not is_mongodb_available():
        return None
    try:
        return _get_db()[SCREENER_RESULTS_COLL].find_one({"_id": iso})
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_screener_result failed (%s): %s", iso, exc)
        return None


def get_tracking_pool(status: str | None = "tracking") -> list[dict[str, Any]]:
    """读取跟踪池文档列表。``status=None`` 表示返回全部（含已剔除/到期）。"""
    if not is_mongodb_available():
        return []
    query: dict[str, Any] = {}
    if status:
        query["status"] = status
    try:
        return list(_get_db()[SCREENER_TRACKING_COLL].find(query))
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_tracking_pool failed: %s", exc)
        return []


def get_tracking_doc(code: str) -> Optional[dict[str, Any]]:
    """按代码读取一条跟踪文档。"""
    cid = bare_symbol(code)
    if not cid or not is_mongodb_available():
        return None
    try:
        return _get_db()[SCREENER_TRACKING_COLL].find_one({"_id": cid})
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_tracking_doc failed (%s): %s", cid, exc)
        return None


def upsert_tracking_doc(doc: dict[str, Any]) -> bool:
    """整文档 upsert 一条跟踪记录（_id=code）。"""
    code = bare_symbol(str(doc.get("code") or doc.get("_id") or ""))
    if not code or not is_mongodb_available():
        return False
    try:
        body = dict(doc)
        body["_id"] = code
        body["code"] = code
        body["updatedAt"] = _utc_now_iso()
        _get_db()[SCREENER_TRACKING_COLL].replace_one(
            {"_id": code}, body, upsert=True
        )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("upsert_tracking_doc failed (%s): %s", code, exc)
        return False


def bulk_upsert_tracking(docs: Iterable[dict[str, Any]]) -> int:
    """批量 upsert 跟踪文档，返回成功写入条数。"""
    items = [d for d in docs if d]
    if not items or not is_mongodb_available():
        return 0
    try:
        import pymongo

        now = _utc_now_iso()
        ops = []
        for doc in items:
            code = bare_symbol(str(doc.get("code") or doc.get("_id") or ""))
            if not code:
                continue
            body = dict(doc)
            body["_id"] = code
            body["code"] = code
            body["updatedAt"] = now
            ops.append(pymongo.ReplaceOne({"_id": code}, body, upsert=True))
        if not ops:
            return 0
        result = _get_db()[SCREENER_TRACKING_COLL].bulk_write(ops, ordered=False)
        return int((result.upserted_count or 0) + (result.modified_count or 0))
    except Exception as exc:  # noqa: BLE001
        logger.warning("bulk_upsert_tracking failed: %s", exc)
        return 0


def reset_cached_connection() -> None:
    """Clear cached Mongo client (tests)."""
    _get_db.cache_clear()
