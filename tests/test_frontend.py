from pathlib import Path


def test_frontend_has_safety_evidence_and_resilience_elements() -> None:
    frontend = Path("frontend")
    html = (frontend / "index.html").read_text(encoding="utf-8")
    script = (frontend / "app.js").read_text(encoding="utf-8")

    assert "No patient data" in html
    assert 'id="safety-status"' in html
    assert 'id="method-metadata"' in html
    assert 'id="retry"' in html
    assert 'id="evidence"' in html
    assert "renderEvidence" in script
    assert "renderMethodDetails" in script
    assert "citationByChunk" in script
    assert "AbortController" in script
    assert "textContent = payload.answer" in script
