"""Build the versioned Day 4 evaluation set from reviewed cases and corpus probes."""

from __future__ import annotations

import math
from collections import Counter
from pathlib import Path

from irishclinicalrag.evaluation.models import EvaluationCase
from irishclinicalrag.models import EvidenceChunk
from irishclinicalrag.retrieval.text import normalize_tokens
from irishclinicalrag.storage import read_jsonl, write_jsonl

PROBE_COUNTS = {
    "hse-amric-ams-guidance-v1-2022": 19,
    "hse-community-cap-adults-v2-2024": 5,
    "hse-infective-copd-exacerbation-v2-2024": 3,
    "hse-uncomplicated-uti-female-v2-2-2025": 3,
    "hse-c-difficile-v2-2023": 7,
    "hse-penicillin-cephalosporin-allergy-v2-2026": 7,
    "ncec-ipc-guideline-30-volume-1-2025": 19,
    "ncec-ipc-guideline-30-volume-2-2025": 12,
}

_STOP_WORDS = {
    "about",
    "after",
    "also",
    "been",
    "before",
    "being",
    "between",
    "could",
    "document",
    "during",
    "from",
    "guidance",
    "guideline",
    "have",
    "health",
    "healthcare",
    "into",
    "ireland",
    "irish",
    "more",
    "national",
    "other",
    "page",
    "people",
    "recommendation",
    "service",
    "should",
    "their",
    "there",
    "these",
    "they",
    "this",
    "those",
    "through",
    "under",
    "used",
    "using",
    "were",
    "when",
    "where",
    "which",
    "with",
    "within",
    "would",
}


def _document_frequencies(chunks: list[EvidenceChunk]) -> Counter[str]:
    frequencies: Counter[str] = Counter()
    for chunk in chunks:
        frequencies.update(set(normalize_tokens(chunk.content)))
    return frequencies


def _probe_terms(
    chunk: EvidenceChunk, frequencies: Counter[str], corpus_size: int
) -> list[str]:
    counts = Counter(
        token
        for token in normalize_tokens(chunk.content)
        if len(token) >= 5 and token.isalpha() and token not in _STOP_WORDS
    )
    ranked = sorted(
        counts,
        key=lambda token: (
            -(1 + math.log(counts[token]))
            * math.log((corpus_size + 1) / (frequencies[token] + 1)),
            token,
        ),
    )
    return ranked[:3]


def _candidate_score(chunk: EvidenceChunk, terms: list[str]) -> tuple[int, int, str]:
    content = chunk.content.casefold()
    recommendation_terms = sum(
        content.count(token)
        for token in (" should ", " recommend", " must ", " avoid ", " consider ")
    )
    return recommendation_terms, len(terms), chunk.chunk_id


def build_evaluation_dataset(
    chunks: list[EvidenceChunk], curated_path: Path, output_path: Path
) -> list[EvaluationCase]:
    """Combine 25 reviewed cases with 75 deterministic source-grounded probes."""
    curated = read_jsonl(curated_path, EvaluationCase)
    if len(curated) != 25 or any(case.cohort != "curated" for case in curated):
        raise ValueError("curated evaluation seed must contain exactly 25 curated cases")

    chunk_ids = {chunk.chunk_id for chunk in chunks}
    missing = sorted(
        expected
        for case in curated
        for expected in case.expected_chunk_ids
        if expected not in chunk_ids
    )
    if missing:
        raise ValueError(f"curated labels are absent from the corpus: {', '.join(missing)}")

    frequencies = _document_frequencies(chunks)
    by_document: dict[str, list[tuple[EvidenceChunk, list[str]]]] = {}
    for chunk in chunks:
        terms = _probe_terms(chunk, frequencies, len(chunks))
        if len(terms) == 3 and "table of contents" not in chunk.content.casefold():
            by_document.setdefault(chunk.document_id, []).append((chunk, terms))

    probes: list[EvaluationCase] = []
    for document_id, target_count in PROBE_COUNTS.items():
        candidates = sorted(
            by_document.get(document_id, []),
            key=lambda item: _candidate_score(item[0], item[1]),
            reverse=True,
        )
        selected: list[tuple[EvidenceChunk, list[str]]] = []
        term_signatures: set[tuple[str, ...]] = set()
        for candidate in candidates:
            signature = tuple(candidate[1])
            if signature in term_signatures:
                continue
            term_signatures.add(signature)
            selected.append(candidate)
            if len(selected) == target_count:
                break
        if len(selected) != target_count:
            raise ValueError(
                f"{document_id} has {len(selected)} usable probe chunks; "
                f"{target_count} required"
            )
        for ordinal, (chunk, terms) in enumerate(
            sorted(selected, key=lambda item: item[0].chunk_id), start=1
        ):
            joined_terms = ", ".join(terms[:-1]) + f", and {terms[-1]}"
            probes.append(
                EvaluationCase(
                    case_id=f"probe-{len(probes) + 1:03d}",
                    question=(
                        "Which passage in the indexed Irish guidance discusses "
                        f"{joined_terms}?"
                    ),
                    reference_answer=(
                        f"The expected passage discusses {joined_terms} in the cited guidance."
                    ),
                    expected_chunk_ids=[chunk.chunk_id],
                    expected_document_ids=[chunk.document_id],
                    category=chunk.topic,
                    difficulty="easy",
                    cohort="synthetic_probe",
                    notes=(
                        "Deterministic lexical probe generated from one source chunk; "
                        f"document probe {ordinal}/{target_count}."
                    ),
                )
            )

    cases = curated + probes
    if len(cases) != 100:
        raise AssertionError(f"evaluation dataset must contain 100 cases, got {len(cases)}")
    if len({case.case_id for case in cases}) != len(cases):
        raise ValueError("evaluation case IDs must be unique")
    write_jsonl(output_path, cases)
    return cases
