"""Dependency-free retrieval and deterministic grounded-answer metrics."""

from __future__ import annotations

import math
import re
from collections import Counter

from irishclinicalrag.citations.verification import (
    verify_answer_citations,
    verify_citations,
)
from irishclinicalrag.models import AnswerResponse
from irishclinicalrag.retrieval.text import normalize_tokens


def ranking_metrics(retrieved: list[str], relevant: set[str], k: int = 5) -> dict[str, float]:
    if not relevant:
        raise ValueError("ranking metrics require at least one relevant identifier")
    top_k = retrieved[:k]
    hits = [1 if identifier in relevant else 0 for identifier in top_k]
    hit_count = sum(hits)
    reciprocal_rank = next((1.0 / rank for rank, hit in enumerate(hits, 1) if hit), 0.0)
    dcg = sum(hit / math.log2(rank + 1) for rank, hit in enumerate(hits, 1))
    ideal_hits = min(len(relevant), k)
    ideal_dcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    return {
        f"precision@{k}": hit_count / k,
        f"recall@{k}": hit_count / len(relevant),
        f"hit_rate@{k}": float(hit_count > 0),
        "mrr": reciprocal_rank,
        f"ndcg@{k}": dcg / ideal_dcg if ideal_dcg else 0.0,
    }


def mean_metrics(rows: list[dict[str, float]]) -> dict[str, float]:
    if not rows:
        return {}
    keys = rows[0]
    return {key: sum(row[key] for row in rows) / len(rows) for key in keys}


def token_f1(candidate: str, reference: str) -> float:
    candidate_tokens = Counter(normalize_tokens(candidate))
    reference_tokens = Counter(normalize_tokens(reference))
    if not candidate_tokens or not reference_tokens:
        return 0.0
    overlap = sum((candidate_tokens & reference_tokens).values())
    if not overlap:
        return 0.0
    precision = overlap / sum(candidate_tokens.values())
    recall = overlap / sum(reference_tokens.values())
    return 2 * precision * recall / (precision + recall)


def extractive_faithfulness(response: AnswerResponse) -> float:
    """Check whether each cited paragraph is copied from its mapped evidence passage."""
    if not response.answer.strip() or not response.citations:
        return 0.0
    citation_by_id = {citation.citation_id: citation for citation in response.citations}
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", response.answer) if part.strip()]
    supported = 0
    for paragraph in paragraphs:
        ids = [f"[{value}]" for value in re.findall(r"\[(\d+)\]", paragraph)]
        claim = re.sub(r"\s*\[\d+\]\s*", " ", paragraph).strip().removesuffix("...")
        normalized_claim = " ".join(claim.split())
        if ids and all(
            identifier in citation_by_id
            and normalized_claim in " ".join(citation_by_id[identifier].passage.split())
            for identifier in ids
        ):
            supported += 1
    return supported / len(paragraphs) if paragraphs else 0.0


def grounded_answer_metrics(response: AnswerResponse, reference_answer: str) -> dict[str, float]:
    return {
        "evidence_sufficient": float(response.evidence_sufficient),
        "citation_correctness": float(verify_citations(response.citations, response.evidence)),
        "citation_completeness": float(
            verify_answer_citations(response.answer, response.citations)
        ),
        "extractive_faithfulness": extractive_faithfulness(response),
        "reference_token_f1": token_f1(response.answer, reference_answer),
    }
