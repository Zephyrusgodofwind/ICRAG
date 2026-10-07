from datetime import UTC, datetime

from irishclinicalrag.models import EvidenceChunk, ManifestRecord, SourceDocument
from irishclinicalrag.validation.corpus import validate_corpus


def _source(document_id: str = "hse-test") -> SourceDocument:
    return SourceDocument(
        document_id=document_id,
        source="HSE",
        source_type="clinical_guideline",
        title="Test Guideline",
        url=f"https://www.hse.ie/{document_id}.pdf",
        topic="test topic",
    )


def _manifest(document_id: str = "hse-test", sha256: str = "a" * 64) -> ManifestRecord:
    return ManifestRecord(
        document_id=document_id,
        source_url=f"https://www.hse.ie/{document_id}.pdf",
        sha256=sha256,
        retrieved_at=datetime(2026, 10, 7, tzinfo=UTC),
        media_type="application/pdf",
        raw_path=f"data/raw/{document_id}/{sha256}.pdf",
        byte_count=100,
        processing_status="processed",
        number_of_chunks=1,
    )


def _chunk(document_id: str = "hse-test", chunk_id: str = "hse-test:0") -> EvidenceChunk:
    import hashlib

    content = "Validated Irish clinical evidence."
    return EvidenceChunk(
        document_id=document_id,
        chunk_id=chunk_id,
        source="HSE",
        source_type="clinical_guideline",
        title="Test Guideline",
        section="Recommendations",
        url=f"https://www.hse.ie/{document_id}.pdf",
        retrieved_at=datetime(2026, 10, 7, tzinfo=UTC),
        topic="test topic",
        content=content,
        content_sha256=hashlib.sha256(content.encode()).hexdigest(),
    )


def test_valid_corpus_has_stable_fingerprint() -> None:
    report = validate_corpus([_source()], [_manifest()], [_chunk()])

    assert report.valid is True
    assert report.document_count == 1
    assert report.chunk_count == 1
    assert len(report.corpus_fingerprint) == 64


def test_validation_rejects_missing_and_duplicate_documents() -> None:
    sources = [_source(), _source()]

    report = validate_corpus(sources, [], [])

    assert report.valid is False
    assert any("duplicate document_id" in error for error in report.errors)
    assert any("without chunks" in error for error in report.errors)


def test_validation_rejects_one_payload_under_two_document_ids() -> None:
    first = _source("hse-first")
    second = _source("hse-second")
    report = validate_corpus(
        [first, second],
        [_manifest("hse-first"), _manifest("hse-second")],
        [_chunk("hse-first", "first:0"), _chunk("hse-second", "second:0")],
    )

    assert report.valid is False
    assert any("share one raw payload" in error for error in report.errors)
