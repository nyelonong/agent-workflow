---
name: workflow
description: Runs the personal adaptive idea-to-commit workflow. Use when the user asks for the workflow or wants a change carried through approval, implementation, review, verification, and commit.
---

# Workflow

Follow the global personal engineering policy. Use the runtime's native user-decision and agent facilities; never claim a tool or enforcement mechanism that the runtime does not provide.

## Entry

- For a clear, routine single change, skip specification and plan artifacts. Obtain implementation approval and continue directly.
- For fuzzy work, shape a concise specification and stop for approval.
- For approved multi-task work, consult exactly one `oracle`, reconcile its advice, write one ordered plan, and stop for plan approval.
- Read-only investigation, review, and verification do not require implementation approval.

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
