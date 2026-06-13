"""Hive-partitioned parquet cache for A-share screener panel data."""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from pathlib import Path

import pandas as pd

from backtest.loaders.base import loader_cache_range_is_final, retry_with_budget

logger = logging.getLogger(__name__)

SCREENER_CACHE_ENV = "VIBE_SCREENER_CACHE"
META_FILENAME = "meta.json"
PANEL_COLUMNS = [
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
DAILY_FIELDS = "ts_code,trade_date,open,high,low,close,pre_close,pct_chg,vol,amount"
DAILY_BASIC_FIELDS = "ts_code,trade_date,turnover_rate"
FETCH_BUDGET_S = 300.0
# 单个交易日的抓取重试预算：让每天都能独立重试，单点超时不拖垮整轮回填。
PER_DATE_FETCH_BUDGET_S = 25.0
THROTTLE_S = 0.3
TUSHARE_TOKEN_PLACEHOLDERS = {"", "your-tushare-token"}


def screener_cache_root() -> Path:
    """Return the screener cache root directory."""
    override = os.getenv(SCREENER_CACHE_ENV, "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".vibe-trading" / "cache" / "screener"


def normalize_trade_date(value: str) -> str:
    """Normalize ``YYYYMMDD`` or ``YYYY-MM-DD`` to ``YYYYMMDD``."""
    return pd.Timestamp(value).strftime("%Y%m%d")


def normalize_query_date(value: str) -> str:
    """Normalize a date string to ``YYYY-MM-DD`` for range filters."""
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def bare_code(code: str) -> str:
    """Return the bare 6-digit A-share code."""
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
    symbol = bare_code(text)
    if symbol.startswith(("8", "4", "92")):
        return f"{symbol}.BJ"
    suffix = "SH" if symbol.startswith(("6", "9")) else "SZ"
    return f"{symbol}.{suffix}"


def _duckdb_sql_string(path: Path) -> str:
    return "'" + str(path).replace("'", "''") + "'"


def _trade_date_iso(value: str) -> str:
    return pd.Timestamp(value).strftime("%Y-%m-%d")


class ScreenerStore:
    """Local parquet store for screener daily panels and index series."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or screener_cache_root()).expanduser()
        self.root.mkdir(parents=True, exist_ok=True)

    @property
    def daily_root(self) -> Path:
        return self.root / "daily"

    @property
    def meta_path(self) -> Path:
        return self.root / META_FILENAME

    def partition_path(self, trade_date: str) -> Path:
        """Return the parquet path for one daily hive partition."""
        td = normalize_trade_date(trade_date)
        return self.daily_root / f"trade_date={td}" / "data.parquet"

    def write_daily_partition(self, trade_date: str, df: pd.DataFrame) -> None:
        """Atomically write one trade-date partition."""
        if df is None or df.empty:
            return

        td = normalize_trade_date(trade_date)
        target = self.partition_path(td)
        target.parent.mkdir(parents=True, exist_ok=True)

        work = df.copy()
        if "trade_date" not in work.columns:
            work["trade_date"] = td
        else:
            work["trade_date"] = work["trade_date"].map(normalize_trade_date)

        for column in PANEL_COLUMNS:
            if column not in work.columns:
                work[column] = pd.NA
        if "ts_code" not in work.columns:
            raise ValueError("daily partition requires ts_code column")

        keep = ["ts_code", "trade_date", *PANEL_COLUMNS]
        work = work[keep]

        unique = f"{os.getpid()}.{uuid.uuid4().hex}"
        tmp_path = target.with_name(f"{target.name}.{unique}.tmp")

        import duckdb

        con = duckdb.connect(database=":memory:")
        try:
            con.register("partition_frame", work)
            con.execute(
                f"COPY partition_frame TO {_duckdb_sql_string(tmp_path)} (FORMAT PARQUET)"
            )
        finally:
            con.close()

        os.replace(tmp_path, target)

    def read_meta(self) -> dict:
        """Read ``meta.json``; return an empty dict when absent."""
        if not self.meta_path.is_file():
            return {}
        try:
            payload = json.loads(self.meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("screener meta read failed: %s", exc)
            return {}
        return payload if isinstance(payload, dict) else {}

    def write_meta(self, meta: dict) -> None:
        """Atomically write ``meta.json``."""
        unique = f"{os.getpid()}.{uuid.uuid4().hex}"
        tmp_path = self.meta_path.with_name(f"{self.meta_path.name}.{unique}.tmp")
        tmp_path.write_text(
            json.dumps(meta, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )
        os.replace(tmp_path, self.meta_path)

    def load_panel(
        self,
        codes: list[str],
        start: str,
        end: str,
    ) -> dict[str, pd.DataFrame]:
        """Load panel slices for ``codes`` over ``[start, end]``."""
        if not codes or not self._has_daily_partitions():
            return {}

        ts_codes = [to_ts_code(code) for code in codes]
        bare_by_ts = {to_ts_code(code): bare_code(code) for code in codes}
        start_date = normalize_query_date(start)
        end_date = normalize_query_date(end)
        glob_path = str(self.daily_root / "trade_date=*" / "data.parquet")

        import duckdb

        placeholders = ", ".join("?" for _ in ts_codes)
        sql = f"""
            SELECT ts_code, trade_date, {", ".join(PANEL_COLUMNS)}
            FROM read_parquet(?, hive_partitioning=true)
            WHERE CAST(
                CASE
                    WHEN length(cast(trade_date AS VARCHAR)) = 8
                        THEN strptime(cast(trade_date AS VARCHAR), '%Y%m%d')
                    ELSE cast(trade_date AS DATE)
                END AS DATE
            ) BETWEEN ?::DATE AND ?::DATE
              AND ts_code IN ({placeholders})
        """

        con = duckdb.connect(database=":memory:")
        try:
            frame = con.execute(sql, [glob_path, start_date, end_date, *ts_codes]).fetchdf()
        finally:
            con.close()

        if frame.empty:
            return {}

        frame["trade_date"] = pd.to_datetime(frame["trade_date"].astype(str), format="%Y%m%d", errors="coerce")
        if frame["trade_date"].isna().any():
            frame["trade_date"] = pd.to_datetime(frame["trade_date"], errors="coerce")

        result: dict[str, pd.DataFrame] = {}
        for ts_code, group in frame.groupby("ts_code", sort=False):
            bare = bare_by_ts.get(str(ts_code), bare_code(str(ts_code)))
            panel = group.set_index("trade_date")[PANEL_COLUMNS].sort_index()
            for column in PANEL_COLUMNS:
                panel[column] = pd.to_numeric(panel[column], errors="coerce")
            result[bare] = panel
        return result

    def load_index_series(
        self,
        start: str,
        end: str,
        index_code: str = "000300",
    ) -> pd.Series:
        """Return daily index returns (``close.pct_change()``) indexed by date."""
        path = self.root / "index" / f"{index_code}.parquet"
        if not path.is_file():
            return pd.Series(dtype=float)

        import duckdb

        start_date = normalize_query_date(start)
        end_date = normalize_query_date(end)
        sql = """
            SELECT trade_date, close
            FROM read_parquet(?)
            WHERE CAST(
                CASE
                    WHEN length(cast(trade_date AS VARCHAR)) = 8
                        THEN strptime(cast(trade_date AS VARCHAR), '%Y%m%d')
                    ELSE cast(trade_date AS DATE)
                END AS DATE
            ) BETWEEN ?::DATE AND ?::DATE
            ORDER BY 1
        """
        con = duckdb.connect(database=":memory:")
        try:
            frame = con.execute(sql, [str(path), start_date, end_date]).fetchdf()
        finally:
            con.close()

        if frame.empty:
            return pd.Series(dtype=float)

        dates = pd.to_datetime(frame["trade_date"].astype(str), format="%Y%m%d", errors="coerce")
        if dates.isna().any():
            dates = pd.to_datetime(frame["trade_date"], errors="coerce")
        close = pd.to_numeric(frame["close"], errors="coerce")
        series = close.pct_change()
        series.index = dates
        return series.sort_index()

    def ensure_fresh(self, end_date: str, *, pro=None) -> None:
        """Backfill missing settled daily partitions through ``end_date``."""
        api = self._resolve_pro(pro)
        meta = self.read_meta()
        latest = str(meta.get("latest_trade_date") or "").strip() or None
        missing = self._missing_trade_dates(api, end_date=end_date, latest=latest)
        if not missing:
            return

        written = self._backfill_dates(api, missing)
        if not written:
            return

        new_latest = max(written + ([normalize_trade_date(latest)] if latest else []))
        meta["latest_trade_date"] = new_latest
        self.write_meta(meta)

    def ensure_panel_history(
        self,
        end_date: str,
        min_trading_days: int,
        *,
        pro=None,
    ) -> None:
        """Backfill at least ``min_trading_days`` settled partitions through ``end_date``."""
        if min_trading_days <= 0:
            return

        end_td = normalize_trade_date(end_date)
        span_cal = int(min_trading_days * 2.5) + 30
        window_start_td = (
            pd.Timestamp(end_td) - pd.Timedelta(days=span_cal)
        ).strftime("%Y%m%d")

        # 只统计最近连续窗口内的分区，避免缓存里残留的远期历史（如往年回测数据）
        # 误判为“已足够”而跳过补数，导致最近history实际不足。
        existing = self._list_settled_partitions(end_td, since=window_start_td)
        if len(existing) >= min_trading_days:
            return

        api = self._resolve_pro(pro)
        start_td = window_start_td
        deadline = time.monotonic() + FETCH_BUDGET_S

        def _fetch_cal() -> pd.DataFrame:
            frame = api.trade_cal(
                exchange="SSE",
                start_date=start_td,
                end_date=end_td,
                is_open="1",
            )
            if frame is None:
                return pd.DataFrame(columns=["cal_date", "is_open"])
            return frame

        cal = retry_with_budget(
            _fetch_cal,
            transient=Exception,
            deadline=deadline,
            label="screener history trade_cal",
        )
        time.sleep(THROTTLE_S)

        if cal.empty or "cal_date" not in cal.columns:
            return

        open_dates = sorted(cal["cal_date"].astype(str).tolist())
        settled = [
            trade_date
            for trade_date in open_dates
            if loader_cache_range_is_final(_trade_date_iso(trade_date))
        ]
        if not settled:
            return

        target_dates = settled[-min_trading_days:]
        written = self._backfill_dates(api, target_dates)
        if not written:
            return

        meta = self.read_meta()
        latest = str(meta.get("latest_trade_date") or "").strip()
        new_latest = max(written + ([normalize_trade_date(latest)] if latest else []))
        meta["latest_trade_date"] = new_latest
        self.write_meta(meta)

    def _backfill_dates(self, pro, trade_dates: list[str]) -> list[str]:
        """Fetch + persist each trade date, tolerating per-date failures.

        A single timed-out / failed date is skipped instead of aborting the whole
        backfill, so a transient data-source hiccup never sinks the scan. Each date
        gets its own retry budget; an overall cap bounds total wall time.
        """
        written: list[str] = []
        if not trade_dates:
            return written

        overall_deadline = time.monotonic() + max(
            FETCH_BUDGET_S, len(trade_dates) * 10 + 60
        )
        for trade_date in trade_dates:
            if self.partition_path(trade_date).is_file():
                written.append(normalize_trade_date(trade_date))
                continue
            if time.monotonic() > overall_deadline:
                logger.warning(
                    "screener backfill budget exhausted; stopping at %s", trade_date
                )
                break
            try:
                merged = self._fetch_partition_frame(
                    pro,
                    trade_date,
                    deadline=time.monotonic() + PER_DATE_FETCH_BUDGET_S,
                )
            except Exception as exc:  # noqa: BLE001 - skip flaky date, keep going
                logger.warning("screener backfill skip %s: %s", trade_date, exc)
                continue
            if merged is None or merged.empty:
                continue
            self.write_daily_partition(trade_date, merged)
            written.append(normalize_trade_date(trade_date))
        return written

    def _list_settled_partitions(
        self,
        end_date: str,
        *,
        since: str | None = None,
    ) -> list[str]:
        """Return sorted settled partition dates in ``[since, end_date]``.

        ``since`` (``YYYYMMDD``) restricts to a recent window so that stale
        far-past partitions are not counted toward recent-history sufficiency.
        """
        if not self._has_daily_partitions():
            return []

        end_td = normalize_trade_date(end_date)
        since_td = normalize_trade_date(since) if since else None
        dates: list[str] = []
        for path in self.daily_root.glob("trade_date=*/data.parquet"):
            trade_date = path.parent.name.split("=", 1)[-1]
            if trade_date > end_td:
                continue
            if since_td is not None and trade_date < since_td:
                continue
            if loader_cache_range_is_final(_trade_date_iso(trade_date)):
                dates.append(trade_date)
        return sorted(set(dates))

    def _has_daily_partitions(self) -> bool:
        if not self.daily_root.is_dir():
            return False
        return any(self.daily_root.glob("trade_date=*/data.parquet"))

    def pro_client(self, pro=None):
        """Public accessor for a Tushare pro client (raises if token missing)."""
        return self._resolve_pro(pro)

    def _resolve_pro(self, pro):
        if pro is not None:
            return pro
        token = os.getenv("TUSHARE_TOKEN", "").strip()
        if token in TUSHARE_TOKEN_PLACEHOLDERS:
            raise RuntimeError("TUSHARE_TOKEN is not configured")
        import tushare as ts  # type: ignore

        return ts.pro_api(token)

    def _missing_trade_dates(
        self,
        pro,
        *,
        end_date: str,
        latest: str | None,
    ) -> list[str]:
        end_td = normalize_trade_date(end_date)
        if latest:
            start_td = (pd.Timestamp(latest) + pd.Timedelta(days=1)).strftime("%Y%m%d")
        else:
            start_td = end_td

        deadline = time.monotonic() + FETCH_BUDGET_S

        def _fetch_cal() -> pd.DataFrame:
            frame = pro.trade_cal(
                exchange="SSE",
                start_date=start_td,
                end_date=end_td,
                is_open="1",
            )
            if frame is None:
                return pd.DataFrame(columns=["cal_date", "is_open"])
            return frame

        cal = retry_with_budget(
            _fetch_cal,
            transient=Exception,
            deadline=deadline,
            label="screener trade_cal",
        )
        time.sleep(THROTTLE_S)

        if cal.empty or "cal_date" not in cal.columns:
            return []

        open_dates = sorted(cal["cal_date"].astype(str).tolist())
        missing: list[str] = []
        for trade_date in open_dates:
            iso_date = _trade_date_iso(trade_date)
            if not loader_cache_range_is_final(iso_date):
                continue
            if self.partition_path(trade_date).is_file():
                continue
            missing.append(trade_date)
        return missing

    def _fetch_partition_frame(
        self,
        pro,
        trade_date: str,
        *,
        deadline: float,
    ) -> pd.DataFrame | None:
        td = normalize_trade_date(trade_date)

        def _fetch_daily() -> pd.DataFrame:
            frame = pro.daily(trade_date=td, fields=DAILY_FIELDS)
            if frame is None:
                return pd.DataFrame()
            return frame

        daily = retry_with_budget(
            _fetch_daily,
            transient=Exception,
            deadline=deadline,
            label=f"screener daily {td}",
        )
        time.sleep(THROTTLE_S)

        def _fetch_basic() -> pd.DataFrame:
            frame = pro.daily_basic(trade_date=td, fields=DAILY_BASIC_FIELDS)
            if frame is None:
                return pd.DataFrame()
            return frame

        basic = retry_with_budget(
            _fetch_basic,
            transient=Exception,
            deadline=deadline,
            label=f"screener daily_basic {td}",
        )
        time.sleep(THROTTLE_S)

        return self._merge_daily_basic(daily, basic)

    @staticmethod
    def _merge_daily_basic(daily: pd.DataFrame, basic: pd.DataFrame) -> pd.DataFrame:
        if daily is None or daily.empty:
            return pd.DataFrame()

        merged = daily.copy()
        merged["trade_date"] = merged["trade_date"].map(normalize_trade_date)
        if basic is not None and not basic.empty:
            basic_frame = basic.copy()
            basic_frame["trade_date"] = basic_frame["trade_date"].map(normalize_trade_date)
            keep_basic = ["ts_code", "trade_date", "turnover_rate"]
            basic_frame = basic_frame[keep_basic].drop_duplicates(
                subset=["ts_code", "trade_date"]
            )
            merged = merged.merge(
                basic_frame,
                on=["ts_code", "trade_date"],
                how="left",
            )

        for column in PANEL_COLUMNS:
            if column not in merged.columns:
                merged[column] = pd.NA
            merged[column] = pd.to_numeric(merged[column], errors="coerce")

        return merged[["ts_code", "trade_date", *PANEL_COLUMNS]]
