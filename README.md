# Personal agent workflow

Portable behavior shared by Claude Code and Google Antigravity so both follow the same visible approval, implementation, review, verification, commit, and remote-action flow as the personal Pi setup.

The package intentionally does not emulate Pi-only tools. Each runtime uses its native question and subagent interfaces.

## Antigravity

```sh
./install.sh install agy
./install.sh check agy
```

The installer manages one marked block in `~/.gemini/GEMINI.md`, the global `workflow` skill, and the `architect` and `reviewer` agents. It removes the old marked Galdr block from `~/.gemini/AGENTS.md` while preserving unrelated content.

## Pi

Pi's `~/.pi/agent/AGENTS.md` is the hand-written master of the rules. Sentences that
only mean something inside Pi sit between `<!-- pi-only:start -->` and
`<!-- pi-only:end -->`. `policy.md` in this repository is generated from that file:

```sh
./install.sh render pi   # regenerate policy.md after editing the Pi file
./install.sh check pi    # fails when policy.md is stale
```

Nothing writes into `~/.pi/agent`. Claude Code, Codex, and Antigravity consume the
generated `policy.md`; re-run `install codex` after a change, since Codex holds a
rendered copy.

## Codex

```sh
./install.sh install codex
./install.sh check codex
```

Codex documents no include directive for its instructions file, so the installer
renders `policy.md` inline into one marked block in `~/.codex/AGENTS.md`, keeping
everything outside the block. It also writes read-only `architect` and `reviewer`
agents to `~/.codex/agents/` (each starts with `# personal-workflow managed`) and
links the `workflow` skill into `~/.codex/skills/`. Re-run `install codex` after a
policy change; `check codex` reports a stale block.

## Claude Code

`~/Projects/personal/claude-config/bootstrap.sh --links-only` consumes the Claude adapter, workflow skill, and role definitions from this repository. Claude configuration remains owned by `claude-config`.

## Prewalk

`./install.sh install claude` adds the prewalk hooks to `~/.claude/settings.json`
beside existing hooks and links `~/.local/bin/claude-prewalk`. `./install.sh install agy`
adds a `prewalk` block to `~/.gemini/config/hooks.json` beside other blocks and links
`~/.local/bin/agy-prewalk`. `claude-prewalk -- <task>` and `agy-prewalk -- <task>` run a
strong model until its first edit, then resume the same session on a cheaper model. The
hooks are inert unless the wrapper armed them; subagents started during phase 1 share
the arming. Defaults for both wrappers come from flags, then
`~/.config/prewalk/config.json` (or under `XDG_CONFIG_HOME`), then shipped values:

```json
{
  "claude": { "from": "fable", "into": "sonnet", "permissionMode": "acceptEdits" },
  "agy": { "from": "claude-opus-4-6-thinking", "into": "gemini-3.8-flash-low", "mode": "accept-edits" }
}
```

The same file carries the Pi extension's `pi` section. A missing file means shipped
defaults; invalid JSON warns once and means shipped defaults. Specifications and plans
are kept locally under `docs/`, which is not tracked.

## Gate

```sh
python3 -m unittest discover -s tests -v
sh -n install.sh
python3 -m py_compile scripts/install.py
```
