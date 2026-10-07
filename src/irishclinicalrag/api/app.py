"""Required retrieval and query endpoints with stable Pydantic contracts."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from irishclinicalrag.generation.service import answer_from_evidence
from irishclinicalrag.models import AnswerResponse, QueryRequest, RetrieveResponse
from irishclinicalrag.observability.metrics import MetricsStore
from irishclinicalrag.pipeline import load_chunks, retrieve
from irishclinicalrag.safety.policy import is_emergency_query
from irishclinicalrag.settings import load_settings


def create_app(
    data_dir: Path = Path("data"),
    config_path: Path = Path("configs/default.json"),
    frontend_dir: Path = Path("frontend"),
) -> FastAPI:
    app = FastAPI(
        title="IrishClinicalRAG API",
        version="0.1.0",
        description="Evidence retrieval from authoritative Irish clinical guidance.",
    )
    metrics = MetricsStore()

    def run_retrieval(question: str) -> RetrieveResponse:
        try:
            chunks = load_chunks(data_dir)
            if not chunks:
                raise HTTPException(status_code=503, detail="No corpus index is available")
            response = retrieve(question, chunks, load_settings(config_path))
            metrics.record_query(response.retrieval_metadata.latency_ms)
            return response
        except HTTPException:
            metrics.record_error()
            raise
        except Exception as exc:
            metrics.record_error()
            raise HTTPException(status_code=500, detail="Retrieval failed") from exc

    @app.get("/health")
    def health() -> dict[str, str | int]:
        return {"status": "ok", "indexed_chunks": len(load_chunks(data_dir))}

    @app.post("/retrieve", response_model=RetrieveResponse)
    def retrieve_endpoint(request: QueryRequest) -> RetrieveResponse:
        return run_retrieval(request.question)

    @app.post("/query", response_model=AnswerResponse)
    def query_endpoint(request: QueryRequest) -> AnswerResponse:
        if is_emergency_query(request.question):
            return answer_from_evidence(
                request.question,
                [],
                retrieval_metadata={
                    "method": "skipped-emergency-safety",
                    "candidates": 0,
                    "returned": 0,
                    "latency_ms": 0,
                },
            )
        retrieval = run_retrieval(request.question)
        return answer_from_evidence(
            request.question,
            retrieval.evidence,
            retrieval.retrieval_metadata,
        )

    @app.get("/sources")
    def sources() -> list[dict[str, str | None]]:
        unique = {}
        for chunk in load_chunks(data_dir):
            unique[chunk.document_id] = {
                "document_id": chunk.document_id,
                "source": chunk.source,
                "title": chunk.title,
                "url": str(chunk.url),
                "publication_date": (
                    chunk.publication_date.isoformat() if chunk.publication_date else None
                ),
                "last_updated": chunk.last_updated.isoformat() if chunk.last_updated else None,
            }
        return list(unique.values())

    @app.get("/metrics")
    def get_metrics() -> dict[str, int | float]:
        return metrics.snapshot()

    if frontend_dir.is_dir():
        app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

        @app.get("/", include_in_schema=False)
        def frontend() -> FileResponse:
            return FileResponse(frontend_dir / "index.html")

        @app.get("/styles.css", include_in_schema=False)
        def frontend_styles() -> FileResponse:
            return FileResponse(frontend_dir / "styles.css", media_type="text/css")

        @app.get("/app.js", include_in_schema=False)
        def frontend_script() -> FileResponse:
            return FileResponse(frontend_dir / "app.js", media_type="text/javascript")

    return app


app = create_app()
