# System architecture

```mermaid
flowchart LR
    A["Authoritative Irish source"] --> B["Immutable downloader"]
    B --> C["Manifest + SHA-256"]
    B --> D["PDF / HTML parser"]
    D --> E["Section-aware chunker"]
    E --> F["Validated chunk JSONL"]
    F --> G["BM25 retriever"]
    F --> H["Dense retriever"]
    G --> I["Reciprocal Rank Fusion"]
    H --> I
    I --> J["Reranker interface"]
    J --> K["Evidence contract"]
    K --> L["Safety + generation"]
    L --> M["FastAPI / web UI"]
```

## Design boundaries

- Ingestion never silently overwrites raw material; blobs are addressed by checksum.
- Metadata is part of the chunk model and is returned with every retrieval result.
- Sparse and dense retrieval can be evaluated independently.
- Fusion consumes ranks, avoiding invalid comparison of unrelated score scales.
- Model-backed embeddings, rerankers, and generation providers are replaceable.
- Retrieval-only operation requires no external LLM and remains testable offline.

