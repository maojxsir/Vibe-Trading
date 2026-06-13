"""CLI to materialize a screener backtest run directory."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
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


def _parse_codes(raw: str) -> list[str]:
    codes = [part.strip() for part in raw.split(",") if part.strip()]
    if not codes:
        raise ValueError("at least one code is required")
    return codes


def render_config(
    *,
    codes: list[str],
    start_date: str,
    end_date: str,
    hold_days: int,
    score_threshold: float,
    source: str = "tushare",
) -> dict:
    """Build config.json payload for the backtest runner."""
    return {
        "source": source,
        "codes": codes,
        "start_date": start_date,
        "end_date": end_date,
        "interval": "1D",
        "engine": "daily",
        "initial_cash": 1_000_000,
        "screener": {
            "hold_days": hold_days,
            "score_threshold": score_threshold,
        },
    }


def render_signal_engine(
    *,
    agent_dir: Path,
    hold_days: int,
    score_threshold: float,
) -> str:
    """Render code/signal_engine.py that wraps ScreenerSignalEngine."""
    agent_path = agent_dir.resolve().as_posix()
    return f'''"""Screener backtest signal engine (auto-generated)."""
from __future__ import annotations

import sys
from pathlib import Path

_AGENT_DIR = Path({agent_path!r})
if str(_AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(_AGENT_DIR))

from src.screener.backtest_signal import ScreenerSignalEngine
from src.screener.config import ScreenerConfig

HOLD_DAYS = {hold_days}
SCORE_THRESHOLD = {score_threshold}


class SignalEngine:
    """Backtest adapter around :class:`ScreenerSignalEngine`."""

    def __init__(self) -> None:
        config = ScreenerConfig(score_threshold=SCORE_THRESHOLD)
        self._engine = ScreenerSignalEngine(
            config,
            hold_days=HOLD_DAYS,
            score_threshold=SCORE_THRESHOLD,
        )

    def generate(self, data_map: dict) -> dict:
        return self._engine.generate(data_map)
'''


def write_run_dir(
    run_dir: Path,
    *,
    codes: list[str],
    start_date: str,
    end_date: str,
    hold_days: int,
    score_threshold: float,
    source: str = "tushare",
) -> Path:
    """Write config.json and code/signal_engine.py under ``run_dir``."""
    run_dir = Path(run_dir)
    code_dir = run_dir / "code"
    code_dir.mkdir(parents=True, exist_ok=True)

    config = render_config(
        codes=codes,
        start_date=start_date,
        end_date=end_date,
        hold_days=hold_days,
        score_threshold=score_threshold,
        source=source,
    )
    (run_dir / "config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (code_dir / "signal_engine.py").write_text(
        render_signal_engine(
            agent_dir=AGENT_DIR,
            hold_days=hold_days,
            score_threshold=score_threshold,
        ),
        encoding="utf-8",
    )
    return run_dir.resolve()


def _default_out_dir() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return AGENT_DIR / "runs" / f"screener_bt_{stamp}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate a screener backtest run directory.",
    )
    parser.add_argument(
        "--codes",
        required=True,
        help="Comma-separated symbols, e.g. 600519,300308",
    )
    parser.add_argument("--start", required=True, metavar="YYYY-MM-DD")
    parser.add_argument("--end", required=True, metavar="YYYY-MM-DD")
    parser.add_argument("--hold-days", type=int, default=5, dest="hold_days")
    parser.add_argument(
        "--score-threshold",
        type=float,
        default=ScreenerConfig().score_threshold,
        dest="score_threshold",
    )
    parser.add_argument(
        "--out",
        dest="out_dir",
        help="Output run directory (default: runs/screener_bt_<timestamp>)",
    )
    parser.add_argument("--source", default="tushare")
    args = parser.parse_args(argv)

    try:
        codes = _parse_codes(args.codes)
        out_dir = Path(args.out_dir) if args.out_dir else _default_out_dir()
        run_dir = write_run_dir(
            out_dir,
            codes=codes,
            start_date=args.start,
            end_date=args.end,
            hold_days=args.hold_days,
            score_threshold=args.score_threshold,
            source=args.source,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(run_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
