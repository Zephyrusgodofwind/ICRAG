"""Persistent model-backed dense index with lazy optional dependencies."""

from __future__ import annotations

import json
import math
from array import array
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from irishclinicalrag.models import DenseIndexMetadata, EvidenceChunk, RetrievalResult, utc_now
from irishclinicalrag.validation.corpus import corpus_fingerprint


class TextEncoder(Protocol):
    model_name: str

    def encode(self, texts: Sequence[str]) -> list[list[float]]: ...


@lru_cache(maxsize=4)
def _load_model(model_name: str, local_files_only: bool):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:  # pragma: no cover - depends on optional installation
        raise RuntimeError(
            'Semantic retrieval requires the optional ML dependencies: pip install -e ".[ml]"'
        ) from exc
    if local_files_only:
        return SentenceTransformer(model_name, local_files_only=True)
    try:
        return SentenceTransformer(model_name, local_files_only=True)
    except OSError:
        return SentenceTransformer(model_name, local_files_only=False)


class SentenceTransformerEncoder:
    """Lazy Sentence Transformers adapter; the model is cached per process."""

    def __init__(
        self, model_name: str, batch_size: int = 32, local_files_only: bool = False
    ) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self.local_files_only = local_files_only

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        embeddings = _load_model(self.model_name, self.local_files_only).encode(
            list(texts),
            batch_size=self.batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=len(texts) > self.batch_size,
        )
        return embeddings.tolist()


def _normalize(vector: Sequence[float]) -> list[float]:
    magnitude = math.sqrt(sum(value * value for value in vector))
    if magnitude == 0:
        return [0.0 for _ in vector]
    return [float(value) / magnitude for value in vector]


def build_dense_index(
    chunks: list[EvidenceChunk],
    index_dir: Path,
    model_name: str,
    query_prefix: str = "",
    encoder: TextEncoder | None = None,
) -> DenseIndexMetadata:
    """Encode a corpus and atomically publish its metadata after vectors are durable."""
    if not chunks:
        raise ValueError("cannot build a dense index for an empty corpus")
    active_encoder = encoder or SentenceTransformerEncoder(model_name)
    vectors = active_encoder.encode([chunk.content for chunk in chunks])
    if len(vectors) != len(chunks):
        raise ValueError("encoder returned a different number of vectors than chunks")
    dimensions = len(vectors[0]) if vectors else 0
    if dimensions < 1 or any(len(vector) != dimensions for vector in vectors):
        raise ValueError("encoder returned invalid or inconsistent vector dimensions")

    index_dir.mkdir(parents=True, exist_ok=True)
    vector_path = index_dir / "dense-vectors.f32"
    temporary_vector_path = index_dir / "dense-vectors.f32.tmp"
    flattened = array("f")
    for vector in vectors:
        flattened.extend(_normalize(vector))
    temporary_vector_path.write_bytes(flattened.tobytes())
    temporary_vector_path.replace(vector_path)

    metadata = DenseIndexMetadata(
        backend="sentence-transformers",
        model_name=model_name,
        dimensions=dimensions,
        chunk_ids=[chunk.chunk_id for chunk in chunks],
        corpus_fingerprint=corpus_fingerprint(chunks),
        query_prefix=query_prefix,
        created_at=utc_now(),
    )
    metadata_path = index_dir / "dense-index.json"
    temporary_metadata_path = index_dir / "dense-index.json.tmp"
    temporary_metadata_path.write_text(metadata.model_dump_json(indent=2), encoding="utf-8")
    temporary_metadata_path.replace(metadata_path)
    return metadata


def load_index_metadata(index_dir: Path) -> DenseIndexMetadata:
    path = index_dir / "dense-index.json"
    return DenseIndexMetadata.model_validate(json.loads(path.read_text(encoding="utf-8")))


class IndexedDenseRetriever:
    """Cosine retrieval over a fingerprint-bound persistent model index."""

    name = "dense-sentence-transformers"

    def __init__(
        self,
        chunks: list[EvidenceChunk],
        index_dir: Path,
        encoder: TextEncoder | None = None,
    ) -> None:
        self.chunks = chunks
        self.metadata = load_index_metadata(index_dir)
        if self.metadata.corpus_fingerprint != corpus_fingerprint(chunks):
            raise ValueError("dense index fingerprint does not match the current corpus")
        if self.metadata.chunk_ids != [chunk.chunk_id for chunk in chunks]:
            raise ValueError("dense index chunk order does not match the current corpus")
        values = array("f")
        values.frombytes((index_dir / "dense-vectors.f32").read_bytes())
        expected = len(chunks) * self.metadata.dimensions
        if len(values) != expected:
            raise ValueError(f"dense vector file has {len(values)} values; expected {expected}")
        self.vectors = [
            values[start : start + self.metadata.dimensions]
            for start in range(0, expected, self.metadata.dimensions)
        ]
        self.encoder = encoder or SentenceTransformerEncoder(
            self.metadata.model_name, local_files_only=True
        )

    def search(self, query: str, top_k: int = 10) -> list[RetrievalResult]:
        encoded = self.encoder.encode([f"{self.metadata.query_prefix}{query}"])
        if len(encoded) != 1 or len(encoded[0]) != self.metadata.dimensions:
            raise ValueError("query encoder output does not match dense index dimensions")
        query_vector = _normalize(encoded[0])
        scored = [
            (index, sum(a * b for a, b in zip(query_vector, vector, strict=True)))
            for index, vector in enumerate(self.vectors)
        ]
        scored = [item for item in scored if item[1] > 0]
        scored.sort(key=lambda item: (-item[1], self.chunks[item[0]].chunk_id))
        return [
            RetrievalResult(
                chunk=self.chunks[index],
                score=score,
                rank=rank,
                retriever=self.name,
                component_scores={self.name: score},
            )
            for rank, (index, score) in enumerate(scored[:top_k], start=1)
        ]
