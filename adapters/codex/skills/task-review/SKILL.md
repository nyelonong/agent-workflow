---
name: task-review
description: "Run fingerprint-bound human review of a visual technical plan before planned implementation, or the real working-tree diff after verification and before committing."
---

# Task review

Invoke with `$task-review` or after the focused evidence for a unit is in. The gate launches the runtime's review surface, hands it the actual working-tree change, blocks until a human decides, and records an approval bound to exactly that state; it owns the diff, so never paste, summarize, or reconstruct the diff, never ask a human to approve a description of a change, and never launch the reviewer or drive its interface yourself.

Run it with the criterion the user approved for this unit and the repository paths the task owns. Scope narrows what the human sees; it never widens it. Read-only investigation, review, and verification need no gate.

The client is `scripts/task_review.py` in the repository that owns this skill; resolve it there, never from the tree under review. `review --criterion TEXT --repo ROOT [--paths a,b]` blocks until the human decides, `verify --repo ROOT [--paths a,b]` checks the recorded approval against the current tree, and `consume --repo ROOT` retires the approval after the commit. Any process that takes one JSON request argument and prints one JSON result line can serve as the reviewer; `TASK_REVIEW_REVIEWER` selects it and defaults to the bundled HTML page (`RDG_CONTROL_COMMAND` is still honored when it is unset), so the gate is how every runtime reaches its review surface.

## Guided diff view

The HTML page keeps **Diff** selected by default and adds **Guided**. For nontrivial
diffs, author a local guide from inspected code: before/after behavior, optional
ordered flow labels, and explained whole-file chapters ordered by logic and risk.
Do not bury consequential database/security changes. Narration is advisory; the
real complete diff and existing approval checks remain authoritative.

Store the JSON outside reviewed repositories. Get the fingerprint using the exact
scope with `status --json REQUEST` or `status --repo ROOT [--paths a,b]`; exit 1 is
normal when no approval exists. Follow the guide schema/bounds in the harness
README. Use canonical repository roots and current diff paths (rename destinations).
Pass `review ... --guide PATH` or inline `guide` in the saved complete JSON request,
never combine `--guide` with `--json`. Capture that request before launch and keep
it unchanged; regenerate the guide after code or scope changes.

Guide-bearing reviews require the bundled `html` backend. Invalid, stale, duplicate
or unknown references fail; unassigned files remain under Other changes. Without a
guide, Guided uses honestly labeled directory groups. Checkboxes track session-only
reading, not approval. No model/network calls or document-review changes are added.

## Await the HTML decision

Before launch, save the criterion, exact repository/path scope or document, checkout, branch, HEAD, pending phase and authorized next action. Use the existing plan's partial checkpoint when it can be updated before the snapshot; do not create a plan just for a review. Keep operational review files in a unique private local directory outside the reviewed tree, with directory mode 0700 and file mode 0600. Record its path in the checkpoint or supported session history, finish any checkpoint edits, then calculate and save the expected fingerprint in the private record. These files recover command execution; they are not a second plan or an approval source.

For a diff review, save a complete request with a unique `review_id` and pass that same request through `review --json REQUEST`. Obtain the expected fingerprint with `status --json REQUEST`; its non-approval exit code is normal when no approval exists. For `review-doc --criterion TEXT --doc PATH`, record the document fingerprint and save the generated review ID from the page's read-only `api/doc` payload when available. If a fast decision completes first, record the ID from that same client invocation's completed validated result, correlated with its unique wrapper launch record, document, criterion, fingerprint, exit status and ledger. Missing launch provenance is a recovery gap; a result or ledger alone is insufficient. Do not submit a decision or operate the human's review controls.

Run the client through a foreground shell wrapper that saves its final stdout, stderr and exit status separately and returns that same status. Set `HTML_REVIEW_URL_FILE` to a file in the private directory; the launcher otherwise buffers the URL on stderr until completion. Save the supported command/session handle as soon as it is returned. Do not detach the command or launch another review because the first call yielded.

Read the URL file using bounded startup checks, present the link in commentary, and await the same command in intervals of about 30 seconds. When the runtime exposes `exec_command`/`write_stdin`, poll the returned command session with `write_stdin`; when an enclosing `functions.exec` yields a cell ID, await that cell with `functions.wait` before resuming its command session. Use only the handles actually returned, and stop polling a handle once completion is reported. Keep the turn active and give brief progress updates at least every 60 seconds. An expired wait interval means pending, not reviewer timeout, failure or approval. Do not disable the reviewer's lifetime limits to keep waiting.

