"""PDF and HTML-to-section parsing."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

from irishclinicalrag.models import ParsedSection

PDF_GLYPH_REPLACEMENTS = str.maketrans(
    {
        "\uf0b7": "•",
        "\uf0a7": "•",
        "\uf0d8": "•",
    }
)


def normalize_extracted_text(text: str) -> str:
    """Replace common private-use PDF bullets with portable Unicode."""
    return text.translate(PDF_GLYPH_REPLACEMENTS)


class _TextHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.blocks: list[tuple[str, str]] = []
        self._tag = ""
        self._buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"h1", "h2", "h3", "h4", "p", "li"}:
            self._flush()
            self._tag = tag

    def handle_endtag(self, tag: str) -> None:
        if tag == self._tag:
            self._flush()

    def handle_data(self, data: str) -> None:
        if self._tag:
            self._buffer.append(data)

    def _flush(self) -> None:
        text = re.sub(r"\s+", " ", " ".join(self._buffer)).strip()
        if text:
            self.blocks.append((self._tag, text))
        self._tag = ""
        self._buffer.clear()


def parse_html(path: Path, default_title: str) -> list[ParsedSection]:
    parser = _TextHTMLParser()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    sections: list[ParsedSection] = []
    heading = default_title
    paragraphs: list[str] = []
    for tag, text in parser.blocks:
        if tag.startswith("h"):
            if paragraphs:
                sections.append(ParsedSection(heading=heading, content="\n\n".join(paragraphs)))
                paragraphs = []
            heading = text
        else:
            paragraphs.append(text)
    if paragraphs:
        sections.append(ParsedSection(heading=heading, content="\n\n".join(paragraphs)))
    return sections


def parse_pdf(path: Path, default_title: str) -> list[ParsedSection]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - dependency message is deterministic
        raise RuntimeError("PDF parsing requires the 'pypdf' project dependency") from exc

    reader = PdfReader(path)
    sections: list[ParsedSection] = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = normalize_extracted_text(page.extract_text() or "")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if text:
            sections.append(
                ParsedSection(
                    heading=f"{default_title} — page {page_number}",
                    content=text,
                    page_number=page_number,
                )
            )
    if not sections:
        raise ValueError(f"No extractable text found in PDF: {path}")
    return sections


def parse_document(path: Path, media_type: str, default_title: str) -> list[ParsedSection]:
    if media_type == "application/pdf" or path.suffix.lower() == ".pdf":
        return parse_pdf(path, default_title)
    if media_type in {"text/html", "application/xhtml+xml"} or path.suffix.lower() in {
        ".html",
        ".htm",
    }:
        return parse_html(path, default_title)
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        raise ValueError(f"No text found in document: {path}")
    return [ParsedSection(heading=default_title, content=text)]
