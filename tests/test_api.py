import json
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from irishclinicalrag.api.app import create_app
from irishclinicalrag.models import EvidenceChunk
from irishclinicalrag.storage import write_jsonl


def _client(tmp_path) -> TestClient:
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
    return TestClient(create_app(data_dir=data_dir, config_path=config))


def test_required_api_endpoints(tmp_path) -> None:
    client = _client(tmp_path)

    assert client.get("/").status_code == 200
    assert client.get("/styles.css").headers["content-type"].startswith("text/css")
    assert client.get("/app.js").headers["content-type"].startswith("text/javascript")
    assert client.get("/health").json() == {"status": "ok", "indexed_chunks": 1}
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
    assert client.get("/metrics").json()["query_count"] == 0


def test_query_endpoint_abstains_when_no_matching_evidence(tmp_path) -> None:
    client = _client(tmp_path)

    response = client.post("/query", json={"question": "zzzxxyy unmatched question"})

    assert response.status_code == 200
    assert response.json()["evidence_sufficient"] is False
    assert response.json()["safety_status"] == "insufficient_evidence"
