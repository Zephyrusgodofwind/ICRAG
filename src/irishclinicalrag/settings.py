"""Small, explicit configuration loader with no global mutable settings."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ChunkingSettings:
    target_tokens: int = 500
    overlap_tokens: int = 80
    minimum_tokens: int = 80


@dataclass(frozen=True, slots=True)
class RetrievalSettings:
    dense_dimensions: int = 384
    rrf_k: int = 60
    top_k_initial: int = 20
    top_k_final: int = 5


@dataclass(frozen=True, slots=True)
class Settings:
    chunking: ChunkingSettings = ChunkingSettings()
    retrieval: RetrievalSettings = RetrievalSettings()


def load_settings(path: Path) -> Settings:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return Settings(
        chunking=ChunkingSettings(**payload.get("chunking", {})),
        retrieval=RetrievalSettings(**payload.get("retrieval", {})),
    )

