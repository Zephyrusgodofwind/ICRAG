#!/bin/sh
set -eu

if [ ! -s /app/data/chunks/chunks.jsonl ]; then
  echo "No corpus index found; ingesting the configured authoritative sources."
  irishclinicalrag --data-dir /app/data ingest /app/configs/sources.json
fi

if [ ! -s /app/data/index/dense-index.json ]; then
  echo "No semantic index found; building the configured dense index."
  irishclinicalrag --data-dir /app/data build-index
fi

exec uvicorn irishclinicalrag.api.app:app --host 0.0.0.0 --port 8000
