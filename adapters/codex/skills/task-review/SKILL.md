---
name: task-review
description: "Run the blocking pre-commit human review gate over the real working tree. Use after the unit's focused checks pass and before committing any production change, or whenever the user asks for the review gate."
---

# Task review

Invoke with `$task-review` or after the focused evidence for a unit is in. The gate launches the runtime's review surface, hands it the actual working-tree change, blocks until a human decides, and records an approval bound to exactly that state; it owns the diff, so never paste, summarize, or reconstruct the diff, never ask a human to approve a description of a change, and never launch the reviewer or drive its interface yourself.

Run it with the criterion the user approved for this unit and the repository paths the task owns. Scope narrows what the human sees; it never widens it. Read-only investigation, review, and verification need no gate.

The client is `scripts/task_review.py` in the repository that owns this skill; resolve it there, never from the tree under review. `review --criterion TEXT --repo ROOT [--paths a,b]` blocks until the human decides, `verify --repo ROOT [--paths a,b]` checks the recorded approval against the current tree, and `consume --repo ROOT` retires the approval after the commit. Any process that takes one JSON request argument and prints one JSON result line can serve as the reviewer; `RDG_CONTROL_COMMAND` selects it and defaults to the `rdg` binary, so the gate is how every runtime reaches its review surface.

The command exits 0 only for `approve`.

- `approve` — continue; `verify` must still pass at commit time.
- `request-changes` — apply the annotations in scope, rerun focused evidence, and gate the corrected state again.
- `return-to-planning` — the criterion was wrong, not the code. Stop, return to planning with the user, and re-approve before further work.
- `cancelled` — the human withdrew. Stop.

A failed reviewer, malformed result, timeout, or repository state that changed under the reviewer is an error, not an approval: report it and stop. Never route around a failed gate.

Run `verify` immediately before staging. Any change to the reviewed paths since approval fails it, and that failure must be re-reviewed rather than waived. Run `consume` after the commit lands so the approval cannot cover a second commit. A correction after approval invalidates it; passing tests do not renew it.

When the gate reports a failure that needs a user decision, use the Codex adapter's plain numbered question with a recommendation. The review itself stays in the reviewer's surface, and this skill does not review code, choose files, or approve anything on the user's behalf.

Troubleshooting: when `rdg` is the reviewer it must already be running with the repository open, and every repository root must be a canonical absolute path. The client realpaths each root, so a symlinked path such as `/tmp/x` is rejected while `/private/tmp/x` is accepted.
