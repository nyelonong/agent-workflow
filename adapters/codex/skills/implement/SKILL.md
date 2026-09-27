---
name: implement
description: Use before changing production code. Choose risk-based TDD or proportional verification, then implement the smallest correct change.
---

# Implement

Confirm explicit approval of the current scope and execution path. When a plan applies it must be approved; specification approval alone does not authorize a multi-task implementation. A clear routine change needs an explicit implementation decision, not a specification. Preserve existing approval for in-scope corrections; ask only for a material unresolved decision or scope change.

Classify material failure outcomes using AGENTS.md. Consequential work stays with the parent. This adapter has no automatic model handoff. Use native isolated writers only when explicitly requested or approved parallel work requires isolation; give each exact file ownership, acceptance criteria, boundaries and required evidence. The parent owns user decisions, actual diff review, fresh checks and commits.

Use test-first for bugs, stateful logic, business rules, validation, parsers, public contracts and reproducible regressions. Identify distinct observable behaviors and risks, add focused tests and verify they fail for the intended reason, make the smallest correction, then run focused tests and relevant checks. Use the smallest useful set of tests; tests that only mirror implementation or mock calls do not establish behavior.

For prose, presentation, mechanical edits and simple wiring, explain why new tests add little value and run the narrowest relevant parsing, lint, typecheck, build or direct inspection. If reproduction requires an unavailable environment, record the strongest available evidence and the exact gap rather than guessing a fix or inventing passing coverage.

Inspect callers, contracts and failure paths as warranted by the change. After implementation use `review` for parent inspection and `verify` for fresh evidence. Keep the unit uncommitted until the complete review packet has explicit user approval. Preserve any required fresh independent review before completion; direct implementation never waives it. If a correction materially changes reviewed behavior, show the delta and obtain renewed approval.

Commit one verified logical unit with its tests, staging only task-owned paths. Never create a commit solely to mark a red-green loop or a partial milestone. Continue approved work after passing checks and commits; stop for required review or decisions. Report fresh evidence and its limits before claiming completion.
