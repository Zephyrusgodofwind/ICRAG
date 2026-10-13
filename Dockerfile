FROM python:3.13-slim

LABEL org.opencontainers.image.title="IrishClinicalRAG" \
      org.opencontainers.image.description="Evidence-grounded Irish clinical guidance retrieval" \
      org.opencontainers.image.source="https://github.com/Zephyrusgodofwind/ICRAG"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    IRISHCLINICALRAG_DATA_DIR=/app/data \
    IRISHCLINICALRAG_CONFIG_PATH=/app/configs/default.json \
    IRISHCLINICALRAG_FRONTEND_DIR=/app/frontend

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m pip install ".[ml]"

COPY configs ./configs
COPY frontend ./frontend
COPY scripts/docker-entrypoint.sh ./scripts/docker-entrypoint.sh

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/data/raw /app/data/chunks /app/data/index /app/data/manifests /app/data/models \
    && chown -R appuser:appuser /app

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5m --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

ENTRYPOINT ["/bin/sh", "/app/scripts/docker-entrypoint.sh"]
