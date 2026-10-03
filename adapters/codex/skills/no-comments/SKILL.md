---
name: no-comments
description: Audit a scoped diff for comments, docstrings, and suppressions that have not earned their place. Use for strict comment review or before a branch review.
---

# No comments

Treat comments as guilty until a concrete exception proves them useful.

## Scope

Use the caller's supplied scope when present. Otherwise audit the current Git diff, including staged and unstaged changes, without treating unrelated dirty files as authored work. Read the surrounding code before judging a comment.

This skill is a review and correction workflow. The reviewer must not edit. Do not edit until the parent has an approved scope and implementation path. The parent owns approval, corrections, verification, and the commit.

## Keep list

Keep a comment only when it matches one of these exceptions:

- Legal or license headers.
- Compiler, build, code-generation, cgo, and generated-file directives that tooling requires, such as `//go:build`, `//go:generate`, cgo preambles, and generated-file markers.
- Non-obvious behavior forced by an external dependency, platform, vendor, or protocol.
- Non-obvious constraints or decisions in our code supported by code or contract evidence, including why an intentionally ignored error cannot affect correctness or resource safety.
- Public API documentation that defines a contract.
- An issue or RFC link that records a constraint code cannot express.
- `prettier-ignore` or an equivalent style-only suppression when the rule is faulty or pedantic.

Existing comments receive the same keep-list test as new comments. Narration, banners, tutorial prose, commented-out code, and restatements do not qualify. Prefer clearer names, types, tests, or structure, but do not force restructuring merely to remove a useful rationale. An explanation is not a correctness exemption; unsupported safety claims remain OPEN.

Audit `eslint-disable`, `@ts-ignore`, `@ts-expect-error`, `//nolint`, and similar suppressions. Correctness or safety suppressions are findings. Keep a suppression only when its rule is proven faulty, pedantic, or style-only. Do not remove a compiler-significant directive or generated-file marker.

## Review

1. For an explicit strict comment audit, use one fresh native read-only `reviewer` when available and authorized. When this keep list is used inside another review, apply it there without launching an additional reviewer. If independent review is required but unavailable, stop until it is available or explicitly waived; otherwise report author-only evidence limits. Give it the explicit scope and this skill's keep list. Tell it not to edit, commit, run mutating commands, or spawn children.
2. Require a bounded report with the scoped file, line, disposition (`KEEP`, `KILL`, `RESHAPE`, or `OPEN`), evidence, and the smallest safe next action. A missing exception or an ambiguous keep is not proof that a safety constraint is disposable.
3. Inspect the report against the actual files. Reject scope escapes, invented comments, false exception claims, and findings that would delete compiler, build, code-generation, cgo, or generated-file directives.
4. For accepted `KILL` or `RESHAPE` findings, implement only the smallest root-cause change in the approved scope. If the change needs a type, test, lint rule, runtime check, or structural rewrite, state that decision before editing. If the claimed constraint could affect correctness or safety and no encoding is approved, retain it and report it as `OPEN`.
5. Re-run the reviewer only when the correction changes the reviewed comment or its surrounding contract. Resolve one rejected finding once with the reason recorded. If the second report repeats the rejected finding, leave it open and fail this pass rather than churning the code.

## Report

Return:

- The exact scope.
- The number of comments or suppressions reviewed, killed, retained, reshaped, and left open.
- Each retained exception with the evidence that proves it.
- Each root-cause correction and its validation.
- Unencoded constraints and why they remain open.
- Commands run and what they do not prove.

Do not claim success from a clean-looking report. Inspect the actual diff and run the narrowest fresh check that proves every accepted correction.
