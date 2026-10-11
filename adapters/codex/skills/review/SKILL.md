---
name: review
description: Check completed work against approved outcomes and the technical plan, then quality, before a completion claim or merge.
---

# Review

Review acceptance before quality: compare the actual change with the approved outcome, technical plan and any referenced requirements.

Check acceptance criteria first, then quality:

- Acceptance: every criterion is met or explicitly waived by the user through an approved scope revision. Cite the criterion and waiver when applicable.
- Quality: the change follows the repository's own standards, the same bar `implement` applies. Findings cite the rule. Challenge unsupported assumptions and inspect counterexamples.
- For material or uncertain changes, inspect beyond the diff through applicable callers, contracts, persisted or wire formats, downstream readers, lifecycle timing, feature flags, and external dependencies. Name the smallest load-bearing safety facts and the strongest applicable evidence. Report confirmed risks, cleared checks, and unproved risks; an unproved fact carrying a material safety claim is P1.
- For changed comments, docstrings, and suppressions, use the strict keep list from `no-comments` in audit-only mode. Apply that keep list within this review; do not launch a separate comment reviewer. The audit must not edit or mutate files during ordinary review. Route an explicit strict comment-cleanup request to `no-comments` for its parent-controlled correction workflow.

Label findings by severity:

- P0: critical safety, security, data-loss, or unusable-result defect. Blocks completion.
- P1: missed acceptance criterion or correctness/quality defect that should be fixed now. Blocks completion.
- P2: optional improvement or report-only note. Does not block completion.

Report source findings with a repo-relative path and line when applicable. For a repository-wide absence, command failure, or contract contradiction, cite the exact command output, criterion, or other verifiable evidence instead. A finding without an applicable location or exact evidence is not a finding.

Apply the shared workflow's review units, coverage reuse and delivery timing to the independent-review boundary in `AGENTS.md`. Obtain a fresh independent native read-only `reviewer` when that contract requires it, before the applicable delivery/safety boundary, not merely because this skill was invoked. Give it the actual diff, technical plan and acceptance criteria; require it to inspect the files directly and treat the worker handoff only as context. The parent still inspects the diff and owns the review decision. If the reviewer is unavailable, stop until one is available or the user explicitly waives the missing review. Direct or interactive review does not imply a waiver.

Outside that boundary, parent review may stay proportional. A fresh reviewer remains optional when the user requests one or when credible uncertainty, advice, or bounded isolation clearly benefits the task. A subagent's review is a claim, not evidence — the findings stand on their own, and completion still needs sufficient current evidence under the shared workflow contract.

When independent review is one phase of a run-to-completion task, launch the reviewer asynchronously and wait for its result with the supported wait mechanism. Consume the findings and continue the active task instead of returning control at dispatch or review completion.

Do not change production code while reviewing. Hand P0 and P1 findings to `implement`; hand requirement violations whose cause is unclear to `investigate`.

End with `Next:` and one explicit action only when review was the user's whole request or work is genuinely blocked.
