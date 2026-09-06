---
description: Run a read-only, task-by-task interactive review of a plan against its specification
argument-hint: "<plan-path>"
---
Conduct an interactive, read-only review of the plan at `$1` against its approved
specification. This reviews the plan before implementation: the deliverable is a
revised, approved plan, not code findings.

Establish a durable review-progress record in the plan file's review-progress section
(create it if missing): numbered task groups, status, findings, and revisions. Update
it after every group.

First re-read the approved specification and the full plan. Verify the plan covers every
specification requirement — list any requirement with no owning task before the
walkthrough starts.

Run the review interactively:

1. Start with an overview: task count, parallel waves, dependency order, total estimated
   scope, and the specification items each wave serves.
2. Review exactly one task, or one tightly coupled wave, at a time. For each task
   provide a review packet:
   - the goal and the specification requirement or acceptance criterion it serves;
   - the files, seams, and step-by-step changes it plans, with exact paths;
   - whether the detail is sufficient for a cheap model to execute without judgment
     calls — flag every hidden decision, ambiguous instruction, or missing file path;
   - its acceptance criteria and evidence commands: are they runnable, and do they
     actually prove the criterion;
   - dependency, ordering, parallel-safety, and commit-boundary concerns;
   - risks, edge cases, migrations, security, or contract changes the task understates;
   - concrete questions or concerns, with the smallest credible revision;
   - verdict: **OK**, **question**, or **concern**.
3. Stop after each group and wait for my response. I may ask questions, request deeper
   inspection of the current code or spec, mark it reviewed, request a revision, or skip
   it. Treat `ok` as marking the current group **reviewed**; treat `skip` as
   **skipped**.
4. Apply approved revisions to the plan file immediately, in place, and show the revised
   text before moving on. Record every revision in the progress record.
5. Keep review and execution as separate phases: do not implement anything, run the
   plan's commands beyond read-only inspection, or start the next stage until the
   walkthrough completes and the plan is approved.

After the last group, present the final ledger: total groups; reviewed, skipped, and
revised counts; each verdict; open questions; and remaining specification gaps. Then ask
for plan approval through `ask_decision` and stop. Only explicit approval authorizes
implementation.

Review against the specification before general quality. Cite concrete plan lines and
specification items for findings. Keep the response concise; no large final summary
unless I request one.
