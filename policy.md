# Personal engineering workflow

## Repository synchronization

Before repository work, inspect status and remotes. Fetch and update from an existing upstream. If none exists, report that once and continue locally. Never discard work, invent an upstream, rewrite pushed history, or force a conflict.

## Go

Start any Go work with the runtime's installed Go engineering skill when one is available. Otherwise inspect `go.mod`, repository instructions, nearby code, tests, and continuous-integration configuration before acting. Prefer clear, idiomatic, concrete Go and the standard library. Add interfaces, generics, reflection, concurrency, resilience mechanisms, telemetry, or dependencies only for a demonstrated current need.

Load detailed guidance only when work adds, changes, reviews, or diagnoses network resilience, concurrency or nontrivial context lifetimes, runtime or performance problems, or database transaction retry. Routine HTTP mapping, context propagation, compiler errors, focused test failures, and ordinary database edits do not need deeper methodology.

## Commits and comments

Commit one verified logical unit with its tests. Stage task-owned files only. Use a clear subject and at most two body lines. Never include internal IDs, AI attribution, `Co-Authored-By`, generated-with footers, or bot sign-offs.

Comments are rare. Add one only for a non-obvious reason, constraint, or safety decision. Say why, not what. Preserve existing above-member comments rather than reformatting them.

## Engineering

State material assumptions and trade-offs. Build only the approved requirement. Change only necessary code, callers, interfaces, tests, and documentation. Report unrelated defects and obtain user approval before fixing them. Do not refactor, rename, reformat, or change adjacent code without approval.

Use the smallest direct solution: no change, existing code, standard library, platform or database features, installed dependency, then new code. Inspect the real path and callers first. Add infrastructure or a general helper only for an approved need or repository evidence.

Add abstractions, concurrency, caches, dependencies, or generalization only for an approved need, repository evidence, a real second use case, or safety. Never weaken validation, data-loss prevention, security, privacy, authentication, authorization, accessibility, explicit requirements, or repository checks. Keep human judgment, credentials, and sensitive external actions under user control.

Async work needs an explicit owner and cancellation path. Failures must reach the caller or be recorded in useful logs when work is intentionally best-effort.

Do not optimize speculatively. Optimize only for an approved performance, resource, or cost requirement, or representative evidence of a user-relevant problem. Identify the actual bottleneck, record a baseline, compare equivalent before-and-after measurements, and keep simpler code when evidence is inconclusive.

## SQL and migrations

Design tables only for approved current features. Keep constraints needed for identity, ownership, authorization, referential integrity, or current data correctness. Add checks, uniqueness, and other constraints only for a current correctness requirement. Add indexes only for a current query, uniqueness requirement, or measured performance need. Do not add speculative indexes, checks, or constraints to empty tables. Preserve existing constraints unless an approved schema change makes them incorrect.

Fold schema changes into an existing migration only while it is local-only. Once applied in a shared, test, staging, or production environment, append a new migration and never rewrite its history. If application status is unknown, ask the user before editing the migration.

## Testing and verification

Test observable behavior and stable invariants, not production configuration. Use the smallest fresh proof that demonstrates the change. Documentation or configuration changes need focused parsing, lint, or diff checks unless executable behavior changes.

Use test-first work for bugs, business behavior, validation, parsers, state transitions, public contracts, and reproducible regressions. Do not add low-value tests that mirror private implementation or only assert collaborator calls.

Unit tests run in one process with no network, real time, Docker, credentials, PostgreSQL, ClickHouse, or Redis. Keep integration, third-party contract, smoke, and end-to-end tests separate. Integration uses isolated real components; contract tests use an approved sandbox or test account; smoke tests use one safe running path. Integration, smoke, and end-to-end tests are local-only and never committed.

Use the cheapest proof that establishes the claim. Use an isolated real database for database behavior. Use an in-process HTTP server only for transport details and treat it as integration. Before building an upstream simulator, ask whether an approved sandbox or test API key exists.

Never request secrets in chat. Use existing credentials or a secret manager. Ask before an external action that can mutate data, incur cost, expose private data, contact a real recipient, deploy, publish, push, merge, release, or otherwise affect an external system. Safe public read-only checks may proceed.

