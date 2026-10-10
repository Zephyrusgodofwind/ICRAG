"""Typed contracts for evaluation data and predictions."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    question: str = Field(min_length=5)
    reference_answer: str = Field(min_length=3)
    expected_chunk_ids: list[str] = Field(min_length=1)
    expected_document_ids: list[str] = Field(min_length=1)
    category: str = Field(min_length=3)
    difficulty: Literal["easy", "medium", "hard"]
    cohort: Literal["curated", "synthetic_probe"]
    notes: str = ""


class RetrievalPrediction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    method: str
    retrieved_chunk_ids: list[str]
    retrieved_document_ids: list[str]
    scores: list[float]
    latency_ms: float = Field(ge=0)
