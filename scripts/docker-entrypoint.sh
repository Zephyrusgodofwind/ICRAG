#!/bin/sh
set -eu

DATA_DIR="${IRISHCLINICALRAG_DATA_DIR:-/app/data}"
CONFIG_PATH="${IRISHCLINICALRAG_CONFIG_PATH:-/app/configs/default.json}"
SOURCE_CATALOG="${IRISHCLINICALRAG_SOURCE_CATALOG:-/app/configs/sources.json}"
HOST="${IRISHCLINICALRAG_HOST:-0.0.0.0}"
PORT="${IRISHCLINICALRAG_PORT:-8000}"
LOG_LEVEL="${IRISHCLINICALRAG_LOG_LEVEL:-info}"

if [ ! -s "$DATA_DIR/chunks/chunks.jsonl" ]; then
  echo "No corpus index found; ingesting the configured authoritative sources."
  irishclinicalrag --config "$CONFIG_PATH" --data-dir "$DATA_DIR" ingest "$SOURCE_CATALOG"
fi

if [ ! -s "$DATA_DIR/index/dense-index.json" ]; then
  echo "No semantic index found; building the configured dense index."
  irishclinicalrag --config "$CONFIG_PATH" --data-dir "$DATA_DIR" build-index
fi

exec uvicorn irishclinicalrag.api.app:app \
  --host "$HOST" \
  --port "$PORT" \
  --log-level "$LOG_LEVEL" \
  --timeout-graceful-shutdown 30
