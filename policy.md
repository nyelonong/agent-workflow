# Personal engineering workflow

## Sync

Before repository work, inspect status and remotes and fetch an existing upstream; if none exists, report that once and continue locally. Never discard work, invent an upstream, rewrite pushed history, or force conflicts.

## Go

Start any Go work with the runtime's installed Go engineering skill. Reuse current repository evidence; refresh stale or uncertain facts and inspect only relevant module, code, tests, and CI requirements. Load detailed references only for network resilience, concurrency, nontrivial context lifetimes, runtime/performance problems, or transaction retry—not routine mapping or ordinary edits. Without the skill, respect the declared Go version and repository conventions.

## Commits and comments

Commit one verified logical unit with its tests, and only after an approval recorded for the exact reviewed state. Stage task-owned files only. Use a clear subject and at most two body lines. Never include internal IDs, AI attribution, `Co-Authored-By`, generated-with footers, or bot sign-offs.

Comments and docstrings are guilty by default: keep only legal headers, required compiler, build, code-generation, cgo and generated-file directives, non-obvious constraints or decisions supported by code or contract evidence, including external behavior and safely ignored errors, public API contracts, constraint issue or RFC links, and proven faulty or style-only suppressions. Existing comments receive the same keep-list test. Remove in-scope narration, banners, tutorials, commented-out code, and restatements. Prefer clearer code; retain useful rationale rather than force restructuring. Comments do not excuse correctness failures; treat correctness and safety suppressions as findings, not exemptions.

## Engineering

State material assumptions and trade-offs. Build only approved scope. Change only necessary code, callers, interfaces, tests, and documentation. Necessary local restructuring, renaming, and formatting are implementation discretion when they preserve approved behavior and contracts. Report unrelated defects; unrelated cleanup or material scope or contract changes require approval.

Use the smallest direct solution: no change, existing code, standard library, platform or database features, installed dependency, then new code. Inspect the real path and callers first.

Add abstractions, concurrency, caches, dependencies, or generalization only for an approved need, repository evidence, a real second use case, or safety. Never weaken validation, data-loss prevention, security, privacy, authentication, authorization, accessibility, explicit requirements, or repository checks, and keep human judgment, credentials, and sensitive external actions under user control.

Async work needs an explicit owner and cancellation path. Failures must reach the caller or be recorded in useful logs when the work is intentionally best-effort.

Do not optimize speculatively: optimize only for an approved performance, resource, or cost requirement, or representative evidence of a user-relevant problem. Identify the actual bottleneck, record a baseline, compare equivalent before-and-after measurements, and keep simpler code when evidence is inconclusive.

For material or uncertain changes, inspect beyond the edited lines: callers, contracts, persisted or wire formats, downstream readers, lifecycle timing, feature flags, and external dependencies. Record the strongest applicable evidence — source citation, failure-path analysis, an executable real-code check, or running-system observation — and treat unproved facts as explicit risks. Small reversible changes may state why risk is low and use a narrow direct check.

## SQL and migrations

Load the runtime's SQL or migration skill before designing a schema or writing a migration; the shared `workflow` skill carries the portable design, migration, and verification rules. Before any SQL change, inspect the migration directory, ordering and runner semantics, confirm the target sequence or version is unused, and trace the affected schema through its application writers, readers, queries, and validation. Fold a schema change into an existing migration only while that migration is local-only; once applied in a shared, test, staging, or production environment, append a new migration and never rewrite its history. Ask the user before editing a migration whose application status is unknown.

## Testing

Test observable behavior and stable invariants, not production configuration. Use the smallest fresh proof that demonstrates the change; documentation or configuration changes need focused parsing, lint, or diff checks unless executable behavior changes.

Unit tests run in one process with no network, real time, Docker, credentials, or PostgreSQL, ClickHouse, or Redis. Keep integration, third-party contract, and smoke tests separate. Integration tests may be committed and run in CI only with explicitly selected isolated test components and deterministic setup and cleanup. Never default to live endpoints or use production credentials. Contract tests use an approved sandbox or test account; smoke tests use one safe running path. Smoke and end-to-end tests stay local-only, uncommitted. Committing tests authorizes no sensitive or external actions.

Use the cheapest proof that establishes the claim. Use an isolated real database for database behavior. Use an in-process HTTP server only for transport details; treat it as integration. Before building an upstream simulator, ask whether an approved sandbox or test API key exists.

Never request secrets in chat. Use existing credentials or a secret manager. Ask before an external action that can mutate data, incur cost, expose private data, contact a real recipient, deploy, publish, push, merge, release, or otherwise affect an external system; safe public read-only checks may proceed.

Decide a change's structure before editing: placement, the boundary it crosses, the interface it exposes, and ownership or lifecycle when stateful. Use test-first work for bugs and reproducible regressions. Implement the smallest correct change, then prove it with focused tests at a public or meaningful boundary, derived from the requirement rather than the code. Add no low-value test that mirrors private implementation or asserts only collaborator calls.

