"""Replaceable grounded-generation providers; retrieval imports no vendor SDK."""

from __future__ import annotations

import json
import os
import re
import urllib.request
from collections.abc import Callable
from typing import Any, Protocol

from irishclinicalrag.models import Citation, RetrievalResult
from irishclinicalrag.retrieval.text import normalize_tokens
from irishclinicalrag.settings import GenerationSettings

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "be",
    "for",
    "how",
    "in",
    "is",
    "of",
    "should",
    "the",
    "to",
    "what",
    "when",
    "with",
}


def _term_set(text: str) -> set[str]:
    normalized: set[str] = set()
    aliases = {"considered": "consider", "recommendation": "recommend"}
    for term in normalize_tokens(text):
        if term in STOPWORDS:
            continue
        singular = term[:-1] if len(term) > 4 and term.endswith("s") else term
        normalized.add(aliases.get(singular, singular))
    return normalized


def _sentence_score(question: str, sentence: str) -> tuple[float, int]:
    query_terms = _term_set(question)
    sentence_terms = _term_set(sentence)
    score = float(len(query_terms & sentence_terms) * 2)
    normalized_question = question.casefold()
    if "when" in normalized_question and sentence_terms & {"if", "when", "associated"}:
        score += 3
    if "first" in normalized_question and sentence_terms & {"first", "choice", "recommended"}:
        score += 2
    if "should" in normalized_question and sentence_terms & {"should", "recommend", "consider"}:
        score += 1
    return score, -len(sentence)


class LLMProvider(Protocol):
    name: str

    def generate(
        self,
        messages: list[dict[str, str]],
        context: list[RetrievalResult],
        citations: list[Citation],
        **kwargs: object,
    ) -> str: ...


class ExtractiveEvidenceProvider:
    """Offline answer baseline selecting question-relevant evidence sentences."""

    name = "extractive-evidence-baseline"

    def generate(
        self,
        messages: list[dict[str, str]],
        context: list[RetrievalResult],
        citations: list[Citation],
        **kwargs: object,
    ) -> str:
        del context, kwargs
        question = messages[-1]["content"] if messages else ""
        statements: list[str] = []
        for citation in citations[:2]:
            candidates = [
                " ".join(sentence.split())
                for sentence in re.split(r"(?<=[.!?])\s+|\n+", citation.passage)
                if sentence.strip()
            ]
            candidates = [
                sentence for sentence in candidates if len(normalize_tokens(sentence)) >= 8
            ]
            if not candidates:
                continue
            passage = max(candidates, key=lambda sentence: _sentence_score(question, sentence))
            if _sentence_score(question, passage)[0] <= 0:
                continue
            if len(passage) > 500:
                passage = passage[:497].rsplit(" ", 1)[0] + "..."
            statements.append(f"{passage} {citation.citation_id}")
        return "\n\n".join(statements)


JsonPost = Callable[[str, dict[str, Any], dict[str, str], int], dict[str, Any]]


def _post_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout_seconds: int,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


class OpenAICompatibleProvider:
    """Minimal provider for OpenAI-compatible local, hosted, or RunPod endpoints."""

    name = "openai-compatible"

    def __init__(
        self,
        model: str,
        base_url: str,
        api_key: str,
        timeout_seconds: int = 60,
        temperature: float = 0.0,
        post_json: JsonPost = _post_json,
    ) -> None:
        if not model or not base_url or not api_key:
            raise ValueError("model, base URL, and API key are required")
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.post_json = post_json

    def generate(
        self,
        messages: list[dict[str, str]],
        context: list[RetrievalResult],
        citations: list[Citation],
        **kwargs: object,
    ) -> str:
        del context, kwargs
        evidence = "\n\n".join(
            f"{citation.citation_id} {citation.source} — {citation.title}"
            f"{f', page {citation.page_number}' if citation.page_number else ''}\n"
            f"{citation.passage}"
            for citation in citations
        )
        grounded_messages = [
            messages[0],
            {
                "role": "system",
                "content": (
                    "Retrieved evidence follows. Use no other medical facts. Every answer "
                    f"paragraph must cite at least one supplied ID.\n\n{evidence}"
                ),
            },
            *messages[1:],
        ]
        response = self.post_json(
            f"{self.base_url}/chat/completions",
            {
                "model": self.model,
                "messages": grounded_messages,
                "temperature": self.temperature,
            },
            {"Authorization": f"Bearer {self.api_key}"},
            self.timeout_seconds,
        )
        try:
            return str(response["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("generation endpoint returned an invalid response") from exc


def provider_from_settings(settings: GenerationSettings) -> LLMProvider:
    if settings.provider == "extractive":
        return ExtractiveEvidenceProvider()
    api_key = os.environ.get(settings.api_key_env, "")
    if not api_key:
        raise RuntimeError(f"generation credential is missing from {settings.api_key_env}")
    return OpenAICompatibleProvider(
        model=settings.model,
        base_url=settings.base_url,
        api_key=api_key,
        timeout_seconds=settings.timeout_seconds,
        temperature=settings.temperature,
    )
