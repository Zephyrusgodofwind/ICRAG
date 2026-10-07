"""Small, explicit configuration loader with no global mutable settings."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True, slots=True)
class ChunkingSettings:
    target_tokens: int = 500
    overlap_tokens: int = 80
    minimum_tokens: int = 80


@dataclass(frozen=True, slots=True)
class RetrievalSettings:
    dense_dimensions: int = 384
    dense_backend: Literal["auto", "hashing", "sentence-transformers"] = "auto"
    dense_model: str = "BAAI/bge-small-en-v1.5"
    dense_query_prefix: str = "Represent this sentence for searching relevant passages: "
    rrf_k: int = 60
    top_k_initial: int = 20
    top_k_final: int = 5
    default_method: Literal["bm25", "dense", "hybrid", "hybrid-rerank"] = "hybrid"


@dataclass(frozen=True, slots=True)
class RerankingSettings:
    model: str = "cross-encoder/ms-marco-MiniLM-L6-v2"
    candidate_k: int = 20
    top_k: int = 5
    batch_size: int = 16


@dataclass(frozen=True, slots=True)
class GenerationSettings:
    provider: Literal["extractive", "openai-compatible"] = "extractive"
    model: str = ""
    base_url: str = ""
    api_key_env: str = "IRISHCLINICALRAG_LLM_API_KEY"
    timeout_seconds: int = 60
    temperature: float = 0.0


@dataclass(frozen=True, slots=True)
class Settings:
    chunking: ChunkingSettings = ChunkingSettings()
    retrieval: RetrievalSettings = RetrievalSettings()
    reranking: RerankingSettings = RerankingSettings()
    generation: GenerationSettings = GenerationSettings()


def load_settings(path: Path) -> Settings:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return Settings(
        chunking=ChunkingSettings(**payload.get("chunking", {})),
        retrieval=RetrievalSettings(**payload.get("retrieval", {})),
        reranking=RerankingSettings(**payload.get("reranking", {})),
        generation=GenerationSettings(**payload.get("generation", {})),
    )
