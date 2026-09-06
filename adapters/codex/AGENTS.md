# Codex adapter

Use a plain numbered question for required decisions: state the question, recommend one option with its reason, and stop until the user answers. Never treat a sandbox or command approval prompt as product or implementation approval.

Invoke the personal `workflow` skill when the user asks for the workflow or invokes `$workflow`. For approved multi-task planning, spawn the `oracle` agent exactly once and treat its output as advisory. Spawn the `reviewer` agent only when the global independent-review boundary applies, the user requests it, or credible uncertainty justifies optional review. Ordinary parent work spawns no agent.

Codex-specific hooks, `config.toml`, sandbox and approval settings, plugins, MCP servers, and repository `AGENTS.md` files remain authoritative within their narrower scope.
