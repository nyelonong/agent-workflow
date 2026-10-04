---
name: workflow
description: Run the adaptive idea-to-finish workflow, or resume approved work. Owns proportional entry, artifact design, continuous closeout, evidence reuse and logical review units.
---

# Workflow

Apply the global engineering policy and relevant repository requirements. This is the shared workflow contract; native adapters supply invocation, waiting and recovery mechanics, not alternate policy. Reuse instructions and repository evidence while available and current; load a specialist or tool only for an actual need.

## Entry and design

- For a clear, routine single change, use the bounded implementation request as authorization under global policy. Default to direct parent implementation; continue without a specification, plan, or separate execution-choice question. Ask only for unresolved scope, authority, isolation or cost.
- For fuzzy work or unresolved material decisions, shape a concise specification. Consequence alone does not require a new specification when scope and decisions are settled.
- Plan only multiple logical tasks. Consult at most one read-only architect when useful, not as a prerequisite. Reconcile its advice against the approved specification and repository.
- Read-only investigation, shaping, review and verification need no implementation approval. Preserve existing authorization on resume unless scope, authority, isolation or cost materially changes.

A specification archives approved decisions; a plan derives their execution and adds none.

| Artifact | Decision-relevant coverage |
| --- | --- |
| Specification | Goal, non-goals, constraints, decision log, acceptance outcomes and proof; affected roles when defined. Architecture/boundaries, ownership/lifecycle/invariants and affected contracts: producers/consumers, transport, schema/field meanings, validation, authorization, errors, compatibility and sensitive-data handling. Diagram material structure, flow or data and failure paths. Database work includes conceptual entities, relationship cardinality, ownership, keys/constraints, query-backed indexes, retention and compatibility. Record actual section references or justified not-applicable areas in a compact design-coverage table. |
| Plan | Reference specification sections and acceptance criteria rather than restating them. Record baseline, existing dirty-path ownership, dependencies, exact paths/source seams, ordered changes, authority, evidence commands/results, risks and recovery. Classify consequence and independent-review necessity separately. Maintain task/review progress and one authoritative `next:`. |

Scale both artifacts to decisions, not the longest template. Settle material unknowns before approval; a read-before-edit list cannot hide a design decision. A task must be executable from the plan, specification and repository.

Use the shared `task-review` client `scripts/task_review.py review-doc` for new or materially revised specifications/plans. Apply annotations and re-review changed documents; walkthrough acknowledgements are not approval. Specification approval authorizes planning only; a single-change entry must explicitly authorize implementation. Plan approval authorizes its implementation. No separate chat approval competes with the document gate.

## Implementation responsibilities

The parent implements one authorized task or tightly coupled unit and owns decisions, actual diff inspection, proof and commits. Use an isolated writer only on user request or for approved parallel writers needing separate checkouts. Delegation does not waive any boundary.

Settle placement, consuming interfaces, branch representation and state ownership before editing. Use the global engineering and testing policy: test-first for reproducible bugs/regressions; choose an appropriate sequence for new behavior with meaningful boundary proof. Prose, configuration and mechanical changes may need only parsing, lint or direct checks. Preserve stricter repository requirements.

## Evidence reuse

Evidence proves a particular claim and scope, not a phase name. Reuse proof produced after the last relevant edit while relevant code, dependencies, configuration and environment remain unchanged. Refresh missing, stale or uncertain proof with the smallest necessary check. Do not reread available current instructions, repeat reports, or rerun tests merely because review, verification or approval began.

Behavior-changing corrections invalidate affected checks and review coverage; preserve unaffected evidence. Every changed reviewed state invalidates human approval, even if tests pass. A fingerprint proves identity, not behavioral sufficiency. Approval alone neither invalidates executable evidence nor supplies missing proof. Repository-required gates remain required.

## Continuous closeout

