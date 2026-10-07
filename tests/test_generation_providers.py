import pytest

from irishclinicalrag.generation.providers import (
    ExtractiveEvidenceProvider,
    OpenAICompatibleProvider,
    provider_from_settings,
)
from irishclinicalrag.settings import GenerationSettings


def test_extractive_provider_selects_conditional_evidence() -> None:
    citation = type(
        "CitationStub",
        (),
        {
            "citation_id": "[1]",
            "passage": (
                "Azithromycin prevention requires specialist direction. "
                "Consider prescribing antibiotics if exacerbation is associated with "
                "increased dyspnoea and sputum purulence."
            ),
        },
    )()

    answer = ExtractiveEvidenceProvider().generate(
        [{"role": "user", "content": "When should antibiotics be considered?"}],
        [],
        [citation],
    )

    assert "if exacerbation is associated" in answer
    assert answer.endswith("[1]")


def test_openai_compatible_provider_sends_grounded_context() -> None:
    captured = {}

    def fake_post(url, payload, headers, timeout):
        captured.update(url=url, payload=payload, headers=headers, timeout=timeout)
        return {"choices": [{"message": {"content": "Grounded answer [1]"}}]}

    provider = OpenAICompatibleProvider(
        model="test-model",
        base_url="https://example.test/v1/",
        api_key="secret",
        post_json=fake_post,
    )
    citation = type(
        "CitationStub",
        (),
        {
            "citation_id": "[1]",
            "source": "HSE",
            "title": "Guideline",
            "page_number": 2,
            "passage": "Exact evidence.",
        },
    )()

    answer = provider.generate(
        [{"role": "system", "content": "grounding"}, {"role": "user", "content": "question"}],
        [],
        [citation],
    )

    assert answer == "Grounded answer [1]"
    assert captured["url"] == "https://example.test/v1/chat/completions"
    assert "Exact evidence." in captured["payload"]["messages"][1]["content"]
    assert captured["headers"]["Authorization"] == "Bearer secret"


def test_configured_remote_provider_requires_environment_secret(monkeypatch) -> None:
    monkeypatch.delenv("TEST_LLM_KEY", raising=False)
    settings = GenerationSettings(
        provider="openai-compatible",
        model="model",
        base_url="https://example.test/v1",
        api_key_env="TEST_LLM_KEY",
    )

    with pytest.raises(RuntimeError, match="TEST_LLM_KEY"):
        provider_from_settings(settings)
