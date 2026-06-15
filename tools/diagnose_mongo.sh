#!/usr/bin/env bash
# Detect MongoDB connection settings and print recommended MONGO_URI / MONGO_DB.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$SCRIPT_DIR/.sync_env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$SCRIPT_DIR/.sync_env"
    set +a
fi

MONGO_URI="${MONGO_URI:-mongodb://127.0.0.1:27017}"
MONGO_DB="${MONGO_DB:-stock_data}"

echo "============================================="
echo "MongoDB 诊断"
echo "============================================="

echo ""
echo "[1] 进程 / 端口"
if command -v lsof >/dev/null 2>&1; then
    if lsof -iTCP:27017 -sTCP:LISTEN >/dev/null 2>&1; then
        echo "  ✅ 27017 端口有监听"
        lsof -iTCP:27017 -sTCP:LISTEN | sed -n '1,3p' | sed 's/^/    /'
    else
        echo "  ❌ 27017 无监听（MongoDB 可能未启动）"
    fi
else
    echo "  ⚠️  无法检测端口（缺少 lsof）"
fi

if pgrep -x mongod >/dev/null 2>&1 || pgrep -f '[m]ongod ' >/dev/null 2>&1; then
    echo "  ✅ 发现 mongod 进程"
else
    echo "  ❌ 未发现 mongod 进程"
fi

if command -v docker >/dev/null 2>&1; then
    mongo_containers="$(docker ps --filter publish=27017 --format '{{.Names}} {{.Ports}}' 2>/dev/null || true)"
    if [ -n "$mongo_containers" ]; then
        echo "  🐳 Docker MongoDB 容器:"
        echo "$mongo_containers" | sed 's/^/    /'
    else
        echo "  ℹ️  未发现映射 27017 的 Docker 容器（可能是本机 mongod）"
    fi
else
    echo "  ℹ️  Docker 不可用，跳过容器检测"
fi

echo ""
echo "[2] 连接测试"
if ! command -v mongosh >/dev/null 2>&1; then
    echo "  ❌ 未安装 mongosh，无法进一步检测鉴权/库名"
    echo "  建议: brew install mongosh  或  apt install mongodb-mongosh"
    exit 1
fi

if ! mongosh "$MONGO_URI" --quiet --eval 'db.adminCommand({ ping: 1 })' >/dev/null 2>&1; then
    echo "  ❌ 无法连接: $MONGO_URI"
    echo "  可先执行: bash $SCRIPT_DIR/ensure_mongo.sh"
    exit 1
fi

echo "  ✅ 可连接: $MONGO_URI"

auth_info="$(mongosh "$MONGO_URI" --quiet --eval 'JSON.stringify(db.adminCommand({ connectionStatus: 1 }).authInfo.authenticatedUsers || [])')"
if [ "$auth_info" = "[]" ]; then
    echo "  ✅ 鉴权: 无需用户名密码（匿名可连）"
    recommended_uri="$MONGO_URI"
else
    echo "  🔐 鉴权: 已启用，URI 需带账号，例如:"
    echo "     mongodb://user:pass@127.0.0.1:27017/?authSource=admin"
    recommended_uri="mongodb://<user>:<pass>@127.0.0.1:27017/?authSource=admin"
fi

echo ""
echo "[3] 数据库与集合"
mongosh "$MONGO_URI" --quiet --eval "
const target = '$MONGO_DB';
const names = db.adminCommand({ listDatabases: 1 }).databases.map(d => d.name);
print('  已有库: ' + names.join(', '));
const cols = ['stock_basic_info','stock_daily_quotes','stock_financial_data','stock_moneyflow','stock_margin','stock_top10_holders','stock_forecast'];
function show(dbName) {
  const d = db.getSiblingDB(dbName);
  print('  --- ' + dbName + ' ---');
  cols.forEach(c => {
    if (d.getCollectionNames().includes(c)) {
      print('    ' + c + ': ' + d.getCollection(c).countDocuments());
    }
  });
}
show(target);
if (target !== 'stock_data') show('stock_data');
" | sed 's/^/  /'

echo ""
echo "[4] 推荐 agent/.env 配置"
echo "  VIBE_USE_MONGODB=1"
echo "  MONGO_URI=$recommended_uri"
echo "  MONGO_DB=$MONGO_DB"
echo ""
echo "  Docker 容器访问宿主机 MongoDB 时，Mac/Win 可用:"
echo "  MONGO_URI=mongodb://host.docker.internal:27017"
echo "  Linux 常用宿主机网关 IP，例如:"
echo "  MONGO_URI=mongodb://172.17.0.1:27017"
echo "============================================="
