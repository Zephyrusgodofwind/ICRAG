"""Shared clinical-text normalization."""

from __future__ import annotations

import re

WORD_RE = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)*", re.IGNORECASE)


def normalize_tokens(text: str) -> list[str]:
    return [match.group(0).casefold() for match in WORD_RE.finditer(text)]

