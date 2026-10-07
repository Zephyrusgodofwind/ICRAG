# Development workflow

## Daily closeout

Daily GitHub delivery is a project requirement, not an optional activity metric.

```powershell
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\pytest.exe --cov=irishclinicalrag --cov-report=term-missing
git status --short
git diff --check
git add <intentional-files>
git commit -m "feat: describe the coherent daily increment"
git push origin main
git status --short
```

Confirm on GitHub that the commit appears on `main` and that CI passed. Never push
secrets, source-document blobs, patient data, local indexes, or fabricated metrics.

If work is incomplete at closeout, commit only a coherent, tested slice. Do not create
empty activity commits. Record any blocker in `docs/STATUS.md` and surface it immediately.

## Verification policy

- Unit and contract tests must pass before every push.
- Retrieval experiments must record config, corpus version, timestamp, and Git SHA.
- Real clinical source acquisition runs must produce an append-only manifest record.
- Docker changes must be built and health-checked on a machine with Docker available.
- Public demo questions must be synthetic and contain no identifiable health data.

