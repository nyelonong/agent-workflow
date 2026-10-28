---
name: verify-doc
description: Use when auditing one design, architecture, or runbook document against code, or explaining a subsystem as a new evidence-cited document.
---

# verify-doc

A document is a set of claims about code. Check those claims from source or Git evidence inspected in this session, never from memory, another document, or earlier logs.

Choose one mode from the request and state it with the target in the first output line.

| Mode | Trigger | Deliverable |
|---|---|---|
| `audit` | An existing document may have drifted | Claim table, then an approved rewrite |
| `explain` | A subsystem needs a new explanation | Diagram, claim table, unknowns |

Both modes are read-only until the user approves a document write. Neither mode changes code, pushes, or opens a pull request.

## Before acting

1. When `graphify-out/` exists and Graphify is available, orient with `graphify query "<question>"`; otherwise use targeted repository search and note that Graphify was unavailable.
2. Identify the document for `audit` or the subsystem for `explain`.
3. State the mode and target, then begin. This step is done when both are unambiguous.

## Claims and evidence

Claims include component names, callers, data flow, queues, configuration keys, schemas, retries, timeouts, endpoints, flags, paths, and ownership. Rationale, opinions, proposals, and explicit "should" statements are not factual claims; preserve them and label that distinction. A historical statement asserting what happened is factual. When history is in scope, verify it from source or Git evidence inspected in this session; otherwise mark it UNVERIFIABLE rather than preserving it as a non-claim.

Cite source evidence as `path:line` and identify Git evidence by commit and path. A claim spanning files gets every necessary citation. Similar names do not identify the same component: establish the distinction before using either name.

## Audit mode

1. Extract every factual assertion into a numbered checklist before verifying any. Record sentence coverage separately; extraction is done when every factual sentence belongs to exactly one coverage batch, all its assertions map to checklist items, and gaps are explicit.
2. For a very large single document, partition work by heading or bounded claim ranges. Assign claim numbers once, keep them stable, and state each batch's coverage.
3. Verify each item and report one row per claim:

   | # | Claim | Verdict | Evidence |
   |---|---|---|---|

4. Use exactly **CONFIRMED**, **CONTRADICTED**, or **UNVERIFIABLE**. A contradicted row states what the code does. An unverifiable row states what was inspected and why the claim cannot be decided.
5. Complete every batch, then present one combined complete verdict table and request rewrite approval. No rewrite starts until every factual sentence is covered exactly once, every claim has a row, and gaps are explicit.
6. On approval, rewrite only contradicted sections while preserving voice, structure, and heading order. Re-run the claim table for changed sections before calling the rewrite done.

Open questions and backlog items are separate from a contradicted-section rewrite and need explicit approval plus a destination.

## Explain mode

Deliver these sections in order:

1. An ASCII diagram of components and data direction.
2. A claim table without a verdict column; every explanation statement has `path:line` evidence.
3. **UNKNOWNS**, with one reason each, such as a running system, another repository, or production-only configuration.
4. **Candidate changes** when evidence reveals a problem, with risk stated and no implementation.

The explanation is done when every statement has a citation or appears under UNKNOWNS.

## Open-question destination

Use the first destination that exists:

1. An existing `docs/BLOCKERS.md`, `docs/BLOCKED-ON-HUMAN.md`, `docs/backlog.md`, or `BLOCKERS.md`.
2. A destination chosen by the user. Do not create a second ledger beside an existing one.

## Cost

For a multi-document sweep, batch by directory and state the coverage of each batch. Name the model tier and rough call count before fan-out. A stopped sweep must leave a known boundary.
