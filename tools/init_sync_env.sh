#!/usr/bin/env bash
# Non-interactive .sync_env for ECS host-side stock-sync.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="${1:-$SCRIPT_DIR/.sync_env}"

MONGO_URI="${MONGO_URI:-mongodb://127.0.0.1:27017}"
MONGO_DB="${MONGO_DB:-stock_data}"
TUSHARE_TOKEN="${TUSHARE_TOKEN:-}"
BATCH_SIZE="${BATCH_SIZE:-200}"

if [ -z "$TUSHARE_TOKEN" ] && [ -f "$SCRIPT_DIR/../agent/.env" ]; then
    TUSHARE_TOKEN="$(grep -E '^TUSHARE_TOKEN=' "$SCRIPT_DIR/../agent/.env" | head -1 | cut -d= -f2- || true)"
fi

cat > "$ENV_FILE" <<EOF
MONGO_URI=$MONGO_URI
MONGO_DB=$MONGO_DB
TUSHARE_TOKEN=$TUSHARE_TOKEN
BATCH_SIZE=$BATCH_SIZE
VENV_DIR=$SCRIPT_DIR/venv
EOF

echo "✅ 已写入 $ENV_FILE"
echo "   MONGO_URI=$MONGO_URI"
echo "   MONGO_DB=$MONGO_DB"
