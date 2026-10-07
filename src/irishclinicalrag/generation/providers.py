"""Provider abstraction; retrieval never imports a vendor SDK."""

from __future__ import annotations

from typing import Protocol

from irishclinicalrag.models import Citation, RetrievalResult


class LLMProvider(Protocol):
    name: str

    def generate(
        self,
        messages: list[dict[str, str]],
        context: list[RetrievalResult],
        citations: list[Citation],
        **kwargs: object,
    ) -> str: ...


class ExtractiveEvidenceProvider:
    """Offline, auditable baseline that quotes only retrieved passages.

    This is deliberately labelled as an extractive baseline rather than an LLM.
    Vendor or local LLM providers can replace it without changing retrieval.
    """

    name = "extractive-evidence-baseline"

    def generate(
        self,
        messages: list[dict[str, str]],
        context: list[RetrievalResult],
        citations: list[Citation],
        **kwargs: object,
    ) -> str:
        del messages, context, kwargs
        statements: list[str] = []
        for citation in citations[:2]:
            passage = " ".join(citation.passage.split())
            if len(passage) > 360:
                passage = passage[:357].rsplit(" ", 1)[0] + "…"
            statements.append(f"{passage} {citation.citation_id}")
        return "\n\n".join(statements)

