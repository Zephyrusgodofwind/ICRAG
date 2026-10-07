"""Paragraph-aware chunking with deterministic IDs and bounded overlap."""

from __future__ import annotations

import hashlib
import re

from irishclinicalrag.models import EvidenceChunk, ManifestRecord, ParsedSection, SourceDocument
from irishclinicalrag.settings import ChunkingSettings

TOKEN_RE = re.compile(r"\w+(?:[-'][\w]+)*|[^\w\s]", re.UNICODE)


def tokens(text: str) -> list[str]:
    """Deterministic token approximation used for chunk sizing, not model billing."""
    return TOKEN_RE.findall(text)


def _paragraphs(text: str) -> list[str]:
    blocks = [re.sub(r"\s+", " ", part).strip() for part in re.split(r"\n\s*\n", text)]
    return [block for block in blocks if block]


def _split_long_paragraph(paragraph: str, limit: int) -> list[str]:
    words = paragraph.split()
    if len(tokens(paragraph)) <= limit:
        return [paragraph]
    return [" ".join(words[start : start + limit]) for start in range(0, len(words), limit)]


def chunk_sections(
    source: SourceDocument,
    manifest: ManifestRecord,
    sections: list[ParsedSection],
    settings: ChunkingSettings,
) -> list[EvidenceChunk]:
    chunks: list[EvidenceChunk] = []
    for section in sections:
        paragraphs: list[str] = []
        for paragraph in _paragraphs(section.content):
            paragraphs.extend(_split_long_paragraph(paragraph, settings.target_tokens))

        current: list[str] = []
        current_tokens = 0
        section_parts: list[str] = []
        for paragraph in paragraphs:
            paragraph_tokens = len(tokens(paragraph))
            if current and current_tokens + paragraph_tokens > settings.target_tokens:
                section_parts.append("\n\n".join(current))
                overlap: list[str] = []
                overlap_size = 0
                for prior in reversed(current):
                    size = len(tokens(prior))
                    if overlap and overlap_size + size > settings.overlap_tokens:
                        break
                    overlap.insert(0, prior)
                    overlap_size += size
                current = overlap
                current_tokens = overlap_size
            current.append(paragraph)
            current_tokens += paragraph_tokens
        if current:
            section_parts.append("\n\n".join(current))

        for part_index, part in enumerate(section_parts):
            if (
                len(tokens(part)) < settings.minimum_tokens
                and chunks
                and part_index == len(section_parts) - 1
                and chunks[-1].document_id == source.document_id
                and chunks[-1].section == section.heading
            ):
                previous = chunks.pop()
                part = f"{previous.content}\n\n{part}"
            digest = hashlib.sha256(part.encode("utf-8")).hexdigest()
            chunk_id = f"{source.document_id}:{len(chunks):05d}:{digest[:12]}"
            chunks.append(
                EvidenceChunk(
                    document_id=source.document_id,
                    chunk_id=chunk_id,
                    source=source.source,
                    source_type=source.source_type,
                    title=source.title,
                    section=section.heading,
                    url=source.url,
                    publication_date=source.publication_date,
                    last_updated=source.last_updated,
                    retrieved_at=manifest.retrieved_at,
                    topic=source.topic,
                    content=part,
                    country=source.country,
                    clinical_specialty=source.clinical_specialty,
                    document_version=source.document_version,
                    page_number=section.page_number,
                    language=source.language,
                    content_sha256=digest,
                )
            )
    return chunks
