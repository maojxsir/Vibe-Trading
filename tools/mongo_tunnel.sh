#!/usr/bin/env bash
# One-click SSH tunnel to the server's MongoDB.
#
# 把本地端口（默认 27018）转发到服务器 MongoDB（默认 127.0.0.1:27017），
# 使本机的 agent/.env（MONGO_URI=mongodb://127.0.0.1:27018）可直连远端库。
# 依赖已配置好的 SSH 免密（ssh-copy-id 到 SSH_HOST）。
#
# 用法:
#   tools/mongo_tunnel.sh [start|stop|status|restart]
# 环境变量（可覆盖默认值）:
#   SSH_HOST     SSH 目标（~/.ssh/config 中的 Host，默认 aliyun）
#   LOCAL_PORT   本地监听端口（默认 27018）
#   REMOTE_HOST  服务器侧 MongoDB 主机（默认 127.0.0.1）
#   REMOTE_PORT  服务器侧 MongoDB 端口（默认 27017）
set -euo pipefail

SSH_HOST="${SSH_HOST:-aliyun}"
LOCAL_PORT="${LOCAL_PORT:-27018}"
REMOTE_HOST="${REMOTE_HOST:-127.0.0.1}"
REMOTE_PORT="${REMOTE_PORT:-27017}"

# 用于匹配/清理本隧道进程的特征串。只认 "-L <forward> <host>"，
# 这样不受 ssh 选项顺序（-o ...）影响，也能识别手动起的等价隧道。
FORWARD_SPEC="${LOCAL_PORT}:${REMOTE_HOST}:${REMOTE_PORT}"
PROC_PATTERN="-L ${FORWARD_SPEC} ${SSH_HOST}"

port_listening() {
    if command -v lsof >/dev/null 2>&1; then
        lsof -nP -iTCP:"$LOCAL_PORT" -sTCP:LISTEN >/dev/null 2>&1
        return $?
    fi
    python3 - "$LOCAL_PORT" <<'PY'
import socket, sys
s = socket.socket()
s.settimeout(1)
try:
    s.connect(("127.0.0.1", int(sys.argv[1])))
except OSError:
    raise SystemExit(1)
finally:
    s.close()
PY
}

tunnel_pids() {
    pgrep -f -- "$PROC_PATTERN" 2>/dev/null || true
}

do_status() {
    local pids
    pids="$(tunnel_pids)"
    if [ -n "$pids" ] && port_listening; then
        echo "✅ 隧道运行中: 本地 ${LOCAL_PORT} → ${SSH_HOST}:${REMOTE_HOST}:${REMOTE_PORT} (pid: ${pids//$'\n'/ })"
        return 0
    fi
    if port_listening; then
        echo "⚠️  本地 ${LOCAL_PORT} 已被占用，但不是本脚本启动的隧道"
        return 0
    fi
    echo "❌ 隧道未运行（本地 ${LOCAL_PORT} 未监听）"
    return 1
}

do_start() {
    if port_listening; then
        echo "✅ 本地 ${LOCAL_PORT} 已在监听，跳过启动"
        do_status || true
        return 0
    fi
    echo "⏳ 启动隧道: 本地 ${LOCAL_PORT} → ${SSH_HOST} (${REMOTE_HOST}:${REMOTE_PORT}) ..."
    # ControlMaster=no + ControlPath=none：独立连接，避免被 ~/.ssh/config 里
    #   Host * 的连接复用（ControlMaster auto）牵连——否则别的 ssh 会话结束时
    #   会拆掉共享 master，连带把后台隧道也杀掉。
    # ExitOnForwardFailure：端口转发失败时不要留下空连接。
    # ServerAlive*：保活，链路空闲时自动探测，断了好察觉。
    ssh -fN \
        -o ControlMaster=no \
        -o ControlPath=none \
        -o ConnectTimeout=10 \
        -o ExitOnForwardFailure=yes \
        -o ServerAliveInterval=30 \
        -o ServerAliveCountMax=3 \
        -L "$FORWARD_SPEC" \
        "$SSH_HOST"
    # 等待端口就绪。
    for _ in $(seq 1 10); do
        if port_listening; then
            echo "✅ 隧道已建立"
            return 0
        fi
        sleep 1
    done
    echo "❌ 隧道启动后本地 ${LOCAL_PORT} 仍未监听" >&2
    return 1
}

do_stop() {
    local pids
    pids="$(tunnel_pids)"
    if [ -z "$pids" ]; then
        echo "ℹ️  未发现本脚本的隧道进程"
        return 0
    fi
    # shellcheck disable=SC2086
    kill $pids 2>/dev/null || true
    echo "🛑 已停止隧道 (pid: ${pids//$'\n'/ })"
}

case "${1:-start}" in
    start)   do_start ;;
    stop)    do_stop ;;
    restart) do_stop; sleep 1; do_start ;;
    status)  do_status ;;
    *)
        echo "用法: $0 [start|stop|status|restart]" >&2
        exit 2
        ;;
esac
