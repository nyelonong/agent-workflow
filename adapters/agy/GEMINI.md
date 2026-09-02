# Antigravity adapter

Use Antigravity's native user prompt for required decisions. Ask one concrete question, recommend one option, and stop until the user answers. Never treat a tool-permission prompt as product or implementation approval.

Load the personal `workflow` skill when the user invokes `/workflow` or asks to run the workflow. For approved multi-task planning, use only the `oracle` agent. Use the `reviewer` agent only when the global independent-review boundary applies, the user requests it, or credible uncertainty justifies optional review. Ordinary parent work needs no agent delegation.

Antigravity-specific hooks, permissions, MCP servers, and workspace `AGENTS.md` or `GEMINI.md` files remain authoritative within their narrower scope.
