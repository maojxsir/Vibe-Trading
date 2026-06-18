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
# Stage 2: Python runtime
# ============================================================================
FROM python:3.11-slim AS runtime

LABEL org.opencontainers.image.title="Vibe-Trading" \
    org.opencontainers.image.description="Natural-language finance research AI agent with backtesting" \
    org.opencontainers.image.version="0.1.7" \
    org.opencontainers.image.source="https://github.com/HKUDS/Vibe-Trading" \
    org.opencontainers.image.licenses="MIT"

WORKDIR /app

# PyPI: default Aliyun mirror for CN ECS builds; override for other regions:
#   docker build --build-arg PIP_INDEX_URL=https://pypi.org/simple/ .
ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ENV PIP_INDEX_URL=${PIP_INDEX_URL} \
    PIP_TRUSTED_HOST=mirrors.aliyun.com \
    PIP_DEFAULT_TIMEOUT=300

# Debian APT: default Aliyun mirror for CN ECS builds (deb.debian.org is rate-
# limited from CN and stalls the build); override for other regions:
#   docker build --build-arg APT_MIRROR=deb.debian.org .
ARG APT_MIRROR=mirrors.aliyun.com

# SLIM=1 (default for prod ECS): keep holdings OCR (rapidocr/opencv) but drop
# weasyprint/matplotlib system libs to reduce build time and memory on small VMs.
# SLIM=0: full Shadow Account PDF + CJK fonts.
ARG SLIM=1

# Runtime system libraries for native Python wheels (slim image has almost none).
RUN sed -i "s|deb.debian.org|${APT_MIRROR}|g; s|security.debian.org|${APT_MIRROR}|g" \
        /etc/apt/sources.list.d/debian.sources /etc/apt/sources.list 2>/dev/null; \
    if [ "$SLIM" = "1" ]; then \
        apt-get update && apt-get install -y --no-install-recommends \
            build-essential \
            libglib2.0-0 libgl1 libxcb1 \
            && rm -rf /var/lib/apt/lists/*; \
    else \
        apt-get update && apt-get install -y --no-install-recommends \
            build-essential \
            libglib2.0-0 libgl1 libxcb1 \
            libsm6 libxext6 libxrender1 libgomp1 \
            libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
            libgdk-pixbuf-2.0-0 shared-mime-info fontconfig fonts-noto-cjk \
            libfreetype6 \
            && rm -rf /var/lib/apt/lists/*; \
    fi

# Python deps (install before copying code for layer caching)
COPY agent/requirements.txt agent/requirements-slim.txt agent/
RUN if [ "$SLIM" = "1" ]; then REQ=requirements-slim.txt; else REQ=requirements.txt; fi && \
    pip install --no-cache-dir --default-timeout=300 --retries 10 \
    -r agent/$REQ

# Copy project
COPY pyproject.toml LICENSE README.md ./
COPY agent/ agent/

# Copy built frontend
COPY --from=frontend-build /app/frontend/dist frontend/dist

# Install CLI entrypoint (slim: --no-deps to skip weasyprint/matplotlib from pyproject)
RUN if [ "$SLIM" = "1" ]; then \
        pip install --no-cache-dir --default-timeout=300 --retries 10 -e . --no-deps; \
    else \
        pip install --no-cache-dir --default-timeout=300 --retries 10 -e .; \
    fi

# Runtime should not run as root. Keep writable app data directories owned by
# the service user so named Docker volumes inherit usable permissions.
RUN useradd --create-home --shell /usr/sbin/nologin vibe \
    && mkdir -p agent/runs agent/sessions agent/uploads agent/.swarm/runs \
    && mkdir -p /home/vibe/.vibe-trading \
    && chown -R vibe:vibe /app /home/vibe/.vibe-trading
USER vibe

# Default port
EXPOSE 8899

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8899/health')" || exit 1

# Run API server (serves frontend/dist as static files)
CMD ["vibe-trading", "serve", "--host", "0.0.0.0", "--port", "8899"]
