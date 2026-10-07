# System architecture

```mermaid
flowchart LR
    A["Authoritative Irish source"] --> B["Immutable downloader"]
    B --> C["Manifest + SHA-256"]
    B --> D["PDF / HTML parser"]
    D --> E["Section-aware chunker"]
    E --> V["Corpus integrity gate + fingerprint"]
    V --> F["Validated chunk JSONL"]
    F --> G["BM25 retriever"]
    F --> H["Persistent BGE dense index"]
    G --> I["Reciprocal Rank Fusion"]
    H --> I
    I --> J["Cross-encoder reranker"]
    J --> K["Evidence contract"]
    K --> L["Safety + generation"]
    L --> M["FastAPI / web UI"]
```

## Design boundaries

- Ingestion never silently overwrites raw material; blobs are addressed by checksum.
- Metadata is part of the chunk model and is returned with every retrieval result.
- Sparse and dense retrieval can be evaluated independently.
- Fusion consumes ranks, avoiding invalid comparison of unrelated score scales.
- The semantic index is bound to the corpus fingerprint and exact chunk order.
- Model-backed embeddings, rerankers, and generation providers are replaceable.
- Retrieval-only operation requires no external LLM and remains testable offline.
