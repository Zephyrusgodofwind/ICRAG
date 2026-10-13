import json
import logging
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from irishclinicalrag.api.app import create_app
from irishclinicalrag.models import EvidenceChunk
from irishclinicalrag.observability.events import QueryEventLogger
from irishclinicalrag.storage import write_jsonl


def _client(tmp_path, query_event_logger=None, config_payload=None) -> TestClient:
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
        content=(
            "Antimicrobial prescriptions should include a documented review date "
            "for safe prescribing."
        ),
        content_sha256="f" * 64,
    )
    write_jsonl(data_dir / "chunks" / "chunks.jsonl", [chunk])
    config = tmp_path / "config.json"
    config.write_text(json.dumps(config_payload or {}), encoding="utf-8")
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
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {
        "status": "ok",
        "ready": True,
        "indexed_chunks": 1,
        "indexed_documents": 1,
        "semantic_index": False,
        "component_cache_loaded": True,
        "component_cache_hit": False,
        "component_cache_generation": 1,
    }
    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/sources").json()[0]["source"] == "HSE"
    retrieval = client.post(
        "/retrieve", json={"question": "Should antimicrobial prescriptions have a review date?"}
    )
    assert retrieval.status_code == 200
    assert retrieval.json()["evidence"][0]["chunk"]["chunk_id"] == "hse-test:1"
    assert retrieval.json()["retrieval_metadata"]["parameters"]["component_cache_hit"]
    metrics = client.get("/metrics").json()
    assert metrics["query_count"] == 1
    assert metrics["component_cache_hits"] == 1


def test_readiness_fails_closed_without_corpus(tmp_path) -> None:
    config = tmp_path / "config.json"
    config.write_text(json.dumps({}), encoding="utf-8")
    client = TestClient(create_app(data_dir=tmp_path / "missing", config_path=config))

    assert client.get("/health/live").status_code == 200
    readiness = client.get("/health")
    assert readiness.status_code == 503
    assert readiness.json()["status"] == "not_ready"
    assert readiness.json()["error_code"] == "corpus_or_config_missing"


def test_emergency_query_skips_retrieval(tmp_path) -> None:
    client = _client(tmp_path)

    response = client.post("/query", json={"question": "I have chest pain and cannot breathe"})

    assert response.status_code == 200, response.text
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


def test_missing_remote_generation_configuration_uses_safe_fallback(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.delenv("TEST_MISSING_LLM_KEY", raising=False)
    client = _client(
        tmp_path,
        config_payload={
            "generation": {
                "provider": "openai-compatible",
                "model": "unavailable-model",
                "base_url": "https://example.test/v1",
                "api_key_env": "TEST_MISSING_LLM_KEY",
            }
        },
    )

    response = client.post(
        "/query",
        json={"question": "Do antimicrobial prescriptions require a documented review date?"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["evidence_sufficient"] is True
    assert payload["generation_metadata"]["provider"] == "extractive-evidence-baseline"
    assert payload["generation_metadata"]["fallback_used"] is True
    assert (
        payload["generation_metadata"]["fallback_reason"]
        == "provider_configuration_unavailable"
    )
    assert client.get("/metrics").json()["generation_fallback_count"] == 1


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
    assert event["component_cache_hit"] is False
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
