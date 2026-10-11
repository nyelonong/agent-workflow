---
name: task-review
description: Obtain fingerprint-bound human approval of a technical plan or the actual working-tree diff in a browser. Use once before planned implementation and after verification before committing.
---

# Task review

The gate launches the runtime's review surface, hands it the real working-tree
change, blocks until a human decides, and records an approval bound to exactly
that state. It owns the diff; you never restate it.

## Run it

- Run the gate after the last focused check for the unit and before any commit
  of production changes.
- Pass the criterion the user approved for this unit and the repository paths
  the task owns. Scope narrows what the human sees; it never widens it.
- Never summarize, paste, or reconstruct the diff, and never ask a human to
  approve a description of the change. The gate reads the working tree itself.
- Never launch the reviewer yourself, and never drive its UI. The gate is the
  only supported way to reach it.
- Read-only investigation, review, and verification need no gate.

## Delegation

In every coding-agent runtime, always delegate preparation and invocation of
both `review` and `review-doc` to one bounded native subagent. This is a workflow
requirement, not a runtime guard. A parent-owned background command with no
subagent is not delegation. The delegated gate runner executes the client
directly and must not delegate again.

Before each new gate, the parent selects the model:

- Inspect the runtime's executable agents and live available model catalog.
- Restrict candidates to available tool-capable chat models in the parent's
  **current provider**, active runtime model scope and applicable child model
  restrictions. Treat an unrestricted scope as all available models; do not
  infer the active scope solely from settings on disk.
- Keep the latest stable available member of each documented model family,
  then choose the lowest catalog input-plus-output token rate. This equal-token
  comparison is a selection proxy, not a total-cost or subscription-quota claim.
  Use current registry/catalog evidence for prices and family versions; model
  names alone do not establish pricing or recency across families. Unknown
  pricing is not free. Break price ties by documented recency.
- Pass the selected exact native model identifier explicitly, with low supported
  thinking, fresh context and no priority/fast mode. Inspect configured fallbacks too;
  none may escape the provider, scope or selected cost/recency policy. Do not
  pin model IDs in this skill, inherit the parent's expensive default, silently
  upgrade, or switch providers. Missing evidence, no eligible model or a launch
  failure blocks the gate; ask the user rather than bypassing delegation.

Use an executable role with client-command and private-artifact permissions,
not the independent code reviewer. Use native delegation and supported waiting;
keep the parent's model unchanged. If delegation, explicit child model selection
or waiting is unavailable, report that limitation and ask the user; do not emulate
a subagent with a shell command or silently run the gate in the parent.
Its packet must include the approved criterion, exact canonical repository/path
scope or document, client location, verification evidence and a private recovery
directory outside reviewed inputs.
Permit code/diff inspection, advisory guide authoring and client-owned approval
metadata only; forbid source/document edits, scope changes, nested delegation,
staging, commits, approval consumption and external mutations.

The child prepares any guide from the actual inspected changes, runs the
canonical gate once, reports the browser URL while waiting, and returns the
validated result, exit code, review ID and saved request/result/recovery paths.
Retain the native run/command handle and cancellation path; recover that owned
gate before relaunching. Child prose alone cannot establish approval. The parent checks the
canonical artifacts and applies annotations or stop decisions; it still owns
`verify`/`verify-doc`, `consume`/`consume-doc`, corrections and commits. This runner
does not replace any required independent code review or human decision.

In Pi, inspect `subagent({ action: "list", capabilities: true })` and
`subagent({ action: "models" })`, copy an exact `provider/id`, and launch with
fresh context and `async: true` through `subagent` or `runs.run` in one async
workflow. A childless `runs.host` gate is not delegation. Other adapters own
their native launch, model-selection and waiting mechanics.

## Guided diff view

The bundled HTML page opens **Diff** by default and offers **Guided** beside it.
For a nontrivial diff, prepare an agent-authored guide from inspected code before
launching the gate: before/after behavior, optional ordered flow labels, and
whole-file chapters with explanations. Order chapters by the change's logic and
review risk; do not bury consequential database or security changes as boilerplate.
The actual diff remains authoritative; the guide is advisory, not a replacement
for complete diff review or proof that the explanation is true.

Store guide JSON in a private location outside the reviewed repositories. Use
`status --repo ROOT [--paths a,b]` (or `status --json REQUEST`) to obtain the scoped
fingerprint; its non-approval exit is normal. Pass `review ... --guide PATH`, or
include `guide` in the complete JSON request, never both. Follow the versioned
format and bounds in the owning repository's README. Use canonical repository
roots and captured current paths, including rename destinations; regenerate the
guide after code/scope changes. Duplicate/out-of-scope references and stale guides
fail; omitted scoped files remain visible under Other changes.

