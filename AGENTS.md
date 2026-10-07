# IrishClinicalRAG repository instructions

These instructions apply to every file and every contributor/agent in this repository.

## Source of truth

Before making project changes, read `IrishClinicalRAG_PROJECT_PLAN.md` in full.
Treat it as the authoritative product, engineering, research, safety, evaluation,
documentation, and deadline specification. When trade-offs are required, follow its
deadline-protection order and preserve every non-negotiable requirement.

Do not claim the project is complete until the charter's definition of done is met.
Do not invent evaluation results, medical claims, corpus coverage, or deployment status.

## Daily GitHub discipline — non-negotiable

Every active development day must end with the day's coherent, verified work committed
and pushed to the configured GitHub repository.

Daily closeout:

1. Run the tests and relevant checks.
2. Update `docs/STATUS.md` with truthful progress and blockers.
3. Inspect `git diff` and ensure no secrets, patient data, generated corpus blobs, or
   unrelated files are staged.
4. Use a meaningful conventional commit message (`feat:`, `test:`, `eval:`, `docs:`,
   `fix:`, `chore:`).
5. Push the current branch to GitHub and verify the remote accepted the commit.

Never manufacture empty commits merely to create activity. A daily push represents
real, reviewable project progress. If authentication, connectivity, or repository access
blocks a push, keep the verified local commit, document the exact blocker, and surface
it immediately; retry as soon as access is restored.

## Engineering guardrails

- Preserve metadata from acquisition through the final answer and UI.
- Keep raw source downloads checksum-addressed and never silently overwrite them.
- Keep sparse, dense, hybrid, and reranked retrieval independently evaluable.
- Keep generation providers replaceable and retrieval usable without an LLM.
- Default to abstention when evidence is insufficient.
- Use only public clinical documents and synthetic/demo queries; never store patient data.
- Prefer typed, small, testable modules and environment variables for secrets.
- Keep notebooks exploratory; production logic belongs under `src/irishclinicalrag/`.
- Preserve transparent attribution for upstream ideas or reused code.

