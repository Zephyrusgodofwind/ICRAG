"""Structured query events that deliberately exclude the question and answer text."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field


@dataclass(frozen=True, slots=True)
class QueryEvent:
    """One API outcome containing operational metadata but no clinical text."""

    request_id: str
    route: str
    outcome: str
    query_characters: int
    query_token_count: int
    total_latency_ms: float
    retrieval_method: str | None = None
    retrieval_latency_ms: float = 0.0
    component_cache_hit: bool | None = None
    generation_provider: str | None = None
    generation_model: str | None = None
    generation_latency_ms: float = 0.0
    generation_fallback_used: bool = False
    generation_fallback_reason: str | None = None
    answer_token_count: int = 0
    evidence_count: int = 0
    retrieved_documents: list[str] = field(default_factory=list)
    retrieval_scores: list[float] = field(default_factory=list)
    safety_status: str | None = None
    error_status: str | None = None


class QueryEventLogger:
    """Emit stable JSON events without persisting raw health questions or passages."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger("irishclinicalrag.query")

    def emit(self, event: QueryEvent) -> None:
        payload = {"event": "clinical_query", **asdict(event)}
        self._logger.info(json.dumps(payload, sort_keys=True, separators=(",", ":")))
