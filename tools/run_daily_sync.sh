#!/usr/bin/env bash
# Nightly incremental sync for stock_data MongoDB collections.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="${SYNC_LOG_DIR:-$SCRIPT_DIR/logs}"
LOG_FILE="$LOG_DIR/daily_sync_$(date +%Y%m%d).log"

mkdir -p "$LOG_DIR"

bash "$SCRIPT_DIR/ensure_mongo.sh"

if [ -f "$SCRIPT_DIR/.sync_env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$SCRIPT_DIR/.sync_env"
    set +a
fi

VENV_PY="$SCRIPT_DIR/venv/bin/python"
if [ ! -f "$VENV_PY" ]; then
    echo "❌ 请先运行 bash $SCRIPT_DIR/deploy.sh 初始化环境" >&2
    exit 1
fi

echo "[$(date -Iseconds)] daily sync start" | tee -a "$LOG_FILE"
"$VENV_PY" "$SCRIPT_DIR/stock_data_sync.py" --daily >>"$LOG_FILE" 2>&1
echo "[$(date -Iseconds)] daily sync done" | tee -a "$LOG_FILE"
