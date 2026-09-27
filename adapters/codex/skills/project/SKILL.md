---
name: project
description: Project briefing — summary, recap, backlogs, and next recommendation
---
Give a status briefing on the current project. Use the user's optional focus (a subsystem, ticket, or date range); without it, cover the whole project. Read-only: never mutate Jira, git, or files.

## Gather

- Git: `git log --oneline -20` with dates, current branch and status, uncommitted changes, active worktrees, unpushed branches.
- Repo docs: README, CONTEXT.md, AGENTS.md, and `docs/` (specs, plans, research).
- Backlog source — detect which one this repo uses:
  - A mapped Jira project: query it read-only only when an existing connector is available and authorized (open issues, priorities, assignments).
  - In-repo backlog files: `TODO.md`, `docs/backlog*.md`, `docs/*-plan.md`, or similar.
  - GitHub issues, open PRs, or remote branches when the repo has a remote.
- Current session tasks when the runtime exposes them. Mark unavailable remote or session sources as evidence gaps; do not install integrations for this briefing.

## Report

1. **Summary** — one paragraph: what the project is and its current state.
2. **Recap** — recent work: last commits (with dates), in-flight branches, uncommitted changes, recent tasks.
3. **Backlog** — open items in priority order, each with its source (Jira key, file path, branch). State the source explicitly; never invent a backlog.
4. **What next** — one concrete recommendation for the next unit of work with reasoning, and one alternative.
5. **Risks and blockers** — stalled work, failing gates, unresolved decisions.

## Rules

- Every claim cites its source; mark anything inferred as inferred.
- Terminal-readable: short lines, plain ASCII, no images.
- End with `Next:` and one explicit action Zaki can take.
