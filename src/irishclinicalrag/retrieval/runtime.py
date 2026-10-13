"""Fingerprint-aware, in-process caching for immutable retrieval components."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock

from irishclinicalrag.models import EvidenceChunk, RetrieveResponse
from irishclinicalrag.pipeline import RetrievalEngine, load_chunks
from irishclinicalrag.settings import Settings, load_settings

FileSignature = tuple[tuple[str, int, int], ...]


class RetrievalRuntimeUnavailable(RuntimeError):
    """Raised when a usable corpus/configuration snapshot cannot be prepared."""


@dataclass(frozen=True, slots=True)
class RuntimeState:
    chunks: list[EvidenceChunk]
    settings: Settings
    engine: RetrievalEngine
    signature: FileSignature
    generation: int
    loaded_at: datetime


@dataclass(frozen=True, slots=True)
class RuntimeRetrieval:
    response: RetrieveResponse
    settings: Settings
    component_cache_hit: bool
    cache_generation: int


class RetrievalRuntime:
    """Reuse corpus, index, retriever, and reranker adapters until files change.

    Query strings and responses are never cached. The cache contains only public corpus
    data, model adapters, and configuration so a production-like process does not retain
    raw health questions for performance reasons.
    """

    def __init__(self, data_dir: Path, config_path: Path) -> None:
        self.data_dir = data_dir
        self.config_path = config_path
        self._lock = RLock()
        self._state: RuntimeState | None = None
        self._generation = 0
        self._model_warm_error: str | None = None

    def _signature(self) -> FileSignature:
        paths = (
            self.config_path,
            self.data_dir / "chunks" / "chunks.jsonl",
            self.data_dir / "index" / "dense-index.json",
            self.data_dir / "index" / "dense-vectors.f32",
        )
        signature = []
        for path in paths:
            try:
                stat = path.stat()
                signature.append((str(path.resolve()), stat.st_mtime_ns, stat.st_size))
            except FileNotFoundError:
                signature.append((str(path.resolve()), -1, -1))
        return tuple(signature)

    def _build_state(self, signature: FileSignature) -> RuntimeState:
        chunks = load_chunks(self.data_dir)
        if not chunks:
            raise RetrievalRuntimeUnavailable("corpus_unavailable")
        settings = load_settings(self.config_path)
        engine = RetrievalEngine(
            chunks,
            settings,
            data_dir=self.data_dir,
            method=settings.retrieval.default_method,
        )
        self._generation += 1
        return RuntimeState(
            chunks=chunks,
            settings=settings,
            engine=engine,
            signature=signature,
            generation=self._generation,
            loaded_at=datetime.now(UTC),
        )

    def prepare(self) -> tuple[RuntimeState, bool]:
        signature = self._signature()
        with self._lock:
            if self._state is not None and self._state.signature == signature:
                return self._state, True
            state = self._build_state(signature)
            final_signature = self._signature()
            if final_signature != signature:
                state = self._build_state(final_signature)
            self._state = state
            self._model_warm_error = None
            return state, False

    def retrieve(self, question: str) -> RuntimeRetrieval:
        state, cache_hit = self.prepare()
        response = state.engine.retrieve(question)
        metadata = response.retrieval_metadata.model_copy(
            update={
                "parameters": {
                    **response.retrieval_metadata.parameters,
                    "component_cache_hit": cache_hit,
                    "component_cache_generation": state.generation,
                }
            }
        )
        return RuntimeRetrieval(
            response=response.model_copy(update={"retrieval_metadata": metadata}),
            settings=state.settings,
            component_cache_hit=cache_hit,
            cache_generation=state.generation,
        )

    def chunks(self) -> list[EvidenceChunk]:
        state, _ = self.prepare()
        return list(state.chunks)

    def warm_models(self) -> dict[str, str | int | bool]:
        state, cache_hit = self.prepare()
        status: dict[str, str | int | bool] = {
            "component_cache_hit": cache_hit,
            "component_cache_generation": state.generation,
        }
        try:
            status.update(state.engine.warm_models())
        except (OSError, RuntimeError):
            self._model_warm_error = "dense_model_unavailable"
            status.update({"dense": "unavailable", "ready": False})
            return status
        self._model_warm_error = None
        status["ready"] = True
        return status

    def health(self) -> dict[str, str | int | bool]:
        try:
            state, cache_hit = self.prepare()
        except (FileNotFoundError, RetrievalRuntimeUnavailable):
            return {
                "status": "not_ready",
                "ready": False,
                "error_code": "corpus_or_config_missing",
                "indexed_chunks": 0,
                "indexed_documents": 0,
                "semantic_index": False,
                "component_cache_loaded": False,
                "component_cache_generation": self._generation,
            }
        except (OSError, RuntimeError, ValueError):
            return {
                "status": "not_ready",
                "ready": False,
                "error_code": "retrieval_runtime_invalid",
                "indexed_chunks": 0,
                "indexed_documents": 0,
                "semantic_index": False,
                "component_cache_loaded": False,
                "component_cache_generation": self._generation,
            }
        if self._model_warm_error:
            return {
                "status": "not_ready",
                "ready": False,
                "error_code": self._model_warm_error,
                "indexed_chunks": len(state.chunks),
                "indexed_documents": len({chunk.document_id for chunk in state.chunks}),
                "semantic_index": (self.data_dir / "index" / "dense-index.json").exists(),
                "component_cache_loaded": True,
                "component_cache_generation": state.generation,
            }
        return {
            "status": "ok",
            "ready": True,
            "indexed_chunks": len(state.chunks),
            "indexed_documents": len({chunk.document_id for chunk in state.chunks}),
            "semantic_index": (self.data_dir / "index" / "dense-index.json").exists(),
            "component_cache_loaded": True,
            "component_cache_hit": cache_hit,
            "component_cache_generation": state.generation,
        }
