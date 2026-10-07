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


def retrieve(
    query: str,
    chunks: list[EvidenceChunk],
    settings: Settings,
    data_dir: Path = Path("data"),
    method: str = "hybrid",
) -> RetrieveResponse:
    started = time.perf_counter()
    sparse = BM25Retriever(chunks) if method in {"bm25", "hybrid"} else None
    dense = None
    if method in {"dense", "hybrid"}:
        index_path = data_dir / "index"
        use_semantic = settings.retrieval.dense_backend == "sentence-transformers" or (
            settings.retrieval.dense_backend == "auto"
            and (index_path / "dense-index.json").exists()
        )
        dense = (
            IndexedDenseRetriever(chunks, index_path)
            if use_semantic
            else HashingDenseRetriever(chunks, dimensions=settings.retrieval.dense_dimensions)
        )
    if method == "bm25":
        assert sparse is not None
        evidence = sparse.search(query, top_k=settings.retrieval.top_k_final)
        active_method = sparse.name
    elif method == "dense":
        assert dense is not None
        evidence = dense.search(query, top_k=settings.retrieval.top_k_final)
        active_method = dense.name
    elif method == "hybrid":
        assert sparse is not None and dense is not None
        hybrid = HybridRetriever([sparse, dense], rrf_k=settings.retrieval.rrf_k)
        evidence = hybrid.search(
            query,
            top_k=settings.retrieval.top_k_final,
            candidate_k=settings.retrieval.top_k_initial,
        )
        active_method = hybrid.name
    else:
        raise ValueError(f"unknown retrieval method: {method}")
    elapsed_ms = (time.perf_counter() - started) * 1000
    return RetrieveResponse(
        query=query,
        evidence=evidence,
        retrieval_metadata=RetrievalMetadata(
            method=active_method,
            candidates=min(len(chunks), settings.retrieval.top_k_initial * 2),
            returned=len(evidence),
            latency_ms=elapsed_ms,
            parameters={
                "rrf_k": settings.retrieval.rrf_k,
                "top_k_initial": settings.retrieval.top_k_initial,
                "top_k_final": settings.retrieval.top_k_final,
                "dense_backend": dense.name if dense else None,
                "dense_model": (
                    dense.metadata.model_name if isinstance(dense, IndexedDenseRetriever) else None
                ),
                "corpus_fingerprint": (
                    dense.metadata.corpus_fingerprint
                    if isinstance(dense, IndexedDenseRetriever)
                    else None
                ),
            },
        ),
    )
