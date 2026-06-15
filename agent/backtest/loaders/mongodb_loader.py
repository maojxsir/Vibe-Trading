"""MongoDB loader for A-share daily bars backed by ``stock_data`` collections."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import pandas as pd

from backtest.loaders.base import validate_date_range
from backtest.loaders.registry import register
from src.data import mongodb_stock

logger = logging.getLogger(__name__)


@register
class DataLoader:
    """MongoDB-backed OHLCV loader with on-demand sync for missing symbols."""

    name = "mongodb"
    markets = {"a_share"}
    requires_auth = False

    def is_available(self) -> bool:
        return mongodb_stock.is_mongodb_available()

    def fetch(
        self,
        codes: List[str],
        start_date: str,
        end_date: str,
        fields: Optional[List[str]] = None,
        interval: str = "1D",
    ) -> Dict[str, pd.DataFrame]:
        validate_date_range(start_date, end_date)

        if interval != "1D":
            logger.info("MongoDB loader only supports 1D bars; skipping %s", interval)
            return {}

        if fields:
            logger.debug("MongoDB loader ignores extra fields: %s", fields)

        result: Dict[str, pd.DataFrame] = {}
        missing: list[str] = []

        for code in codes:
            ts_code = mongodb_stock.to_ts_code(code)
            frame = mongodb_stock.fetch_daily_ohlcv(code, start_date, end_date)
            if mongodb_stock.coverage_is_sufficient(frame, start_date, end_date):
                result[ts_code] = frame
            else:
                missing.append(code)

        if missing and mongodb_stock.trigger_symbol_sync(
            missing,
            start_date=start_date,
            end_date=end_date,
        ):
            for code in missing:
                ts_code = mongodb_stock.to_ts_code(code)
                frame = mongodb_stock.fetch_daily_ohlcv(code, start_date, end_date)
                if mongodb_stock.coverage_is_sufficient(frame, start_date, end_date):
                    result[ts_code] = frame

        return result