No harness model/network calls are made. Without an authored guide, Guided uses
honestly labeled directory groups. Chapter checkboxes are session-only reading
progress, not decisions or exemptions. Guide-bearing reviews require the bundled
`html` backend; leave existing non-HTML and document flows unchanged.

## Waiting and recovery

Before capture, retain the criterion, exact scope/document, authorized phase and recovery location in supported history or an existing plan. Keep private command records outside the reviewed tree; do not create a plan merely to wait. Native adapters own command handles and waiting. Keep reviewed inputs unchanged through approval verification and use/consumption; record interim operational state externally. Recover the original command and result before relaunching. Unknown ownership or consequential outcome blocks replay and progression; it never implies approval.

## Act on the decision

The command exits 0 only for `approve`.

- `approve` — continue; `verify` must still pass at commit time.
- `request-changes` — apply the annotations in scope, rerun focused checks, and
  gate the corrected state again.
- `return-to-planning` — the criterion was wrong, not the code. Stop, return to
  planning with the user, and re-approve before further work.
- `cancelled` — the human withdrew. Stop.

Every other outcome is an error: a failed reviewer, a malformed result, a
timeout, or a repository state that changed under the reviewer. Report it and
stop. Never route around a failed gate.

## Reviewers

The gate speaks one protocol, so the surface is a choice, not a branch. It opens
the bundled HTML page by default. `TASK_REVIEW_REVIEWER=rdg` sends the identical
request to RDG, which reviews inside a running editor window; the repository must
be open there and the root must be a canonical absolute path. The README records
a known RDG failure, so keep the HTML page unless told otherwise. Choose the supported surface before launch, never mid-decision: one human decision
for the captured state.

## Commit

- Run `verify` immediately before staging. Any change to the reviewed paths since
  approval fails it; that failure is real and must be re-reviewed, not waived.
- Run `consume` after the commit lands, so the approval cannot cover a second
  commit.
- A correction after approval invalidates it. A passing test suite does not
  renew an approval. Executable evidence follows the shared workflow's freshness
  contract; approval alone is not a reason to rerun it.

## Technical-plan documents

Present the single technical plan through the document gate. Its approval
authorizes the listed implementation scope directly, not a second planning phase:

```sh
scripts/task_review.py review-doc --criterion "<the question this document must answer>" --doc <path>
scripts/task_review.py verify-doc --doc <path>
scripts/task_review.py consume-doc --doc <path>
```

The page renders the document as a document: headings, paragraphs, tables and
code, with a heading outline in the sidebar. A comment names the **source range**
of the block it was written on, so a comment on a paragraph spanning lines 5-7
comes back as `start_line: 5, end_line: 7` and the agent edits the right place.
Fenced code is tokenized only when the fence names a language the reviewer
handles; anything else stays plain.

Apply the returned annotations, edit the document, and run `review-doc` again:
the approval is bound to a fingerprint of the exact text, so an edit after
approval invalidates it.

- `request-changes` — revise the document against every comment, then re-review.
- `return-to-planning` — the premise is wrong, not the prose. Stop and return.
- `approve` — the document is approved as written; `consume-doc` retires the
  approval once the next phase has used it.
- `cancelled` — the human withdrew. Stop.

This is the one pre-implementation document approval used by `plan`. Do not add a
separate specification gate, mandatory walkthrough or competing chat confirmation.
If the page cannot be opened, report the failure and stop. No automatic unbound
chat fallback is permitted; a supported replacement requires explicit authorization.

## Commands

The client is `scripts/task_review.py` in the repository that owns this skill.
Resolve it there, never from the tree under review.

- `review --criterion TEXT --repo ROOT [--paths a,b]` opens the review and
  blocks until the human decides.
- `verify --repo ROOT [--paths a,b]` checks the recorded approval against the
  current tree.
- `consume --repo ROOT` retires the approval after the commit.

The reviewer is any process that takes one JSON request argument and prints one
JSON result line. `TASK_REVIEW_REVIEWER` selects it and defaults to the bundled
HTML page; `RDG_CONTROL_COMMAND` is still honored when it is unset. When `rdg` is
the reviewer, the repository must already be open in the
running application, and every repository root must be a canonical absolute
path — the client realpaths it, so a symlinked path such as `/tmp/x` is
rejected while `/private/tmp/x` is accepted.
