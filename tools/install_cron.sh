#!/usr/bin/env bash
# Install a weekday nightly cron job for tools/run_daily_sync.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SYNC_SCRIPT="$SCRIPT_DIR/run_daily_sync.sh"
CRON_TIME="${CRON_TIME:-0 22 * * 1-5}"
CRON_LINE="$CRON_TIME cd $SCRIPT_DIR && /usr/bin/env bash $SYNC_SCRIPT"

if [ ! -x "$SYNC_SCRIPT" ]; then
    chmod +x "$SYNC_SCRIPT"
fi

TMP="$(mktemp)"
crontab -l 2>/dev/null | grep -Fv "$SYNC_SCRIPT" >"$TMP" || true
echo "$CRON_LINE" >>"$TMP"
crontab "$TMP"
rm -f "$TMP"

echo "✅ 已安装 cron：$CRON_LINE"
echo "   查看：crontab -l"
echo "   日志：$SCRIPT_DIR/logs/"
