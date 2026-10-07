from datetime import UTC, datetime

from irishclinicalrag.models import EvidenceChunk
from irishclinicalrag.storage import read_jsonl, write_jsonl


def test_jsonl_round_trip_preserves_contract(tmp_path) -> None:
    chunk = EvidenceChunk(
        document_id="hse-test-guideline",
        chunk_id="chunk-1",
        source="HSE",
        source_type="clinical_guideline",
        title="Test Guideline",
        section="Scope",
        url="https://www.hse.ie/test.pdf",
        retrieved_at=datetime(2026, 10, 7, tzinfo=UTC),
        topic="test",
        content="Evidence content.",
        content_sha256="c" * 64,
    )
    path = tmp_path / "chunks.jsonl"

    assert write_jsonl(path, [chunk]) == 1
    loaded = read_jsonl(path, EvidenceChunk)

    assert loaded == [chunk]

