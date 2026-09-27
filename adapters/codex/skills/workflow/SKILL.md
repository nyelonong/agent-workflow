---
name: workflow
description: "Run Zaki's adaptive idea-to-finish workflow: use only the artifacts the work earns, get one strong plan for multi-task work, implement directly in the parent, review each uncommitted task once, and finish with risk-based independent review. Use when the user invokes /skill:workflow, asks to run 'the workflow', or resumes a workflow plan."
---

# Workflow

Use the global engineering policy and the Codex adapter for approval and agent authority. The parent implements approved work directly and owns each user decision. Do not emulate runtime tools or automatic model switching.

## Choose the entry

For one clear, routine change, obtain implementation approval and use `implement`; no specification or plan is needed. For unclear work, use `shape` and stop for specification approval. An approved specification with several tasks goes to `plan`: consult at most one native read-only `architect`, and only when an independent view materially improves the plan, then reconcile the advice against repository evidence, write the ordered plan, and stop for approval. Do not consult another architect for the same planning phase. Read-only investigation, shaping and review can proceed within the user's request.

## Specification and plan ownership

A specification archives the approved decisions; a plan derives from them and adds none.

- The specification owns approved architecture and boundaries, diagrams that clarify material structure or flow, boundary-level request, function, and data flows, database design, ownership, lifecycle, and invariants, and inbound and outbound data contracts.
- The plan owns the exact repository mapping, internal function-call seams, migration mechanics, sequencing, compatibility work, and verification for those decisions. It never duplicates or silently redesigns the specification.

After writing or materially revising either artifact, run the `task-review` `review-doc` gate on the
file and stop until the human approves it there; apply every annotation it returns and re-review. Do not
also ask a separate numbered question for the same document. A specification approval authorizes planning only; a single-change entry must explicitly authorize implementation. A material scope change needs new approval.

## Schema and migrations

This runtime has no dedicated SQL skill, so the shared workflow skill owns these rules.

- Design tables only for approved current features. Keep in the database the constraints it must independently protect: identity, ownership, authorization, referential integrity, uniqueness, and enforced invariants. Keep application-owned states, transitions, formats, secret rules, and version compatibility in application code unless independent database enforcement is an approved correctness requirement.
- Prefer soft deletion for business-owned records and retain their foreign-key and ownership constraints. Add no hard-delete cascade speculatively; physical deletion needs an approved retention, privacy, or correctness need and an explicit migration design.
- Add checks, constraints, and indexes only for a current correctness requirement, a current query, a uniqueness requirement, or a measured need. Never duplicate equivalent guarantees, add speculative constraints to empty tables, or retain fields and indexes without a current reader, query, or correctness need. Preserve existing constraints unless an approved change makes them incorrect.
- After the last SQL change, run the repository's migration parser, linter, or runner when one exists, prove behavior against an isolated real database, inspect the resulting schema, and run the affected tests plus the repository-required gate.
- Verify rollback only where the repository relies on it. Never change tests or verification assets to make a schema check pass. Report skipped checks, evidence limits, and residual risks.

## Implement and review

Read the approved scope and the plan's `next:` when present. Implement one task or tightly coupled unit through `implement`. The parent retains implementation ownership; use an isolated writer only when the user requests it or approved parallel work requires separate checkouts. Never delegate an unresolved user decision.

Keep the unit uncommitted while running focused evidence and parent review. Present one complete review packet containing the criterion, complete unified diff, affected callers and error paths, exact tests and results, assumptions, trade-offs, residual risks and a verdict. This is one user review point per unit; do not automatically substitute the group-by-group `interactive-review` skill.

Stop for explicit approval of the packet. Correct approved in-scope findings and rerun evidence. When a correction materially changes reviewed behavior, show the correction delta and obtain renewed approval. Only then stage task-owned files and commit the verified logical unit. Update task progress, review progress and `next:` in the plan, then continue the next approved dependency. A passing check or commit is not a stopping point.

## Integrated review and finish

After the last unit, inspect the integrated diff against the approved scope. The independent-review boundary in AGENTS.md is separate from implementation consequence. Outside that boundary, parent verification and user review suffice. When it applies, obtain one fresh native read-only `reviewer` before completion; supply the criterion, actual changed files, diff and evidence limits. If that reviewer is unavailable, stop until one is available or the user explicitly waives the missing independent review. Direct implementation and interactive review never imply that waiver.

Inspect the findings yourself. Resolve concrete findings once, using the same approval and verification gates; use one focused follow-up when corrections alter reviewed behavior. A new consequential problem in that follow-up requires reconsideration or a user decision. Use `finish` for the full repository gate and final handoff. Remote writes require explicit authorization for the exact action.

## Continuity

Keep approved scope, baseline, task progress, review progress and `next:` in the local plan. Resume using `resume-plan` and its referenced recovery procedure. Compaction does not end the task. Read durable artifacts and supported session history when needed; if missing approval or scope cannot be recovered, ask instead of assuming. Do not reopen settled decisions merely because a new session started.
