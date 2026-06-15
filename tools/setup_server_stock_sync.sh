#!/usr/bin/env bash
# Bootstrap host-side ~/stock-sync on Aliyun ECS (non-interactive).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_DIR="${STOCK_SYNC_DIR:-$HOME/stock-sync}"

echo "============================================="
echo "ECS stock-sync 配置"
echo "源: $SCRIPT_DIR"
echo "目标: $TARGET_DIR"
echo "============================================="

mkdir -p "$TARGET_DIR"
if command -v rsync >/dev/null 2>&1; then
    rsync -a \
        --exclude venv \
        --exclude logs \
        --exclude sync.log \
        "$SCRIPT_DIR/" "$TARGET_DIR/"
else
    cp -R "$SCRIPT_DIR/"* "$TARGET_DIR/"
fi

chmod +x "$TARGET_DIR"/*.sh 2>/dev/null || true
bash "$TARGET_DIR/init_sync_env.sh" "$TARGET_DIR/.sync_env"

echo ""
echo "📦 创建 venv 并安装依赖..."
bash "$TARGET_DIR/deploy.sh" <<'INPUT' || true
mongodb://127.0.0.1:27017
stock_data

0
INPUT

echo ""
echo "🔗 若 Vibe-Trading 跑在 Docker，需一次性开放 mongod 给容器："
echo "   sudo bash $TARGET_DIR/configure_mongodb_docker_access.sh"
echo ""
echo "⏰ 安装 nightly cron："
echo "   bash $TARGET_DIR/install_cron.sh"
echo ""
bash "$TARGET_DIR/diagnose_mongo.sh" || true
