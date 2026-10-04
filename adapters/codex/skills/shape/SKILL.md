---
name: shape
description: Turn an idea into an approved implementation specification. Explore unclear work with one decision at a time; synthesize clear requirements directly.
---

# Shape

Use explore when the request has unresolved scope, behavior, trade-off, or architecture decisions. Read the relevant repository context before proposing a direction.

Before enumerating decisions, check the ask itself. If you cannot state what the user wants in one sentence — who it is for, and what success looks like — the question, not the options, is the problem. Probe the intent first:

- Ask the smallest question that would let you state the intent, through a plain numbered question, with your best guess as the recommended option. A user reacts faster to a wrong guess than to a blank question.
- When the answer sounds like what a thoughtful answer should be — "scalable", "clean", "best practice" — rather than what the user wants, ask what they would build if they did not have to justify it, through a plain numbered question, with the concrete readings as options.
- Stop probing when you can predict the user's answer to the next question you would ask.

Probe answers shape the Goal and Non-goals; decisions shape the decision log. Resolve each required decision through a plain numbered question, one at a time and in dependency order. Recommend one concrete option and explain its trade-off; stop until the user answers.

Use synthesis when the requirements are already clear. Do not create clarification work merely to follow a process; draft the specification directly.

Apply deeper lenses only when the work needs them:

- For flow-heavy architecture or data work, use [the graph lens](references/graph-lens.md).
- For changes to a user's task or interaction, apply [the interface flow lens](references/interface-flow.md), including permissions, focus and empty/loading/error/denied states. Skip it when no interaction behavior changes.

Straightforward work should skip these lenses.

Write the draft to `<repository-root>/docs/specs/YYYY-MM-DD-<topic>.md`. Determine the repository root from the active project (for example, Git's top-level directory); if no repository root exists, use the current working directory. Do not commit the draft.

Apply the shared workflow's specification and design-coverage contract; do not copy a separate runtime template. Scale diagrams, ownership, contracts and evidence to material decisions. Record actual section references or justified not-applicable areas. Settle material unknowns before approval; missing external evidence or authority is an explicit blocker.

Before showing the draft, self-check it for unsupported assumptions and counterexamples. Fix findings inline.

Present the specification through the `task-review` `review-doc` gate, stating which phase approval authorizes under `AGENTS.md`. Follow the Codex `task-review` skill to await the same command and apply returned annotations before re-review. Do not also ask a numbered approval question for that document. A material revision requires approval again.

Specification approval authorizes planning; a single-change option must explicitly authorize implementation. Do not begin the next phase before its approval.
