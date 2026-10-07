"""Deterministic safeguards that run outside the generation model."""

from __future__ import annotations

import re
from dataclasses import dataclass

from irishclinicalrag.models import RetrievalResult
from irishclinicalrag.retrieval.text import normalize_tokens

EMERGENCY_PATTERNS = (
    r"\b(can'?t|cannot|unable to) breathe\b",
    r"\bchest pain\b",
    r"\bsevere bleeding\b",
    r"\bunconscious\b",
    r"\bnot breathing\b",
    r"\bsuicid(?:e|al)\b",
    r"\boverdose\b",
    r"\banaphylaxis\b",
    r"\bstroke symptoms?\b",
)

EMERGENCY_MESSAGE = (
    "This may describe a medical emergency. Call 112 or 999 in Ireland now, "
    "or go to the nearest emergency department. Do not rely on this research tool "
    "for emergency assessment or treatment."
)
INSUFFICIENT_MESSAGE = (
    "I could not find sufficiently strong evidence in the indexed Irish clinical "
    "sources to answer this reliably."
)


@dataclass(frozen=True, slots=True)
class EvidenceAssessment:
    sufficient: bool
    confidence: float
    query_coverage: float


def is_emergency_query(query: str) -> bool:
    normalized = " ".join(query.casefold().split())
    return any(re.search(pattern, normalized) for pattern in EMERGENCY_PATTERNS)


def assess_evidence(query: str, results: list[RetrievalResult]) -> EvidenceAssessment:
    query_terms = {term for term in normalize_tokens(query) if len(term) > 2}
    if not results or not query_terms:
        return EvidenceAssessment(sufficient=False, confidence=0.0, query_coverage=0.0)
    evidence_terms = set()
    for result in results[:3]:
        evidence_terms.update(normalize_tokens(result.chunk.content))
    coverage = len(query_terms & evidence_terms) / len(query_terms)
    sufficient = coverage >= 0.25
    confidence = min(0.95, 0.2 + 0.55 * coverage + 0.04 * min(len(results), 5))
    if not sufficient:
        confidence = min(confidence, 0.39)
    return EvidenceAssessment(
        sufficient=sufficient,
        confidence=round(confidence, 3),
        query_coverage=round(coverage, 3),
    )

