---
description: Reset the agent's task state after a requirement, scope, or branch change
argument-hint: "[new context]"
---
Before continuing, restate the current task using this structure:

- Goal
- Acceptance criteria
- Non-goals
- Allowed repositories and files
- Target branch
- Required verification
- Prior assumptions or work that no longer apply

Use $@ as additional context. Do not modify files or run mutating commands. Use `ask_decision` to request approval or correction, then stop on cancellation.
