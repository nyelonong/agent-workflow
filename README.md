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

`policy/core.md` is the editable portable policy, and `adapters/pi/AGENTS.md`
contains Pi-only mechanics. `policy.md` is generated from the portable source.
`install pi` owns one marked block in `~/.pi/agent/AGENTS.md` and one exact entry
for each of the workflow skill and Pi prompt directory in `settings.json`; it
preserves unrelated content and refuses active default-root duplicates. It also
checks existing configured absolute or `~/` skill and prompt sources for the
managed names (resolving links and aliases); missing or cwd-relative sources
fail rather than being assumed safe. Pi package and extension resources are
not enumerable from this local settings updater, so migration checks discover
them afresh instead of claiming they were verified.

```sh
./install.sh render pi   # regenerate policy.md from policy/core.md
./install.sh install pi  # install only owned Pi resources
./install.sh check pi    # verify generated policy and managed Pi resources
```

Pi extensions remain Pi-owned. Claude Code, Codex, and Antigravity consume the
generated `policy.md`; their install and check commands fail when it is stale.
Re-run `install codex` after a policy change, since Codex holds a rendered copy.
Pi writes `AGENTS.md` and `settings.json` atomically only after complete semantic
preflight, but they are not one cross-file transaction. Use the Git-backed
migration/re-run path to recover an interruption. See [control-plane ownership](ARCHITECTURE.md).

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

```sh
./install.sh install claude
./install.sh check claude
```

These commands directly own the personal-workflow block in `~/.claude/CLAUDE.md`,
the workflow skill and role links, and the managed prewalk integration. `claude-config`
is only a delegating caller of this installer; it does not own this workflow content.

## Prewalk

`./install.sh install claude` adds the prewalk hooks to `~/.claude/settings.json`
beside existing hooks and links `~/.local/bin/claude-prewalk`; it is the direct
Claude workflow owner even when invoked by `claude-config`. `./install.sh install agy`
adds a `prewalk` block to `~/.gemini/config/hooks.json` beside other blocks and links
`~/.local/bin/agy-prewalk`. `claude-prewalk -- <task>` and `agy-prewalk -- <task>` run a
strong model until its first edit, then resume the same session on a cheaper model. The
hooks are inert unless the wrapper armed them; subagents started during phase 1 share
the arming. Defaults for each wrapper come from flags, then that agent's own flat
config file, then shipped values. `install claude` links `adapters/claude/prewalk.json`
to `~/.claude/prewalk.json` (or `$CLAUDE_CONFIG_DIR/prewalk.json`) and `install agy`
links `adapters/agy/prewalk.json` to `~/.gemini/prewalk.json`:

```json
{ "from": "fable", "into": "sonnet", "permissionMode": "acceptEdits" }
{ "from": "claude-opus-4-6-thinking", "into": "gemini-3.8-flash-low", "mode": "accept-edits" }
```

The Pi prewalk extension reads its own `~/.pi/agent/prewalk.json` (`autoArm`,
per-provider `starts`, per-provider `targets`), hand-written in the Pi repository like
its rules. A missing file means shipped defaults; invalid JSON warns once and means
shipped defaults. Specifications and plans are kept locally under `docs/`, which is not
tracked.

## Gate

```sh
python3 -m unittest discover -s tests -v
sh -n install.sh
python3 -m py_compile scripts/install.py
```
