---
name: plan
description: Decompose an approved specification into ordered, dependency-declared tasks, each independently testable. Use when the approved spec spans more than one logical change; a single-change spec goes straight to implement.
---

# Plan

Plan only when an approved specification spans several logical changes. A single-change specification goes directly to `implement`. Consult at most one native read-only `architect` for this planning phase, and only when an independent view materially improves the plan, unless that consultation already occurred in the active workflow. Treat its output as advice; the parent resolves it against the approved specification and repository evidence. If an optional adviser is unavailable, do not invent a consultation or block settled planning solely for that reason.

Write `<repository-root>/docs/plans/YYYY-MM-DD-<topic>.md`, referencing the approved specification. Keep the plan local and uncommitted. Record the implementation baseline and a `next:` line that names plan approval before approval and the next dependency afterward. Do not restate specification-owned behavior.

Apply the shared workflow's artifact contract. Validate the specification's design coverage and record a design map to actual sections before declaring readiness; missing material decisions return to shaping. Each task names its goal, exact files and source seams, ordered changes, dependencies, authority boundaries, observable acceptance criteria, exact evidence commands and what passing proves. Classify implementation consequence and independent-review necessity separately using AGENTS.md. Credible uncertainty remains explicit; do not use keyword scores. Name the parent execution path and the review path. For genuinely complex dependencies, read [delegation planning](references/delegation-planning.md); otherwise keep work sequential.

Present the complete plan through the `task-review` `review-doc` gate and stop before implementation. Follow the Codex `task-review` skill to await the same command and apply returned annotations before re-review; do not also ask a numbered approval question. After approval the parent uses `implement` for one task or tightly coupled unit, uses the shared closeout contract for evidence, required review, exact-state approval, fingerprint verification and commit before advancing. Do not pause merely because a task passed. A material scope or plan change returns to approval; never edit the specification to disguise a mismatch.

Maintain task progress, review progress and `next:` as work proceeds. Route failed evidence to `investigate`. Use [context recovery](references/context-recovery.md) when interrupted or resuming a checkpoint. Compaction alone is not a response boundary and does not require creating a checkpoint. Finish the last task with `next: finish` and use `finish` for integrated evidence and the user's final action decision.

Record deferred work and its reason in the local plan; proposing it does not authorize implementation.
