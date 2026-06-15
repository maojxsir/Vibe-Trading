#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SYNC_SCRIPT="$SCRIPT_DIR/stock_data_sync.py"
VENV_DIR="$SCRIPT_DIR/venv"

echo "============================================="
echo "📈 股票数据同步工具 - 一键部署"
echo "============================================="

# ---- 1. 检查 Python ----
echo ""
echo "🔍 [1/5] 检查 Python 环境..."

PYTHON=""
for cmd in python3 python; do
    if command -v $cmd &>/dev/null; then
        VER=$($cmd --version 2>&1 | grep -oP '\d+\.\d+')
        MAJOR=${VER%.*}
        if [ "$MAJOR" -ge 3 ]; then
            PYTHON=$cmd
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "❌ 未找到 Python 3，请先安装: apt install python3 python3-pip python3-venv"
    exit 1
fi
echo "   ✅ $($PYTHON --version)"

# ---- 2. 创建虚拟环境并安装依赖 ----
echo ""
echo "📦 [2/5] 创建虚拟环境并安装依赖（~40MB）..."

if [ ! -d "$VENV_DIR" ]; then
    $PYTHON -m venv "$VENV_DIR"
    echo "   ✅ 虚拟环境已创建"
fi

VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"

$VENV_PIP install --upgrade pip -q 2>/dev/null || true

DEPS=("pymongo" "pandas" "tushare" "akshare")
for dep in "${DEPS[@]}"; do
    if $VENV_PYTHON -c "import $dep" 2>/dev/null; then
        echo "   ✅ $dep 已安装"
    else
        echo "   ⏳ 正在安装 $dep ..."
        $VENV_PIP install "$dep" -q 2>&1
        if $VENV_PYTHON -c "import $dep" 2>/dev/null; then
            echo "   ✅ $dep 安装成功"
        else
            echo "   ❌ $dep 安装失败"
            exit 1
        fi
    fi
done

# ---- 3. 配置 ----
echo ""
echo "🔧 [3/5] 配置..."

if [ -f "$SCRIPT_DIR/.sync_env" ]; then
    source "$SCRIPT_DIR/.sync_env"
fi

read -p "   MongoDB 连接地址 [${MONGO_URI:-mongodb://localhost:27017}]: " input_uri
MONGO_URI="${input_uri:-${MONGO_URI:-mongodb://localhost:27017}}"

read -p "   数据库名 [${MONGO_DB:-stock_data}]: " input_db
MONGO_DB="${input_db:-${MONGO_DB:-stock_data}}"

read -p "   Tushare Token (留空跳过): " tushare_token

cat > "$SCRIPT_DIR/.sync_env" << ENVEOF
MONGO_URI=$MONGO_URI
MONGO_DB=$MONGO_DB
TUSHARE_TOKEN=$tushare_token
BATCH_SIZE=200
VENV_DIR=$VENV_DIR
ENVEOF
echo "   ✅ 配置已保存"

# ---- 4. 测试 MongoDB 连接 ----
echo ""
echo "🔗 [4/5] 测试 MongoDB 连接..."
if $VENV_PYTHON -c "
from pymongo import MongoClient
c = MongoClient('$MONGO_URI', serverSelectionTimeoutMS=5000)
c.server_info()
print('ok')
" 2>/dev/null; then
    echo "   ✅ MongoDB 连接成功"
else
    echo "   ⚠️  MongoDB 连接失败，请检查 MongoDB 是否已启动"
    echo "     安装: apt install -y mongodb-org && systemctl start mongod"
    read -p "   继续？(y/N): " cont
    [ "$cont" != "y" ] && exit 1
fi

# ---- 5. 运行同步 ----
echo ""
echo "🚀 [5/5] 选择同步模式..."
echo ""
echo "============================================="
echo "  1) 完整同步（2016年起，推荐）"
echo "  2) 全量历史（1990年起，几小时）"
echo "  3) 仅基础信息（快）"
echo "  4) 仅某只股票"
echo "  0) 退出"
echo "============================================="
echo ""
read -p "  请输入 [0-4]: " mode

export MONGO_URI MONGO_DB TUSHARE_TOKEN

case $mode in
    1)
        echo "🚀 同步 2016 年至今..."
        $VENV_PYTHON "$SYNC_SCRIPT" --full
        ;;
    2)
        echo "🚀 全量同步（1990至今）..."
        $VENV_PYTHON "$SYNC_SCRIPT" --full --all
        ;;
    3)
        $VENV_PYTHON "$SYNC_SCRIPT" --basic
        echo ""
        echo "💡 后续需要其他数据时："
        echo "   $VENV_PYTHON $SYNC_SCRIPT --kline --financial --moneyflow --margin --top10 --forecast"
        ;;
    4)
        read -p "  股票代码: " stock_code
        $VENV_PYTHON "$SYNC_SCRIPT" --symbol "$stock_code" --full
        ;;
    0) echo "👋 退出"; exit 0 ;;
    *) echo "❌ 无效选项"; exit 1 ;;
esac

echo ""
echo "============================================="
echo "✅ 同步完成！"
echo "   MongoDB: $MONGO_URI/$MONGO_DB"
echo "  下次直接: cd $SCRIPT_DIR && bash run.sh"
echo "============================================="
