---
description: Resume an approved plan from its continuation checkpoint
argument-hint: "<plan-path>"
---
Resume the approved plan at `$ARGUMENTS`.

Load the `plan` skill and follow its context-recovery reference. Validate the continuation checkpoint against the repository, checkout, branch, commit, dirty paths, child state, and recorded evidence before changing project files. Investigate any unexplained mismatch or failed evidence.

After validation passes, if `next: finish`, mark the checkpoint `consumed` and load `finish`. Otherwise, retain the execution path recorded by the approved plan. Only when a legacy plan records no execution path, use `ask_decision` to choose one for the remaining approved work:

- **Direct implementation + interactive review** (recommended for ordinary work): implement remaining tasks directly, then run `/interactive-review` before `finish`.
- **Full worker/reviewer workflow**: use the `pi-subagents` writer path where the approved plan or consequence policy requires isolation.

Treat the recorded or newly selected path as implementation authorization for the existing approved scope. Independently apply the global independent-review boundary: direct implementation never waives a review that boundary requires. Then mark the checkpoint `consumed` and execute only its authoritative `next:` value. Do not reopen approved decisions unless validation reveals a material scope change.
