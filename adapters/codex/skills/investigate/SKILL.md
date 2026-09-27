---
name: investigate
description: Diagnose a bug, flaky behavior, or unexpected result through evidence before proposing any fix.
---

# Investigate

State the expected behavior, observed behavior, affected environment, and known reproduction conditions before forming hypotheses. Read the relevant code, configuration, logs, tests, and recent changes before proposing a cause.

Keep ordinary investigation in the parent. Use bounded native read-only advice only when delegation is authorized and distinct source seams justify it. The parent personally reads the load-bearing evidence, owns the hypotheses, and synthesizes the diagnosis. Do not launch a generic agent tree merely because the investigation is broad.

Reproduce the issue when practical. Reduce it to the smallest failing behavior. If a suspected regression may propagate, inspect beyond direct callers through persisted or wire formats, downstream consumers, flags, lifecycle timing, pinned dependency behavior, and external boundaries. Keep observations, hypotheses, cleared risks, and unproved risks distinct. Test one hypothesis at a time with the smallest relevant evidence. For flaky behavior, run a bounded number of repeated attempts and report the occurrence count, conditions, timing, seed, or other variables that affect reproduction; one passing run does not establish absence.

When the issue cannot be reproduced, collect the available logs, versions, configuration, and affected paths. State the strongest supported hypothesis and the exact missing evidence. Do not guess a fix.

Ask one plain numbered question, with a recommendation and reason, only when repository evidence and the user request cannot resolve a required decision. Stop until the answer arrives.

Do not change production code while investigating.

If the user asked only for diagnosis, stop with the supported cause and end the response with `Next:` and one explicit action. If the active request asks for a fix, investigation is not a response boundary: once the cause is supported, load `implement` and continue within the existing approval. If implementation scope or execution path is not yet approved, obtain that approval before editing.
