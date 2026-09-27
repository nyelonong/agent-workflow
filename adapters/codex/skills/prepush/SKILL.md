---
name: prepush
description: Review the complete Git branch for correctness and PR quality before push
---

Review the current Git branch before it is pushed. Use the base ref and review context supplied in the user message. If no base is given, establish it from repository evidence using the precedence below.

The goal is not merely passing tests. Decide whether the branch is correct, focused, verified, and
presentable enough that its pull request will not look careless or mostly machine-generated.

## Reviewer stance

Use a seasoned Unix maintainer's lens: patient with real complexity and merciless toward code that
has not earned its place. Be blunt, technically conservative, and evidence-based.
For every addition, ask:

1. Which approved requirement or concrete risk needs this?
2. What breaks if it is deleted?
3. Could existing code, the standard library, or the platform do it already?
4. Does the repository already express this idea another way?
5. Is the test proving behavior, or only confirming the code's own mocks and assumptions?
6. Would an experienced maintainer understand why this exists six months from now?

Strict does not mean short, clever, or under-tested. Protect necessary complexity, clear names,
boundary validation, safety controls, useful documentation, and real regression coverage. A slop
finding must cite the code, name its maintenance or correctness cost, and offer a smaller credible
alternative. If no concrete cost can be shown, do not invent a finding.

## Boundaries

- Start without editing tracked or untracked files until the findings are complete; fetching remote
  refs is allowed.
- Never push, open or merge a pull request, rebase, amend, reset, force-update, discard changes, or
  clean the worktree.
- Preserve unrelated work. Distinguish branch commits, staged changes, unstaged changes, and
  untracked files.
- Follow repository approval rules before running commands that can change external data, expose
  private data, use credentials, or incur cost.
- Do not install dependencies or create a test service merely to complete the review; ask when
  required evidence is unavailable.

## 1. Establish the review range

1. Inspect repository status, current branch, upstream, remotes, worktrees, and recent commits.
2. Fetch the existing remote when available so the comparison is current; never pull or merge. If
   fetching fails, report that remote refs may be stale. Continue only when the base remains safe.
3. Determine the intended target in this order:
   - an explicit valid ref supplied by the user;
   - the base of an existing pull request when it can be read safely;
   - the remote default branch;
   - the current branch's upstream for unpushed default-branch commits.
4. If the target remains materially ambiguous, ask one plain numbered question with a recommendation and reason, and stop until answered.
5. Review commits from the merge base through `HEAD`, plus staged, unstaged, and untracked files.
   State each category separately so local files are never mistaken for push content.
6. Count commits in that range and inspect every subject. More than 20 commits is a P1 finding
   unless repository policy or an explicit approved exception justifies it. Temporary, `fixup!`,
   `squash!`, `WIP`, or meaningless subjects such as `update` or `fix stuff` are P1 at any count.
7. Read the applicable ticket, approved specification, plan, repository instructions, and changed
   code paths. Do not invent acceptance criteria when no source exists.

## 2. Review the integrated change

Load and follow the `review` skill, including its severity labels and consequence-based independent
review rule. Review the complete integrated diff, not only the latest commit. Check:

- Requested behavior, regressions, failure paths, boundary validation, and error handling.
- Security, privacy, authentication, authorization, secrets, unsafe logging, and data exposure.
- Data changes, migrations, transactions, concurrency, retries, idempotency, and external calls.
- Public interfaces, compatibility, configuration, deployment assumptions, and rollback concerns.
- Scope discipline: unrelated changes, duplicate logic, unnecessary services, wrappers, helpers,
  dependencies, configuration, generated files, or speculative abstractions.
- Test quality: observable behavior, important risks, correct test level, useful assertions, and no
  claim that mocks prove database, provider, network, or deployment behavior.
- Documentation, examples, changelog, generated output, lockfiles, and schema changes when relevant.
- Repository hygiene: debug output, commented-out code, placeholders, stale TODOs, dead code,
  misleading names, broad formatting churn, accidental binaries, editor files, or credentials.
- Commit hygiene: logical scope, honest messages, acceptable count, no temporary or accidental
  fixup commits, no machine attribution, and no history rewrite that would endanger already-pushed
  work. When a high count represents several independent changes, recommend splitting the pull
  request rather than blindly squashing everything.

### Interface and contract audit

For every added, removed, or changed function, method, request, response, event, command, or
configuration interface:

- Identify added, removed, renamed, or reordered parameters; changed types, optionality, defaults,
  variadic behavior, return values, result shapes, and errors.
- Trace all callers, implementations, adapters, mocks, and tests. Confirm none still rely on the old
  signature or silently ignore a new result or error.
