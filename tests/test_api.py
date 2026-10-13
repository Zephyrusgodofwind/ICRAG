import json
import logging
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from irishclinicalrag.api.app import create_app
from irishclinicalrag.models import EvidenceChunk
from irishclinicalrag.observability.events import QueryEventLogger
from irishclinicalrag.storage import write_jsonl


def _client(tmp_path, query_event_logger=None) -> TestClient:
    data_dir = tmp_path / "data"
    chunk = EvidenceChunk(
        document_id="hse-test",
        chunk_id="hse-test:1",
        source="HSE",
        source_type="clinical_guideline",
        title="Guideline",
        section="Prescribing",
        url="https://www.hse.ie/test.pdf",
        retrieved_at=datetime(2026, 10, 7, tzinfo=UTC),
        topic="antimicrobial stewardship",
        content="Antimicrobial prescriptions require a documented review date.",
        content_sha256="f" * 64,
    )
    write_jsonl(data_dir / "chunks" / "chunks.jsonl", [chunk])
    config = tmp_path / "config.json"
    config.write_text(json.dumps({}), encoding="utf-8")
    return TestClient(
        create_app(
            data_dir=data_dir,
            config_path=config,
            query_event_logger=query_event_logger,
        )
    )


def test_required_api_endpoints(tmp_path) -> None:
    client = _client(tmp_path)

    assert client.get("/").status_code == 200
    assert client.get("/styles.css").headers["content-type"].startswith("text/css")
    assert client.get("/app.js").headers["content-type"].startswith("text/javascript")
    assert client.get("/health").json() == {
        "status": "ok",
        "indexed_chunks": 1,
        "indexed_documents": 1,
        "semantic_index": False,
    }
    assert client.get("/sources").json()[0]["source"] == "HSE"
    retrieval = client.post(
        "/retrieve", json={"question": "Should antimicrobial prescriptions have a review date?"}
    )
    assert retrieval.status_code == 200
    assert retrieval.json()["evidence"][0]["chunk"]["chunk_id"] == "hse-test:1"
    assert client.get("/metrics").json()["query_count"] == 1


def test_emergency_query_skips_retrieval(tmp_path) -> None:
    client = _client(tmp_path)

    response = client.post("/query", json={"question": "I have chest pain and cannot breathe"})

    assert response.status_code == 200
    assert response.json()["safety_status"] == "emergency_escalation"
    assert response.json()["retrieval_metadata"]["method"] == "skipped-emergency-safety"
    metrics = client.get("/metrics").json()
    assert metrics["query_count"] == 1
    assert metrics["answer_request_count"] == 1
    assert metrics["retrieval_operation_count"] == 0
    assert metrics["emergency_escalation_count"] == 1


def test_query_endpoint_abstains_when_no_matching_evidence(tmp_path) -> None:
    client = _client(tmp_path)

    response = client.post("/query", json={"question": "zzzxxyy unmatched question"})

    assert response.status_code == 200
    assert response.json()["evidence_sufficient"] is False
    assert response.json()["safety_status"] == "insufficient_evidence"
    metrics = client.get("/metrics").json()
    assert metrics["abstention_count"] == 1
    assert metrics["average_total_latency_ms"] >= 0


def test_structured_query_log_excludes_clinical_text(tmp_path, caplog) -> None:
    logger = logging.getLogger("test.api.structured-query")
    client = _client(tmp_path, QueryEventLogger(logger))
    private_text = "synthetic private phrase about a medication"

    with caplog.at_level(logging.INFO, logger=logger.name):
        response = client.post("/query", json={"question": private_text})

    assert response.status_code == 200
    event = json.loads(caplog.records[-1].message)
    assert event["event"] == "clinical_query"
    assert event["route"] == "query"
    assert event["query_characters"] == len(private_text)
    assert event["query_token_count"] == len(private_text.split())
    assert private_text not in caplog.text
    assert "question" not in event
    assert "answer" not in event


def test_failed_retrieval_is_counted_without_leaking_question(tmp_path, caplog) -> None:
    config = tmp_path / "config.json"
    config.write_text(json.dumps({}), encoding="utf-8")
    logger = logging.getLogger("test.api.failed-query")
    client = TestClient(
        create_app(
            data_dir=tmp_path / "missing",
            config_path=config,
            query_event_logger=QueryEventLogger(logger),
        )
    )
    private_text = "synthetic unavailable corpus question"

    with caplog.at_level(logging.INFO, logger=logger.name):
        response = client.post("/retrieve", json={"question": private_text})

    assert response.status_code == 503
    metrics = client.get("/metrics").json()
    assert metrics["request_count"] == 1
    assert metrics["error_count"] == 1
    assert json.loads(caplog.records[-1].message)["error_status"] == "http_503"
    assert private_text not in caplog.text