If the URL cannot be recovered, inspect diagnostics and command state; do not relaunch or infer failure just because the URL file is missing. The reviewer removes it on completion. If waiting is unavailable or the runtime interrupts the turn, preserve the recovery record and report the limitation when possible. Never claim that a future page submission will wake an ended turn automatically.

## Act on the result

After the command completes, read its final JSON, annotations, diagnostics and exit status. Match the result's protocol version and review ID to this review; missing, incomplete or inconsistent artifacts require recovery, not an inferred decision. An HTML submission is the human decision for this gate; do not ask for the same approval or change request again in chat. It does not authorize another phase, changed scope or a remote action beyond existing approval.

The command exits 0 only for `approve`.

- `approve` — reuse sufficient current evidence under the shared workflow contract; run only missing or invalidated checks, then `verify` for the exact approved scope immediately before staging and continue the authorized local work. Do not edit approved files to address an annotation without re-reviewing the changed state.
- `request-changes` — exit 1 is an expected decision. Read the annotations, apply authorized in-scope corrections, rerun focused evidence, and gate the corrected state again with a new review ID and private directory. A material scope change needs the user's decision first.
- `return-to-planning` — the criterion was wrong, not the code. Stop, return to planning with the user, and re-approve before further work.
- `cancelled` — the human withdrew. Stop.

A failed reviewer, malformed result, timeout, or repository state that changed under the reviewer is an error, not an approval: report it and stop. Never route around a failed gate.

Run `verify` immediately before staging. Any change to the reviewed paths since approval fails it, and that failure must be re-reviewed rather than waived. Run `consume` after the commit lands so the approval cannot cover a second commit. A correction after approval invalidates it; passing tests do not renew it.

For document approval, use `verify-doc --doc PATH` with the recorded criterion before beginning the authorized next phase, and `consume-doc` once that phase has used the approval. Apply requested document corrections and run `review-doc` again. Keep reviewed files, including embedded checkpoints, unchanged from launch through verification and approval use/consumption; for a diff, this includes the commit and `consume`. Record interim recovery state externally instead of marking a reviewed checkpoint consumed. A technical-plan approval authorizes its bounded implementation directly; do not insert a separate specification gate.

## Recover an interrupted review

Inspect the checkpoint/session record, saved command artifacts, current checkout and approval ledger before replaying anything. For a scoped diff, inspect `status --json REQUEST` using the saved repository/path scope; an unscoped `status --repo ROOT` can describe a different fingerprint. The ledger records decisions and annotations but does not record the review ID or a running command handle, so its newest entry alone cannot identify an interrupted review.

- If the original command is still running and its handle is usable, await it and reuse its review URL. A saved handle or PID is only a hint until the runtime confirms ownership and state; do not assume handles survive a new session.
- If it completed, correlate the saved result and exit status with the recorded review ID, criterion, scope, expected fingerprint and newest client-written ledger entry. Recover annotations from the matching result/entry, then follow the decision above. Approval additionally requires fresh `verify` or `verify-doc`; command output or a checkpoint alone cannot authorize a commit or phase transition.
- If a commit may already have happened, inspect HEAD and the committed task diff before committing or consuming approval again. A consumed approval cannot authorize a second commit.
- If artifacts are missing, a process failed, identity cannot be established, or state changed, preserve the work and report the specific gap. Silence, elapsed time, a dead URL and process failure never imply approval. Establish that the original review has ended before offering a replacement; unknown ownership blocks a duplicate launch. A replacement is a new human review, not recovery of an assumed approval.

Record terminal review state and the next authorized action after processing the outcome. Keep the operational artifacts through interruption recovery and approval consumption; retire only this review's files when they are no longer needed. Never clear another session's files or shared ledger entries as cleanup.

When the gate reports a failure that needs a user decision, use the Codex adapter's plain numbered question with a recommendation. The review itself stays in the reviewer's surface, and this skill does not review code, choose files, or approve anything on the user's behalf.

Troubleshooting: when `rdg` is the reviewer it must already be running with the repository open, and every repository root must be a canonical absolute path. The client realpaths each root, so a symlinked path such as `/tmp/x` is rejected while `/private/tmp/x` is accepted.
