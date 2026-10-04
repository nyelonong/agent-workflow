# Personal engineering workflow

## Sync

Inspect status and remotes when entering a repository, and fetch an existing upstream; if none exists, report that once and continue locally. Reuse current status and remote evidence; refresh when it may have changed, and recheck status before staging or committing. Never discard work, invent an upstream, rewrite pushed history, or force conflicts.

## Go

Start any Go work with the runtime's installed Go engineering skill. Reuse current repository evidence; refresh stale or uncertain facts and inspect only relevant module, code, tests, and CI requirements. Load detailed references only for network resilience, concurrency, nontrivial context lifetimes, runtime/performance problems, or transaction retry—not routine mapping or ordinary edits. Without the skill, respect the declared Go version and repository conventions.

## Commits and comments

Commit one verified logical unit with its tests, and only after an approval recorded for the exact reviewed state. Stage task-owned files only. Use a clear subject and at most two body lines. Never include internal IDs, AI attribution, `Co-Authored-By`, generated-with footers, or bot sign-offs.

Comments and docstrings are guilty by default: keep only legal headers, required compiler, build, code-generation, cgo and generated-file directives, non-obvious constraints or decisions supported by code or contract evidence, including external behavior and safely ignored errors, public API contracts, constraint issue or RFC links, and proven faulty or style-only suppressions. Existing comments receive the same keep-list test. Remove in-scope narration, banners, tutorials, commented-out code, and restatements. Prefer clearer code; retain useful rationale rather than force restructuring. Comments do not excuse correctness failures; treat correctness and safety suppressions as findings, not exemptions.

## Engineering

State material assumptions and trade-offs. Build only approved scope. Change only necessary code, callers, interfaces, tests, and documentation. Necessary local restructuring, renaming, and formatting are implementation discretion when they preserve approved behavior and contracts. Report unrelated defects; unrelated cleanup or material scope or contract changes require approval.

Prefer no change, existing code, standard library, platform/database features, installed dependencies, then new code. Inspect the real path and callers first.

Choose the simplest structure that makes behavior clear, keeps shared rules consistent, and supports meaningful testing. Allow genuinely simpler local duplication when the behavior can evolve independently, not duplication of one shared invariant. Shared logic or narrow consuming boundaries need a demonstrated clarity, consistency, maintenance, isolation, or behavioral-testing benefit; one production implementation can suffice. Do not add interfaces solely for call-count assertions, ceremony, or hypothetical implementations. Add concurrency, caches, dependencies, or generalization only for an approved need, evidence, or safety. Never weaken validation, data-loss prevention, security, privacy, authentication, authorization, accessibility, explicit requirements, or repository checks, and keep human judgment, credentials, and sensitive external actions under user control.

Async work needs a clear owner and an appropriate cancellation or shutdown path. Reuse existing lifecycle mechanisms. Failures must reach the caller or useful logs for intentionally best-effort work. Persistence, workflow frameworks, and extra design artifacts require an approved need; durable recovery is separate.

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

Do not claim completion from stale evidence or another agent's report. Use the shared workflow's evidence-reuse contract: after the last relevant change, establish applicable focused checks, consequential regression coverage, and the repository-required gate. Run missing or invalidated checks; phase changes and human approval alone do not invalidate executable evidence. Report failures, skips, evidence limits, and residual risks.

## Continuity and communication

Continue authorized work through closeout and commits under the shared workflow; no phase, passing check or task commit is a response boundary. Never end with intent-only text. Stop for completion, external block, required decision/approval, cancellation, requested report or an honest permitted checkpoint. Automatic context compaction is not a task boundary; recover missing detail from supported history or durable artifacts. A planned continuation checkpoint requires durable safe or honest partial state and does not relax requested-outcome continuity.

Use simple English names and prose; allow common terms and abbreviations. Explain mentioned IDs, tickets, blockers, and commit SHAs or omit them. Recommend and say why.

A local commit does not authorize a remote write. Every remote mutation requires explicit user approval for that exact current-task action, unless already supplied.

## Workflow

Act directly for read-only work. Production implementation requires explicit approval of bounded scope; a clear user request to implement that local change supplies it. Discussion, read-only requests, silence, tool permissions, and blanket edit permission are not scope approval. Default to direct parent execution; ask only for unresolved scope, authority, isolation, or cost decisions. Required specification/plan approval, independent review, exact-state pre-commit review, and sensitive/external authorization still apply.

A clear, routine single change needs no specification or plan. Fuzzy/multi-task entry follows the shared workflow. New/materially revised artifacts need approval. Approval authorizes the next phase only: specification approval authorizes planning; a single-change option must explicitly authorize implementation.

The shared `workflow` skill owns entry, artifact ownership, continuous closeout, logical review units, evidence reuse, and legitimate stops. Phase skills apply that contract; they are responsibilities, not a mandatory invocation chain.

Before committing, obtain one human decision on the complete actual uncommitted diff for the logical unit: approved criterion, callers/contracts, evidence, assumptions, trade-offs and risks. Never substitute a summary for the collected diff. Changed reviewed state needs fresh approval; failure, cancellation or supersession authorizes no commit.

Apply in-scope corrections and refresh affected evidence and review coverage. Material scope or approved-contract changes require renewed authorization. Immediately before staging, verify the exact-state approval fingerprint. Repeat executable checks only when evidence is missing or invalidated, not because approval occurred. A failed gate blocks; no automatic unbound chat fallback is permitted.

A consequential change can materially affect data/migrations, concurrency or async lifecycle, security, privacy, authentication, external systems, network or database behavior, public or user-visible contracts, cross-cutting behavior, or expensive/irreversible validation. Credible uncertainty is consequential.

Seek structured advice for consequential durable trade-offs. Consequential implementation and user decisions stay with the parent. Isolated writing is only on user request or for approved parallel writers needing separate checkouts.

Implementation consequence and independent-review necessity are separate decisions. Fresh independent review is mandatory only when a reachable defect could materially affect application runtime behavior or a public or user-visible contract; data integrity, loss, migrations, or database correctness; security, privacy, authentication, or authorization; concurrency, asynchronous ownership, cancellation, or resource lifetime; external systems through network calls, remote mutations, real messages, deployment, or material cost; or an operational authority or safety boundary such as approval and stop controls, destructive commands, secrets, or permission to push, deploy, delete, or contact real recipients.

Identify the actual reachable failure and material impact; language, backend terminology, or production use alone does not establish the boundary.

Documentation, skills, prompts, and configuration prose use parent verification and user review unless they control one of those boundaries. A reviewer remains optional when the user requests one or credible uncertainty benefits from an independent view. If a mandatory reviewer is unavailable, completion blocks until one is available or the user explicitly waives it; an author-only review does not satisfy the requirement. Direct user decisions block delegation and editing until resolved. High-risk seams retain focused parent inspection and integrated review. The shared workflow schedules required fresh read-only review, independent from the author, before the applicable delivery/safety boundary. Skills apply this boundary.

Local implementation scope does not authorize destructive, costly, security-sensitive, shared-state, private-data, consequential or external actions; obtain exact authority when missing, not again when already supplied.

## Conventions

Render existing absolute local paths as percent-encoded `file://` Markdown links. Use `id.afrani.app.{app_name}` for application bundle identifiers. Keep runtime-specific mechanics in the runtime adapter, not in the shared policy.
