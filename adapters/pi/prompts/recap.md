---
description: Recap session changes, workflow, usage, cost, and provider quota delta
argument-hint: "[focus or extra instructions]"
---
Recap the current Pi session using read-only evidence. Additional focus, if provided: ${@:-none}.

Do not modify files, commit, send notifications, or expose credentials, tokens, raw authorization URLs, or unrelated session content. Inspect the current session record, relevant repositories, completed delegated runs, and available provider quota sources before answering. Prefer `PI_SESSION_FILE` and `PI_SESSION_ID` when available; if either is unavailable, state the fallback used.

Use these accounting rules:

- Treat the earliest timestamp in the current Pi session record as the session start and the measurement timestamp as the end. Report elapsed wall-clock time.
- Summarize only changes and decisions attributable to this session. Distinguish committed changes, uncommitted changes, external actions, and pre-existing dirty work. Describe every commit SHA you mention.
- For usage, prefer Pi's authoritative session totals when accessible. Otherwise sum assistant usage records from the current session and separately add delegated runs spawned by this parent session.
- Count each top-level delegated workflow once. Exclude nested or resumed child status records that duplicate a parent workflow's reported usage.
- Report non-cached input, cache reads, cache writes, output, and total processed tokens. Treat reasoning tokens as a subset when the provider reports them that way; do not add them twice.
- Sum reported usage cost rather than recomputing historical prices. Separate main-agent and delegated-run cost, then show the combined estimate. State that subscription billing may differ from Pi's API-equivalent estimate.
- Never derive provider quota consumption from token counts or cost.

For provider quota buckets:

1. Find the earliest valid quota snapshot associated with this session start. A snapshot is valid only if it was actually captured then or comes from provider history tied to that timestamp.
2. Obtain a fresh read-only snapshot at recap time from each available active provider. Use documented or verified sources; for Codex, prefer the local app-server `account/rateLimits/read` method when available.
3. Match buckets by provider, stable limit identifier, window duration, and reset period.
4. Show before, after, and delta for used and remaining percentages, plus reset time. Express percentage deltas as percentage points.
5. If the reset period changed, label the bucket `reset during session` and do not present a misleading arithmetic delta.
6. If no valid before snapshot exists, write `unavailable` for before and delta, show the fresh after value, and explain that the current value cannot be reconstructed from session tokens.
7. Preserve opaque provider bucket identifiers exactly and explain what each identifier represents when known.

Structure the answer as:

1. **Outcome summary** - the user-visible result and final repository or runtime state.
2. **Changes** - files, commits, settings, and external actions attributable to this session.
3. **Workflow graph** - one readable plain-ASCII graph covering investigation, decisions, approvals, implementation or analysis, delegated workers and reviewers, failures, corrections, verification, and final disposition. Use only terminal-safe ASCII characters such as `+`, `-`, `|`, `[`, `]`, and `->`.
4. **Session metrics** - a compact table with start, end, elapsed time, token categories, and main/delegated/combined estimated cost.
5. **Provider quota delta** - a per-provider, per-bucket table with before, after, delta, remaining, reset time, and comparability status.
6. **Evidence and limitations** - exact evidence sources, unavailable measurements, possible double-counting avoided, and anything automation did not prove.

Keep the recap concise but complete. Use exact measurements when available, label estimates, and never invent a baseline or successful outcome.
