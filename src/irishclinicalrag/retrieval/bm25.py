"""Dependency-free Okapi BM25 baseline."""

from __future__ import annotations

import math
from collections import Counter

from irishclinicalrag.models import EvidenceChunk, RetrievalResult
from irishclinicalrag.retrieval.text import normalize_tokens


class BM25Retriever:
    name = "bm25"

    def __init__(self, chunks: list[EvidenceChunk], k1: float = 1.5, b: float = 0.75) -> None:
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self.documents = [normalize_tokens(chunk.content) for chunk in chunks]
        self.lengths = [len(document) for document in self.documents]
        self.average_length = sum(self.lengths) / max(len(self.lengths), 1)
        self.term_frequencies = [Counter(document) for document in self.documents]
        document_frequency: Counter[str] = Counter()
        for document in self.documents:
            document_frequency.update(set(document))
        count = len(self.documents)
        self.idf = {
            term: math.log(1 + (count - frequency + 0.5) / (frequency + 0.5))
            for term, frequency in document_frequency.items()
        }

    def search(self, query: str, top_k: int = 10) -> list[RetrievalResult]:
        query_terms = normalize_tokens(query)
        scored: list[tuple[int, float]] = []
        for index, frequencies in enumerate(self.term_frequencies):
            length_norm = 1 - self.b + self.b * self.lengths[index] / max(self.average_length, 1)
            score = 0.0
            for term in query_terms:
                frequency = frequencies.get(term, 0)
                if not frequency:
                    continue
                score += self.idf.get(term, 0.0) * (
                    frequency * (self.k1 + 1) / (frequency + self.k1 * length_norm)
                )
            if score > 0:
                scored.append((index, score))
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

