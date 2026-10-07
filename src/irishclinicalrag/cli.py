"""Command-line entry point for reproducible pipeline operations."""

from __future__ import annotations

import argparse
from pathlib import Path

from irishclinicalrag.pipeline import ingest_catalog, load_chunks, retrieve
from irishclinicalrag.settings import load_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="irishclinicalrag")
    parser.add_argument("--config", type=Path, default=Path("configs/default.json"))
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest = subparsers.add_parser("ingest", help="download, parse, and chunk source catalog")
    ingest.add_argument("catalog", type=Path, nargs="?", default=Path("configs/sources.json"))

    retrieve_parser = subparsers.add_parser("retrieve", help="run hybrid evidence retrieval")
    retrieve_parser.add_argument("query")
    retrieve_parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = load_settings(args.config)
    if args.command == "ingest":
        chunks = ingest_catalog(args.catalog, args.data_dir, settings)
        print(f"Ingested {len(chunks)} chunks into {args.data_dir / 'chunks' / 'chunks.jsonl'}")
        return 0

    response = retrieve(args.query, load_chunks(args.data_dir), settings)
    if args.as_json:
        print(response.model_dump_json(indent=2))
        return 0
    print(f"{response.retrieval_metadata.method} — {response.retrieval_metadata.latency_ms:.1f} ms")
    for item in response.evidence:
        page = f", page {item.chunk.page_number}" if item.chunk.page_number else ""
        print(f"\n[{item.rank}] {item.chunk.source}: {item.chunk.title}{page}")
        print(f"score={item.score:.6f}  {item.chunk.url}")
        print(item.chunk.content[:700].replace("\n", " "))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
