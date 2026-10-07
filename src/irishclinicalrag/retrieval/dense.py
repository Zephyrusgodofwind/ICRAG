"""Dense retrieval interfaces and an offline deterministic vector baseline."""

from __future__ import annotations

import hashlib
import math

from irishclinicalrag.models import EvidenceChunk, RetrievalResult
from irishclinicalrag.retrieval.text import normalize_tokens


class HashingDenseRetriever:
    """Signed feature hashing into dense vectors.

    This is an offline engineering baseline, not a biomedical semantic model. It
    exists so indexing and evaluation are reproducible before model downloads.
    """

    name = "dense-hashing"

    def __init__(self, chunks: list[EvidenceChunk], dimensions: int = 384) -> None:
        if dimensions < 16:
            raise ValueError("dimensions must be at least 16")
        self.chunks = chunks
        self.dimensions = dimensions
        self.vectors = [self.embed(chunk.content) for chunk in chunks]

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        terms = normalize_tokens(text)
        features = terms + [f"{a}_{b}" for a, b in zip(terms, terms[1:], strict=False)]
        for feature in features:
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            number = int.from_bytes(digest, "little")
            index = number % self.dimensions
            sign = 1.0 if number & 1 else -1.0
            vector[index] += sign
        magnitude = math.sqrt(sum(value * value for value in vector))
        return [value / magnitude for value in vector] if magnitude else vector

    def search(self, query: str, top_k: int = 10) -> list[RetrievalResult]:
        query_vector = self.embed(query)
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
