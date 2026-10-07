from datetime import UTC, datetime

import pytest

from irishclinicalrag.models import EvidenceChunk
from irishclinicalrag.retrieval.index import IndexedDenseRetriever, build_dense_index


class FakeEncoder:
    model_name = "test-encoder"

    def encode(self, texts):
        vectors = []
        for text in texts:
            lowered = text.lower()
            vectors.append(
                [
                    float("antibiotic" in lowered or "prescription" in lowered),
                    float("handover" in lowered),
                    0.1,
                ]
            )
        return vectors


def _chunk(identifier: str, content: str) -> EvidenceChunk:
    import hashlib

    return EvidenceChunk(
        document_id="hse-test",
        chunk_id=identifier,
        source="HSE",
        source_type="clinical_guideline",
        title="Guideline",
        section="Evidence",
        url="https://www.hse.ie/test.pdf",
        retrieved_at=datetime(2026, 10, 7, tzinfo=UTC),
        topic="test",
        content=content,
        content_sha256=hashlib.sha256(content.encode()).hexdigest(),
    )


def test_persistent_dense_index_round_trip(tmp_path) -> None:
    chunks = [
        _chunk("c1", "Review every antibiotic prescription."),
        _chunk("c2", "Use a structured clinical handover."),
    ]

    metadata = build_dense_index(
        chunks,
        tmp_path,
        model_name="test-encoder",
        query_prefix="search: ",
        encoder=FakeEncoder(),
    )
    results = IndexedDenseRetriever(chunks, tmp_path, encoder=FakeEncoder()).search(
        "antibiotic prescription", top_k=1
    )

    assert metadata.dimensions == 3
    assert results[0].chunk.chunk_id == "c1"
    assert results[0].retriever == "dense-sentence-transformers"


def test_dense_index_rejects_changed_corpus(tmp_path) -> None:
    original = [_chunk("c1", "Original evidence")]
    build_dense_index(original, tmp_path, "test-encoder", encoder=FakeEncoder())

    with pytest.raises(ValueError, match="fingerprint"):
        IndexedDenseRetriever([_chunk("c1", "Changed evidence")], tmp_path, encoder=FakeEncoder())
