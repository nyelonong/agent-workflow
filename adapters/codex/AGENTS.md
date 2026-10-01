# Codex adapter

Use a plain numbered question for required decisions: state the question, recommend one option with its reason, and stop until the user answers. Never treat a sandbox or command approval prompt as product or implementation approval.

For an HTML `task-review` decision, present the review URL in commentary and keep the turn active using the command's supported bounded wait mechanism. Await that same command, then act on its validated decision without asking the user to repeat it in chat. Follow the Codex `task-review` skill for result recovery and exact-state verification. A running command or background notification does not by itself guarantee a new turn after this one ends; do not promise automatic wake-up or install a continuation hook or Goal implicitly.

Invoke the personal `workflow` skill when the user asks for the workflow or invokes `$workflow`. For approved multi-task planning, spawn the `architect` agent at most once, and only when an independent view materially improves the plan, and treat its output as advisory. Spawn the `reviewer` agent only when the global independent-review boundary applies, the user requests it, or credible uncertainty justifies optional review. Ordinary parent work spawns no agent.

Codex-specific hooks, `config.toml`, sandbox and approval settings, plugins, MCP servers, and repository `AGENTS.md` files remain authoritative within their narrower scope.

This adapter provides no automatic model switching. Keep the current model unless the user authorizes a change through available native controls. Do not promise a first-edit handoff or emulate one by launching another writer.
