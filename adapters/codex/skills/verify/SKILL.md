---
name: verify
description: Prove a completion claim with fresh, proportional evidence after the last relevant change.
---

# Verify

Name the claim being verified. For a task-level claim, run the narrowest command that proves it after the last relevant change, preferring a documented focused check when one exists. Reserve the repository's full gate for integrated completion through `finish` or a claim broad enough to require it.

Confirm that the evidence exercises the changed code or behavior through a focused test, trace or log, observed output, or concrete manual step; an unrelated passing suite is insufficient. For material or uncertain changes, record the changed path, load-bearing safety facts, strongest applicable evidence, and any unproved claim that remains a risk. Report the command, pass or fail result, passed and skipped test counts where applicable, and what the evidence does not cover. Do not treat stale output, a subagent report, a coverage number, or a process milestone as evidence.

When automation cannot prove a user-visible change, perform a concrete manual smoke check. Report the exact steps and observed result.

Do not change production code while verifying. Hand a failure to `investigate` when the cause is unknown or `implement` when the cause and required change are clear.

When verification belongs to a broader active task, it is not a response boundary. Continue with the identified fix or the next planned dependency without waiting for another user message. End with `Next:` and one explicit action only when verification was the user's whole request or work is genuinely blocked.
