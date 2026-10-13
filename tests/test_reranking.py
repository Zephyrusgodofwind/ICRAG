from datetime import UTC, datetime

import pytest

from irishclinicalrag.models import EvidenceChunk, RetrievalResult
from irishclinicalrag.pipeline import RetrievalEngine
from irishclinicalrag.reranking.cross_encoder import CrossEncoderReranker
from irishclinicalrag.settings import Settings


class KeywordScorer:
    name = "keyword-test-scorer"

    def score(self, query, passages):
        del query
        return [2.0 if "specific recommendation" in passage else -1.0 for passage in passages]


class BrokenScorer:
    name = "broken"

    def score(self, query, passages):
        del query, passages
        return []


class UnavailableScorer:
    name = "unavailable"

    def score(self, query, passages):
        del query, passages
        raise RuntimeError("model unavailable")


def _result(identifier: str, content: str, rank: int) -> RetrievalResult:
    chunk = EvidenceChunk(
        document_id="hse-test",
        chunk_id=identifier,
        source="HSE",
        source_type="clinical_guideline",
        title="Guideline",
        section="Recommendations",
        url="https://www.hse.ie/test.pdf",
        retrieved_at=datetime(2026, 10, 7, tzinfo=UTC),
        topic="test",
        content=content,
        content_sha256="a" * 64,
    )
    return RetrievalResult(
        chunk=chunk,
        score=1 / (60 + rank),
        rank=rank,
        retriever="hybrid-rrf",
        component_scores={"bm25_rank": float(rank)},
    )


def test_cross_encoder_reranks_and_preserves_provenance() -> None:
    candidates = [
        _result("c1", "Broad background.", 1),
        _result("c2", "The specific recommendation is here.", 2),
    ]
    reranker = CrossEncoderReranker("test-model", scorer=KeywordScorer())

    results = reranker.rerank("What is recommended?", candidates, top_k=2)

    assert results[0].chunk.chunk_id == "c2"
    assert results[0].chunk.url == candidates[1].chunk.url
    assert results[0].retriever == "hybrid-rrf+cross-encoder"
    assert results[0].component_scores["pre_rerank_rank"] == 2
    assert results[0].component_scores["reranker_raw"] == 2


def test_cross_encoder_rejects_misaligned_scores() -> None:
    reranker = CrossEncoderReranker("test-model", scorer=BrokenScorer())

    with pytest.raises(ValueError, match="different number"):
        reranker.rerank("question", [_result("c1", "evidence", 1)])


def test_cross_encoder_handles_empty_candidates() -> None:
    reranker = CrossEncoderReranker("test-model", scorer=KeywordScorer())

    assert reranker.rerank("question", []) == []


def test_pipeline_falls_back_to_hybrid_when_reranker_is_unavailable(tmp_path) -> None:
    engine = RetrievalEngine(
        [_result("c1", "A specific recommendation for antibiotic review.", 1).chunk],
        Settings(),
        data_dir=tmp_path,
        method="hybrid-rerank",
    )
    engine.reranker = CrossEncoderReranker("unavailable", scorer=UnavailableScorer())

    first = engine.retrieve("specific recommendation antibiotic review")
    second = engine.retrieve("specific recommendation antibiotic review")

    assert first.retrieval_metadata.method == "hybrid-rrf+reranker-fallback"
    assert first.retrieval_metadata.parameters["reranker_fallback_used"] is True
    assert first.retrieval_metadata.parameters["reranker_fallback_reason"] == "model_unavailable"
    assert first.evidence[0].retriever == "hybrid-rrf"
    assert second.retrieval_metadata.method == "hybrid-rrf+reranker-fallback"
