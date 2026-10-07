from datetime import UTC, datetime

import pytest

from irishclinicalrag.models import EvidenceChunk
from irishclinicalrag.pipeline import retrieve
from irishclinicalrag.retrieval.bm25 import BM25Retriever
from irishclinicalrag.retrieval.dense import HashingDenseRetriever
from irishclinicalrag.retrieval.hybrid import HybridRetriever
from irishclinicalrag.settings import Settings


def _chunk(identifier: str, content: str) -> EvidenceChunk:
    return EvidenceChunk(
        document_id="hse-test-guideline",
        chunk_id=identifier,
        source="HSE",
        source_type="clinical_guideline",
        title="Test Guideline",
        section="Recommendations",
        url="https://www.hse.ie/test.pdf",
        retrieved_at=datetime(2026, 10, 7, tzinfo=UTC),
        topic="antimicrobial stewardship",
        content=content,
        content_sha256="b" * 64,
    )


def test_hybrid_retrieval_returns_relevant_chunk_with_provenance() -> None:
    chunks = [
        _chunk("c1", "Antimicrobial stewardship requires review of antibiotic prescriptions."),
        _chunk("c2", "Clinical handover should use structured communication."),
    ]
    hybrid = HybridRetriever([BM25Retriever(chunks), HashingDenseRetriever(chunks)])

    results = hybrid.search("How should antibiotic prescriptions be reviewed?", top_k=2)

    assert results[0].chunk.chunk_id == "c1"
    assert results[0].chunk.source == "HSE"
    assert str(results[0].chunk.url).startswith("https://www.hse.ie/")
    assert "bm25_raw" in results[0].component_scores


def test_empty_retrieval_returns_no_evidence() -> None:
    chunks = [_chunk("c1", "structured clinical handover")]
    hybrid = HybridRetriever([BM25Retriever(chunks), HashingDenseRetriever(chunks)])

    assert hybrid.search("zzzxxyy unmatched", top_k=5) == []


@pytest.mark.parametrize(
    ("method", "expected"),
    [("bm25", "bm25"), ("dense", "dense-hashing"), ("hybrid", "hybrid-rrf")],
)
def test_pipeline_keeps_retrieval_paths_independently_selectable(
    tmp_path, method: str, expected: str
) -> None:
    response = retrieve(
        "antibiotic prescription review",
        [_chunk("c1", "Review each antibiotic prescription.")],
        Settings(),
        data_dir=tmp_path,
        method=method,
    )

    assert response.retrieval_metadata.method == expected
    assert response.evidence[0].chunk.chunk_id == "c1"
    if method == "bm25":
        assert response.retrieval_metadata.parameters["dense_backend"] is None


def test_pipeline_rejects_unknown_retrieval_method(tmp_path) -> None:
    with pytest.raises(ValueError, match="unknown retrieval method"):
        retrieve("question", [_chunk("c1", "evidence")], Settings(), tmp_path, "unknown")
