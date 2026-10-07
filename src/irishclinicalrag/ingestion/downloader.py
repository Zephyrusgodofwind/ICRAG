"""Checksum-addressed downloader that never silently overwrites raw documents."""

from __future__ import annotations

import hashlib
import mimetypes
import urllib.request
from pathlib import Path

from irishclinicalrag.models import ManifestRecord, SourceDocument, utc_now
from irishclinicalrag.storage import append_jsonl

USER_AGENT = "IrishClinicalRAG/0.1 (+research and educational retrieval project)"


def _extension(media_type: str, url: str) -> str:
    guessed = mimetypes.guess_extension(media_type.split(";", 1)[0].strip())
    if guessed:
        return ".jpg" if guessed == ".jpe" else guessed
    suffix = Path(urllib.request.url2pathname(url.split("?", 1)[0])).suffix
    return suffix if suffix else ".bin"


def download_document(
    source: SourceDocument,
    raw_dir: Path,
    manifest_path: Path,
    timeout_seconds: int = 60,
) -> ManifestRecord:
    request = urllib.request.Request(str(source.url), headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
        payload = response.read()
        media_type = response.headers.get_content_type()

    if not payload:
        raise ValueError(f"Downloaded empty response for {source.document_id}")

    digest = hashlib.sha256(payload).hexdigest()
    filename = f"{digest}{_extension(media_type, str(source.url))}"
    destination = raw_dir / source.document_id / filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.read_bytes() != payload:
        raise RuntimeError(f"Checksum collision at {destination}")
    if not destination.exists():
        destination.write_bytes(payload)

    record = ManifestRecord(
        document_id=source.document_id,
        source_url=source.url,
        sha256=digest,
        retrieved_at=utc_now(),
        media_type=media_type,
        raw_path=destination.as_posix(),
        byte_count=len(payload),
        document_version=source.document_version,
    )
    append_jsonl(manifest_path, record)
    return record
