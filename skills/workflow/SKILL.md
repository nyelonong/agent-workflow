---
name: workflow
description: Runs the personal adaptive idea-to-commit workflow. Use when the user asks for the workflow or wants a change carried through approval, implementation, review, verification, and commit.
---

# Workflow

Follow the global personal engineering policy. Use the runtime's native user-decision and agent facilities; never claim a tool or enforcement mechanism that the runtime does not provide.

## Entry

- For a clear, routine single change, skip specification and plan artifacts. Obtain implementation approval and continue directly.
- For fuzzy work, shape a concise specification, then run the `task-review` `review-doc` gate on the file and stop until the human approves it there.
- For approved multi-task work, consult at most one `architect`, and only when an independent view materially improves the plan. Reconcile its advice, write one ordered plan, then run the `task-review` `review-doc` gate on the plan file and stop until the human approves it there.
- Read-only investigation, review, and verification do not require implementation approval.

## Specification and plan ownership

A specification archives the approved decisions; a plan derives from them and
adds no new ones.

- The specification owns approved architecture and boundaries, diagrams that
  clarify material structure or flow, boundary-level request, function, and
  data flows, database design, ownership, lifecycle, and invariants, and
  inbound and outbound data contracts.
- The plan references those decisions and owns their exact repository mapping,
  internal function-call seams, migration mechanics, sequencing, compatibility
  work, and verification. It never duplicates or silently redesigns the
  specification.

After writing or materially revising either artifact, present it for approval
and stop before implementation. A specification approval authorizes planning
only; a single-change option must explicitly authorize implementation. A
material scope change needs new approval.

## Implementation

The parent implements one approved task or tightly coupled unit at a time and owns every user decision. Use a writer only when the global consequence policy requires isolation or the user requests delegation. Do not launch generic subagents for ordinary work.

Choose test-first development for observable behavior and reproducible regressions. Use proportional fresh verification for prose, configuration, mechanical changes, and simple wiring.

## User review

Before each task commit, show one complete uncommitted review packet:

- the approved criterion;
- the complete diff;
- affected callers and interfaces;
- tests and exact results;
- assumptions and trade-offs;
- residual risks and evidence limits.

Wait for explicit user approval. Apply approved corrections in scope. If reviewed production behavior materially changes, show the correction delta and obtain renewed approval before commit.

## Independent review

Work outside the global independent-review boundary receives parent verification and user review, with no mandatory subagent review. When the boundary applies, launch at most one fresh `reviewer` over the integrated change before completion. The reviewer is read-only and independent from the author. One focused follow-up may check accepted corrections; do not start an open-ended reviewer loop.

## Verification and finish

After the last relevant change, run focused checks and the repository-required gate. Inspect the staged paths, commit one verified logical unit, and report the evidence and limits. A local commit does not authorize a push, pull request, merge, release, deployment, publication, message, or other remote mutation. Obtain explicit approval for the exact remote action.

Continue through approved local work without pausing at passing tests, task boundaries, or commits. Stop only for a required decision, external blocker, user review, remote-action approval, or completion.

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
