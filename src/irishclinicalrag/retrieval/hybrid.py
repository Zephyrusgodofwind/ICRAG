"""Reciprocal-rank fusion across independently testable retrievers."""

from __future__ import annotations

from collections import defaultdict
from typing import Protocol

from irishclinicalrag.models import EvidenceChunk, RetrievalResult


class Retriever(Protocol):
    name: str

    def search(self, query: str, top_k: int = 10) -> list[RetrievalResult]: ...


class HybridRetriever:
    name = "hybrid-rrf"

    def __init__(self, retrievers: list[Retriever], rrf_k: int = 60) -> None:
        if len(retrievers) < 2:
            raise ValueError("hybrid retrieval requires at least two retrievers")
        self.retrievers = retrievers
        self.rrf_k = rrf_k

    def search(self, query: str, top_k: int = 5, candidate_k: int = 20) -> list[RetrievalResult]:
        scores: defaultdict[str, float] = defaultdict(float)
        components: defaultdict[str, dict[str, float]] = defaultdict(dict)
        chunks: dict[str, EvidenceChunk] = {}
        for retriever in self.retrievers:
            for result in retriever.search(query, top_k=candidate_k):
                chunk_id = result.chunk.chunk_id
                chunks[chunk_id] = result.chunk
                scores[chunk_id] += 1.0 / (self.rrf_k + result.rank)
                components[chunk_id][f"{retriever.name}_raw"] = result.score
                components[chunk_id][f"{retriever.name}_rank"] = float(result.rank)

        ordered = sorted(scores, key=lambda key: (-scores[key], key))
        return [
            RetrievalResult(
                chunk=chunks[chunk_id],
                score=scores[chunk_id],
                rank=rank,
                retriever=self.name,
                component_scores=components[chunk_id],
            )
            for rank, chunk_id in enumerate(ordered[:top_k], start=1)
        ]

