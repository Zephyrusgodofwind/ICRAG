"""Reproducible experiment runner for the required retrieval matrix and grounded RAG."""

from __future__ import annotations

import hashlib
import json
import statistics
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from irishclinicalrag.evaluation.metrics import (
    grounded_answer_metrics,
    mean_metrics,
    ranking_metrics,
)
from irishclinicalrag.evaluation.models import EvaluationCase, RetrievalPrediction
from irishclinicalrag.generation.service import answer_from_evidence
from irishclinicalrag.models import EvidenceChunk, RetrievalMetadata, RetrievalResult
from irishclinicalrag.reranking.cross_encoder import CrossEncoderReranker
from irishclinicalrag.retrieval.bm25 import BM25Retriever
from irishclinicalrag.retrieval.dense import HashingDenseRetriever
from irishclinicalrag.retrieval.hybrid import HybridRetriever
from irishclinicalrag.retrieval.index import IndexedDenseRetriever, load_index_metadata
from irishclinicalrag.settings import Settings
from irishclinicalrag.storage import read_jsonl
from irishclinicalrag.validation.corpus import corpus_fingerprint

METHODS = ("bm25", "dense", "hybrid", "hybrid-rerank")


def load_evaluation_cases(path: Path) -> list[EvaluationCase]:
    cases = read_jsonl(path, EvaluationCase)
    identifiers = [case.case_id for case in cases]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("evaluation case IDs must be unique")
    return cases


