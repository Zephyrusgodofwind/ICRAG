"""Composable ingestion and retrieval orchestration."""

from __future__ import annotations

import json
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from pydantic import TypeAdapter

from irishclinicalrag.chunking.semantic import chunk_sections
from irishclinicalrag.ingestion.downloader import download_document
from irishclinicalrag.models import (
    EvidenceChunk,
    ManifestRecord,
    RetrievalMetadata,
    RetrieveResponse,
    SourceDocument,
)
from irishclinicalrag.parsing.documents import parse_document
from irishclinicalrag.reranking.cross_encoder import CrossEncoderReranker
from irishclinicalrag.retrieval.bm25 import BM25Retriever
from irishclinicalrag.retrieval.dense import HashingDenseRetriever
from irishclinicalrag.retrieval.hybrid import HybridRetriever
from irishclinicalrag.retrieval.index import IndexedDenseRetriever
from irishclinicalrag.settings import Settings
from irishclinicalrag.storage import append_jsonl, read_jsonl, write_jsonl
from irishclinicalrag.validation.corpus import validate_corpus

SOURCE_LIST = TypeAdapter(list[SourceDocument])


def load_source_catalog(path: Path) -> list[SourceDocument]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return SOURCE_LIST.validate_python(payload["sources"])


def ingest_catalog(catalog_path: Path, data_dir: Path, settings: Settings) -> list[EvidenceChunk]:
    sources = load_source_catalog(catalog_path)
    all_chunks: list[EvidenceChunk] = []
    processed_manifests: list[ManifestRecord] = []
    for source in sources:
        manifest = download_document(
            source,
            raw_dir=data_dir / "raw",
            manifest_path=data_dir / "manifests" / "acquisitions.jsonl",
        )
        sections = parse_document(Path(manifest.raw_path), manifest.media_type, source.title)
        document_chunks = chunk_sections(source, manifest, sections, settings.chunking)
        all_chunks.extend(document_chunks)
        processed = manifest.model_copy(
            update={"processing_status": "processed", "number_of_chunks": len(document_chunks)}
        )
        processed_manifests.append(processed)
        append_jsonl(data_dir / "manifests" / "acquisitions.jsonl", processed)

    report = validate_corpus(sources, processed_manifests, all_chunks)
    report_path = data_dir / "manifests" / "validation-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    if not report.valid:
        raise ValueError("Corpus validation failed: " + "; ".join(report.errors))

    write_jsonl(data_dir / "chunks" / "chunks.jsonl", all_chunks)
    _write_corpus_lock(
        data_dir / "manifests" / "corpus-lock.json",
        sources,
        processed_manifests,
        all_chunks,
        report.corpus_fingerprint,
    )
    return all_chunks


