# ============================================================================
# Stage 1: Build frontend
# ============================================================================
FROM node:20-slim AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --ignore-scripts
COPY frontend/ ./
RUN npm run build

# ============================================================================
# Stage 2: Python dependencies (build tools allowed here)
# ============================================================================
FROM python:3.11-slim AS python-deps

ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ENV PIP_INDEX_URL=${PIP_INDEX_URL} \
    PIP_TRUSTED_HOST=mirrors.aliyun.com \
    PIP_DEFAULT_TIMEOUT=300 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

ARG APT_MIRROR=mirrors.aliyun.com

# SLIM levels (see docker-compose.prod.yml):
#   0 = full (PDF + OCR + all deps)
#   1 = slim (OCR, no PDF) — needs ~4 GB+ RAM to build
#   2 = ecs (default) — screener/Web/Agent only, no local OCR
ARG SLIM=2

RUN sed -i "s|deb.debian.org|${APT_MIRROR}|g; s|security.debian.org|${APT_MIRROR}|g" \
        /etc/apt/sources.list.d/debian.sources /etc/apt/sources.list 2>/dev/null; \
    if [ "$SLIM" = "0" ]; then \
        apt-get update && apt-get install -y --no-install-recommends \
            build-essential \
            libglib2.0-0 libgl1 libxcb1 libsm6 libxext6 libxrender1 libgomp1 \
            libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 \
            shared-mime-info fontconfig fonts-noto-cjk libfreetype6 \
            && rm -rf /var/lib/apt/lists/*; \
    elif [ "$SLIM" = "1" ]; then \
        apt-get update && apt-get install -y --no-install-recommends \
            build-essential libglib2.0-0 libgl1 libxcb1 \
            && rm -rf /var/lib/apt/lists/*; \
    else \
        apt-get update && apt-get install -y --no-install-recommends \
            build-essential \
            && rm -rf /var/lib/apt/lists/*; \
    fi

COPY agent/requirements.txt agent/requirements-slim.txt agent/requirements-ecs.txt agent/
RUN if [ "$SLIM" = "0" ]; then REQ=requirements.txt; \
    elif [ "$SLIM" = "1" ]; then REQ=requirements-slim.txt; \
    else REQ=requirements-ecs.txt; fi && \
    pip install --no-cache-dir --default-timeout=300 --retries 10 \
    -r agent/$REQ

# ============================================================================
# Stage 3: Python runtime (no gcc/build-essential)
# ============================================================================
FROM python:3.11-slim AS runtime

LABEL org.opencontainers.image.title="Vibe-Trading" \
    org.opencontainers.image.description="Natural-language finance research AI agent with backtesting" \
    org.opencontainers.image.version="0.1.7" \
    org.opencontainers.image.source="https://github.com/HKUDS/Vibe-Trading" \
    org.opencontainers.image.licenses="MIT"

WORKDIR /app

ARG SLIM=2

COPY --from=python-deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=python-deps /usr/local/bin /usr/local/bin

COPY pyproject.toml LICENSE README.md ./
COPY agent/ agent/
COPY --from=frontend-build /app/frontend/dist frontend/dist

RUN if [ "$SLIM" = "0" ]; then \
        pip install --no-cache-dir --default-timeout=300 --retries 10 -e .; \
    else \
        pip install --no-cache-dir --default-timeout=300 --retries 10 -e . --no-deps; \
    fi

RUN useradd --create-home --shell /usr/sbin/nologin vibe \
    && mkdir -p agent/runs agent/sessions agent/uploads agent/.swarm/runs \
    && mkdir -p /home/vibe/.vibe-trading \
    && chown -R vibe:vibe /app /home/vibe/.vibe-trading
USER vibe

EXPOSE 8899

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8899/health')" || exit 1

CMD ["vibe-trading", "serve", "--host", "0.0.0.0", "--port", "8899"]