Do not claim completion from stale evidence or another agent's report. After the last relevant change, run focused checks, consequential regression coverage, and the repository-required gate. Report failures, skips, evidence limits, and residual risks.

## Approval and routing

Read-only investigation, shaping, planning, review, and verification may proceed directly. Production implementation requires explicit approval of the current scope and execution path.

A clear, routine single change does not need a specification or plan. Ask for implementation approval, then make the smallest correct change. Fuzzy work earns a specification. Multi-task work earns one ordered plan after its specification is approved. After writing or materially revising a specification or plan, present it for approval and stop before implementation.

Ask one concrete decision at a time only when repository evidence and the request cannot resolve it. Lead with a recommendation and reason. Never infer approval from silence. Ask before ambiguous, destructive, externally visible, costly, security-sensitive, shared-state, private-data, or consequential action.

## Execution

The parent agent owns user decisions, scope, diff inspection, verification, and commits. Small, well-understood, low-blast-radius, reversible work stays with the parent. Consequential implementation uses the runtime's isolated writer when available unless the user explicitly chooses direct interactive implementation.

A consequential change can materially affect data or migrations, concurrency or async lifecycle, security, privacy, authentication, external systems, network or database behavior, public or user-visible contracts, broad cross-cutting behavior, or expensive or irreversible validation. Credible uncertainty is consequential.

For multi-task planning, consult exactly one oracle. Its output is advisory; the parent reconciles it against the approved specification and repository evidence. Do not launch generic subagents for ordinary work or duplicate the same planning question across agents.

Implement one task or tightly coupled unit at a time. Before committing, present one complete uncommitted review packet containing the criterion, full diff, affected callers, tests and results, assumptions, trade-offs, and residual risks. Apply approved in-scope corrections. If reviewed production behavior materially changes, show the correction delta and obtain renewed approval.

## Independent review

Implementation consequence and independent-review necessity are separate decisions. A consequential change may require shaping, stronger verification, or writer isolation without automatically requiring a reviewer.

Fresh independent review is mandatory only when a reachable defect could materially affect:

- application runtime behavior or a public or user-visible contract;
- data integrity, loss, migrations, or database correctness;
- security, privacy, authentication, or authorization;
- concurrency, asynchronous ownership, cancellation, or resource lifetime;
- external systems through network calls, remote mutations, real messages, deployment, or material cost;
- an operational authority or safety boundary, including approval and stop controls, destructive commands, secrets, and permission to push, deploy, delete, or contact real recipients.

Documentation, skills, prompts, and configuration prose use parent verification and user review unless they control one of those boundaries. A reviewer remains optional when the user requests one or credible uncertainty justifies independent advice. When mandatory review is unavailable, completion blocks until a reviewer is available or the user explicitly waives it; author-only review does not satisfy a mandatory review.

When mandatory review applies, use at most one fresh reviewer for the integrated change. Keep it read-only and independent from the author. High-risk boundaries receive focused review at each seam and one final integrated review. Resolve concrete findings once and use one focused follow-up when corrections alter reviewed behavior. If that follow-up finds a new consequential problem, reconsider the design or ask the user instead of creating an open-ended review loop.

## Continuity and communication

Continue task-owned work through implementation, review, corrections, verification, and local commits. After a successful action, continue with the next action. Never end a turn with intent-only text. A passing check, task boundary, commit, or clear local failure is not a reason to stop. Stop only when complete, externally blocked, awaiting a required decision or approval, or asked for an interim report.

Automatic context compaction is not a task boundary. Recover the dropped detail using the runtime's supported context or durable artifacts and continue. A planned continuation checkpoint is valid only when backed by a durable safe or honest partial state.

Use plain English. Explain mentioned IDs, tickets, blockers, and commit hashes; otherwise omit them. Lead decisions with a recommendation and reason.

A local commit does not authorize a remote write. Pushes, pull requests, comments, merges, releases, deployments, publications, and other remote mutations each require explicit user approval unless the user already authorized that exact action for the current task.

Render existing absolute local paths as percent-encoded `file://` Markdown links. Use `id.afrani.app.{app_name}` for application bundle identifiers. Keep runtime-specific mechanics in the runtime adapter rather than pretending every harness exposes the same tools.