1. Assess each logical change's approved requirements, complete actual diff, relevant callers/contracts, risks and verification evidence together. Review owns acceptance/quality; verify owns evidence sufficiency/freshness. These are responsibilities within this pass, not required skill calls.
2. For material or uncertain changes inspect load-bearing seams beyond edited lines, using the strongest applicable evidence. Integrate comment/docstring/suppression auditing; do not schedule a separate comment reviewer unless explicitly requested or required by the global material-failure boundary.
3. Fix approved in-scope gaps, refresh affected proof and reassess. Requirements-first, evidence-backed P0/P1 findings block. P2 is optional; do not expand scope to eliminate it.
4. When the global independent-review boundary applies, use one fresh read-only independent reviewer for the integrated reviewable unit before its applicable delivery or safety boundary. Do not defer required review automatically until plan completion or require one reviewer per checklist task. Separately delivered units can have separate boundaries. Outside that boundary there is no mandatory subagent review. A required unavailable reviewer blocks until available or explicitly waived by the user.
5. Reuse applicable unchanged review coverage. Resolve concrete findings once; use one focused follow-up when corrections alter reviewed behavior. A new consequential problem in that follow-up requires reconsideration or a user decision. High-risk seams retain focused parent inspection.
6. Explain the change once with its criterion, callers/contracts, evidence, assumptions, trade-offs and risks. Keep the unit uncommitted; `task-review` collects the real complete diff for task-owned paths. The user records approve, request changes, return to planning or cancel there. Never replace the collected diff with a summary or duplicate chat confirmation. Changed state requires fresh human review; errors and cancellation authorize no commit.
7. On approval, run `task_review.py verify` immediately before staging. Only a matching approval fingerprint and sufficient current evidence permit staging task-owned paths and one logical commit. Repeat executable checks only if missing or invalidated, not solely after approval. Inspect staged paths, commit, and `consume` the approval. Record actual results and advance the plan's `next:` when present; continue authorized work.

A failed gate blocks; never automatically fall back to unbound chat approval. A supported replacement approval mechanism requires explicit authorization. Sensitive or external actions need their own existing authority; local approval does not authorize push, pull request, merge, deploy, publication, contact or destructive cleanup.

## Integrated finish and continuity

After the last plan task, assess the integrated result against specification and plan. Per-task checks do not alone prove interactions. Establish the repository's full gate against that result; reuse an already applicable full-gate result, or refresh it when invalidated or repository rules require it. Required independent review may be this integrated pass when no earlier delivery/safety boundary requires it; do not add a duplicate finish reviewer.

Resolve blockers through the same closeout. Report gate results, skips, evidence limits and residual risks. The final merge, pull-request, keep or discard decision stays with the user; a passing gate authorizes none of them.

A phase change, passing check, task boundary or commit is not a stop while authorized work remains. Stop for completion, external block, required decision/approval, cancellation, requested report, or a permitted honest continuation checkpoint. Automatic compaction is transparent, not a task boundary.

On resume or retry inspect durable state, supported history and available results before replaying operations. Necessary read-only checks are allowed; never blindly repeat writes or infer unknown consequential outcomes. Recover a pending review before launching another; unknown ownership blocks a duplicate launch. Keep reviewed inputs unchanged through approval use/consumption, recording operational recovery state outside the reviewed scope. Read-only roles do not edit reviewed code/data, stage, commit or remotely mutate; any necessary local metadata, outputs or private operational records need explicit scoped permission.

## Schema and migrations

Load this section before designing a schema or writing a migration; the global
policy owns only the migration-history rule.

- Design tables only for approved current features. Keep in the database the
  constraints it must independently protect: identity, ownership,
  authorization, referential integrity, uniqueness, and enforced invariants.
- Keep application-owned states, transitions, formats, secret rules, and
  version compatibility in application code, unless independent database
  enforcement is an approved correctness requirement.
- Prefer soft deletion for business-owned records and retain their foreign-key
  and ownership constraints. Add no hard-delete cascade speculatively; physical
  deletion needs an approved retention, privacy, or correctness need and an
  explicit migration design.
- Add checks, constraints, and indexes only for a current correctness
  requirement, a current query, a uniqueness requirement, or a measured need.
  Never duplicate equivalent uniqueness or index guarantees, add speculative
  constraints to empty tables, or retain fields and indexes without a current
  reader, query, or correctness requirement. Preserve existing constraints
  unless an approved change makes them incorrect.
- After the last SQL change, run the repository's migration parser, linter, or
  runner when one exists, prove behavior against an isolated real database,
  inspect the resulting schema with its required constraints and indexes, and
  run the affected tests plus the repository-required gate.
- Verify rollback only where the repository supports and relies on it. Never
  change tests or verification assets to make a schema check pass. Report
  skipped checks, evidence limits, and residual risks explicitly.