def _write_corpus_lock(
    path: Path,
    sources: list[SourceDocument],
    manifests: list[ManifestRecord],
    chunks: list[EvidenceChunk],
    fingerprint: str,
) -> None:
    chunks_per_document = Counter(chunk.document_id for chunk in chunks)
    manifest_by_document = {manifest.document_id: manifest for manifest in manifests}
    documents = []
    for source in sources:
        manifest = manifest_by_document[source.document_id]
        documents.append(
            {
                "document_id": source.document_id,
                "source": source.source,
                "title": source.title,
                "url": str(source.url),
                "sha256": manifest.sha256,
                "byte_count": manifest.byte_count,
                "number_of_chunks": chunks_per_document[source.document_id],
                "publication_date": (
                    source.publication_date.isoformat() if source.publication_date else None
                ),
                "publication_date_precision": source.publication_date_precision,
                "last_updated": source.last_updated.isoformat() if source.last_updated else None,
                "last_updated_precision": source.last_updated_precision,
                "document_version": source.document_version,
            }
        )
    payload = {
        "schema_version": 1,
        "corpus_version": datetime.now(UTC).date().isoformat(),
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "corpus_fingerprint": fingerprint,
        "document_count": len(documents),
        "chunk_count": len(chunks),
        "documents": documents,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(".json.tmp")
    temporary_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary_path.replace(path)


def load_chunks(data_dir: Path) -> list[EvidenceChunk]:
    return read_jsonl(data_dir / "chunks" / "chunks.jsonl", EvidenceChunk)


class RetrievalEngine:
    """Reusable retrieval components bound to one corpus and configuration snapshot."""

    def __init__(
        self,
        chunks: list[EvidenceChunk],
        settings: Settings,
        data_dir: Path = Path("data"),
        method: str = "hybrid",
    ) -> None:
        if method not in {"bm25", "dense", "hybrid", "hybrid-rerank"}:
            raise ValueError(f"unknown retrieval method: {method}")
        self.chunks = chunks
        self.settings = settings
        self.data_dir = data_dir
        self.method = method
        self.sparse = (
            BM25Retriever(chunks) if method in {"bm25", "hybrid", "hybrid-rerank"} else None
        )
        self.dense = None
        if method in {"dense", "hybrid", "hybrid-rerank"}:
            index_path = data_dir / "index"
            use_semantic = settings.retrieval.dense_backend == "sentence-transformers" or (
                settings.retrieval.dense_backend == "auto"
                and (index_path / "dense-index.json").exists()
            )
            self.dense = (
                IndexedDenseRetriever(chunks, index_path)
                if use_semantic
                else HashingDenseRetriever(
                    chunks, dimensions=settings.retrieval.dense_dimensions
                )
            )
        self.hybrid = (
            HybridRetriever(
                [self.sparse, self.dense],
                rrf_k=settings.retrieval.rrf_k,
            )
            if method in {"hybrid", "hybrid-rerank"}
            and self.sparse is not None
            and self.dense is not None
            else None
        )
        self.reranker = (
            CrossEncoderReranker(
                settings.reranking.model,
                batch_size=settings.reranking.batch_size,
            )
            if method == "hybrid-rerank"
            else None
        )
        self._reranker_unavailable_reason: str | None = None

    def warm_models(self) -> dict[str, str]:
        """Load optional model weights without retaining or fabricating a query."""
        status: dict[str, str] = {}
        if isinstance(self.dense, IndexedDenseRetriever):
            self.dense.warm()
            status["dense"] = "ready"
        if self.reranker is not None:
            try:
                self.reranker.warm()
                status["reranker"] = "ready"
            except (OSError, RuntimeError):
                self._reranker_unavailable_reason = "model_unavailable"
                status["reranker"] = "fallback"
        return status

    def retrieve(self, query: str) -> RetrieveResponse:
        started = time.perf_counter()
        candidate_count = 0
        reranker_fallback_used = False
        if self.method == "bm25":
            assert self.sparse is not None
            evidence = self.sparse.search(
                query, top_k=self.settings.retrieval.top_k_final
            )
            candidate_count = len(evidence)
            active_method = self.sparse.name
        elif self.method == "dense":
            assert self.dense is not None
            evidence = self.dense.search(
                query, top_k=self.settings.retrieval.top_k_final
            )
            candidate_count = len(evidence)
            active_method = self.dense.name
        else:
            assert self.hybrid is not None
            candidate_k = (
                self.settings.reranking.candidate_k
                if self.method == "hybrid-rerank"
                else self.settings.retrieval.top_k_initial
            )
            hybrid_top_k = (
                self.settings.reranking.candidate_k
                if self.method == "hybrid-rerank"
                else self.settings.retrieval.top_k_final
            )
            candidates = self.hybrid.search(
                query,
                top_k=hybrid_top_k,
                candidate_k=candidate_k,
            )
            candidate_count = len(candidates)
            if self.method == "hybrid-rerank":
                if self._reranker_unavailable_reason:
                    reranker_fallback_used = True
                    evidence = candidates[: self.settings.reranking.top_k]
                else:
                    assert self.reranker is not None
                    try:
                        evidence = self.reranker.rerank(
                            query,
                            candidates,
                            top_k=self.settings.reranking.top_k,
                        )
                    except (OSError, RuntimeError):
                        self._reranker_unavailable_reason = "model_unavailable"
                        reranker_fallback_used = True
                        evidence = candidates[: self.settings.reranking.top_k]
                active_method = (
                    f"{self.hybrid.name}+reranker-fallback"
                    if reranker_fallback_used
                    else f"{self.hybrid.name}+cross-encoder"
                )
            else:
                evidence = candidates
                active_method = self.hybrid.name
        elapsed_ms = (time.perf_counter() - started) * 1000
        return RetrieveResponse(
            query=query,
            evidence=evidence,
            retrieval_metadata=RetrievalMetadata(
                method=active_method,
                candidates=candidate_count,
                returned=len(evidence),
                latency_ms=elapsed_ms,
                parameters={
                    "rrf_k": self.settings.retrieval.rrf_k,
                    "top_k_initial": self.settings.retrieval.top_k_initial,
                    "top_k_final": self.settings.retrieval.top_k_final,
                    "dense_backend": self.dense.name if self.dense else None,
                    "dense_model": (
                        self.dense.metadata.model_name
                        if isinstance(self.dense, IndexedDenseRetriever)
                        else None
                    ),
                    "corpus_fingerprint": (
                        self.dense.metadata.corpus_fingerprint
                        if isinstance(self.dense, IndexedDenseRetriever)
                        else None
                    ),
                    "reranker_model": (
                        self.settings.reranking.model
                        if self.method == "hybrid-rerank"
                        else None
                    ),
                    "rerank_candidate_k": (
                        self.settings.reranking.candidate_k
                        if self.method == "hybrid-rerank"
                        else None
                    ),
                    "reranker_fallback_used": reranker_fallback_used,
                    "reranker_fallback_reason": (
                        self._reranker_unavailable_reason
                        if reranker_fallback_used
                        else None
                    ),
                },
            ),
        )


def retrieve(
    query: str,
    chunks: list[EvidenceChunk],
    settings: Settings,
    data_dir: Path = Path("data"),
    method: str = "hybrid",
) -> RetrieveResponse:
    return RetrievalEngine(chunks, settings, data_dir, method).retrieve(query)
