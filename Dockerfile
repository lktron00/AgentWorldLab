FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim@sha256:e5b65587bce7de595f299855d7385fe7fca39b8a74baa261ba1b7147afa78e58

LABEL org.opencontainers.image.title="Agent World Lab" \
      org.opencontainers.image.description="Local experiments with AgentSociety 2, OASIS and OpenEnv" \
      org.opencontainers.image.source="https://github.com/lktron00/AgentWorldLab" \
      org.opencontainers.image.url="https://github.com/lktron00/AgentWorldLab" \
      org.opencontainers.image.version="0.1.0"

ENV UV_PYTHON_INSTALL_DIR=/opt/python \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    RAY_USAGE_STATS_ENABLED=0 \
    MEM0_TELEMETRY=False \
    ANONYMIZED_TELEMETRY=False \
    GRADIO_ANALYTICS_ENABLED=False

RUN apt-get update && apt-get install -y --no-install-recommends \
    git ca-certificates build-essential libmagic1 libcairo2 libgomp1 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY upstreams.json ./
COPY requirements ./requirements
COPY scripts/bootstrap.py ./scripts/bootstrap.py
RUN --mount=type=cache,target=/root/.cache/uv python scripts/bootstrap.py
COPY . .
RUN useradd --create-home --uid 10001 worldlab \
    && mkdir -p /app/data \
    && chown worldlab:worldlab /app /app/data /app/vendor/* /app/vendor/*/.git
# Installed interpreters and packages stay root-owned and readable. Changing
# ownership recursively would duplicate several GB into a second image layer.
USER worldlab
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
    CMD .venv-api/bin/python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/health',timeout=3)"
# The container network is isolated. Publish ONLY on the host's loopback
# interface; compose.yaml supplies that binding and a non-root user.
CMD [".venv-api/bin/python", "-m", "uvicorn", "worldlab.server:app", "--host", "0.0.0.0", "--port", "8765"]
