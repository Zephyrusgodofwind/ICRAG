"""Required retrieval and query endpoints with stable Pydantic contracts."""

from __future__ import annotations

import json
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from irishclinicalrag.generation.providers import provider_from_settings
from irishclinicalrag.generation.service import answer_from_evidence
from irishclinicalrag.models import AnswerResponse, QueryRequest, RetrieveResponse
from irishclinicalrag.observability.events import QueryEvent, QueryEventLogger
from irishclinicalrag.observability.metrics import MetricsStore
from irishclinicalrag.retrieval.runtime import (
    RetrievalRuntime,
    RetrievalRuntimeUnavailable,
    RuntimeRetrieval,
)
from irishclinicalrag.safety.policy import is_emergency_query


def create_app(
    data_dir: Path = Path("data"),
    config_path: Path = Path("configs/default.json"),
    frontend_dir: Path = Path("frontend"),
    query_event_logger: QueryEventLogger | None = None,
    retrieval_runtime: RetrievalRuntime | None = None,
    warm_models: bool | None = None,
) -> FastAPI:
    runtime = retrieval_runtime or RetrievalRuntime(data_dir, config_path)
    should_warm_models = (
        warm_models
        if warm_models is not None
        else os.environ.get("IRISHCLINICALRAG_WARM_MODELS", "0") == "1"
    )
    runtime_logger = logging.getLogger("uvicorn.error")

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if should_warm_models:
            try:
                warm_status = await run_in_threadpool(runtime.warm_models)
                runtime_logger.info(
                    json.dumps(
                        {"event": "retrieval_runtime_warm", **warm_status},
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                )
            except Exception:
                runtime_logger.warning(
                    '{"event":"retrieval_runtime_warm","status":"failed"}'
                )
        yield

    app = FastAPI(
        title="IrishClinicalRAG API",
        version="0.1.0",
        description="Evidence retrieval from authoritative Irish clinical guidance.",
        lifespan=lifespan,
    )
    app.state.retrieval_runtime = runtime
    metrics = MetricsStore()
    query_events = query_event_logger or QueryEventLogger(logging.getLogger("uvicorn.error"))

    def run_retrieval(question: str) -> RuntimeRetrieval:
        try:
            return runtime.retrieve(question)
        except HTTPException:
            raise
        except (FileNotFoundError, RetrievalRuntimeUnavailable) as exc:
            raise HTTPException(status_code=503, detail="No corpus index is available") from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail="Retrieval failed") from exc

    def emit_event(
        *,
        request_id: str,
        route: str,
        question: str,
        started: float,
        outcome: str,
        retrieval: RetrieveResponse | None = None,
        answer: AnswerResponse | None = None,
        error_status: str | None = None,
    ) -> float:
        total_latency_ms = (time.perf_counter() - started) * 1000
        evidence = answer.evidence if answer else retrieval.evidence if retrieval else []
        retrieval_metadata = (
            answer.retrieval_metadata
            if answer
            else retrieval.retrieval_metadata
            if retrieval
            else None
        )
        generation_metadata = answer.generation_metadata if answer else None
        query_events.emit(
            QueryEvent(
                request_id=request_id,
                route=route,
                outcome=outcome,
                query_characters=len(question),
                query_token_count=len(question.split()),
                total_latency_ms=round(total_latency_ms, 3),
                retrieval_method=retrieval_metadata.method if retrieval_metadata else None,
                retrieval_latency_ms=(
                    round(retrieval_metadata.latency_ms, 3) if retrieval_metadata else 0.0
                ),
                component_cache_hit=(
                    retrieval_metadata.parameters.get("component_cache_hit")
                    if retrieval_metadata
                    else None
                ),
                generation_provider=(
                    generation_metadata.provider if generation_metadata else None
                ),
                generation_model=generation_metadata.model if generation_metadata else None,
                generation_latency_ms=(
                    round(generation_metadata.latency_ms, 3) if generation_metadata else 0.0
                ),
                generation_fallback_used=(
                    generation_metadata.fallback_used if generation_metadata else False
                ),
                generation_fallback_reason=(
                    generation_metadata.fallback_reason if generation_metadata else None
                ),
                answer_token_count=len(answer.answer.split()) if answer else 0,
                evidence_count=len(evidence),
                retrieved_documents=list(
                    dict.fromkeys(item.chunk.document_id for item in evidence)
                ),
                retrieval_scores=[round(item.score, 6) for item in evidence],
                safety_status=answer.safety_status if answer else None,
                error_status=error_status,
            )
        )
        return total_latency_ms

    @app.get("/health/live")
    def liveness() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health")
    def health(response: Response) -> dict[str, str | int | bool]:
        status = runtime.health()
        if not status["ready"]:
            response.status_code = 503
        return status

    @app.post("/retrieve", response_model=RetrieveResponse)
    def retrieve_endpoint(request: QueryRequest) -> RetrieveResponse:
        started = time.perf_counter()
        request_id = str(uuid4())
        try:
            outcome = run_retrieval(request.question)
        except HTTPException as exc:
            elapsed = emit_event(
                request_id=request_id,
                route="retrieve",
                question=request.question,
                started=started,
                outcome="error",
                error_status=f"http_{exc.status_code}",
            )
            metrics.record_failure(route="retrieve", total_latency_ms=elapsed)
            raise
        response = outcome.response
        elapsed = emit_event(
            request_id=request_id,
            route="retrieve",
            question=request.question,
            started=started,
            outcome="success",
            retrieval=response,
        )
        metrics.record_success(
            route="retrieve",
            retrieval_latency_ms=response.retrieval_metadata.latency_ms,
            generation_latency_ms=0.0,
            total_latency_ms=elapsed,
            evidence_count=len(response.evidence),
            retrieval_performed=True,
            generation_performed=False,
            component_cache_hit=outcome.component_cache_hit,
        )
        return response

    @app.post("/query", response_model=AnswerResponse)
    def query_endpoint(request: QueryRequest) -> AnswerResponse:
        started = time.perf_counter()
        request_id = str(uuid4())
        retrieval: RetrieveResponse | None = None
        component_cache_hit: bool | None = None
        try:
            if is_emergency_query(request.question):
                answer = answer_from_evidence(
                    request.question,
                    [],
                    retrieval_metadata={
                        "method": "skipped-emergency-safety",
                        "candidates": 0,
                        "returned": 0,
                        "latency_ms": 0,
                    },
                )
            else:
                outcome = run_retrieval(request.question)
                retrieval = outcome.response
                component_cache_hit = outcome.component_cache_hit
                provider_configuration_fallback = False
                try:
                    provider = provider_from_settings(outcome.settings.generation)
                except RuntimeError:
                    provider = None
                    provider_configuration_fallback = True
                answer = answer_from_evidence(
                    request.question,
                    retrieval.evidence,
                    retrieval.retrieval_metadata,
                    provider=provider,
                )
                if provider_configuration_fallback and answer.evidence_sufficient:
                    generation_metadata = answer.generation_metadata.model_copy(
                        update={
                            "fallback_used": True,
                            "fallback_reason": "provider_configuration_unavailable",
                        }
                    )
                    answer = answer.model_copy(
                        update={"generation_metadata": generation_metadata}
                    )
        except HTTPException as exc:
            elapsed = emit_event(
                request_id=request_id,
                route="query",
                question=request.question,
                started=started,
                outcome="error",
                retrieval=retrieval,
                error_status=f"http_{exc.status_code}",
            )
            metrics.record_failure(route="query", total_latency_ms=elapsed)
            raise
        except Exception as exc:
            elapsed = emit_event(
                request_id=request_id,
                route="query",
                question=request.question,
                started=started,
                outcome="error",
                retrieval=retrieval,
                error_status="http_500",
            )
            metrics.record_failure(route="query", total_latency_ms=elapsed)
            raise HTTPException(status_code=500, detail="Answer generation failed") from exc

        elapsed = emit_event(
            request_id=request_id,
            route="query",
            question=request.question,
            started=started,
            outcome="success",
            answer=answer,
        )
        metrics.record_success(
            route="query",
            retrieval_latency_ms=answer.retrieval_metadata.latency_ms,
            generation_latency_ms=answer.generation_metadata.latency_ms,
            total_latency_ms=elapsed,
            evidence_count=len(answer.evidence),
            retrieval_performed=answer.retrieval_metadata.method != "skipped-emergency-safety",
            generation_performed=not answer.generation_metadata.provider.startswith("skipped-"),
            generation_fallback_used=answer.generation_metadata.fallback_used,
            component_cache_hit=component_cache_hit,
            safety_status=answer.safety_status,
        )
        return answer

    @app.get("/sources")
    def sources() -> list[dict[str, str | None]]:
        unique = {}
        try:
            chunks = runtime.chunks()
        except (FileNotFoundError, RetrievalRuntimeUnavailable) as exc:
            raise HTTPException(status_code=503, detail="No corpus index is available") from exc
        for chunk in chunks:
            unique[chunk.document_id] = {
                "document_id": chunk.document_id,
                "source": chunk.source,
                "title": chunk.title,
                "url": str(chunk.url),
                "publication_date": (
                    chunk.publication_date.isoformat() if chunk.publication_date else None
                ),
                "publication_date_precision": chunk.publication_date_precision,
                "last_updated": chunk.last_updated.isoformat() if chunk.last_updated else None,
                "last_updated_precision": chunk.last_updated_precision,
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


app = create_app(
    data_dir=Path(os.environ.get("IRISHCLINICALRAG_DATA_DIR", "data")),
    config_path=Path(
        os.environ.get("IRISHCLINICALRAG_CONFIG_PATH", "configs/default.json")
    ),
    frontend_dir=Path(os.environ.get("IRISHCLINICALRAG_FRONTEND_DIR", "frontend")),
)
