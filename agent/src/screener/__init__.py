"""A-share limit-up screener package."""

from src.screener.board import detect_board, is_limit_up, limit_up_threshold
from src.screener.config import ScreenerConfig

__all__ = [
    "ScreenerConfig",
    "detect_board",
    "is_limit_up",
    "limit_up_threshold",
]
