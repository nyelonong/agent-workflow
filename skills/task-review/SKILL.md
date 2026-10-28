---
name: task-review
description: Obtain fingerprint-bound human approval of a technical plan or the actual working-tree diff in a browser. Use only when the user requests a plan, document or diff review.
---

# Task review

The gate launches the runtime's review surface, hands it the real working-tree
change, blocks until a human decides, and records an approval bound to exactly
that state. It owns the diff; you never restate it.

## Run it

- Run the gate only when the user requests a review, after the last focused check
  for the unit and before committing it.
- Pass the criterion the user approved for this unit and the repository paths
  the task owns. Scope narrows what the human sees; it never widens it.
- Never summarize, paste, or reconstruct the diff, and never ask a human to
  approve a description of the change. The gate reads the working tree itself.
- Never launch the reviewer yourself, and never drive its UI. The gate is the
  only supported way to reach it.
- Read-only investigation, review, and verification need no gate.

## Delegation

In every coding-agent runtime, delegate canonical request preparation and
invocation of `review` and `review-doc` to one bounded native gate runner.
The parent authors any optional guide itself before delegating; the runner never
writes or repairs guides. Only one runner may invoke the actual review.
A parent-owned background command is not delegation; the gate runner executes
the client directly and must not delegate again.

Use **GPT-6 Luna (`gpt-6-luna`)** for every plan and diff gate runner unless the
runtime adapter explicitly names a different fixed task-review model. Use that
adapter's fixed model when specified; do not choose dynamically.

- Inspect the runtime's executable agents and confirm that the fixed model is
  available and tool-capable in the parent's **current provider**, active runtime
  model scope and applicable child model restrictions. Reuse current evidence;
  do not compare prices or select a newer model. Do not infer the active scope
  solely from settings on disk.
- Pass the exact native identifier for the fixed model explicitly, with low
  supported thinking, fresh context and no priority/fast mode. Do not inherit
  the parent's model, substitute another version or model, or switch providers.
- Disable alternate-model fallbacks or confirm that every configured fallback
  resolves to the same fixed model within those limits. If availability,
  eligibility or fallback behavior cannot be confirmed, or launch fails, stop
  and ask the user rather than choosing another model or bypassing delegation.

Use an executable role with client-command and private-artifact permissions,
not the independent code reviewer. Use native delegation and supported waiting;
keep the parent's model unchanged. If delegation, explicit child model selection
or waiting is unavailable, report that limitation and ask the user; do not emulate
a subagent with a shell command or silently run the gate in the parent.
Its packet must include the approved criterion, exact canonical repository/path
scope or document, client location, verification evidence and a private recovery
directory outside reviewed inputs.
Permit code/diff inspection and client-owned approval metadata only; forbid source/document edits, scope changes, nested delegation,
staging, commits, approval consumption and external mutations.

Run the maintained client directly in the child's foreground command with
`--recovery-dir PATH`; the client creates the private directory and owns request,
process, diagnostic and decision artifacts. Do not generate Python/shell launchers,
PID files, output redirection, process substitution, or detached processes.
The child needs read and foreground-command tools. The native async subagent run is the owner and cancellation handle:
child-side background-command or supervisor-message tools are not prerequisites.

The gate runner receives either the parent's preflighted guide or explicit
`guide: none`. Run the canonical gate
once and return the validated result, exit code, review ID and recovery directory.
Live stderr and `browser-url.txt` report the URL during the human wait. The parent
can read them without requiring the blocked child to send a progress message.
Retain the native run/cancellation handle and recover it before relaunching.
Child prose alone cannot establish approval. The parent checks the canonical
artifacts and applies annotations or stop decisions; it still owns
`verify`/`verify-doc`, `consume`/`consume-doc`, corrections and commits.
This runner does not replace required independent review or a human decision.

In Pi, inspect `subagent({ action: "list", capabilities: true })` and
`subagent({ action: "models" })`. With the `openai-codex` provider, pass
`model: "openai-codex/gpt-6-luna:low"` explicitly. For another current provider,
use only its available exact identifier for the same GPT-6 Luna model; if none
exists, stop. Launch with fresh context and `async: true` through `subagent`
or `runs.run` in one async workflow. A childless `runs.host` gate is not
delegation. Other adapters own their native launch, model-selection and waiting
mechanics.

