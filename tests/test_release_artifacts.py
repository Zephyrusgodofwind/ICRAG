import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_release_documentation_and_screenshots_are_present() -> None:
    required_text = [
        "README.md",
        "docs/METHODOLOGY.md",
        "docs/DAY7_VERIFICATION.md",
        "docs/ROADMAP.md",
        "docs/PORTFOLIO.md",
        "docs/architecture/system.md",
    ]
    required_images = [
        "docs/assets/irishclinicalrag-grounded.png",
        "docs/assets/irishclinicalrag-workspace.png",
        "docs/assets/irishclinicalrag-provenance.png",
    ]

    for relative_path in required_text:
        path = ROOT / relative_path
        assert path.is_file(), relative_path
        assert path.read_text(encoding="utf-8").strip(), relative_path

    for relative_path in required_images:
        path = ROOT / relative_path
        assert path.is_file(), relative_path
        assert path.stat().st_size > 10_000, relative_path


def test_readme_headline_metrics_match_canonical_results() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    metrics = json.loads(
        (ROOT / "experiments/results/day4/metrics.json").read_text(encoding="utf-8")
    )
    labels = {
        "bm25": "BM25",
        "dense": "Dense",
        "hybrid": "Hybrid",
        "hybrid-rerank": "Hybrid + reranker",
    }

    for method, label in labels.items():
        reviewed = metrics["retrieval"][method]["curated"]
        expected = (
            f"| {label} | {reviewed['recall@5']:.3f} | "
            f"{reviewed['mrr']:.3f} |"
        )
        assert expected in readme
