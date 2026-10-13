from pathlib import Path


def test_container_runs_non_root_with_readiness_healthcheck() -> None:
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert "USER appuser" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "http://127.0.0.1:8000/health" in dockerfile
    assert "--start-period=5m" in dockerfile
    assert "read_only: true" in compose
    assert "no-new-privileges:true" in compose
    assert "cap_drop:\n      - ALL" in compose
    assert 'IRISHCLINICALRAG_WARM_MODELS: "1"' in compose


def test_container_entrypoint_uses_configurable_paths_and_graceful_shutdown() -> None:
    entrypoint = Path("scripts/docker-entrypoint.sh").read_text(encoding="utf-8")

    assert "${IRISHCLINICALRAG_DATA_DIR:-/app/data}" in entrypoint
    assert "${IRISHCLINICALRAG_CONFIG_PATH:-/app/configs/default.json}" in entrypoint
    assert 'exec uvicorn irishclinicalrag.api.app:app \\' in entrypoint
    assert "--timeout-graceful-shutdown 30" in entrypoint


def test_ci_builds_the_production_container() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "container-build:" in workflow
    assert "actions/checkout@v7" in workflow
    assert "actions/setup-python@v7" in workflow
    assert "docker/setup-buildx-action@v4" in workflow
    assert "docker/build-push-action@v7" in workflow
    assert "push: false" in workflow
