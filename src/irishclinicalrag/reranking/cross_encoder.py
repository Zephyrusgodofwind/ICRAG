"""Cross-encoder reranking with lazy, local-first model loading."""

from __future__ import annotations

from collections.abc import Sequence
from functools import lru_cache
from typing import Protocol

from irishclinicalrag.models import RetrievalResult


class PairScorer(Protocol):
    name: str

    def score(self, query: str, passages: Sequence[str]) -> list[float]: ...


@lru_cache(maxsize=4)
def _load_cross_encoder(model_name: str, local_files_only: bool):
    try:
        from sentence_transformers import CrossEncoder
    except ImportError as exc:  # pragma: no cover - optional installation
        raise RuntimeError(
            'Cross-encoder reranking requires: pip install -e ".[ml]"'
        ) from exc
    if local_files_only:
        return CrossEncoder(model_name, local_files_only=True)
    try:
        return CrossEncoder(model_name, local_files_only=True)
    except OSError:
        return CrossEncoder(model_name, local_files_only=False)


class SentenceTransformerPairScorer:
    def __init__(
        self,
        model_name: str,
        batch_size: int = 16,
        local_files_only: bool = False,
    ) -> None:
        self.name = model_name
        self.model_name = model_name
        self.batch_size = batch_size
        self.local_files_only = local_files_only

    def score(self, query: str, passages: Sequence[str]) -> list[float]:
        if not passages:
            return []
        model = _load_cross_encoder(self.model_name, self.local_files_only)
        scores = model.predict(
            [(query, passage) for passage in passages],
            batch_size=self.batch_size,
            show_progress_bar=False,
        )
        return [float(score) for score in scores]


class CrossEncoderReranker:
    """Rerank fused candidates while preserving their complete provenance."""

    name = "cross-encoder"

    def __init__(
        self,
        model_name: str,
        batch_size: int = 16,
        scorer: PairScorer | None = None,
        local_files_only: bool = False,
    ) -> None:
        self.model_name = model_name
        self.scorer = scorer or SentenceTransformerPairScorer(
            model_name,
            batch_size=batch_size,
            local_files_only=local_files_only,
        )

    def rerank(
        self,
        query: str,
        candidates: list[RetrievalResult],
        top_k: int = 5,
    ) -> list[RetrievalResult]:
        if not candidates or top_k < 1:
            return []
        scores = self.scorer.score(query, [item.chunk.content for item in candidates])
        if len(scores) != len(candidates):
            raise ValueError("reranker returned a different number of scores than candidates")
        ordered = sorted(
            zip(candidates, scores, strict=True),
            key=lambda item: (-item[1], item[0].rank, item[0].chunk.chunk_id),
        )
        reranked: list[RetrievalResult] = []
        for rank, (candidate, score) in enumerate(ordered[:top_k], start=1):
            components = dict(candidate.component_scores)
            components["pre_rerank_score"] = candidate.score
            components["pre_rerank_rank"] = float(candidate.rank)
            components["reranker_raw"] = score
            reranked.append(
                RetrievalResult(
                    chunk=candidate.chunk,
                    score=score,
                    rank=rank,
                    retriever=f"{candidate.retriever}+{self.name}",
                    component_scores=components,
                )
            )
        return reranked
