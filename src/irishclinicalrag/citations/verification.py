"""Construct citations only from retrieved evidence and verify their mapping."""

from __future__ import annotations

from irishclinicalrag.models import Citation, RetrievalResult


def build_citations(results: list[RetrievalResult], limit: int = 3) -> list[Citation]:
    return [
        Citation(
            citation_id=f"[{index}]",
            chunk_id=result.chunk.chunk_id,
            source=result.chunk.source,
            title=result.chunk.title,
            url=result.chunk.url,
            page_number=result.chunk.page_number,
            passage=result.chunk.content,
            retrieval_score=result.score,
        )
        for index, result in enumerate(results[:limit], start=1)
    ]


def verify_citations(citations: list[Citation], results: list[RetrievalResult]) -> bool:
    retrieved = {result.chunk.chunk_id: result.chunk for result in results}
    if not citations:
        return False
    for citation in citations:
        chunk = retrieved.get(citation.chunk_id)
        if chunk is None or citation.passage != chunk.content or citation.url != chunk.url:
            return False
    return True

