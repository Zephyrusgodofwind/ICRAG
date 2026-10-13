"""Console entry point for the API development server."""

from __future__ import annotations

import os


def main() -> None:
    import uvicorn

    uvicorn.run(
        "irishclinicalrag.api.app:app",
        host=os.environ.get("IRISHCLINICALRAG_HOST", "0.0.0.0"),
        port=int(os.environ.get("IRISHCLINICALRAG_PORT", "8000")),
        log_level=os.environ.get("IRISHCLINICALRAG_LOG_LEVEL", "info"),
    )
