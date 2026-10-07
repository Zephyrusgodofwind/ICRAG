"""Composable ingestion and retrieval orchestration."""

from __future__ import annotations

import json
import time
from pathlib import Path

from pydantic import TypeAdapter

from irishclinicalrag.chunking.semantic import chunk_sections
from irishclinicalrag.ingestion.downloader import download_document
from irishclinicalrag.models import (
    EvidenceChunk,
    RetrievalMetadata,
    RetrieveResponse,
    SourceDocument,
)
from irishclinicalrag.parsing.documents import parse_document
from irishclinicalrag.retrieval.bm25 import BM25Retriever
from irishclinicalrag.retrieval.dense import HashingDenseRetriever
from irishclinicalrag.retrieval.hybrid import HybridRetriever
from irishclinicalrag.settings import Settings
from irishclinicalrag.storage import append_jsonl, read_jsonl, write_jsonl

SOURCE_LIST = TypeAdapter(list[SourceDocument])


def load_source_catalog(path: Path) -> list[SourceDocument]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return SOURCE_LIST.validate_python(payload["sources"])


def ingest_catalog(catalog_path: Path, data_dir: Path, settings: Settings) -> list[EvidenceChunk]:
    all_chunks: list[EvidenceChunk] = []
    for source in load_source_catalog(catalog_path):
        manifest = download_document(
            source,
            raw_dir=data_dir / "raw",
            manifest_path=data_dir / "manifests" / "acquisitions.jsonl",
        )
        sections = parse_document(Path(manifest.raw_path), manifest.media_type, source.title)
        document_chunks = chunk_sections(source, manifest, sections, settings.chunking)
        all_chunks.extend(document_chunks)
        append_jsonl(
            data_dir / "manifests" / "acquisitions.jsonl",
            manifest.model_copy(
                update={"processing_status": "processed", "number_of_chunks": len(document_chunks)}
            ),
        )
    write_jsonl(data_dir / "chunks" / "chunks.jsonl", all_chunks)
    return all_chunks


def load_chunks(data_dir: Path) -> list[EvidenceChunk]:
    return read_jsonl(data_dir / "chunks" / "chunks.jsonl", EvidenceChunk)


def retrieve(query: str, chunks: list[EvidenceChunk], settings: Settings) -> RetrieveResponse:
    started = time.perf_counter()
    sparse = BM25Retriever(chunks)
    dense = HashingDenseRetriever(chunks, dimensions=settings.retrieval.dense_dimensions)
    hybrid = HybridRetriever([sparse, dense], rrf_k=settings.retrieval.rrf_k)
    evidence = hybrid.search(
        query,
        top_k=settings.retrieval.top_k_final,
        candidate_k=settings.retrieval.top_k_initial,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    return RetrieveResponse(
        query=query,
        evidence=evidence,
        retrieval_metadata=RetrievalMetadata(
            method=hybrid.name,
            candidates=min(len(chunks), settings.retrieval.top_k_initial * 2),
            returned=len(evidence),
            latency_ms=elapsed_ms,
            parameters={
                "rrf_k": settings.retrieval.rrf_k,
                "top_k_initial": settings.retrieval.top_k_initial,
                "top_k_final": settings.retrieval.top_k_final,
                "dense_backend": dense.name,
            },
        ),
    )