Set runner command/run deadlines longer than the client's review timeout
(`TASK_REVIEW_TIMEOUT`, default 1800 seconds).
An open foreground tool while the client is `reviewing` is expected human waiting,
not a failed or stuck gate; inspect its native state and recovery artifacts before
interrupting it.

## Guided diff view

The bundled HTML page opens **Diff** by default and offers **Guided** beside it.
Write a concise guide for every diff review except a single small file; it is a
best-effort enhancement, not a prerequisite for human review. Include inspected before/after
behavior, optional flow labels and whole-file chapters ordered by logic and risk.
The real complete diff remains authoritative.

The parent writes the guide itself from the diff it has already inspected; no
child, preparation phase or deadline is involved. Store guide JSON privately
outside reviewed repositories and the client recovery directory. Obtain the exact
scoped fingerprint with `status --repo ROOT [--paths a,b]` or `status --json
REQUEST`; exit 1 for no approval is normal. Each `(repository, path)` belongs to
one chapter. Preflight the criterion, scope and guide before delegating; preflight
opens no reviewer, changes no ledger and never establishes approval.

If the guide fails preflight, correct it once from the reported error and preflight
again. If it still fails, skip the guide: hand the runner `guide: none` with the
same criterion and scope, require plain preflight to pass, and report briefly that
the guide was skipped and why. Repository, scope, permission or other non-guide
failures remain blockers. Pass `--guide PATH` or an inline guide, never both. The
actual review repeats strict validation; a failure after the canonical review is
invoked follows the gate's normal stop/recovery rules, not a guide fallback.

No harness model/network calls are made. Without an authored guide, Guided uses
honestly labeled directory groups. Chapter checkboxes are session-only reading
progress, not decisions or exemptions. Guide-bearing reviews require the bundled
`html` backend; leave existing non-HTML and document flows unchanged.

## Waiting and recovery

Before capture, retain the criterion, exact scope/document, authorized phase and recovery location in supported history or an existing plan. Keep private command records outside the reviewed tree; do not create a plan merely to wait. Native adapters own command handles and waiting. Keep reviewed inputs unchanged through approval verification and use/consumption; record interim operational state externally. Recover the original command and result before relaunching. Unknown ownership or consequential outcome blocks replay and progression; it never implies approval.

For delegated gates, pass a new or empty private recovery directory outside the
reviewed inputs. Do not prepopulate it; the client creates it with mode 0700 and
files with mode 0600. Existing nonempty directories are refused, never overwritten.
Inspect `request.json`, `process.json`, `state.json`, `stderr.log`, and the native
run before deciding whether a new invocation is safe. Recorded PIDs aid diagnosis;
use native cancellation, not blind PID-based killing or replay.

`state.json` distinguishes `starting`, `reviewing`, `finished`, and `error`.
`finished` includes the human decision and exit code: exit 1 with
`request-changes`, `return-to-planning`, or `cancelled` is not a launcher failure.
`result.json` exists only after protocol, decision and ledger checks succeed;
approval additionally requires unchanged reviewed inputs. Read `browser-url.txt`
while waiting; it is withdrawn on normal
completion, while the URL remains in `stderr.log`. Error state or missing result
never grants approval. Recovery artifacts do not replace parent verification.

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

When requested, this is the pre-implementation document approval used by `plan`. Do not add a
separate specification gate, mandatory walkthrough or competing chat confirmation.
If the page cannot be opened, report the failure and stop. No automatic unbound
chat fallback is permitted; a supported replacement requires explicit authorization.

## Commands

The client is the trusted workflow harness's `scripts/task_review.py`, never a script in the repository under review. For omp, resolve the physical `skill://task-review` directory first: it is `<harness>/skills/task-review`, so its client is two parent directories above it at `<harness>/scripts/task_review.py`. For this installation that resolves to `/Users/zaki/Projects/personal/agent-workflow/scripts/task_review.py`.

- `review --criterion TEXT --repo ROOT [--paths a,b] --recovery-dir PATH`
  opens the review, retains client-owned artifacts, and waits for a human decision.
- `review-doc --criterion TEXT --doc PATH --recovery-dir PATH` does the same for
  the technical plan.
- `preflight --criterion TEXT --repo ROOT [--paths a,b] [--guide PATH]`
  checks inputs without opening a review or changing an approval.
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
