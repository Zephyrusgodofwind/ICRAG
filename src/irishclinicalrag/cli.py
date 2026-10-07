"""Command-line entry point for reproducible pipeline operations."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from irishclinicalrag.models import ManifestRecord
from irishclinicalrag.pipeline import ingest_catalog, load_chunks, load_source_catalog, retrieve
from irishclinicalrag.retrieval.index import build_dense_index
from irishclinicalrag.settings import load_settings
from irishclinicalrag.storage import read_jsonl
from irishclinicalrag.validation.corpus import validate_corpus


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="irishclinicalrag")
    parser.add_argument("--config", type=Path, default=Path("configs/default.json"))
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest = subparsers.add_parser("ingest", help="download, parse, and chunk source catalog")
    ingest.add_argument("catalog", type=Path, nargs="?", default=Path("configs/sources.json"))

    validate = subparsers.add_parser("validate", help="validate corpus metadata and integrity")
    validate.add_argument("catalog", type=Path, nargs="?", default=Path("configs/sources.json"))

    build_index = subparsers.add_parser("build-index", help="build a persistent semantic index")
    build_index.add_argument("--model", default=None)

    retrieve_parser = subparsers.add_parser("retrieve", help="run evidence retrieval")
    retrieve_parser.add_argument("query")
    retrieve_parser.add_argument(
        "--method", choices=("bm25", "dense", "hybrid", "hybrid-rerank"), default=None
    )
    retrieve_parser.add_argument("--debug", action="store_true")
    retrieve_parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    args = build_parser().parse_args(argv)
    settings = load_settings(args.config)
    if args.command == "ingest":
        chunks = ingest_catalog(args.catalog, args.data_dir, settings)
        print(f"Ingested {len(chunks)} chunks into {args.data_dir / 'chunks' / 'chunks.jsonl'}")
        return 0

    if args.command == "validate":
        sources = load_source_catalog(args.catalog)
        records = read_jsonl(
            args.data_dir / "manifests" / "acquisitions.jsonl", ManifestRecord
        )
        latest_processed = {
            record.document_id: record
            for record in records
            if record.processing_status == "processed"
        }
        report = validate_corpus(
            sources, list(latest_processed.values()), load_chunks(args.data_dir)
        )
        print(report.model_dump_json(indent=2))
        return 0 if report.valid else 1

    if args.command == "build-index":
        chunks = load_chunks(args.data_dir)
        model_name = args.model or settings.retrieval.dense_model
        metadata = build_dense_index(
            chunks,
            args.data_dir / "index",
            model_name=model_name,
            query_prefix=settings.retrieval.dense_query_prefix,
        )
        print(
            f"Built {metadata.backend} index: {len(metadata.chunk_ids)} chunks, "
            f"{metadata.dimensions} dimensions, model={metadata.model_name}"
        )
        return 0

    response = retrieve(
        args.query,
        load_chunks(args.data_dir),
        settings,
        data_dir=args.data_dir,
        method=args.method or settings.retrieval.default_method,
    )
    if args.as_json:
        print(response.model_dump_json(indent=2))
        return 0
    print(f"{response.retrieval_metadata.method} - {response.retrieval_metadata.latency_ms:.1f} ms")
    if args.debug:
        parameters = response.retrieval_metadata.parameters
        print(
            f"backend={parameters.get('dense_backend')} "
            f"model={parameters.get('dense_model') or 'n/a'} "
            f"corpus={parameters.get('corpus_fingerprint') or 'unversioned'}"
        )
    for item in response.evidence:
        page = f", page {item.chunk.page_number}" if item.chunk.page_number else ""
        print(f"\n[{item.rank}] {item.chunk.source}: {item.chunk.title}{page}")
        print(f"score={item.score:.6f}  {item.chunk.url}")
        if args.debug:
            components = "  ".join(
                f"{name}={value:.6f}" for name, value in sorted(item.component_scores.items())
            )
            print(f"components: {components}")
        print(item.chunk.content[:700].replace("\n", " "))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