def _git_commit() -> str:
    try:
        workspace = Path.cwd().resolve().as_posix()
        result = subprocess.run(
            ["git", "-c", f"safe.directory={workspace}", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, math_ceil(percentile * len(ordered)) - 1)
    return ordered[max(index, 0)]


def math_ceil(value: float) -> int:
    integer = int(value)
    return integer if value == integer else integer + 1


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


class EvaluationRunner:
    def __init__(self, chunks: list[EvidenceChunk], settings: Settings, data_dir: Path) -> None:
        self.chunks = chunks
        self.settings = settings
        self.sparse = BM25Retriever(chunks)
        index_dir = data_dir / "index"
        self.dense = (
            IndexedDenseRetriever(chunks, index_dir)
            if (index_dir / "dense-index.json").exists()
            else HashingDenseRetriever(chunks, settings.retrieval.dense_dimensions)
        )
        self.hybrid = HybridRetriever(
            [self.sparse, self.dense], rrf_k=settings.retrieval.rrf_k
        )
        self.reranker = CrossEncoderReranker(
            settings.reranking.model,
            batch_size=settings.reranking.batch_size,
            local_files_only=True,
        )

    def search(self, method: str, query: str) -> tuple[list[RetrievalResult], float, int]:
        started = time.perf_counter()
        if method == "bm25":
            evidence = self.sparse.search(query, top_k=self.settings.retrieval.top_k_final)
            candidate_count = len(evidence)
        elif method == "dense":
            evidence = self.dense.search(query, top_k=self.settings.retrieval.top_k_final)
            candidate_count = len(evidence)
        elif method == "hybrid":
            evidence = self.hybrid.search(
                query,
                top_k=self.settings.retrieval.top_k_final,
                candidate_k=self.settings.retrieval.top_k_initial,
            )
            candidate_count = len(evidence)
        elif method == "hybrid-rerank":
            candidates = self.hybrid.search(
                query,
                top_k=self.settings.reranking.candidate_k,
                candidate_k=self.settings.reranking.candidate_k,
            )
            candidate_count = len(candidates)
            evidence = self.reranker.rerank(
                query, candidates, top_k=self.settings.reranking.top_k
            )
        else:
            raise ValueError(f"unknown evaluation method: {method}")
        return evidence, (time.perf_counter() - started) * 1000, candidate_count


def _cohort_summary(
    cases: list[EvaluationCase], predictions: list[RetrievalPrediction], k: int
) -> dict[str, float | int]:
    prediction_by_id = {prediction.case_id: prediction for prediction in predictions}
    chunk_rows = []
    source_rows = []
    latencies = []
    for case in cases:
        prediction = prediction_by_id[case.case_id]
        chunk_rows.append(
            ranking_metrics(
                prediction.retrieved_chunk_ids,
                set(case.expected_chunk_ids),
                k=k,
            )
        )
        source_rows.append(
            ranking_metrics(
                _unique(prediction.retrieved_document_ids),
                set(case.expected_document_ids),
                k=k,
            )
        )
        latencies.append(prediction.latency_ms)
    chunk_metrics = mean_metrics(chunk_rows)
    source_metrics = {
        f"source_{key}": value for key, value in mean_metrics(source_rows).items()
    }
    return {
        "case_count": len(cases),
        **chunk_metrics,
        **source_metrics,
        "latency_mean_ms": statistics.fmean(latencies) if latencies else 0.0,
        "latency_median_ms": statistics.median(latencies) if latencies else 0.0,
        "latency_p95_ms": _percentile(latencies, 0.95),
    }


def run_experiment(
    cases: list[EvaluationCase],
    chunks: list[EvidenceChunk],
    settings: Settings,
    data_dir: Path,
    dataset_path: Path,
    methods: tuple[str, ...] = METHODS,
    include_rag: bool = True,
) -> tuple[dict[str, object], list[RetrievalPrediction]]:
    if not cases:
        raise ValueError("evaluation dataset is empty")
    unknown_methods = sorted(set(methods) - set(METHODS))
    if unknown_methods:
        raise ValueError(f"unknown evaluation methods: {', '.join(unknown_methods)}")
    runner = EvaluationRunner(chunks, settings, data_dir)
    all_predictions: list[RetrievalPrediction] = []
    method_summaries: dict[str, object] = {}
    evidence_by_case: dict[str, list[RetrievalResult]] = {}

    for method in methods:
        # Keep model-loading and one-time initialization out of per-query latency.
        runner.search(method, cases[0].question)
        predictions: list[RetrievalPrediction] = []
        for case in cases:
            evidence, latency_ms, _ = runner.search(method, case.question)
            prediction = RetrievalPrediction(
                case_id=case.case_id,
                method=method,
                retrieved_chunk_ids=[item.chunk.chunk_id for item in evidence],
                retrieved_document_ids=[item.chunk.document_id for item in evidence],
                scores=[item.score for item in evidence],
                latency_ms=latency_ms,
            )
            predictions.append(prediction)
            if method == "hybrid-rerank":
                evidence_by_case[case.case_id] = evidence
        all_predictions.extend(predictions)
        curated = [case for case in cases if case.cohort == "curated"]
        probes = [case for case in cases if case.cohort == "synthetic_probe"]
        method_summaries[method] = {
            "all": _cohort_summary(cases, predictions, settings.retrieval.top_k_final),
            "curated": _cohort_summary(curated, predictions, settings.retrieval.top_k_final),
            "synthetic_probe": _cohort_summary(
                probes, predictions, settings.retrieval.top_k_final
            ),
        }

    rag_summary: dict[str, object] = {"status": "not_run"}
    if include_rag:
        if "hybrid-rerank" not in methods:
            raise ValueError("RAG evaluation requires the hybrid-rerank method")
        rag_rows = []
        for case in (item for item in cases if item.cohort == "curated"):
            evidence = evidence_by_case[case.case_id]
            response = answer_from_evidence(
                case.question,
                evidence,
                RetrievalMetadata(
                    method="hybrid-rrf+cross-encoder",
                    candidates=settings.reranking.candidate_k,
                    returned=len(evidence),
                    latency_ms=0,
                ),
            )
            metrics = grounded_answer_metrics(response, case.reference_answer)
            metrics["expected_source_cited"] = float(
                any(
                    citation.chunk_id in case.expected_chunk_ids
                    or evidence_item.chunk.document_id in case.expected_document_ids
                    for citation in response.citations
                    for evidence_item in evidence
                    if evidence_item.chunk.chunk_id == citation.chunk_id
                )
            )
            rag_rows.append(metrics)
        rag_summary = {
            "status": "complete",
            "cohort": "curated",
            "case_count": len(rag_rows),
            "metrics": mean_metrics(rag_rows),
            "judge": "deterministic checks only; no LLM-as-judge",
        }

    dataset_bytes = dataset_path.read_bytes()
    index_path = data_dir / "index" / "dense-index.json"
    index_metadata = load_index_metadata(data_dir / "index") if index_path.exists() else None
    result: dict[str, object] = {
        "schema_version": 1,
        "experiment": "day4-retrieval-and-grounded-rag",
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "git_commit": _git_commit(),
        "dataset": {
            "path": dataset_path.as_posix(),
            "sha256": hashlib.sha256(dataset_bytes).hexdigest(),
            "case_count": len(cases),
            "curated_count": sum(case.cohort == "curated" for case in cases),
            "synthetic_probe_count": sum(case.cohort == "synthetic_probe" for case in cases),
        },
        "corpus_fingerprint": (
            index_metadata.corpus_fingerprint
            if index_metadata is not None
            else corpus_fingerprint(chunks)
        ),
        "models": {
            "dense": (
                index_metadata.model_name
                if index_metadata is not None
                else f"hashing-{settings.retrieval.dense_dimensions}d-fallback"
            ),
            "reranker": settings.reranking.model,
            "generation": "extractive-evidence-baseline",
        },
        "parameters": {
            "top_k": settings.retrieval.top_k_final,
            "candidate_k": settings.reranking.candidate_k,
            "rrf_k": settings.retrieval.rrf_k,
            "chunk_target_tokens": settings.chunking.target_tokens,
            "chunk_overlap_tokens": settings.chunking.overlap_tokens,
            "chunk_minimum_tokens": settings.chunking.minimum_tokens,
            "prompt_version": "extractive-evidence-v1",
            "warmup_queries_per_method": 1,
            "latency_scope": "warm query execution; model loading excluded",
        },
        "retrieval": method_summaries,
        "rag": rag_summary,
        "limitations": [
            "Synthetic probes are easier than the separately reported curated questions.",
            "Relevance labels are sparse and may not enumerate every acceptable chunk.",
            "RAG metrics are deterministic grounding checks, not clinical correctness ratings.",
            "No LLM-as-judge or clinician review is represented in these results.",
        ],
    }
    return result, all_predictions


def write_experiment_outputs(
    output_dir: Path,
    result: dict[str, object],
    predictions: list[RetrievalPrediction],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "metrics.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    with (output_dir / "predictions.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for prediction in predictions:
            handle.write(prediction.model_dump_json() + "\n")
    (output_dir / "comparison.md").write_text(_comparison_markdown(result), encoding="utf-8")


def _comparison_markdown(result: dict[str, object]) -> str:
    retrieval = result["retrieval"]
    assert isinstance(retrieval, dict)
    lines = [
        "# Day 4 retrieval comparison\n",
        "Metrics are measured on the committed dataset. See `metrics.json` for full precision, "
        "source-recall, latency, cohort, model, and limitation details.\n",
        "| Method | Cohort | Recall@5 | MRR | nDCG@5 | Source recall@5 | Median latency (ms) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for method, cohorts in retrieval.items():
        assert isinstance(cohorts, dict)
        for cohort in ("curated", "all"):
            metrics = cohorts[cohort]
            assert isinstance(metrics, dict)
            lines.append(
                f"| {method} | {cohort} | {metrics['recall@5']:.3f} | "
                f"{metrics['mrr']:.3f} | {metrics['ndcg@5']:.3f} | "
                f"{metrics['source_recall@5']:.3f} | {metrics['latency_median_ms']:.1f} |"
            )
    lines.append("\nThese results do not establish clinical validity or medical correctness.\n")
    return "\n".join(lines)
