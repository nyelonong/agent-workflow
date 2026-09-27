---
name: finish
description: "Close a completed plan: run the repository's full gate against the integrated result, then hand the merge decision to the user. Use when a plan's last task is verified."
---

# Finish

When a plan's last task is verified, load `review` and inspect the integrated diff against the approved specification and plan. Resolve P0 and P1 findings before running the repository's full gate against the integrated result. Per-task review and evidence prove each task; they do not prove the whole built from them.

Use the repository's documented full gate; when none exists, use the widest command set the repository supports: typecheck, lint, and the full test suite.

After integrated review and the full gate pass, set the plan's `next:` line to the merge decision. Present that decision with a recommendation: merge, open a pull request, keep, or discard. Include the final review verdict, gate evidence, and residual risks. The decision is the user's; state your recommendation and its reason first.

Perform cleanup only after the selected decision explicitly authorizes the exact action. Never delete a branch or worktree or discard changes until its work is integrated or durably preserved and the user has approved the cleanup. Hand a failing review or gate to `investigate` when the cause is unknown or `implement` when the cause and required change are clear.

A passing gate does not authorize a commit before its required user review, or any remote action. When no final action is authorized, present the required decision and stop.
