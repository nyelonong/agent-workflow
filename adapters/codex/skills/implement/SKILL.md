---
name: implement
description: Use before changing production code. Settle structure, use test-first for reproducible regressions, and prove the smallest approved change.
---

# Implement

Confirm authorization under AGENTS.md and the shared technical-plan contract. A clear routine implementation request may already supply approval; state the short approach and tasks without asking again. Otherwise obtain approval of the one technical plan before editing. Preserve approval for in-scope corrections and ordinary implementation choices. Changed outcome, scope, authority or material risk requires renewed approval. Implementation approval does not replace exact-state pre-commit review or authorization for sensitive or external actions.

Classify material failure outcomes using AGENTS.md. Consequential work stays with the parent. This adapter has no automatic model handoff. Use native isolated writers only when explicitly requested or approved parallel work requires isolation; give each exact file ownership, acceptance criteria, boundaries and required evidence. The parent owns user decisions, actual diff review, fresh checks and commits.

Settle placement, boundaries, consuming interfaces, behavior branches and ownership before editing. Use the global testing baseline: test-first for bugs and reproducible regressions. Verify intended failures before correcting them. For new behavior choose an appropriate sequence and meaningful boundary tests derived from the requirement. Use the smallest useful proof; implementation mirrors and call-count-only mocks do not establish behavior.

For prose, presentation, mechanical edits and simple wiring, explain why new tests add little value and run the narrowest relevant parsing, lint, typecheck, build or direct inspection. If reproduction requires an unavailable environment, record the strongest available evidence and the exact gap rather than guessing a fix or inventing passing coverage.

Inspect relevant callers, contracts and failure paths. Contribute changes and initial proof to the shared workflow's continuous closeout; do not require review/verify skill calls to advance a phase. Keep the unit uncommitted through required review and exact-state task-review. Follow the shared evidence-reuse, correction and delivery rules, including fingerprint verification immediately before staging.

Commit one verified logical unit with its tests, staging only task-owned paths. Never create a commit solely to mark a red-green loop or a partial milestone. Continue approved work after passing checks and commits; stop for required review or decisions. Report fresh evidence and its limits before claiming completion.
