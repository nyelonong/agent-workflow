---
name: task-review
description: "Run fingerprint-bound human review of a visual technical plan or the real working-tree diff, only when the user requests one."
---

# Task review

Invoke with `$task-review` or after the focused evidence for a unit is in. The gate launches the runtime's review surface, hands it the actual working-tree change, blocks until a human decides, and records an approval bound to exactly that state; it owns the diff, so never paste, summarize, or reconstruct the diff, never ask a human to approve a description of a change, and never launch the reviewer or drive its interface yourself.

Run it with the criterion the user approved for this unit and the repository paths the task owns. Scope narrows what the human sees; it never widens it. Read-only investigation, review, and verification need no gate.

The client is `scripts/task_review.py` in the repository that owns this skill; resolve it there, never from the tree under review. `review --criterion TEXT --repo ROOT [--paths a,b]` blocks until the human decides, `verify --repo ROOT [--paths a,b]` checks the recorded approval against the current tree, and `consume --repo ROOT` retires the approval after the commit. Any process that takes one JSON request argument and prints one JSON result line can serve as the reviewer; `TASK_REVIEW_REVIEWER` selects it and defaults to the bundled HTML page (`RDG_CONTROL_COMMAND` is still honored when it is unset), so the gate is how every runtime reaches its review surface.

## Delegation

Delegate canonical request preparation and invocation of `review`/`review-doc`
to one bounded native gate runner, following the [shared guide-phase, model and
authority policy](../../../../skills/task-review/SKILL.md#delegation). Optional
guide preparation is separately bounded and cannot invoke a reviewer. Use GPT-6 Luna
(`gpt-6-luna`) within the current provider's available runtime scope. Do not compare
prices, inherit the parent's model or substitute another model/version; if Luna
is unavailable or disallowed, stop and ask the user. Keep the parent's model
unchanged. Use native child model controls; if delegation, model selection or
supported waiting is unavailable, report the blocker and ask the user rather
than running the gate in the parent or switching providers.

Give the child the approved criterion, exact scope/document, owning client,
verification evidence and private recovery directory. It may inspect code,
author the advisory guide and run the canonical client; it may not edit reviewed
inputs, widen scope, spawn children, stage, commit or consume approval. The gate
runner executes the maintained client directly with `--recovery-dir PATH` and
does not delegate again. The client saves its exact request, process record,
live diagnostics, state and validated result. Do not generate launch scripts,
PID files, shell redirection, process substitution or detached commands.
Read and foreground-command tools suffice; write is needed only for guides,
and optional child progress messaging is not a prerequisite.
The parent must inspect the canonical artifacts, apply annotations or stop
decisions, and own exact-state verification and approval consumption. This is
not independent code review and never replaces the human decision.

The waiting/recovery instructions below apply to the delegated runner's command;
the parent retains the child handle, relays the review URL and waits using native
supported controls. A background shell command alone is not a subagent. Never
infer approval from a child's summary or assume completion will wake a stopped
parent turn.

## Guided diff view

The HTML page keeps **Diff** selected by default and adds **Guided**. Guides are
best-effort under the shared **120-second total preparation deadline**, including
inspection, authoring and preflight. Use a preparation-only native phase with no
authority to invoke `review`/`review-doc`; keep the native deadline, command/run
handle and supported cancellation/settlement path. A model instruction alone is
not a deadline. If these controls are unavailable, skip the optional guide.

For a successful attempt, inspect the actual diff, author concise before/after
behavior and whole-file chapters ordered by risk, and preflight the same criterion
and canonical repo/path scope. Each `(repository, path)` appears once. Store guide
artifacts outside reviewed inputs and the client's separate recovery directory.

On preparation failure, invalid/missing output, failed guide preflight or expiry,
do not repair/retry or ask again: cancel and settle pending preparation, discard
late output, then use a launch-only native runner with no guide. Resume the
successful preparer only where native continuation preserves ownership; otherwise
use a fresh fixed-model launch-only runner. Remove only `--guide`/inline `guide`,
retain criterion/scope and require plain preflight to pass. Report the skip reason.
Non-guide failures and explicit user cancellation remain blockers.

Never restart an already invoked review as a guide fallback. If preparation
crossed into review without authority, recover that invocation and honor its
decision/error/stop rules. Unknown ownership blocks a replacement. Stop the guide
timer before the actual human gate; native command/run limits must allow the normal
human decision timeout, not cancel it after two minutes.

Guided without a guide uses honestly labeled directory groups; the complete diff,
human decision and exact-state verification remain mandatory. Supplied guides
remain strictly validated, including recapture at review invocation. No harness
model/network calls or document-review changes are added.

## Await the HTML decision

Before launch, retain the criterion, exact scope/document, checkout, branch,
HEAD, pending phase and authorized next action in supported session history or
an existing plan. Finish checkpoint edits before capture; do not create a plan
merely to wait. Supply a new or empty private recovery directory outside reviewed
inputs with `--recovery-dir PATH`; the client creates it and refuses a nonempty
directory rather than overwriting an existing run.

Run `review --criterion TEXT --repo ROOT [--paths a,b] --recovery-dir PATH`,
`review --json REQUEST --recovery-dir PATH`, or
`review-doc --criterion TEXT --doc PATH --recovery-dir PATH` directly in the
child's foreground command. Retain the native child and command/session handles
with their supported cancellation path. Set native run/tool deadlines longer
than the client's timeout (default 1800 seconds) plus preparation time.

The client owns `request.json`, `process.json`, `state.json`, `stderr.log` and
the validated `result.json`; it sets `browser-url.txt` automatically for HTML.
Diagnostics stream immediately. Match request/result IDs and scope, and inspect
the recorded fingerprint, exit code and ledger; artifacts are not approval
without parent verification. Never submit a decision or operate review controls.

Read the URL file using bounded startup checks, present the link in commentary, and await the same command in intervals of about 30 seconds. When the runtime exposes `exec_command`/`write_stdin`, poll the returned command session with `write_stdin`; when an enclosing `functions.exec` yields a cell ID, await that cell with `functions.wait` before resuming its command session. Use only the handles actually returned, and stop polling a handle once completion is reported. Keep the turn active and give brief progress updates at least every 60 seconds. An expired wait interval means pending, not reviewer timeout, failure or approval. Do not disable the reviewer's lifetime limits to keep waiting.

If the URL cannot be recovered, inspect diagnostics and command state; do not relaunch or infer failure just because the URL file is missing. The reviewer removes it on completion. If waiting is unavailable or the runtime interrupts the turn, preserve the recovery record and report the limitation when possible. Never claim that a future page submission will wake an ended turn automatically.

## Act on the result

After completion, inspect the client-owned artifacts. `state.json` distinguishes
`starting`, `reviewing`, `finished` and `error`; `finished` contains a decision
and exit code, whereas `error` grants no approval. Read the validated result,
annotations and diagnostics, matching protocol version and review ID to
`request.json` and the native owned run. Missing or inconsistent artifacts require
recovery, not an inferred decision. A human HTML submission is the decision for
this gate; do not ask for the same approval again in chat. It does not authorize
another phase, changed scope or a remote action beyond existing approval.

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