- For HTTP, inspect paths, methods, path and query parameters, headers, request bodies, status
  codes, response fields, error envelopes, pagination, and content types.
- For JSON and other wire formats, inspect field names, tags, nullability, omitted fields, enum
  values, timestamps, numeric units, and backward-compatible decoding.
- Apply the same check to gRPC, GraphQL, events, CLI flags and output, configuration, schemas, and
  database-facing contracts when present.
- Confirm schemas, generated clients, examples, fixtures, documentation, and migration or versioning
  instructions remain accurate.
- Require contract or integration evidence for wire behavior that unit tests cannot prove.

An unapproved breaking change, missed caller, stale schema, or undocumented public request or
response change is P1 and makes the branch **NOT READY**.

Perform a hostile AI-slop pass over every changed hunk. The following are P1 findings unless the
requirement, repository convention, or safety need clearly justifies them:

- A new service, manager, helper, utility, wrapper, interface, package, configuration key, feature
  flag, dependency, compatibility layer, or file with no demonstrated present use.
- An abstraction with one caller or implementation that only renames or forwards existing behavior.
- Pass-through layers, nested adapters, generic factories, speculative extension points, or fallback
  paths for versions and environments the repository does not support.
- Repeated validation of impossible internal states, broad exception handling, or error wrapping
  that hides the useful cause instead of improving recovery or context.
- Apply the `no-comments` keep list within this review in audit-only mode for changed comments, docstrings, and suppressions. It
  applies the strict keep list, protects compiler, build, code-generation, cgo, and generated-file
  directives, and must not edit or mutate files. Preserve the existing correction approval gate
  for accepted findings.
- Copied boilerplate, repeated branches, needless conversion between equivalent types, verbose code
  that replaces a direct language or platform feature, or a dependency for a standard-library task.
- Tests that only confirm mocks or implementation steps, duplicate production configuration, use the
  wrong test level, build an unnecessary fake service, repeat equivalent cases, or cannot fail for a
  meaningful regression.
- Unrelated cleanup, broad formatting churn, renamed symbols without need, dead code, placeholders,
  stale TODOs, debug output, commented-out code, accidental files, or generated artifacts with no
  documented source.
- Vague commit messages, unresolved fixup commits, inflated PR prose, machine attribution, or a
  large diff whose size cannot be traced to the approved requirement.

Challenge every new concept, but do not demand deletion merely to reduce line count. Prefer boring
code that matches the repository over clever compression or a new personal style.

For material or uncertain changes, inspect beyond the diff through callers, contracts, persisted or
wire formats, downstream readers, lifecycle timing, feature flags, and external dependencies when
applicable. Record the load-bearing safety facts, strongest applicable evidence, confirmed and cleared
checks, and unproved risks before deciding branch readiness.

## 3. Verify branch-wide readiness

Load and follow the `verify` skill. Because this is a branch-wide readiness claim, run the
repository's documented full gate when it is safe and available. Otherwise run the widest relevant
existing checks without inventing new infrastructure: formatting or diff checks, type checking,
lint, tests, build, and required generated-file checks.

Keep evidence honest and separate:

- Unit tests do not prove database, network, or deployment behavior.
- Integration tests must name the real components they exercised.
- Third-party contract tests require an approved sandbox or test account.
- Smoke tests must name the running service and path exercised.
- Record failures, skipped checks, missing credentials, unavailable services, and what remains
  unproved.

Recheck status after validation and report any files created or changed by the commands.

## 4. Report one verdict

Use exactly one verdict:

- **READY TO PUSH** — no blocking findings; every new concept has a present justification; the
  intended branch change is committed, focused, free of obvious AI slop, and supported by the
  required fresh evidence.
- **NOT READY** — correctable P0 or P1 findings, missing intended commits, accidental files, or
  clear pull-request quality problems remain.
- **BLOCKED** — the base, requirement, or required validation cannot be established safely.

Report:

1. Verdict and one-sentence reason.
2. Review base, commit range, and separate local-change categories.
3. Complete prioritized findings with file and line evidence.
4. Non-blocking risks or polish items.
5. Commands run and their fresh results.
6. What the evidence does not prove.
7. When ready, a concise suggested pull-request title, summary, and honest test plan.

Do not hide findings behind a summary and do not report speculative concerns as facts.

## 5. Corrections

When the verdict is **NOT READY**, ask one plain numbered question recommending grouped correction of P0 and P1 findings, with its reason; the user may select narrower corrections or report-only. Do not edit before that approval. Load and follow
the `implement` skill for accepted corrections, handle them together, run focused verification,
then perform one follow-up review. If the follow-up finds a new consequential problem, stop and
reconsider or ask the user instead of starting another automatic correction loop.

Even after a **READY TO PUSH** verdict, never push. The user owns that external action.
