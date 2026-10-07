"""Fail-closed corpus validation and reproducible corpus fingerprints."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict

from irishclinicalrag.models import (
    CorpusValidationReport,
    EvidenceChunk,
    ManifestRecord,
    SourceDocument,
    utc_now,
)


def corpus_fingerprint(chunks: list[EvidenceChunk]) -> str:
    """Hash stable content and provenance metadata while excluding retrieval time."""
    digest = hashlib.sha256()
    for chunk in sorted(chunks, key=lambda item: item.chunk_id):
        stable_record = chunk.model_dump(
            mode="json",
            exclude={"content", "retrieved_at"},
        )
        digest.update(
            json.dumps(stable_record, sort_keys=True, separators=(",", ":")).encode("utf-8")
        )
        digest.update(b"\n")
    return digest.hexdigest()


def validate_corpus(
    sources: list[SourceDocument],
    manifests: list[ManifestRecord],
    chunks: list[EvidenceChunk],
) -> CorpusValidationReport:
    """Validate document coverage, provenance continuity, and unique identities."""
    errors: list[str] = []
    warnings: list[str] = []
    source_counts = Counter(source.document_id for source in sources)
    duplicate_sources = sorted(key for key, count in source_counts.items() if count > 1)
    if duplicate_sources:
        errors.append(f"duplicate document_id values: {', '.join(duplicate_sources)}")

    source_by_id = {source.document_id: source for source in sources}
    chunk_id_counts = Counter(chunk.chunk_id for chunk in chunks)
    duplicate_chunk_ids = sorted(key for key, count in chunk_id_counts.items() if count > 1)
    if duplicate_chunk_ids:
        errors.append(f"duplicate chunk_id values: {', '.join(duplicate_chunk_ids[:10])}")

    chunks_per_document = Counter(chunk.document_id for chunk in chunks)
    missing_documents = sorted(set(source_by_id) - set(chunks_per_document))
    if missing_documents:
        errors.append(f"catalog documents without chunks: {', '.join(missing_documents)}")

    unknown_documents = sorted(set(chunks_per_document) - set(source_by_id))
    if unknown_documents:
        errors.append(f"chunks from documents outside catalog: {', '.join(unknown_documents)}")

    for chunk in chunks:
        source = source_by_id.get(chunk.document_id)
        if source is None:
            continue
        expected = {
            "source": source.source,
            "source_type": source.source_type,
            "title": source.title,
            "url": str(source.url),
            "country": source.country,
            "language": source.language,
            "document_version": source.document_version,
            "publication_date_precision": source.publication_date_precision,
            "last_updated_precision": source.last_updated_precision,
        }
        actual = {
            "source": chunk.source,
            "source_type": chunk.source_type,
            "title": chunk.title,
            "url": str(chunk.url),
            "country": chunk.country,
            "language": chunk.language,
            "document_version": chunk.document_version,
            "publication_date_precision": chunk.publication_date_precision,
            "last_updated_precision": chunk.last_updated_precision,
        }
        mismatches = [name for name in expected if expected[name] != actual[name]]
        if mismatches:
            errors.append(
                f"{chunk.chunk_id} metadata differs from catalog: {', '.join(mismatches)}"
            )
        if not str(chunk.url).startswith("https://"):
            errors.append(f"{chunk.chunk_id} uses a non-HTTPS source URL")
        if chunk.country != "Ireland":
            errors.append(f"{chunk.chunk_id} is not marked as Irish evidence")
        expected_digest = hashlib.sha256(chunk.content.encode("utf-8")).hexdigest()
        if chunk.content_sha256 != expected_digest:
            errors.append(f"{chunk.chunk_id} content checksum does not match")

    manifests_by_document: defaultdict[str, list[ManifestRecord]] = defaultdict(list)
    payload_documents: defaultdict[str, set[str]] = defaultdict(set)
    for manifest in manifests:
        manifests_by_document[manifest.document_id].append(manifest)
        payload_documents[manifest.sha256].add(manifest.document_id)
    for document_id in source_by_id:
        records = manifests_by_document.get(document_id, [])
        if not records:
            errors.append(f"{document_id} has no acquisition manifest")
        elif not any(record.processing_status == "processed" for record in records):
            errors.append(f"{document_id} has no processed acquisition record")
        else:
            processed = next(
                record for record in reversed(records) if record.processing_status == "processed"
            )
            if processed.number_of_chunks != chunks_per_document.get(document_id, 0):
                errors.append(f"{document_id} manifest chunk count does not match corpus")
            if str(processed.source_url) != str(source_by_id[document_id].url):
                errors.append(f"{document_id} manifest URL does not match catalog")
    duplicate_payloads = [
        sorted(document_ids)
        for document_ids in payload_documents.values()
        if len(document_ids) > 1
    ]
    for document_ids in duplicate_payloads:
        errors.append(f"different document IDs share one raw payload: {', '.join(document_ids)}")

    content_documents: defaultdict[str, set[str]] = defaultdict(set)
    for chunk in chunks:
        content_documents[chunk.content_sha256].add(chunk.document_id)
    cross_document_duplicates = sum(
        1 for document_ids in content_documents.values() if len(document_ids) > 1
    )
    if cross_document_duplicates:
        warnings.append(
            f"{cross_document_duplicates} exact chunk texts recur across documents; "
            "review if unexpected"
        )

    return CorpusValidationReport(
        valid=not errors,
        document_count=len(source_by_id),
        chunk_count=len(chunks),
        corpus_fingerprint=corpus_fingerprint(chunks),
        errors=errors,
        warnings=warnings,
        chunks_per_document=dict(sorted(chunks_per_document.items())),
        generated_at=utc_now(),
    )
