#!/usr/bin/env bash
# One-time setup on Aliyun ECS: allow Docker containers to reach host mongod on 27017.
# mongod default bindIp=127.0.0.1 blocks container traffic via docker0 / host-gateway.
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "请用 root 执行: sudo bash $0" >&2
    exit 1
fi

CONF=""
for candidate in /etc/mongod.conf /etc/mongodb.conf; do
    if [ -f "$candidate" ]; then
        CONF="$candidate"
        break
    fi
done

if [ -z "$CONF" ]; then
    echo "❌ 未找到 /etc/mongod.conf" >&2
    exit 1
fi

DOCKER_GW="${DOCKER_GATEWAY_IP:-172.17.0.1}"
BACKUP="${CONF}.bak.$(date +%Y%m%d%H%M%S)"
cp "$CONF" "$BACKUP"
echo "✅ 已备份: $BACKUP"

python3 <<PY
from pathlib import Path
import re

conf = Path("$CONF")
text = conf.read_text(encoding="utf-8")
bind_ips = ["127.0.0.1", "$DOCKER_GW"]

if re.search(r"^\s*bindIp\s*:", text, re.M):
    def repl(match):
        line = match.group(0)
        current = re.search(r"bindIp\s*:\s*(.+)", line).group(1).strip()
        parts = [p.strip() for p in re.split(r"[,\s]+", current) if p.strip()]
        for ip in bind_ips:
            if ip not in parts:
                parts.append(ip)
        return "  bindIp: " + ",".join(parts)
    text = re.sub(r"^\s*bindIp\s*:.*$", repl, text, count=1, flags=re.M)
else:
    if re.search(r"^net\s*:", text, re.M):
        text = re.sub(r"(^net\s*:\n)", r"\1  bindIp: " + ",".join(bind_ips) + "\n", text, count=1, flags=re.M)
    else:
        text += "\nnet:\n  bindIp: " + ",".join(bind_ips) + "\n"

conf.write_text(text, encoding="utf-8")
print("✅ 已写入 bindIp:", ",".join(bind_ips))
PY

if command -v systemctl >/dev/null 2>&1; then
    systemctl restart mongod
    systemctl is-active --quiet mongod
    echo "✅ mongod 已重启"
else
    echo "⚠️  请手动重启 mongod"
fi

echo ""
echo "验证（宿主机）:"
mongosh "mongodb://127.0.0.1:27017" --quiet --eval 'db.adminCommand({ ping: 1 })' && echo "  localhost OK"
mongosh "mongodb://${DOCKER_GW}:27017" --quiet --eval 'db.adminCommand({ ping: 1 })' && echo "  ${DOCKER_GW} OK"

echo ""
echo "下一步:"
echo "  1) agent/.env 使用 MONGO_URI=mongodb://host.docker.internal:27017"
echo "  2) cd ~/TradingBuddy && docker compose -f docker-compose.prod.yml up -d --force-recreate"
