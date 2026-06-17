#!/usr/bin/env bash
# Start MongoDB when it is not listening on port 27017.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$SCRIPT_DIR/.sync_env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$SCRIPT_DIR/.sync_env"
    set +a
fi

MONGO_URI="${MONGO_URI:-mongodb://127.0.0.1:27017}"
PORT="${MONGO_PORT:-27017}"
# Default to the Linux systemd package data dir; never silently create an empty
# DB under the Homebrew path /usr/local/var/mongodb.
DBPATH="${MONGO_DBPATH:-/var/lib/mongodb}"
LOGPATH="${MONGO_LOGPATH:-/var/log/mongodb/mongod.log}"
# Bind loopback + docker bridge so containers can reach the host mongod.
BIND_IP="${MONGO_BIND_IP:-127.0.0.1,172.17.0.1}"

port_open() {
    if command -v lsof >/dev/null 2>&1; then
        lsof -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1
        return $?
    fi
    python3 - <<PY
import socket
s = socket.socket()
s.settimeout(1)
try:
    s.connect(("127.0.0.1", int("$PORT")))
except OSError:
    raise SystemExit(1)
finally:
    s.close()
PY
}

wait_ready() {
    for _ in $(seq 1 20); do
        if command -v mongosh >/dev/null 2>&1; then
            mongosh "$MONGO_URI" --quiet --eval 'db.adminCommand({ ping: 1 })' >/dev/null 2>&1 && return 0
        elif port_open; then
            return 0
        fi
        sleep 1
    done
    return 1
}

if port_open; then
    echo "✅ MongoDB 已在 ${PORT} 端口运行"
    exit 0
fi

echo "⏳ MongoDB 未运行，尝试启动..."

# Prefer the systemd unit (reads /etc/mongod.conf, so dbPath/bindIp stay correct)
# instead of a manual --dbpath start that can create an empty DB.
if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files 2>/dev/null | grep -q '^mongod\.service'; then
    echo "   使用 systemd: systemctl start mongod"
    sudo systemctl start mongod 2>/dev/null || systemctl start mongod
elif command -v brew >/dev/null 2>&1; then
    echo "   尝试: brew services start mongodb-community"
    brew services start mongodb-community >/dev/null 2>&1 || brew services start mongodb/brew/mongodb-community >/dev/null 2>&1 || true
else
    # Last-resort manual start (uses the corrected DBPATH/BIND_IP defaults).
    mkdir -p "$DBPATH" "$(dirname "$LOGPATH")"
    MONGOD_BIN=""
    for candidate in \
        /usr/bin/mongod \
        /usr/local/bin/mongod \
        /opt/homebrew/bin/mongod \
        /tmp/mongod-arm64 \
        "$(command -v mongod 2>/dev/null || true)"; do
        if [ -n "$candidate" ] && [ -x "$candidate" ]; then
            MONGOD_BIN="$candidate"
            break
        fi
    done
    if [ -z "$MONGOD_BIN" ]; then
        echo "❌ 找不到 mongod，请先安装 MongoDB" >&2
        exit 1
    fi
    echo "   使用: $MONGOD_BIN (dbpath=$DBPATH)"
    "$MONGOD_BIN" \
        --dbpath "$DBPATH" \
        --port "$PORT" \
        --logpath "$LOGPATH" \
        --logappend \
        --bind_ip "$BIND_IP" \
        --fork
fi

if wait_ready; then
    echo "✅ MongoDB 已启动: $MONGO_URI"
    exit 0
fi

echo "❌ MongoDB 启动后仍无法连接，请查看日志: $LOGPATH" >&2
exit 1
