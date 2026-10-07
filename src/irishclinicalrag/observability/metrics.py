"""In-memory aggregate metrics; raw health questions are intentionally not stored."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock


@dataclass(slots=True)
class MetricsStore:
    _lock: Lock = field(default_factory=Lock)
    query_count: int = 0
    error_count: int = 0
    total_retrieval_latency_ms: float = 0.0

    def record_query(self, retrieval_latency_ms: float) -> None:
        with self._lock:
            self.query_count += 1
            self.total_retrieval_latency_ms += retrieval_latency_ms

    def record_error(self) -> None:
        with self._lock:
            self.error_count += 1

    def snapshot(self) -> dict[str, int | float]:
        with self._lock:
            average = (
                self.total_retrieval_latency_ms / self.query_count if self.query_count else 0.0
            )
            return {
                "query_count": self.query_count,
                "error_count": self.error_count,
                "average_retrieval_latency_ms": round(average, 3),
            }
