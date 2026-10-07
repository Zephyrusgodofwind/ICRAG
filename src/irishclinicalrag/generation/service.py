"""Safety-first orchestration for grounded answers."""

from __future__ import annotations

from irishclinicalrag.citations.verification import build_citations, verify_citations
from irishclinicalrag.generation.providers import ExtractiveEvidenceProvider, LLMProvider
from irishclinicalrag.models import AnswerResponse, RetrievalMetadata, RetrievalResult
from irishclinicalrag.safety.policy import (
    EMERGENCY_MESSAGE,
    INSUFFICIENT_MESSAGE,
    assess_evidence,
    is_emergency_query,
)

LIMITATIONS = (
    "Research and educational decision support only. The indexed corpus is incomplete; "
    "guidance may have changed. Verify against the linked source and use clinical judgement."
)


def answer_from_evidence(
    question: str,
    evidence: list[RetrievalResult],
    retrieval_metadata: RetrievalMetadata,
    provider: LLMProvider | None = None,
) -> AnswerResponse:
    if is_emergency_query(question):
        return AnswerResponse(
            answer=EMERGENCY_MESSAGE,
            evidence=[],
            citations=[],
            confidence=0.0,
            evidence_sufficient=False,
            limitations=LIMITATIONS,
            safety_status="emergency_escalation",
            retrieval_metadata=retrieval_metadata,
        )

    assessment = assess_evidence(question, evidence)
    if not assessment.sufficient:
        return AnswerResponse(
            answer=INSUFFICIENT_MESSAGE,
            evidence=evidence,
            citations=[],
            confidence=assessment.confidence,
            evidence_sufficient=False,
            limitations=LIMITATIONS,
            safety_status="insufficient_evidence",
            retrieval_metadata=retrieval_metadata,
        )

    citations = build_citations(evidence)
    if not verify_citations(citations, evidence):
        raise RuntimeError("citation provenance validation failed")
    selected_provider = provider or ExtractiveEvidenceProvider()
    answer = selected_provider.generate(
        messages=[
            {
                "role": "system",
                "content": (
                    "Use only retrieved evidence. Cite every medical statement. "
                    "State uncertainty and never invent a source."
                ),
            },
            {"role": "user", "content": question},
        ],
        context=evidence,
        citations=citations,
    )
    return AnswerResponse(
        answer=answer,
        evidence=evidence,
        citations=citations,
        confidence=assessment.confidence,
        evidence_sufficient=True,
        limitations=LIMITATIONS,
        safety_status="grounded",
        retrieval_metadata=retrieval_metadata,
    )

