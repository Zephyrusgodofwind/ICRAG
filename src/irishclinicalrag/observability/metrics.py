"""Privacy-safe aggregate metrics for the API process."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock


@dataclass(slots=True)
class MetricsStore:
    _lock: Lock = field(default_factory=Lock)
    _request_count: int = 0
    _retrieve_request_count: int = 0
    _answer_request_count: int = 0
    _retrieval_operation_count: int = 0
    _generation_operation_count: int = 0
    _generation_fallback_count: int = 0
    _component_cache_hits: int = 0
    _component_cache_misses: int = 0
    _error_count: int = 0
    _abstention_count: int = 0
    _emergency_escalation_count: int = 0
    _evidence_returned: int = 0
    _total_retrieval_latency_ms: float = 0.0
    _total_generation_latency_ms: float = 0.0
    _total_request_latency_ms: float = 0.0

    def record_success(
        self,
        *,
        route: str,
        retrieval_latency_ms: float,
        generation_latency_ms: float,
        total_latency_ms: float,
        evidence_count: int,
        retrieval_performed: bool,
        generation_performed: bool,
        generation_fallback_used: bool = False,
        component_cache_hit: bool | None = None,
        safety_status: str | None = None,
    ) -> None:
        with self._lock:
            self._request_count += 1
            self._retrieve_request_count += int(route == "retrieve")
            self._answer_request_count += int(route == "query")
            self._retrieval_operation_count += int(retrieval_performed)
            self._generation_operation_count += int(generation_performed)
            self._generation_fallback_count += int(generation_fallback_used)
            self._component_cache_hits += int(component_cache_hit is True)
            self._component_cache_misses += int(component_cache_hit is False)
            self._abstention_count += int(safety_status == "insufficient_evidence")
            self._emergency_escalation_count += int(safety_status == "emergency_escalation")
            self._evidence_returned += evidence_count
            self._total_retrieval_latency_ms += retrieval_latency_ms
            self._total_generation_latency_ms += generation_latency_ms
            self._total_request_latency_ms += total_latency_ms

    def record_failure(self, *, route: str, total_latency_ms: float) -> None:
        with self._lock:
            self._request_count += 1
            self._retrieve_request_count += int(route == "retrieve")
            self._answer_request_count += int(route == "query")
            self._error_count += 1
            self._total_request_latency_ms += total_latency_ms

    def snapshot(self) -> dict[str, int | float]:
        with self._lock:
            average_retrieval = (
                self._total_retrieval_latency_ms / self._retrieval_operation_count
                if self._retrieval_operation_count
                else 0.0
            )
            average_generation = (
                self._total_generation_latency_ms / self._generation_operation_count
                if self._generation_operation_count
                else 0.0
            )
            average_total = (
                self._total_request_latency_ms / self._request_count
                if self._request_count
                else 0.0
            )
            average_evidence = (
                self._evidence_returned / self._request_count if self._request_count else 0.0
            )
            cache_attempts = self._component_cache_hits + self._component_cache_misses
            cache_hit_rate = (
                self._component_cache_hits / cache_attempts if cache_attempts else 0.0
            )
            return {
                # Retained for compatibility with the original metrics contract.
                "query_count": self._request_count,
                "request_count": self._request_count,
                "retrieve_request_count": self._retrieve_request_count,
                "answer_request_count": self._answer_request_count,
                "retrieval_operation_count": self._retrieval_operation_count,
                "generation_operation_count": self._generation_operation_count,
                "generation_fallback_count": self._generation_fallback_count,
                "component_cache_hits": self._component_cache_hits,
                "component_cache_misses": self._component_cache_misses,
                "component_cache_hit_rate": round(cache_hit_rate, 3),
                "error_count": self._error_count,
                "abstention_count": self._abstention_count,
                "emergency_escalation_count": self._emergency_escalation_count,
                "average_evidence_returned": round(average_evidence, 3),
                "average_retrieval_latency_ms": round(average_retrieval, 3),
                "average_generation_latency_ms": round(average_generation, 3),
                "average_total_latency_ms": round(average_total, 3),
            }
