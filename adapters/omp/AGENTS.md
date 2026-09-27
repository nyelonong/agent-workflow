# omp adapter

Use the `ask` tool for required decisions: give concrete options, mark the recommended index, and stop until the user answers. It is interactive-only and a cancelled `ask` is a refusal, not a decision. Never treat an edit, command, or sandbox permission prompt as product or implementation approval.

Load the personal `workflow` skill with `read` at `skill://workflow` when the user asks for the workflow, or let them invoke `/skill:workflow`; load `skill://task-review` before committing production changes. Inspect with `read`, `bash`, `grep`, and `glob`. For approved multi-task planning, dispatch the `task` tool at most once with an `architect` agent, when one is defined in `~/.omp/agent/agents/`, and only when an independent view materially improves the plan; its output is advisory. Dispatch `reviewer` only when the global independent-review boundary applies, the user requests it, or credible uncertainty justifies optional review, and use `scout` for read-only codebase research. Ordinary parent work dispatches no subagent.

omp-specific settings, hooks, extensions, MCP servers, and repository `.omp/` or standalone `AGENTS.md` files remain authoritative within their narrower scope.
