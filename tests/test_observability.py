import json
import logging

import pytest

from irishclinicalrag.observability.events import QueryEvent, QueryEventLogger
from irishclinicalrag.observability.metrics import MetricsStore


def test_metrics_store_tracks_routes_safety_and_latencies() -> None:
    metrics = MetricsStore()
    metrics.record_success(
        route="retrieve",
        retrieval_latency_ms=10,
        generation_latency_ms=0,
        total_latency_ms=12,
        evidence_count=5,
        retrieval_performed=True,
        generation_performed=False,
    )
    metrics.record_success(
        route="query",
        retrieval_latency_ms=20,
        generation_latency_ms=4,
        total_latency_ms=27,
        evidence_count=3,
        retrieval_performed=True,
        generation_performed=True,
        safety_status="insufficient_evidence",
    )
    metrics.record_failure(route="query", total_latency_ms=3)

    snapshot = metrics.snapshot()
    assert snapshot["request_count"] == 3
    assert snapshot["retrieve_request_count"] == 1
    assert snapshot["answer_request_count"] == 2
    assert snapshot["retrieval_operation_count"] == 2
    assert snapshot["generation_operation_count"] == 1
    assert snapshot["error_count"] == 1
    assert snapshot["abstention_count"] == 1
    assert snapshot["average_retrieval_latency_ms"] == 15
    assert snapshot["average_generation_latency_ms"] == 4
    assert snapshot["average_evidence_returned"] == pytest.approx(2.667)
    assert snapshot["average_total_latency_ms"] == 14


def test_query_event_logger_emits_json_without_text(caplog) -> None:
    logger = logging.getLogger("test.privacy-safe-query-event")
    event_logger = QueryEventLogger(logger)
    event = QueryEvent(
        request_id="request-1",
        route="query",
        outcome="success",
        query_characters=30,
        query_token_count=5,
        total_latency_ms=42.5,
        retrieval_method="hybrid-rerank",
        retrieved_documents=["hse-test"],
        retrieval_scores=[0.75],
        safety_status="grounded",
    )

    with caplog.at_level(logging.INFO, logger=logger.name):
        event_logger.emit(event)

    payload = json.loads(caplog.records[-1].message)
    assert payload["event"] == "clinical_query"
    assert payload["request_id"] == "request-1"
    assert payload["retrieved_documents"] == ["hse-test"]
    assert set(payload).isdisjoint({"question", "answer", "passages"})
