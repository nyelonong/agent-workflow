---
name: task-review
description: Runs the blocking review gate in scripts/task_review.py so a human approves the real working-tree change, or a specification or plan, by annotating it in a browser page. Use after focused verification and before committing, and for every specification and plan approval.
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
a known RDG failure, so keep the HTML page unless told otherwise. Choose by mood,
never mid-decision: one approval, one reviewer.

## Commit

- Run `verify` immediately before staging. Any change to the reviewed paths since
  approval fails it; that failure is real and must be re-reviewed, not waived.
- Run `consume` after the commit lands, so the approval cannot cover a second
  commit.
- A correction after approval invalidates it. A passing test suite does not
  renew an approval.

## Documents: specifications and plans

A specification or a plan is approved through the same gate, on the document
itself rather than on a summary of it:

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

This is the approval step for `shape` and `plan`. Do not also ask a separate
approve/deny question for the same document. If the page cannot be opened at
all, fall back to the runtime's own question interface, and say plainly that
the approval was not bound to a fingerprint.

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
