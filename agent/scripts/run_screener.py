"""CLI entry point for the A-share limit-up screener."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
AGENT_DIR = HERE.parent
sys.path.insert(0, str(AGENT_DIR))

try:
    from dotenv import load_dotenv

    load_dotenv(AGENT_DIR / ".env")
except ImportError:
    pass

from src.screener.config import ScreenerConfig  # noqa: E402
from src.screener.scan import run  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the A-share limit-up screener scan.")
    parser.add_argument(
        "--date",
        dest="trade_date",
        metavar="YYYY-MM-DD",
        help="Trade date to scan (default: latest available in store)",
    )
    args = parser.parse_args(argv)

    out_path = run(ScreenerConfig(), trade_date=args.trade_date)
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
