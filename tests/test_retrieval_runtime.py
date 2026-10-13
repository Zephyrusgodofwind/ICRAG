import json
from datetime import UTC, datetime
from pathlib import Path

from irishclinicalrag.models import EvidenceChunk
from irishclinicalrag.retrieval.runtime import RetrievalRuntime
from irishclinicalrag.storage import write_jsonl


def _runtime(tmp_path) -> tuple[RetrievalRuntime, Path]:
    data_dir = tmp_path / "data"
    chunk = EvidenceChunk(
        document_id="hse-runtime-test",
        chunk_id="hse-runtime-test:1",
        source="HSE",
        source_type="clinical_guideline",
        title="Runtime guideline",
        section="Recommendation",
        url="https://www.hse.ie/runtime-test.pdf",
        retrieved_at=datetime(2026, 10, 13, tzinfo=UTC),
        topic="antimicrobial stewardship",
        content="Review each antimicrobial prescription and document the review date.",
        content_sha256="a" * 64,
    )
    write_jsonl(data_dir / "chunks" / "chunks.jsonl", [chunk])
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({}), encoding="utf-8")
    return RetrievalRuntime(data_dir, config_path), config_path


def test_runtime_reuses_public_corpus_components_without_caching_queries(tmp_path) -> None:
    runtime, _ = _runtime(tmp_path)

    first = runtime.retrieve("Should prescriptions be reviewed?")
    second = runtime.retrieve("When should the review date be documented?")

    assert first.component_cache_hit is False
    assert second.component_cache_hit is True
    assert first.cache_generation == second.cache_generation == 1
    assert first.response.query != second.response.query
    assert second.response.retrieval_metadata.parameters["component_cache_hit"] is True
    assert not hasattr(runtime, "query_cache")


def test_runtime_invalidates_components_when_configuration_changes(tmp_path) -> None:
    runtime, config_path = _runtime(tmp_path)
    first = runtime.retrieve("antimicrobial prescription review")
    config_path.write_text(
        json.dumps({"retrieval": {"top_k_final": 1}}),
        encoding="utf-8",
    )

    second = runtime.retrieve("antimicrobial prescription review")

    assert first.cache_generation == 1
    assert second.component_cache_hit is False
    assert second.cache_generation == 2
    assert second.response.retrieval_metadata.parameters["top_k_final"] == 1


def test_failed_dense_model_warmup_marks_runtime_not_ready(tmp_path, monkeypatch) -> None:
    runtime, _ = _runtime(tmp_path)
    state, _ = runtime.prepare()

    def fail_warmup():
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(state.engine, "warm_models", fail_warmup)

    warm_status = runtime.warm_models()
    health = runtime.health()

    assert warm_status["ready"] is False
    assert warm_status["dense"] == "unavailable"
    assert health["ready"] is False
    assert health["error_code"] == "dense_model_unavailable"
