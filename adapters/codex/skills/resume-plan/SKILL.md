---
name: resume-plan
description: Resume an approved plan from its continuation checkpoint
---

# Resume Plan

Use the plan path supplied by the user; ask for it only when it cannot be established from the active context. Read `plan` and [context recovery](../plan/references/context-recovery.md). Validate repository identity, checkout, branch, commit, dirty paths, child state and recorded evidence before modifying project files. Investigate unexplained mismatches and failed evidence.

Preserve the existing approved scope and execution path. A new session does not require reselecting execution mode. When approval cannot be recovered or a material scope change appears, ask a plain numbered question with a recommendation and stop until answered.

After validation, mark an existing checkpoint consumed and execute its authoritative `next:`; use `finish` when that is the next phase. If no checkpoint exists, inspect the actual diff and rerun the last recorded evidence before continuing the plan's current task. Keep the parent as implementer unless the user explicitly authorized another path.

Direct implementation or interactive review never waives required independent review. Preserve the global review boundary, user review of each uncommitted unit, and explicit authorization for remote actions. If a mandatory reviewer is unavailable, completion blocks until one is available or the user explicitly waives the missing review.
