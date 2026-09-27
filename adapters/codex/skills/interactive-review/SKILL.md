---
name: interactive-review
description: Run a read-only, group-by-group code review
---
Conduct an interactive code review of the repository and comparison supplied by the user. Infer the active repository when omitted; establish the comparison from the existing upstream or remote default branch. Ask if that choice remains ambiguous. Read-only applies to production files; the review-progress record below is the sole permitted local write.

First inspect repository status and remotes, then fetch the existing relevant remote. Do not invent a remote when none exists. Preserve all existing worktree changes. Do not edit production files, commit, stash, move files, run migrations, push, rebase, reset, or run finish gates unless the user explicitly asks later.

Before reviewing, establish a durable review-progress record. If I supply a related plan, use its `Review progress` section; otherwise create `docs/reviews/YYYY-MM-DD-<topic>-review.md`. Record the comparison ref, numbered groups, status, findings, and deferred fixes. Update this record after every group.

Inspect the complete comparison diff with the actual repository path and confirmed refs, using `rtk git diff --binary --full-index`. State separately whether staged, unstaged and untracked work is included; never imply those were covered by a committed range alone.

Run the review interactively:

1. Start with an overview: ahead/behind, commits, diff size, logical changed-file groups, and the requirement or plan item each group serves.
2. Review exactly one logical file or tightly related group at a time.
3. For each group provide a detailed review packet:
   - paths and the requirement, acceptance criterion, or risk addressed;
   - relevant unified diff with exact line references;
   - a plain-English before/after behavior explanation for each material hunk;
   - affected callers, data flow, configuration, interfaces, and error paths;
   - expected behavior, edge cases, regressions, and compatibility concerns;
   - relevant tests: what each proves, what it does not prove, and missing evidence;
   - concrete questions or concerns, with the smallest credible next check or fix;
   - verdict: **OK**, **question**, or **concern**.
4. Stop after each group and wait for my response. I may ask questions, request deeper inspection, mark it reviewed, or skip it. Treat `ok` as marking the current group **reviewed**; treat `skip` as **skipped**.
5. Update the progress record after every response. Record concerns as deferred fixes.
6. Keep review and execution as separate phases: until every group has been reviewed or skipped and the final ledger is presented, do not implement fixes, run implementation validation, invoke workers, start a correction workflow, or select an execution path. Read-only inspection needed to answer a review question is allowed.
7. Do not turn skipped groups into claimed deep review coverage.

After the last group, write a detailed review ledger: total groups; reviewed, skipped, and questioned counts; each verdict; findings and their evidence; deferred fixes; validation run; and evidence still missing. Stop for my decision after presenting that ledger. Only after I approve selected fixes may you select the proportionate implementation path (direct, plan, or subagent workflow) and obtain any further required implementation approval before editing code.

Review against the stated specification or requirements before general quality. Cite concrete paths and lines for findings. Keep the response concise and do not provide one large final summary unless I request one.