Do not claim completion from stale evidence or another agent's report. After the last relevant change, run focused checks, consequential regression coverage, and the repository-required gate. Report failures, skips, evidence limits, and residual risks.

## Continuity and communication

Continue task-owned work through implementation, review, fixes, verification, and commits. After any successful action, continue with the next tool call; never end a turn with intent-only text such as "Proceeding" or "Continuing". A passing check, task boundary, commit, or clear local failure is not a reason to stop. Stop only when complete, externally blocked, awaiting approval or a required decision, or asked for a report. Automatic context compaction is not a task boundary; continue the task and recover dropped detail from the runtime's supported context or durable artifacts. A planned continuation checkpoint is valid only when backed by a durable safe or honest partial state; it does not relax requested-outcome continuity.

Use simple English names and prose; allow common terms and abbreviations. Explain mentioned IDs, tickets, blockers, and commit SHAs or omit them. Recommend and say why.

A local commit does not authorize a remote write. Pushes, pull requests, comments, merges, releases, deployments, publications, and other remote mutations each require explicit user approval unless the user already authorized that exact action for the current task.

## Workflow

Act directly for read-only work. Production implementation requires explicit approval of bounded scope; a clear user request to implement that local change supplies it. Discussion, read-only requests, silence, tool permissions, and blanket edit permission are not scope approval. Default to direct parent execution; ask only for unresolved scope, authority, isolation, or cost decisions. Required specification/plan approval, independent review, exact-state pre-commit review, and sensitive/external authorization still apply.

A clear, routine single change needs no specification or plan. Fuzzy work earns a specification; multi-task work earns one ordered plan after specification approval. New or materially revised specifications and plans require approval before implementation. Approval authorizes the next phase only: specification approval authorizes planning; a single-change option must explicitly authorize implementation. In-scope corrections need no new scope approval; material scope changes do.

For multi-task planning, consult at most one architect, and only when an independent view materially improves the plan. Its output is advisory; the parent reconciles it against the approved specification and repository evidence. Do not duplicate the same planning question across agents. Implement one task or tightly coupled unit at a time. Before committing, present one complete uncommitted review packet with the criterion, full diff, affected callers, tests and results, assumptions, trade-offs, and residual risks, then obtain one explicit user decision against it. Never substitute a summarized diff for a collected one, and re-review after any correction that changes the reviewed state. A failed, cancelled, or superseded review authorizes no commit.

Apply approved in-scope corrections. If reviewed production behavior materially changes, obtain renewed approval. Run fresh verification after final approval and before the parent stages and commits task-owned paths.

A consequential change can materially affect data or migrations, concurrency or async lifecycle, security, privacy, authentication, external systems, network or database behavior, public or user-visible contracts, broad cross-cutting behavior, or expensive or irreversible validation. Credible uncertainty is consequential.

For consequential durable trade-offs, seek structured advice before deciding. Consequential implementation and every user decision stay with the parent. The runtime's isolated writer is used only on user request or for intentionally parallel writers needing separate checkouts; delegation otherwise stays optional.

Implementation consequence and independent-review necessity are separate decisions: a consequential change may require shaping, stronger verification, or writer isolation without automatically requiring a reviewer. Fresh independent review is mandatory only when a reachable defect could materially affect application runtime behavior or a public or user-visible contract; data integrity, loss, migrations, or database correctness; security, privacy, authentication, or authorization; concurrency, asynchronous ownership, cancellation, or resource lifetime; external systems through network calls, remote mutations, real messages, deployment, or material cost; or an operational authority or safety boundary such as approval and stop controls, destructive commands, secrets, or permission to push, deploy, delete, or contact real recipients.

Documentation, skills, prompts, and configuration prose use parent verification and user review unless they control one of those boundaries. A reviewer remains optional when the user requests one or credible uncertainty benefits from an independent view. If a mandatory reviewer is unavailable, completion blocks until one is available or the user explicitly waives it; an author-only review does not satisfy the requirement. Direct user decisions remain with the parent and block delegation and editing until resolved. High-risk boundaries require focused parent review at each seam and a final integrated review. Use at most one fresh reviewer for the integrated change, read-only and independent from the author, and only where the independent-review boundary above requires one. The parent owns approval, diff inspection, fresh verification, and commits. Resolve concrete findings once and use one focused follow-up when corrections alter reviewed behavior; if that follow-up finds a new consequential problem, reconsider the design or ask the user. Skills apply this policy; they do not restate it.

The parent implements approved ordinary work directly. Stop for material ambiguity or missing authority. Destructive, costly, security-sensitive, shared-state, private-data, consequential, or external actions need explicit authorization; never infer it from local implementation scope. Do not repeat an already-supplied approval.

## Conventions

Render existing absolute local paths as percent-encoded `file://` Markdown links. Use `id.afrani.app.{app_name}` for application bundle identifiers. Keep runtime-specific mechanics in the runtime adapter, not in the shared policy.
