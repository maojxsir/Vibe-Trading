#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$SCRIPT_DIR/sync.log"

# 加载环境变量
if [ -f "$SCRIPT_DIR/.sync_env" ]; then
    set -a
    source "$SCRIPT_DIR/.sync_env"
    set +a
fi

VENV_PY="$SCRIPT_DIR/venv/bin/python"
if [ ! -f "$VENV_PY" ]; then
    echo "❌ 请先运行 bash deploy.sh 初始化环境"
    exit 1
fi

# 用 nohup 后台跑，日志写文件
ARGS="$@"
if [ $# -eq 0 ]; then
    ARGS="--full"
fi

nohup "$VENV_PY" "$SCRIPT_DIR/stock_data_sync.py" $ARGS > "$LOG_FILE" 2>&1 &

echo "PID: $!"
echo "日志: $LOG_FILE"
echo "查看: tail -f $LOG_FILE"
