<!-- personal-workflow:claude:start -->
@__POLICY_PATH__

# Claude Code adapter

Use Claude Code's native question interface for required decisions. Ask one concrete question, recommend one option, and stop until the user answers. Never treat a permission prompt as product or implementation approval.

Load the personal `workflow` skill when the user invokes `/workflow` or asks to run the workflow. For approved multi-task planning, use the `architect` agent at most once, and only when an independent view materially improves the plan. Use the `reviewer` agent only when the global independent-review boundary applies, the user requests it, or credible uncertainty justifies optional review. Ordinary parent work needs no agent delegation. Task-review is optional; when the user requests it, delegate plan/diff gate preparation and invocation under the shared task-review skill, using native child model controls to always pass `model: "haiku"` within the current provider and runtime scope; this is Claude Code's fixed-model override of the shared GPT-6 Luna default. Do not compare prices or use alternate-model fallbacks; if unavailable or disallowed, stop rather than substituting another model. Keep the parent model unchanged; unavailable delegation/model selection/waiting blocks rather than falling back to the parent. The parent retains verification, corrections, consumption and commits.

For Go work, load `go-engineering` before design, implementation, review, debugging, or refactoring; read its references only when the task needs them.

Claude-specific hooks, permissions, status line, MCP servers, language skills, and project `CLAUDE.md` files remain authoritative within their narrower scope. `/graphify` uses the installed Graphify skill before anything else.
<!-- personal-workflow:claude:end -->
