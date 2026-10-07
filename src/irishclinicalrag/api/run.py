"""Console entry point for the API development server."""

from __future__ import annotations


def main() -> None:
    import uvicorn

    uvicorn.run("irishclinicalrag.api.app:app", host="0.0.0.0", port=8000)

