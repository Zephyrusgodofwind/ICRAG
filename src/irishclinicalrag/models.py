"""Stable data contracts shared across the evidence pipeline."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

DatePrecision = Literal["day", "month", "year", "unknown"]


class SourceDocument(BaseModel):
    """Catalog metadata for one authoritative source document."""

    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(min_length=3, pattern=r"^[a-z0-9][a-z0-9-]+$")
    source: str = Field(min_length=2)
    source_type: str = Field(min_length=3)
    title: str = Field(min_length=3)
    url: HttpUrl
    publication_date: date | None = None
    publication_date_precision: DatePrecision = "unknown"
    last_updated: date | None = None
    last_updated_precision: DatePrecision = "unknown"
    topic: str = Field(min_length=2)
    clinical_specialty: str | None = None
    document_version: str | None = None
    language: str = "en"
    country: str = "Ireland"


class ManifestRecord(BaseModel):
    """Append-only acquisition record for a checksum-addressed raw file."""

    model_config = ConfigDict(extra="forbid")

    document_id: str
    source_url: HttpUrl
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    retrieved_at: datetime
    media_type: str
    raw_path: str
    byte_count: int = Field(ge=1)
    processing_status: str = "downloaded"
    document_version: str | None = None
    number_of_chunks: int | None = Field(default=None, ge=0)


class ParsedSection(BaseModel):
    """A parser-preserved page or semantic section."""

    model_config = ConfigDict(extra="forbid")

    heading: str
    content: str
    page_number: int | None = Field(default=None, ge=1)

    @field_validator("content")
    @classmethod
    def content_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("section content cannot be blank")
        return value.strip()


class EvidenceChunk(BaseModel):
    """Minimum metadata contract that must survive every pipeline stage."""

    model_config = ConfigDict(extra="forbid")

    document_id: str
    chunk_id: str
    source: str
    source_type: str
    title: str
    section: str
    url: HttpUrl
    publication_date: date | None = None
    publication_date_precision: DatePrecision = "unknown"
    last_updated: date | None = None
    last_updated_precision: DatePrecision = "unknown"
    retrieved_at: datetime
    topic: str
    content: str = Field(min_length=1)
    country: str = "Ireland"
    clinical_specialty: str | None = None
    document_version: str | None = None
    evidence_grade: str | None = None
    page_number: int | None = Field(default=None, ge=1)
    language: str = "en"
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class RetrievalResult(BaseModel):
    """A scored evidence chunk returned to downstream consumers."""

    chunk: EvidenceChunk
    score: float
    rank: int = Field(ge=1)
    retriever: str
    component_scores: dict[str, float] = Field(default_factory=dict)


class DenseIndexMetadata(BaseModel):
    """Versioned description of a persistent dense-vector index."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    backend: str
    model_name: str
    dimensions: int = Field(ge=1)
    chunk_ids: list[str]
    corpus_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    query_prefix: str = ""
    created_at: datetime


class CorpusValidationReport(BaseModel):
    """Machine-readable corpus gate emitted after every ingestion run."""

    model_config = ConfigDict(extra="forbid")

    valid: bool
    document_count: int = Field(ge=0)
    chunk_count: int = Field(ge=0)
    corpus_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    chunks_per_document: dict[str, int] = Field(default_factory=dict)
    generated_at: datetime


class RetrievalMetadata(BaseModel):
    method: str
    candidates: int = Field(ge=0)
    returned: int = Field(ge=0)
    latency_ms: float = Field(ge=0)
    parameters: dict[str, Any] = Field(default_factory=dict)


class RetrieveResponse(BaseModel):
    query: str
    evidence: list[RetrievalResult]
    retrieval_metadata: RetrievalMetadata


class QueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2_000)

    @field_validator("question")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        return " ".join(value.split())


class Citation(BaseModel):
    citation_id: str
    chunk_id: str
    source: str
    title: str
    url: HttpUrl
    page_number: int | None = Field(default=None, ge=1)
    passage: str
    retrieval_score: float


class GenerationMetadata(BaseModel):
    provider: str
    latency_ms: float = Field(ge=0)
    citations_verified: bool
    fallback_used: bool = False


class AnswerResponse(BaseModel):
    answer: str
    evidence: list[RetrievalResult]
    citations: list[Citation]
    confidence: float = Field(ge=0, le=1)
    evidence_sufficient: bool
    limitations: str
    safety_status: str
    retrieval_metadata: RetrievalMetadata
    generation_metadata: GenerationMetadata


def utc_now() -> datetime:
    return datetime.now(UTC)
