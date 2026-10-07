from datetime import UTC, datetime

from irishclinicalrag.citations.verification import build_citations, verify_citations
from irishclinicalrag.models import EvidenceChunk, RetrievalResult


def test_citations_map_exactly_to_retrieved_chunks() -> None:
    chunk = EvidenceChunk(
        document_id="hse-test",
        chunk_id="hse-test:1",
        source="HSE",
        source_type="clinical_guideline",
        title="Guideline",
        section="Scope",
        url="https://www.hse.ie/test.pdf",
        retrieved_at=datetime(2026, 10, 7, tzinfo=UTC),
        topic="test",
        content="Exact evidence passage.",
        content_sha256="e" * 64,
    )
    result = RetrievalResult(chunk=chunk, score=0.02, rank=1, retriever="hybrid-rrf")

    citations = build_citations([result])

    assert verify_citations(citations, [result])
    assert citations[0].passage == chunk.content
    assert citations[0].citation_id == "[1]"

