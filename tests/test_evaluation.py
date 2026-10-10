from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

import irishclinicalrag.evaluation.dataset as dataset_module
import irishclinicalrag.evaluation.runner as runner_module
from irishclinicalrag.evaluation.dataset import build_evaluation_dataset
from irishclinicalrag.evaluation.metrics import ranking_metrics, token_f1
from irishclinicalrag.evaluation.models import EvaluationCase
from irishclinicalrag.evaluation.runner import (
    METHODS,
    load_evaluation_cases,
    run_experiment,
    write_experiment_outputs,
)
from irishclinicalrag.models import EvidenceChunk
from irishclinicalrag.settings import Settings
from irishclinicalrag.storage import write_jsonl


def _chunk(identifier: str, content: str) -> EvidenceChunk:
    return EvidenceChunk(
        document_id="test-guidance",
        chunk_id=identifier,
        source="HSE",
        source_type="clinical_guideline",
        title="Test Irish guidance",
        section="Test section",
        url="https://example.test/guidance.pdf",
        retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
        topic="test topic",
        content=content,
        page_number=1,
        content_sha256="a" * 64,
    )


def _case(identifier: str = "case-001") -> EvaluationCase:
    return EvaluationCase(
        case_id=identifier,
        question="What guidance covers specimen collection before treatment?",
        reference_answer="Collect an appropriate specimen before treatment.",
        expected_chunk_ids=["chunk-relevant"],
        expected_document_ids=["test-guidance"],
        category="test topic",
        difficulty="medium",
        cohort="curated",
        notes="Synthetic unit-test fixture.",
    )


def test_ranking_metrics_use_rank_and_multiple_relevance_labels() -> None:
    metrics = ranking_metrics(["wrong", "right-a", "right-b"], {"right-a", "right-b"}, k=5)

    assert metrics["precision@5"] == pytest.approx(0.4)
    assert metrics["recall@5"] == 1.0
    assert metrics["hit_rate@5"] == 1.0
    assert metrics["mrr"] == 0.5
    assert 0.0 < metrics["ndcg@5"] < 1.0


def test_token_f1_is_order_independent_and_handles_no_overlap() -> None:
    assert token_f1("collect specimen before treatment", "treatment before specimen collect") == 1.0
    assert token_f1("completely unrelated", "specimen collection") == 0.0


def test_evaluation_loader_rejects_duplicate_ids(tmp_path: Path) -> None:
    path = tmp_path / "cases.jsonl"
    write_jsonl(path, [_case(), _case()])

    with pytest.raises(ValueError, match="must be unique"):
        load_evaluation_cases(path)


class _PassThroughReranker:
    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    def rerank(self, query: str, candidates: list, top_k: int = 5) -> list:
        del query
        return candidates[:top_k]


def test_experiment_records_provenance_rag_and_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chunks = [
        _chunk(
            "chunk-relevant",
            "Collect an appropriate microbiological specimen before antimicrobial treatment.",
        ),
        _chunk("chunk-other", "This passage discusses an unrelated administrative process."),
    ]
    cases = [_case()]
    dataset_path = tmp_path / "cases.jsonl"
    write_jsonl(dataset_path, cases)
    monkeypatch.setattr(runner_module, "CrossEncoderReranker", _PassThroughReranker)

    result, predictions = run_experiment(
        cases,
        chunks,
        Settings(),
        tmp_path,
        dataset_path,
        methods=METHODS,
        include_rag=True,
    )

    assert len(predictions) == 4
    assert predictions[0].retrieved_chunk_ids[0] == "chunk-relevant"
    assert result["models"]["dense"] == "hashing-384d-fallback"
    assert len(result["corpus_fingerprint"]) == 64
    assert result["retrieval"]["bm25"]["curated"]["recall@5"] == 1.0
    assert result["rag"]["status"] == "complete"

    output_dir = tmp_path / "results"
    write_experiment_outputs(output_dir, result, predictions)
    assert (output_dir / "metrics.json").exists()
    assert (output_dir / "predictions.jsonl").read_text(encoding="utf-8").count("\n") == 4
    assert "| bm25 | curated |" in (output_dir / "comparison.md").read_text(
        encoding="utf-8"
    )
    assert json.loads(dataset_path.read_text(encoding="utf-8").splitlines()[0])[
        "case_id"
    ] == "case-001"


def _alpha_suffix(number: int) -> str:
    return chr(ord("a") + number // 26) + chr(ord("a") + number % 26)


def test_dataset_builder_combines_reviewed_cases_and_unique_probes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chunks = [
        _chunk(
            f"chunk-{index:03d}",
            "Clinicians should consider "
            f"marker{_alpha_suffix(index)} therapy{_alpha_suffix(index)} "
            f"testing{_alpha_suffix(index)} for this recommendation.",
        )
        for index in range(75)
    ]
    curated = [
        EvaluationCase(
            case_id=f"reviewed-{index:03d}",
            question=f"What does reviewed guidance case {index} recommend?",
            reference_answer="This fixture has a reviewed reference answer.",
            expected_chunk_ids=[chunks[index].chunk_id],
            expected_document_ids=["test-guidance"],
            category="test topic",
            difficulty="medium",
            cohort="curated",
            notes="Synthetic unit-test fixture.",
        )
        for index in range(25)
    ]
    curated_path = tmp_path / "curated.jsonl"
    output_path = tmp_path / "questions.jsonl"
    write_jsonl(curated_path, curated)
    monkeypatch.setattr(dataset_module, "PROBE_COUNTS", {"test-guidance": 75})

    cases = build_evaluation_dataset(chunks, curated_path, output_path)

    assert len(cases) == 100
    assert sum(case.cohort == "curated" for case in cases) == 25
    probe_questions = [case.question for case in cases if case.cohort == "synthetic_probe"]
    assert len(probe_questions) == len(set(probe_questions)) == 75
    assert len(load_evaluation_cases(output_path)) == 100
