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

# Runtime system libraries for native Python wheels (slim image has almost none).
# Grouped by feature — keep in sync when adding deps that call into C libraries.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    # rapidocr-onnxruntime → opencv-python → headless GUI libs
    libglib2.0-0 \
    libgl1 \
    libxcb1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    # weasyprint → shadow-account PDF reports
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info \
    fontconfig \
    fonts-noto-cjk \
    # matplotlib / pillow
    libfreetype6 \
    && rm -rf /var/lib/apt/lists/*

# Python deps (install before copying code for layer caching)
COPY agent/requirements.txt agent/requirements.txt
RUN pip install --no-cache-dir --default-timeout=300 --retries 10 \
    -r agent/requirements.txt

# Copy project
COPY pyproject.toml LICENSE README.md ./
COPY agent/ agent/

# Copy built frontend
COPY --from=frontend-build /app/frontend/dist frontend/dist

# Install CLI entrypoint
RUN pip install --no-cache-dir --default-timeout=300 --retries 10 -e .

# Runtime should not run as root. Keep writable app data directories owned by
# the service user so named Docker volumes inherit usable permissions.
RUN useradd --create-home --shell /usr/sbin/nologin vibe \
    && mkdir -p agent/runs agent/sessions agent/uploads agent/.swarm/runs \
    && chown -R vibe:vibe /app
USER vibe

# Default port
EXPOSE 8899

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8899/health')" || exit 1

# Run API server (serves frontend/dist as static files)
CMD ["vibe-trading", "serve", "--host", "0.0.0.0", "--port", "8899"]
