---
description: Run the Jira-only Galdr workflow for one ticket
argument-hint: "<ISSUE-KEY>"
---

Run the Jira-ticket Galdr workflow for `$1`.

## Input and Jira intake

- Treat `$1` as `JiraIssueKey`. If it is empty or not a Jira issue key, use `ask_decision` to obtain the issue key and stop. If `${@:2}` is non-empty, use `ask_decision` to request a single issue key and stop.
- Retrieve the issue through Atlassian using read-only operations only. Read its description, explicit acceptance criteria where present, comments, linked issues, and attachments before shaping.
- Report inaccessible Jira material explicitly. Never infer its contents.
- Never create, edit, comment on, transition, or otherwise mutate Jira.

## Scope and technical discovery

- The supplied Jira issue is the sole source of product scope and acceptance criteria.
- Linked Jira issues provide context, dependencies, and blockers only. Do not silently add them to the implementation scope.
- Repository rules, verified code, and explicit workspace scope constrain execution but do not create product requirements. Report an irreconcilable conflict as a blocker.
- Identify the target repository or repositories through workspace and code investigation. In the Cekat workspace, run `./scan-repos.sh` before workspace-wide investigation.
- If repository mapping remains uncertain, use `ask_decision` to request the mapping and stop; do not guess. When several repositories are mapped, use `ask_decision` to choose the primary repository root for local Jira artifacts.
- Technical work not stated as a Jira acceptance criterion is permitted only when demonstrably necessary to implement or safely verify a stated requirement. Record it as an implementation detail, not an acceptance criterion. Use `ask_decision` before a nonessential refactor or behaviour change.

## Missing or unclear requirements

- Block shaping when a required Jira source is inaccessible or when the ticket is ambiguous, incomplete, or contradictory.
- Resolve focused clarification questions through `ask_decision`, one at a time and in dependency order. Give evidence-backed options and a recommendation first.
- If the questions cannot be resolved, write a ready-to-paste local Jira-comment draft at `<repository-root>/docs/$1-clarification.md` and stop. Do not make assumptions.

## Jira workflow

1. Once the Jira evidence is sufficient, use `shape` and write a local shaped spec at `<repository-root>/docs/specs/YYYY-MM-DD-$1-spec.md`.
2. The spec must cite the Jira issue URL/key and include a compact traceability table mapping every local requirement or acceptance item to its Jira source location. Omit and raise as a blocker any item without a Jira source.
3. Do not add acceptance criteria, improvements, or creative scope beyond Jira evidence.
4. Stop after the shaped spec and use `ask_decision` for explicit approval.
5. After spec approval, write an implementation plan at `<repository-root>/docs/$1-plan.md`. Retain the Jira URL/key, include per-item Jira-source traceability, and use Jira-keyed filenames for every generated artifact.
6. Stop after the plan and use `ask_decision` for explicit approval before implementation.
7. After plan approval, use `implement`, then `verify`, and perform a fresh read-only review. Follow all repository ownership, TDD, test, gate, and Git rules.

## Implementation blockers

- Stop the affected implementation for a technical blocker, Jira contradiction, or uncovered requirement.
- State what was tried, what is needed to continue, and evidence-backed options with a recommendation first. Use `ask_decision` for a required user decision.
- When Jira clarification or change is needed, write a ready-to-paste comment draft at `<repository-root>/docs/$1-clarification.md`. Do not invent a workaround, expand scope, or write to Jira.

## Completion

After all work is freshly verified and reviewed, provide an evidence-backed completion summary and write a ready-to-paste completion-comment draft at `<repository-root>/docs/$1-completion.md`. Both must cover:

- implemented Jira requirements,
- verification commands and results,
- deliberate exclusions,
- remaining blockers.

Do not post the comment, transition the issue, or make any other remote Jira write.
