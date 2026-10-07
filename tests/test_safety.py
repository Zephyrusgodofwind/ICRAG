from datetime import UTC, datetime

from irishclinicalrag.generation.service import answer_from_evidence
from irishclinicalrag.models import EvidenceChunk, RetrievalMetadata, RetrievalResult
from irishclinicalrag.safety.policy import assess_evidence, is_emergency_query


def _metadata() -> RetrievalMetadata:
    return RetrievalMetadata(method="hybrid-rrf", candidates=0, returned=0, latency_ms=1)


def test_emergency_language_escalates_without_medical_answer() -> None:
    response = answer_from_evidence("I have chest pain and cannot breathe", [], _metadata())

    assert is_emergency_query("severe chest pain")
    assert response.safety_status == "emergency_escalation"
    assert "112 or 999" in response.answer
    assert response.confidence == 0
    assert response.evidence == []


def test_empty_evidence_abstains() -> None:
    response = answer_from_evidence("What is the recommended treatment?", [], _metadata())

    assert response.safety_status == "insufficient_evidence"
    assert not response.evidence_sufficient
    assert "could not find sufficiently strong evidence" in response.answer
    assert response.citations == []


def test_supported_answer_uses_retrieved_citation() -> None:
    chunk = EvidenceChunk(
        document_id="hse-test",
        chunk_id="hse-test:1",
        source="HSE",
        source_type="clinical_guideline",
        title="Guideline",
        section="Principles",
        url="https://www.hse.ie/test.pdf",
        retrieved_at=datetime(2026, 10, 7, tzinfo=UTC),
        topic="antimicrobial stewardship",
        content="Antimicrobial prescriptions should include a documented review date.",
        content_sha256="d" * 64,
    )
    result = RetrievalResult(chunk=chunk, score=0.03, rank=1, retriever="hybrid-rrf")

    response = answer_from_evidence(
        "Should antimicrobial prescriptions include a documented review date?",
        [result],
        _metadata(),
    )

    assert response.evidence_sufficient
    assert response.citations[0].chunk_id == chunk.chunk_id
    assert "[1]" in response.answer
    assert response.generation_metadata.citations_verified


def test_uncited_provider_output_falls_back_to_extractive_answer() -> None:
    class UnsafeProvider:
        name = "unsafe-test-provider"

        def generate(self, messages, context, citations, **kwargs):
            del messages, context, citations, kwargs
            return "This unsupported medical claim has no citation."

    chunk = EvidenceChunk(
        document_id="hse-test",
        chunk_id="hse-test:1",
        source="HSE",
        source_type="clinical_guideline",
        title="Guideline",
        section="Principles",
        url="https://www.hse.ie/test.pdf",
        retrieved_at=datetime(2026, 10, 7, tzinfo=UTC),
        topic="antimicrobial stewardship",
        content="Antimicrobial prescriptions should include a documented review date.",
        content_sha256="d" * 64,
    )
    result = RetrievalResult(chunk=chunk, score=0.8, rank=1, retriever="cross-encoder")

    response = answer_from_evidence(
        "Should antimicrobial prescriptions include a documented review date?",
        [result],
        _metadata(),
        provider=UnsafeProvider(),
    )

    assert response.generation_metadata.provider == "unsafe-test-provider"
    assert response.generation_metadata.fallback_used
    assert "[1]" in response.answer


def test_negative_reranker_signal_forces_abstention() -> None:
    chunk = EvidenceChunk(
        document_id="hse-test",
        chunk_id="hse-test:irrelevant",
        source="HSE",
        source_type="clinical_guideline",
        title="Unrelated Guideline",
        section="Education",
        url="https://www.hse.ie/test.pdf",
        retrieved_at=datetime(2026, 10, 7, tzinfo=UTC),
        topic="education",
        content="This guidance covers education and professional development.",
        content_sha256="e" * 64,
    )
    result = RetrievalResult(
        chunk=chunk,
        score=-9.2,
        rank=1,
        retriever="hybrid-rrf+cross-encoder",
        component_scores={"reranker_raw": -9.2},
    )

    assessment = assess_evidence("What guidance covers quantum dentistry?", [result])

    assert not assessment.sufficient
    assert assessment.relevance_score == -9.2
