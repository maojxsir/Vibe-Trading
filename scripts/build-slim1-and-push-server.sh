#!/usr/bin/env bash
# Build SLIM=1 (OCR, no PDF) linux/amd64 image locally and load on Aliyun ECS.
# Requires: Docker (Docker Desktop or colima), ssh alias `aliyun`.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE="${VT_IMAGE_NAME:-tradingbuddy-vibe-trading:latest}"
ARCH="${VT_PLATFORM:-linux/amd64}"
TAR="${VT_TAR:-/tmp/vibe-slim1-amd64.tar.gz}"
REMOTE="${VT_SSH_HOST:-aliyun}"
COMPOSE_DIR="${VT_COMPOSE_DIR:-~/TradingBuddy}"

echo "==> Build ${IMAGE} (SLIM=1, ${ARCH})"
docker build --platform "${ARCH}" --build-arg SLIM=1 -t "${IMAGE}" "${ROOT}"

echo "==> Save & compress"
docker save "${IMAGE}" | gzip > "${TAR}"
ls -lh "${TAR}"

echo "==> Upload to ${REMOTE}:${TAR}"
scp "${TAR}" "${REMOTE}:${TAR}"

echo "==> Load on server and restart (no on-host build)"
ssh "${REMOTE}" bash -s <<REMOTE_EOF
set -euo pipefail
gunzip -c ${TAR} | docker load
systemctl start mongod 2>/dev/null || true
cd ${COMPOSE_DIR}
git pull --ff-only origin feature/trading_buddy || true
export VT_IMAGE=${IMAGE}
docker compose -f docker-compose.prod.yml up -d --no-build --force-recreate
docker compose -f docker-compose.prod.yml ps
curl -sf http://127.0.0.1:52889/health && echo " health ok"
docker exec tradingbuddy-vibe-trading-1 python -c "from rapidocr_onnxruntime import RapidOCR; print('ocr ok')" || echo "ocr check skipped"
REMOTE_EOF

echo "==> Done. Open http://<server-ip>:52889"
