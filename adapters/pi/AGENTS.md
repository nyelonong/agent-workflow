# Pi adapter

In Pi that skill is `go-engineering`.

In Pi, compaction is pi-vcc; recover dropped detail with `vcc_recall`.

In Pi, every question or approval in this file is an `ask_decision` call:
recommend one option and stop on a headless block or cancellation.

In Pi, `shape` and `plan` end with `ask_decision`. At the implementation
decision, offer direct implementation followed by `/interactive-review` versus
the full worker/reviewer workflow, and recommend direct interactive review for
ordinary work.

In Pi, structured advice is `/council`, and the isolated writer is one async
worker through `workflowScript` with one writer per checkout. Inside an RDG
Terminal Group, `rdg_tile` opens the shaping tile and the one-shot review tile;
outside RDG, `pi-subagents` serves those roles.

## Pi ownership

`agent-workflow` owns the canonical portable policy and this Pi adapter. The
installer renders both into its marked block in Pi's global instructions while
preserving unrelated material. Keep extensions in
`~/.pi/agent/extensions/` and experiments in `~/.pi/agent/wip/extensions/`. A
new LLM-callable tool starts deferred: classify it, obtain approval for its base
or capability-group placement, and record that provenance. Do not add a new
tool to `BASE_TOOLS` automatically. Skills, prompts, and command-only extensions
never consume capability-tool budget. The workflow is `/skill:workflow`;
`architect` and `reviewer` are `pi-subagents` roles.
