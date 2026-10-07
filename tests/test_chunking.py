from datetime import UTC, datetime

from irishclinicalrag.chunking.semantic import chunk_sections
from irishclinicalrag.models import ManifestRecord, ParsedSection, SourceDocument
from irishclinicalrag.settings import ChunkingSettings


def test_chunking_is_deterministic_and_preserves_metadata() -> None:
    source = SourceDocument(
        document_id="hse-test-guideline",
        source="HSE",
        source_type="clinical_guideline",
        title="Test Guideline",
        url="https://www.hse.ie/test.pdf",
        topic="testing",
    )
    manifest = ManifestRecord(
        document_id=source.document_id,
        source_url=source.url,
        sha256="a" * 64,
        retrieved_at=datetime(2026, 10, 7, tzinfo=UTC),
        media_type="application/pdf",
        raw_path="data/raw/test.pdf",
        byte_count=100,
    )
    sections = [
        ParsedSection(
            heading="Recommendations",
            page_number=3,
            content="First evidence paragraph.\n\nSecond evidence paragraph with details.",
        )
    ]
    settings = ChunkingSettings(target_tokens=8, overlap_tokens=2, minimum_tokens=1)

    first = chunk_sections(source, manifest, sections, settings)
    second = chunk_sections(source, manifest, sections, settings)

    assert [chunk.chunk_id for chunk in first] == [chunk.chunk_id for chunk in second]
    assert first[0].source == "HSE"
    assert first[0].page_number == 3
    assert str(first[0].url) == "https://www.hse.ie/test.pdf"

